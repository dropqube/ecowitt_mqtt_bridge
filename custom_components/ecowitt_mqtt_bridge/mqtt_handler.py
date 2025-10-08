from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, Optional, Tuple

from homeassistant.core import HomeAssistant
from homeassistant.components import mqtt
from homeassistant.util.unit_system import METRIC_SYSTEM, IMPERIAL_SYSTEM
from homeassistant.const import UnitOfTemperature, UnitOfPressure, UnitOfSpeed, UnitOfLength

from .lan_mapper import EcowittLanMapper

_LOGGER = logging.getLogger(__name__)

# ----------------------------
# Helpers & unit conversion
# ----------------------------

_RE_KV = re.compile(r"([^=&]+)=([^&]*)")

def parse_flat_payload(raw: str) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for m in _RE_KV.finditer(raw):
        k = m.group(1)
        v = m.group(2)
        out[k] = v
    return out

def as_float(v: Any) -> Optional[float]:
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip()
    s = s.replace(",", ".")
    try:
        return float(s)
    except Exception:
        # Strings wie "0.29 kPa" → nur Zahl extrahieren
        m = re.search(r"[-+]?\d+(\.\d+)?", s)
        if m:
            try:
                return float(m.group(0))
            except Exception:
                return None
        return None

def ha_unit_system(hass: HomeAssistant) -> str:
    return "metric" if hass.config.units is METRIC_SYSTEM else "imperial"

def conv_temp_to_ha(hass: HomeAssistant, f_value: Optional[float]) -> Tuple[Optional[float], str]:
    if f_value is None:
        return None, UnitOfTemperature.CELSIUS
    if ha_unit_system(hass) == "metric":
        c = (f_value - 32.0) * 5.0 / 9.0
        return round(c, 2), UnitOfTemperature.CELSIUS
    return round(f_value, 2), UnitOfTemperature.FAHRENHEIT

def conv_wind_to_ha(hass: HomeAssistant, mph: Optional[float]) -> Tuple[Optional[float], str]:
    if mph is None:
        return None, UnitOfSpeed.MILES_PER_HOUR
    if ha_unit_system(hass) == "metric":
        ms = mph * 0.44704
        return round(ms, 2), UnitOfSpeed.METERS_PER_SECOND
    return round(mph, 2), UnitOfSpeed.MILES_PER_HOUR

def conv_rain_to_ha(hass: HomeAssistant, inch: Optional[float]) -> Tuple[Optional[float], str]:
    if inch is None:
        return None, UnitOfLength.INCHES
    if ha_unit_system(hass) == "metric":
        mm = inch * 25.4
        return round(mm, 2), UnitOfLength.MILLIMETERS
    return round(inch, 2), UnitOfLength.INCHES

def conv_pressure_to_ha(hass: HomeAssistant, inhg: Optional[float]) -> Tuple[Optional[float], str]:
    if inhg is None:
        return None, UnitOfPressure.INHG
    if ha_unit_system(hass) == "metric":
        hpa = inhg * 33.8638866667
        return round(hpa, 1), UnitOfPressure.HPA
    return round(inhg, 3), UnitOfPressure.INHG

# ----------------------------
# Discovery field defs
# ----------------------------

AGGREGATE_SENSORS = [
    # (key, friendly, dev_class, state_class, convert_fn)
    ("tempf",         "Outdoor Temperature",  "temperature",  "measurement", conv_temp_to_ha),
    ("humidity",      "Outdoor Humidity",     "humidity",     "measurement", lambda h,v: (as_float(v), "%")),
    ("windspeedmph",  "Wind Speed",           None,           "measurement", conv_wind_to_ha),
    ("windgustmph",   "Wind Gust",            None,           "measurement", conv_wind_to_ha),
    ("winddir",       "Wind Direction",       None,           None,          lambda h,v: (as_float(v), "°")),
    ("uv",            "UV Index",             None,           "measurement", lambda h,v: (as_float(v), None)),
    ("solarradiation","Solar Radiation",      None,           "measurement", lambda h,v: (as_float(v), "W/m²")),
    ("vpd",           "VPD",                  None,           "measurement", lambda h,v: (as_float(v), "kPa")),
    ("rainratein",    "Rain Rate",            None,           "measurement", conv_rain_to_ha),
    ("dailyrainin",   "Rain (Daily)",         None,           "total_increasing", conv_rain_to_ha),
]

GATEWAY_SENSORS = [
    ("tempinf",    "Indoor Temperature",  "temperature",  "measurement", conv_temp_to_ha),
    ("humidityin", "Indoor Humidity",     "humidity",     "measurement", lambda h,v: (as_float(v), "%")),
    ("baromabsin", "Pressure (Absolute)", "pressure",     "measurement", conv_pressure_to_ha),
    ("baromrelin", "Pressure (Relative)", "pressure",     "measurement", conv_pressure_to_ha),
]

# ----------------------------
# Runtime
# ----------------------------

class EcowittBridgeRuntime:
    """Subscribed auf Ecowitt-Uploads und published HA Discovery inkl. Geräte-Zuordnung."""

    def __init__(
        self,
        hass: HomeAssistant,
        in_topic: str,
        discovery_prefix: str,
        state_prefix: str,
        use_local_api: bool = False,
        gateway_base_url: str = "",
        lan_timeout: float = 5.0,
        map_refresh_sec: int = 600,
        publish_lan_common: bool = False,  # aktuell ungenutzt, Option für später
    ) -> None:
        self.hass = hass
        self.in_topic = in_topic
        self.discovery_prefix = discovery_prefix.rstrip("/")
        self.state_prefix = state_prefix.rstrip("/")
        self._unsub = None

        self._lan: EcowittLanMapper | None = None
        if use_local_api and gateway_base_url:
            self._lan = EcowittLanMapper(gateway_base_url, lan_timeout, map_refresh_sec)

    async def async_start(self) -> None:
        async def _msg_received(topic: str, payload: bytes, qos: int) -> None:
            text = payload.decode(errors="ignore")
            raw = parse_flat_payload(text)
            _LOGGER.debug("[RECV] topic=%s bytes=%d sample='%s...'", topic, len(payload), text[:60])
            await self._handle_flat_gateway(raw)

        self._unsub = await mqtt.async_subscribe(self.hass, self.in_topic, _msg_received, qos=0)
        _LOGGER.info("[MQTT] Subscribed to %s", self.in_topic)
        if self._lan:
            await self._lan.async_start()

    async def async_stop(self) -> None:
        if self._unsub:
            self._unsub()
            self._unsub = None
        if self._lan:
            await self._lan.async_stop()

    # ------------------------
    # Device helpers
    # ------------------------

    def _gw_device(self, passkey: str) -> Dict[str, Any]:
        return {
            "identifiers": [f"ecowitt_gateway_{passkey}"],
            "manufacturer": "Ecowitt",
            "model": "Gateway",
            "name": f"Ecowitt Gateway {passkey[-6:]}",
        }

    def _sensor_device(self, passkey: str, hwid: str, sname: str) -> Dict[str, Any]:
        return {
            "identifiers": [f"ecowitt_sensor_{passkey}_{hwid}"],
            "manufacturer": "Ecowitt",
            "model": sname,
            "name": f"{sname} ({hwid})",
            "via_device": f"ecowitt_gateway_{passkey}",
        }

    def _pick_outdoor_sensor_device(self, passkey: str) -> Dict[str, Any]:
        """Bevorzugt WH90 > WH69 mit idst == '1' (outdoor).
        Fallback: Gateway-Device.
        """
        gw_dev = self._gw_device(passkey)
        if not self._lan:
            return gw_dev

        sensors = self._lan.sensors()
        chosen = None
        # Prioritätenliste
        for hwid, s in sensors.items():
            if s.idst != "1":
                continue
            if s.img.lower() == "wh90":
                chosen = s
                break
        if not chosen:
            for hwid, s in sensors.items():
                if s.idst == "1" and s.img.lower() == "wh69":
                    chosen = s
                    break
        if chosen:
            return self._sensor_device(passkey, chosen.hwid, chosen.name)
        return gw_dev

    # ------------------------
    # Discovery publish
    # ------------------------

    async def _publish_cfg(
        self,
        device: Dict[str, Any],
        unique_id: str,
        name: str,
        unit: Optional[str],
        dev_class: Optional[str],
        state_class: Optional[str],
    ) -> None:
        comp = "sensor"
        obj_id = unique_id
        topic = f"{self.discovery_prefix}/{comp}/{obj_id}/config"
        payload = {
            "name": name,
            "uniq_id": unique_id,
            "stat_t": f"{self.state_prefix}/{obj_id}/state",
            "avty_t": f"{self.state_prefix}/availability",
            "dev": device,
        }
        if unit:
            payload["unit_of_meas"] = unit
        if dev_class:
            payload["dev_cla"] = dev_class
        if state_class:
            payload["stat_cla"] = state_class

        await mqtt.async_publish(self.hass, topic, json.dumps(payload), retain=True)
        _LOGGER.info("[DISCOVERY] %s → %s", topic, name)

    async def _publish_val(self, unique_id: str, value: Any) -> None:
        topic = f"{self.state_prefix}/{unique_id}/state"
        await mqtt.async_publish(self.hass, topic, json.dumps(value), retain=True)

    # ------------------------
    # Main handler
    # ------------------------

    async def _handle_flat_gateway(self, raw: Dict[str, Any]) -> None:
        passkey = (raw.get("PASSKEY") or "unknown").lower()

        # Indoor/Gateway-Werte → Gateway-Device
        gw_dev = self._gw_device(passkey)
        for key, friendly, devcls, stcls, conv in GATEWAY_SENSORS:
            if key not in raw:
                continue
            val = as_float(raw.get(key))
            v2, unit = conv(self.hass, val)
            uid = f"ecowitt_{passkey}_{key}"
            await self._publish_cfg(gw_dev, uid, friendly, unit, devcls, stcls)
            await self._publish_val(uid, v2)

        # Outdoor/Aggregate → wenn möglich an Outdoor-Device hängen (WH90/WH69), sonst Gateway
        out_dev = self._pick_outdoor_sensor_device(passkey)
        for key, friendly, devcls, stcls, conv in AGGREGATE_SENSORS:
            if key not in raw:
                continue
            raw_val = raw.get(key)
            # Spezialfälle:
            if key in ("rainratein", "dailyrainin"):
                v2, unit = conv(self.hass, as_float(raw_val))
            elif key in ("tempf",):
                v2, unit = conv(self.hass, as_float(raw_val))
            elif key in ("windspeedmph", "windgustmph"):
                v2, unit = conv(self.hass, as_float(raw_val))
            elif key in ("solarradiation", "uv", "winddir", "humidity", "vpd"):
                v2, unit = conv(self.hass, raw_val)
            else:
                v2, unit = as_float(raw_val), None

            uid = f"ecowitt_{passkey}_{key}"
            await self._publish_cfg(out_dev, uid, friendly, unit, devcls, stcls)
            await self._publish_val(uid, v2)
