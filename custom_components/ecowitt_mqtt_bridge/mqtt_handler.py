from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from homeassistant.core import HomeAssistant
from homeassistant.components import mqtt
from homeassistant.const import UnitOfTemperature as UTemp

_LOGGER = logging.getLogger(__name__)


def _try_float(x: Any) -> Optional[float]:
    try:
        if isinstance(x, str):
            x = x.replace(",", ".")
        return float(x)
    except Exception:
        return None


# Key, FriendlyName, unit_placeholder, device_class, state_class, extra
AGGREGATE_SENSORS = [
    ("tempf",        "Outdoor Temperature",     None, "temperature", "measurement", None),
    ("humidity",     "Outdoor Humidity",        "%",  "humidity",    "measurement", None),
    ("windspeedmph", "Wind Speed",              None, None,          "measurement", None),
    ("windgustmph",  "Wind Gust",               None, None,          "measurement", None),
    ("winddir",      "Wind Direction",          "°",  None,          "measurement", None),
    ("uv",           "UV Index",                None, None,          "measurement", None),
    ("solarradiation","Solar Radiation",        "W/m²", None,        "measurement", None),
    ("vpd",          "VPD",                     "kPa", None,         "measurement", None),
    ("rainratein",   "Rain Rate",               None, None,          "measurement", None),
    ("dailyrainin",  "Rain (Daily)",            None, None,          "total_increasing", None),
    ("baromrelin",   "Pressure (Relative)",     None, "pressure",    "measurement", None),
    ("baromabsin",   "Pressure (Absolute)",     None, "pressure",    "measurement", None),
]


class EcowittBridgeRuntime:
    """
    Minimaler Runtime-Teil:
    - Abonniert Ecowitt-Flach-Uploads (GW3000 MQTT)
    - Wandelt Einheiten passend zu HA (oder Override)
    - Veröffentlicht MQTT Discovery + States
    """
    def __init__(
        self,
        hass: HomeAssistant,
        discovery_prefix: str,
        state_prefix: str,
        in_topic: str,
        use_local_api: bool,
        gateway_base_url: str,
        lan_timeout: float,
        map_refresh_sec: int,
        publish_lan_common: bool,
        unit_temp: str | None = None,   # "C" | "F" | None
        unit_wind: str | None = None,   # "m/s" | "km/h" | "mph" | None
        unit_rain: str | None = None,   # "mm" | "in" | None
        unit_press: str | None = None,  # "hPa" | "inHg" | None
    ) -> None:
        self.hass = hass
        self.discovery_prefix = discovery_prefix
        self.state_prefix = state_prefix
        self.in_topic = in_topic
        self.use_local_api = use_local_api
        self.gateway_base_url = gateway_base_url.rstrip("/")
        self.lan_timeout = lan_timeout
        self.map_refresh_sec = max(30, map_refresh_sec)
        self.publish_lan_common = publish_lan_common

        self._unit_temp = unit_temp or None if unit_temp else None
        self._unit_wind = unit_wind or None if unit_wind else None
        self._unit_rain = unit_rain or None if unit_rain else None
        self._unit_press = unit_press or None if unit_press else None

        self._unsub = None

    # --------- Ziel-Einheiten bestimmen (HA-System vs. Override) ---------
    def _target_units(self):
        ha_units = self.hass.config.units
        tgt_temp = "C" if ha_units.temperature_unit == UTemp.CELSIUS else "F"
        tgt_wind = "m/s" if ha_units.is_metric else "mph"
        tgt_rain = "mm" if ha_units.is_metric else "in"
        tgt_press = "hPa" if ha_units.is_metric else "inHg"
        if self._unit_temp in ("C", "F"):
            tgt_temp = self._unit_temp
        if self._unit_wind in ("m/s", "km/h", "mph"):
            tgt_wind = self._unit_wind
        if self._unit_rain in ("mm", "in"):
            tgt_rain = self._unit_rain
        if self._unit_press in ("hPa", "inHg"):
            tgt_press = self._unit_press
        return tgt_temp, tgt_wind, tgt_rain, tgt_press

    # --------- Umrechnungen ---------
    def c2f(self, x): return (float(x) * 9.0 / 5.0) + 32.0
    def f2c(self, x): return (float(x) - 32.0) * 5.0 / 9.0
    def ms2kmh(self, x): return float(x) * 3.6
    def ms2mph(self, x): return float(x) * 2.23693629
    def mph2ms(self, x): return float(x) * 0.44704
    def inhg2hpa(self, x): return float(x) * 33.8638866667
    def hpa2inhg(self, x): return float(x) / 33.8638866667
    def inch2mm(self, x): return float(x) * 25.4
    def mm2in(self, x): return float(x) / 25.4

    def _conv_temp(self, val, src):
        ttemp, _, _, _ = self._target_units()
        v = float(val)
        if src == "F":
            v = self.f2c(v)
        v_out = v if ttemp == "C" else self.c2f(v)
        unit = "°C" if ttemp == "C" else "°F"
        return v_out, unit

    def _conv_wind(self, val, src):
        _, twind, _, _ = self._target_units()
        v = float(val)
        v_ms = self.mph2ms(v) if src == "mph" else v
        if twind == "m/s":
            out = v_ms
        elif twind == "km/h":
            out = self.ms2kmh(v_ms)
        else:
            out = self.ms2mph(v_ms)
        return out, twind

    def _conv_rain(self, val, src):
        _, _, train, _ = self._target_units()
        v = float(val)
        v_mm = self.inch2mm(v) if src == "in" else v
        out = v_mm if train == "mm" else self.mm2in(v_mm)
        unit = "mm" if train == "mm" else "in"
        return out, unit

    def _conv_press(self, val, src):
        _, _, _, tpress = self._target_units()
        v = float(val)
        v_hpa = self.inhg2hpa(v) if src == "inHg" else v
        out = v_hpa if tpress == "hPa" else self.hpa2inhg(v_hpa)
        unit = "hPa" if tpress == "hPa" else "inHg"
        return out, unit

    # --------- Lifecycle ---------
    async def async_start(self):
        async def _msg_received(topic: str, payload: bytes, qos: int) -> None:
            txt = payload.decode("utf-8", errors="ignore")
            _LOGGER.debug("[RECV] topic=%s bytes=%s sample=%r", topic, len(payload), txt[:64])
            raw = dict(x.split("=", 1) for x in txt.split("&") if "=" in x)
            await self._handle_flat_gateway(raw)

        self._unsub = await mqtt.async_subscribe(self.hass, self.in_topic, _msg_received, qos=0)
        _LOGGER.info("[MQTT] Subscribed to %s", self.in_topic)

    async def async_stop(self):
        if self._unsub:
            self._unsub()
            self._unsub = None

    # --------- Publish Helpers ---------
    async def _publish_cfg(self, device: Dict[str, Any], unique_id: str, name: str,
                           unit: Optional[str], devcls: Optional[str], stcls: Optional[str]):
        cfg_topic = f"{self.discovery_prefix}/sensor/{unique_id}/config"
        payload: Dict[str, Any] = {
            "name": name,
            "unique_id": unique_id,
            "state_topic": f"{self.state_prefix}/{unique_id}/state",
            "device": device,
        }
        if unit:
            payload["unit_of_measurement"] = unit
        if devcls:
            payload["device_class"] = devcls
        if stcls:
            payload["state_class"] = stcls
        await mqtt.async_publish(self.hass, cfg_topic, json_dumps(payload), qos=0, retain=True)

    async def _publish_val(self, unique_id: str, value: Any):
        await mqtt.async_publish(self.hass, f"{self.state_prefix}/{unique_id}/state", str(value), qos=0, retain=True)

    def _gw_device(self, passkey: str) -> Dict[str, Any]:
        return {
            "identifiers": [f"ecowitt_gateway_{passkey}"],
            "manufacturer": "Ecowitt",
            "model": "Gateway",
            "name": f"Ecowitt Gateway {passkey[-6:]}",
        }

    # --------- Verarbeitung der flachen Gateway-Uploads (MQTT) ---------
    async def _handle_flat_gateway(self, raw: Dict[str, Any]):
        passkey = (raw.get("PASSKEY") or "unknown").lower()
        gw_dev = self._gw_device(passkey)

        for key, friendly, _unit_unused, devcls, stcls, _ in AGGREGATE_SENSORS:
            if key not in raw:
                continue
            sval = raw[key]
            v2 = None
            unit = None

            if key in ("tempf", "tempinf"):
                v = _try_float(sval)
                if v is not None:
                    v2, unit = self._conv_temp(v, "F")
            elif key in ("windspeedmph", "windgustmph"):
                v = _try_float(sval)
                if v is not None:
                    v2, unit = self._conv_wind(v, "mph")
            elif key in ("rainratein", "dailyrainin"):
                v = _try_float(sval)
                if v is not None:
                    v2, unit = self._conv_rain(v, "in")
            elif key in ("baromrelin", "baromabsin"):
                v = _try_float(sval)
                if v is not None:
                    v2, unit = self._conv_press(v, "inHg")
            elif key == "solarradiation":
                v2 = _try_float(sval); unit = "W/m²"
            elif key == "humidity":
                v2 = _try_float(sval); unit = "%"
            elif key == "uv":
                v2 = _try_float(sval); unit = None
            elif key == "vpd":
                v2 = _try_float(sval); unit = "kPa"

            if v2 is None:
                continue
            if isinstance(v2, float):
                v2 = round(v2, 3 if key.startswith("wind") else 2)

            uid = f"ecowitt_{passkey}_{key}"
            await self._publish_cfg(gw_dev, uid, friendly, unit, devcls, stcls)
            await self._publish_val(uid, v2)


def json_dumps(obj: Any) -> str:
    import json
    return json.dumps(obj, separators=(",", ":"), ensure_ascii=False)
