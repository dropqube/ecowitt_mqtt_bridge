from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional, Tuple

from homeassistant.components import mqtt
from homeassistant.components.mqtt.models import ReceiveMessage
from homeassistant.const import (
    UnitOfLength,
    UnitOfPressure,
    UnitOfSpeed,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.util.unit_system import METRIC_SYSTEM

from .lan_mapper import EcowittLanMapper, SensorItem

_LOGGER = logging.getLogger(__name__)

# ----------------------------
# Helpers & unit conversion
# ----------------------------

_RE_KV = re.compile(r"([^=&]+)=([^&]*)")


def parse_flat_payload(raw: str) -> Dict[str, str]:
    """Parse a flat Ecowitt upload (key=value&...)."""

    out: Dict[str, str] = {}
    for match in _RE_KV.finditer(raw):
        key = match.group(1)
        value = match.group(2)
        out[key] = value
    return out


def as_float(value: Any) -> Optional[float]:
    """Convert payload values to floats (accepts comma, units appended)."""

    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    text = text.replace(",", ".")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        match = re.search(r"[-+]?\d+(\.\d+)?", text)
        if match:
            try:
                return float(match.group(0))
            except ValueError:
                return None
        return None


# ----------------------------
# Sensor descriptions & converters
# ----------------------------


class DeviceLocation:
    """Simple enum-ish helper for device assignment."""

    GATEWAY = "gateway"
    OUTDOOR = "outdoor"


@dataclass(frozen=True)
class SensorDescription:
    key: str
    name: str
    device_class: str | None
    state_class: str | None
    converter: Callable[["EcowittBridgeRuntime", Any], Tuple[Any | None, str | None]]
    device: str = DeviceLocation.OUTDOOR
    entity_category: str | None = None
    icon: str | None = None
    device_hwid: str | None = None


def _round_or_none(value: Optional[float], digits: int | None) -> Optional[float]:
    if value is None or digits is None:
        return value
    return round(value, digits)


def _conv_temperature_f(runtime: "EcowittBridgeRuntime", raw: Any) -> Tuple[Optional[float], str]:
    return runtime.convert_temperature_from_f(raw)


def _conv_temperature_c(runtime: "EcowittBridgeRuntime", raw: Any) -> Tuple[Optional[float], str]:
    return runtime.convert_temperature_from_c(raw)


def _conv_humidity_percent(_: "EcowittBridgeRuntime", raw: Any) -> Tuple[Optional[float], str]:
    return _round_or_none(as_float(raw), 1), "%"


def _conv_wind_mph(runtime: "EcowittBridgeRuntime", raw: Any) -> Tuple[Optional[float], str]:
    return runtime.convert_wind_from_mph(raw)


def _conv_wind_ms(runtime: "EcowittBridgeRuntime", raw: Any) -> Tuple[Optional[float], str]:
    return runtime.convert_wind_from_ms(raw)


def _conv_angle_deg(_: "EcowittBridgeRuntime", raw: Any) -> Tuple[Optional[float], str]:
    return _round_or_none(as_float(raw), 0), "°"


def _conv_uv(_: "EcowittBridgeRuntime", raw: Any) -> Tuple[Optional[float], str | None]:
    return _round_or_none(as_float(raw), 1), None


def _conv_solarrad(_: "EcowittBridgeRuntime", raw: Any) -> Tuple[Optional[float], str]:
    return _round_or_none(as_float(raw), 1), "W/m²"


def _conv_vpd(_: "EcowittBridgeRuntime", raw: Any) -> Tuple[Optional[float], str]:
    return _round_or_none(as_float(raw), 2), "kPa"


def _conv_rain_in(runtime: "EcowittBridgeRuntime", raw: Any) -> Tuple[Optional[float], str]:
    return runtime.convert_rain_from_in(raw)


def _conv_rain_mm(runtime: "EcowittBridgeRuntime", raw: Any) -> Tuple[Optional[float], str]:
    return runtime.convert_rain_from_mm(raw)


def _conv_pressure_inhg(runtime: "EcowittBridgeRuntime", raw: Any) -> Tuple[Optional[float], str]:
    return runtime.convert_pressure_from_inhg(raw)


def _conv_pressure_hpa(runtime: "EcowittBridgeRuntime", raw: Any) -> Tuple[Optional[float], str]:
    return runtime.convert_pressure_from_hpa(raw)


def _conv_float(unit: str | None, precision: int | None = 2) -> Callable[["EcowittBridgeRuntime", Any], Tuple[Optional[float], str | None]]:
    def _inner(_: "EcowittBridgeRuntime", raw: Any) -> Tuple[Optional[float], str | None]:
        return _round_or_none(as_float(raw), precision), unit

    return _inner


def _conv_text(_: "EcowittBridgeRuntime", raw: Any) -> Tuple[str | None, str | None]:
    if raw is None:
        return None, None
    return str(raw), None


BASE_GATEWAY_SENSORS: Tuple[SensorDescription, ...] = (
    SensorDescription("tempinf", "Indoor Temperature", "temperature", "measurement", _conv_temperature_f, device=DeviceLocation.GATEWAY),
    SensorDescription("humidityin", "Indoor Humidity", "humidity", "measurement", _conv_humidity_percent, device=DeviceLocation.GATEWAY),
    SensorDescription("baromabsin", "Pressure (Absolute)", "pressure", "measurement", _conv_pressure_inhg, device=DeviceLocation.GATEWAY),
    SensorDescription("baromrelin", "Pressure (Relative)", "pressure", "measurement", _conv_pressure_inhg, device=DeviceLocation.GATEWAY),
)

BASE_OUTDOOR_SENSORS: Tuple[SensorDescription, ...] = (
    SensorDescription("tempf", "Outdoor Temperature", "temperature", "measurement", _conv_temperature_f),
    SensorDescription("dewpointf", "Dew Point", "temperature", "measurement", _conv_temperature_f),
    SensorDescription("feelslikef", "Feels Like", "temperature", "measurement", _conv_temperature_f),
    SensorDescription("windchillf", "Wind Chill", "temperature", "measurement", _conv_temperature_f),
    SensorDescription("humidity", "Outdoor Humidity", "humidity", "measurement", _conv_humidity_percent),
    SensorDescription("windspeedmph", "Wind Speed", None, "measurement", _conv_wind_mph),
    SensorDescription("windgustmph", "Wind Gust", None, "measurement", _conv_wind_mph),
    SensorDescription("maxdailygust", "Wind Gust (Daily Max)", None, "measurement", _conv_wind_mph),
    SensorDescription("winddir", "Wind Direction", None, None, _conv_angle_deg),
    SensorDescription("uv", "UV Index", None, "measurement", _conv_uv),
    SensorDescription("solarradiation", "Solar Radiation", None, "measurement", _conv_solarrad),
    SensorDescription("vpd", "VPD", None, "measurement", _conv_vpd),
    SensorDescription("rainratein", "Rain Rate", None, "measurement", _conv_rain_in),
    SensorDescription("dailyrainin", "Rain (Daily)", None, "total_increasing", _conv_rain_in),
    SensorDescription("hourlyrainin", "Rain (Hourly)", None, "total_increasing", _conv_rain_in),
    SensorDescription("weeklyrainin", "Rain (Weekly)", None, "total_increasing", _conv_rain_in),
    SensorDescription("monthlyrainin", "Rain (Monthly)", None, "total_increasing", _conv_rain_in),
    SensorDescription("yearlyrainin", "Rain (Yearly)", None, "total_increasing", _conv_rain_in),
    SensorDescription("eventrainin", "Rain (Event)", None, "total_increasing", _conv_rain_in),
    SensorDescription("stormrainin", "Rain (Storm)", None, "total_increasing", _conv_rain_in),
)


CUSTOM_CONVERTERS: Dict[str, Callable[["EcowittBridgeRuntime", Any], Tuple[Any | None, str | None]]] = {
    "float": _conv_float(None),
    "float3": _conv_float(None, 3),
    "temperature_f": _conv_temperature_f,
    "temperature_c": _conv_temperature_c,
    "humidity": _conv_humidity_percent,
    "wind_mph": _conv_wind_mph,
    "wind_ms": _conv_wind_ms,
    "angle": _conv_angle_deg,
    "uv": _conv_uv,
    "solarradiation": _conv_solarrad,
    "vpd": _conv_vpd,
    "rain_in": _conv_rain_in,
    "rain_mm": _conv_rain_mm,
    "pressure_inhg": _conv_pressure_inhg,
    "pressure_hpa": _conv_pressure_hpa,
    "text": _conv_text,
}


def _converter_from_name(
    name: str | None,
    unit: str | None,
    precision: int | None = None,
) -> Callable[["EcowittBridgeRuntime", Any], Tuple[Any | None, str | None]]:
    key = (name or "float").lower()
    if key in ("float", "float3"):
        target_precision = precision if precision is not None else (3 if key == "float3" else 2)
        return _conv_float(unit, target_precision)

    converter = CUSTOM_CONVERTERS.get(key)
    if converter:
        if key == "text" and unit:
            def _with_unit(runtime: "EcowittBridgeRuntime", raw: Any) -> Tuple[Any | None, str | None]:
                value, _ = converter(runtime, raw)
                return value, unit

            return _with_unit
        return converter

    if unit:
        return _conv_float(unit, precision)

    return CUSTOM_CONVERTERS["float"]


# ----------------------------
# Runtime
# ----------------------------


class EcowittBridgeRuntime:
    """Subscribe to Ecowitt flat uploads and publish HA MQTT discovery."""

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
        publish_lan_common: bool = False,  # currently unused but kept for compatibility
        custom_sensor_config: str = "",
        unit_overrides: Optional[Dict[str, str]] = None,
    ) -> None:
        self.hass = hass
        self.in_topic = in_topic
        self.discovery_prefix = discovery_prefix.rstrip("/")
        self.state_prefix = state_prefix.rstrip("/")
        self._unsub: Callable[[], None] | None = None
        self._availability_online = False
        self._publish_lan_common = publish_lan_common
        self._config_payloads: Dict[str, str] = {}

        overrides = unit_overrides or {}
        self._unit_overrides = {
            "temperature": (overrides.get("temperature") or "").upper(),
            "wind": (overrides.get("wind") or "").lower(),
            "rain": (overrides.get("rain") or "").lower(),
            "pressure": (overrides.get("pressure") or "").lower(),
        }

        self._lan: EcowittLanMapper | None = None
        if use_local_api and gateway_base_url:
            self._lan = EcowittLanMapper(
                hass,
                gateway_base_url,
                lan_timeout,
                map_refresh_sec,
            )

        self._sensor_descriptions: Dict[str, SensorDescription] = {}
        self._ordered_keys: list[str] = []
        self._load_base_descriptions()
        self._load_custom_descriptions(custom_sensor_config)

    # -------------------------------------------------
    # Initialisation helpers
    # -------------------------------------------------

    def _load_base_descriptions(self) -> None:
        for description in (*BASE_GATEWAY_SENSORS, *BASE_OUTDOOR_SENSORS):
            self._sensor_descriptions[description.key] = description
            self._ordered_keys.append(description.key)

    def _load_custom_descriptions(self, raw_config: str) -> None:
        config = (raw_config or "").strip()
        if not config:
            return
        try:
            data = json.loads(config)
        except json.JSONDecodeError as err:
            _LOGGER.error("Invalid custom sensor JSON: %s", err)
            return
        if not isinstance(data, list):
            _LOGGER.error("Custom sensor configuration must be a list of objects")
            return
        for idx, entry in enumerate(data, start=1):
            if not isinstance(entry, dict):
                _LOGGER.warning("Custom sensor entry %s ignored (expected dict)", idx)
                continue
            key = str(entry.get("key") or "").strip()
            if not key:
                _LOGGER.warning("Custom sensor entry %s missing key", idx)
                continue
            name = str(entry.get("name") or key)
            device = str(entry.get("device") or DeviceLocation.OUTDOOR).lower()
            device_hwid = None
            if device.startswith("hwid:"):
                device_hwid = device.split(":", 1)[1].strip().upper() or None
                device = DeviceLocation.OUTDOOR
            if device not in (DeviceLocation.GATEWAY, DeviceLocation.OUTDOOR):
                _LOGGER.warning("Custom sensor %s has unknown device '%s', using outdoor", key, device)
                device = DeviceLocation.OUTDOOR
            precision = entry.get("precision")
            if isinstance(precision, str) and precision.strip():
                try:
                    precision = int(precision)
                except ValueError:
                    _LOGGER.warning(
                        "Custom sensor %s has invalid precision '%s'", key, precision
                    )
                    precision = None
            unit_value = entry.get("unit")
            if unit_value is not None:
                unit_value = str(unit_value)
            converter = _converter_from_name(
                str(entry.get("convert") or "float"),
                unit_value,
                precision,
            )
            explicit_hwid = entry.get("device_hwid")
            if explicit_hwid and not device_hwid:
                device_hwid = str(explicit_hwid).strip().upper()

            description = SensorDescription(
                key=key,
                name=name,
                device_class=entry.get("device_class"),
                state_class=entry.get("state_class"),
                converter=converter,
                device=device,
                entity_category=entry.get("entity_category"),
                icon=entry.get("icon"),
                device_hwid=device_hwid,
            )
            if key not in self._sensor_descriptions:
                self._ordered_keys.append(key)
            self._sensor_descriptions[key] = description
            _LOGGER.debug("Custom sensor registered: %s (%s)", key, name)

    # -------------------------------------------------
    # Unit helpers
    # -------------------------------------------------

    def _target_temperature_unit(self) -> str:
        override = self._unit_overrides["temperature"]
        if override == "C":
            return UnitOfTemperature.CELSIUS
        if override == "F":
            return UnitOfTemperature.FAHRENHEIT
        return UnitOfTemperature.CELSIUS if self.hass.config.units is METRIC_SYSTEM else UnitOfTemperature.FAHRENHEIT

    def _target_wind_unit(self) -> str:
        override = self._unit_overrides["wind"]
        if override in {"m/s", "ms"}:
            return UnitOfSpeed.METERS_PER_SECOND
        if override in {"km/h", "kph"}:
            return UnitOfSpeed.KILOMETERS_PER_HOUR
        if override == "mph":
            return UnitOfSpeed.MILES_PER_HOUR
        return UnitOfSpeed.METERS_PER_SECOND if self.hass.config.units is METRIC_SYSTEM else UnitOfSpeed.MILES_PER_HOUR

    def _target_rain_unit(self) -> str:
        override = self._unit_overrides["rain"]
        if override == "mm":
            return UnitOfLength.MILLIMETERS
        if override == "in":
            return UnitOfLength.INCHES
        return UnitOfLength.MILLIMETERS if self.hass.config.units is METRIC_SYSTEM else UnitOfLength.INCHES

    def _target_pressure_unit(self) -> str:
        override = self._unit_overrides["pressure"]
        if override == "hpa":
            return UnitOfPressure.HPA
        if override == "inhg":
            return UnitOfPressure.INHG
        return UnitOfPressure.HPA if self.hass.config.units is METRIC_SYSTEM else UnitOfPressure.INHG

    def convert_temperature_from_f(self, raw: Any) -> Tuple[Optional[float], str]:
        value = as_float(raw)
        unit = self._target_temperature_unit()
        if value is None:
            return None, unit
        if unit == UnitOfTemperature.CELSIUS:
            return round((value - 32.0) * 5.0 / 9.0, 2), unit
        return round(value, 2), unit

    def convert_temperature_from_c(self, raw: Any) -> Tuple[Optional[float], str]:
        value = as_float(raw)
        unit = self._target_temperature_unit()
        if value is None:
            return None, unit
        if unit == UnitOfTemperature.CELSIUS:
            return round(value, 2), unit
        return round(value * 9.0 / 5.0 + 32.0, 2), unit

    def convert_wind_from_mph(self, raw: Any) -> Tuple[Optional[float], str]:
        value = as_float(raw)
        unit = self._target_wind_unit()
        if value is None:
            return None, unit
        if unit == UnitOfSpeed.METERS_PER_SECOND:
            return round(value * 0.44704, 2), unit
        if unit == UnitOfSpeed.KILOMETERS_PER_HOUR:
            return round(value * 1.609344, 2), unit
        return round(value, 2), unit

    def convert_wind_from_ms(self, raw: Any) -> Tuple[Optional[float], str]:
        value = as_float(raw)
        unit = self._target_wind_unit()
        if value is None:
            return None, unit
        if unit == UnitOfSpeed.METERS_PER_SECOND:
            return round(value, 2), unit
        if unit == UnitOfSpeed.KILOMETERS_PER_HOUR:
            return round(value * 3.6, 2), unit
        return round(value * 2.23693629, 2), unit

    def convert_rain_from_in(self, raw: Any) -> Tuple[Optional[float], str]:
        value = as_float(raw)
        unit = self._target_rain_unit()
        if value is None:
            return None, unit
        if unit == UnitOfLength.MILLIMETERS:
            return round(value * 25.4, 2), unit
        return round(value, 2), unit

    def convert_rain_from_mm(self, raw: Any) -> Tuple[Optional[float], str]:
        value = as_float(raw)
        unit = self._target_rain_unit()
        if value is None:
            return None, unit
        if unit == UnitOfLength.MILLIMETERS:
            return round(value, 2), unit
        return round(value / 25.4, 2), unit

    def convert_pressure_from_inhg(self, raw: Any) -> Tuple[Optional[float], str]:
        value = as_float(raw)
        unit = self._target_pressure_unit()
        if value is None:
            return None, unit
        if unit == UnitOfPressure.HPA:
            return round(value * 33.8638866667, 1), unit
        return round(value, 3), unit

    def convert_pressure_from_hpa(self, raw: Any) -> Tuple[Optional[float], str]:
        value = as_float(raw)
        unit = self._target_pressure_unit()
        if value is None:
            return None, unit
        if unit == UnitOfPressure.HPA:
            return round(value, 1), unit
        return round(value / 33.8638866667, 3), unit

    # -------------------------------------------------
    # Lifecycle
    # -------------------------------------------------

    async def async_start(self) -> None:
        async def _msg_received(msg: ReceiveMessage) -> None:
            payload = msg.payload or b""
            text = payload.decode(errors="ignore")
            raw = parse_flat_payload(text)
            _LOGGER.debug(
                "[RECV] topic=%s bytes=%d sample='%s...'",
                msg.topic,
                len(payload),
                text[:80],
            )
            await self._handle_flat_gateway(raw)

        self._unsub = await mqtt.async_subscribe(self.hass, self.in_topic, _msg_received, qos=0)
        _LOGGER.info("[MQTT] Subscribed to %s", self.in_topic)
        if self._lan:
            await self._lan.async_start()

    async def async_stop(self) -> None:
        if self._unsub:
            self._unsub()
            self._unsub = None
        if self._availability_online:
            await self._publish_availability(False)
        if self._lan:
            await self._lan.async_stop()

    # -------------------------------------------------
    # Device helpers
    # -------------------------------------------------

    def _gw_device(self, passkey: str) -> Dict[str, Any]:
        return {
            "identifiers": [f"ecowitt_gateway_{passkey}"],
            "manufacturer": "Ecowitt",
            "model": "Gateway",
            "name": f"Ecowitt Gateway {passkey[-6:]}" if passkey != "unknown" else "Ecowitt Gateway",
        }

    def _sensor_device(self, passkey: str, item: SensorItem) -> Dict[str, Any]:
        model = item.img.upper() if item.img else item.typ or "Sensor"
        name = item.name or model
        return {
            "identifiers": [f"ecowitt_sensor_{passkey}_{item.hwid}"],
            "manufacturer": "Ecowitt",
            "model": model,
            "name": f"{name} ({item.hwid})",
            "via_device": f"ecowitt_gateway_{passkey}",
        }

    def _lan_sensor_by_priority(self) -> Optional[SensorItem]:
        if not self._lan:
            return None
        sensors = self._lan.sensors()
        for item in sensors.values():
            if item.idst == "1" and item.img.lower() == "wh90":
                return item
        for item in sensors.values():
            if item.idst == "1" and item.img.lower() == "wh69":
                return item
        for item in sensors.values():
            if item.idst == "1":
                return item
        return None

    def _lan_lookup(self, hwid: str | None) -> Optional[SensorItem]:
        if not hwid or not self._lan:
            return None
        return self._lan.lookup(hwid)

    def _device_for_description(self, passkey: str, description: SensorDescription) -> Dict[str, Any]:
        if description.device_hwid:
            mapped = self._lan_lookup(description.device_hwid)
            if mapped:
                return self._sensor_device(passkey, mapped)
        if description.device == DeviceLocation.GATEWAY:
            return self._gw_device(passkey)
        if self._lan:
            preferred = self._lan_sensor_by_priority()
            if preferred:
                return self._sensor_device(passkey, preferred)
        return self._gw_device(passkey)

    # -------------------------------------------------
    # MQTT discovery helpers
    # -------------------------------------------------

    async def _publish_availability(self, online: bool) -> None:
        topic = f"{self.state_prefix}/availability"
        payload = "online" if online else "offline"
        await mqtt.async_publish(self.hass, topic, payload, retain=True)
        self._availability_online = online

    async def _publish_cfg(
        self,
        description: SensorDescription,
        device: Dict[str, Any],
        unique_id: str,
        unit: str | None,
    ) -> None:
        topic = f"{self.discovery_prefix}/sensor/{unique_id}/config"
        payload: Dict[str, Any] = {
            "name": description.name,
            "uniq_id": unique_id,
            "stat_t": f"{self.state_prefix}/{unique_id}/state",
            "avty_t": f"{self.state_prefix}/availability",
            "dev": device,
        }
        if unit:
            payload["unit_of_meas"] = unit
        if description.device_class:
            payload["dev_cla"] = description.device_class
        if description.state_class:
            payload["stat_cla"] = description.state_class
        if description.entity_category:
            payload["ent_cat"] = description.entity_category
        if description.icon:
            payload["icon"] = description.icon

        payload_json = json.dumps(payload, sort_keys=True)
        if self._config_payloads.get(unique_id) == payload_json:
            return
        self._config_payloads[unique_id] = payload_json
        await mqtt.async_publish(self.hass, topic, payload_json, retain=True)
        _LOGGER.info("[DISCOVERY] %s → %s", topic, description.name)

    async def _publish_val(self, unique_id: str, value: Any | None) -> None:
        topic = f"{self.state_prefix}/{unique_id}/state"
        await mqtt.async_publish(self.hass, topic, json.dumps(value), retain=True)

    # -------------------------------------------------
    # Message handling
    # -------------------------------------------------

    async def _handle_flat_gateway(self, raw: Dict[str, Any]) -> None:
        passkey = (raw.get("PASSKEY") or "unknown").lower()
        if not self._availability_online:
            await self._publish_availability(True)

        gateway_device = self._gw_device(passkey)
        cached_devices: Dict[str, Dict[str, Any]] = {
            DeviceLocation.GATEWAY: gateway_device,
        }

        try:
            for key in self._ordered_keys:
                description = self._sensor_descriptions.get(key)
                if not description or key not in raw:
                    continue

                device_key = description.device_hwid or description.device
                if device_key not in cached_devices:
                    cached_devices[device_key] = self._device_for_description(passkey, description)
                device = cached_devices[device_key]

                unique_id = f"ecowitt_{passkey}_{key}".lower()
                value, unit = description.converter(self, raw.get(key))

                await self._publish_cfg(description, device, unique_id, unit)
                await self._publish_val(unique_id, value)
        except Exception as exc:  # pragma: no cover - defensive log
            _LOGGER.exception("Failed to process MQTT payload: %s", exc)

        _LOGGER.debug("[MQTT] Processed payload for passkey=%s", passkey)
