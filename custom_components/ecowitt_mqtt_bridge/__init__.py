from __future__ import annotations
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import (
    DOMAIN,
    DEFAULTS,
    CONF_IN_TOPIC,
    CONF_DISCOVERY_PREFIX,
    CONF_STATE_PREFIX,
    CONF_USE_LOCAL_API,
    CONF_BASE_URL,
    CONF_LAN_TIMEOUT,
    CONF_MAP_REFRESH,
    CONF_PUBLISH_LAN_COMMON,
    CONF_CUSTOM_SENSORS,
    CONF_UNIT_TEMP,
    CONF_UNIT_WIND,
    CONF_UNIT_RAIN,
    CONF_UNIT_PRESS,
)
from .mqtt_handler import EcowittBridgeRuntime

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up via YAML is not supported."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Boot strap the runtime that bridges MQTT payloads into HA discovery."""

    hass.data.setdefault(DOMAIN, {})

    # Home Assistant 2025+: runtime should respect option overrides in addition
    # to the original config data to allow adjustments from the options flow.
    data: dict[str, Any] = {**DEFAULTS, **entry.data, **entry.options}

    runtime = EcowittBridgeRuntime(
        hass,
        in_topic=data[CONF_IN_TOPIC],
        discovery_prefix=data[CONF_DISCOVERY_PREFIX],
        state_prefix=data[CONF_STATE_PREFIX],
        use_local_api=data[CONF_USE_LOCAL_API],
        gateway_base_url=data[CONF_BASE_URL],
        lan_timeout=float(data[CONF_LAN_TIMEOUT]),
        map_refresh_sec=int(data[CONF_MAP_REFRESH]),
        publish_lan_common=bool(data[CONF_PUBLISH_LAN_COMMON]),
        custom_sensor_config=str(data.get(CONF_CUSTOM_SENSORS, "")),
        unit_overrides={
            "temperature": data.get(CONF_UNIT_TEMP, ""),
            "wind": data.get(CONF_UNIT_WIND, ""),
            "rain": data.get(CONF_UNIT_RAIN, ""),
            "pressure": data.get(CONF_UNIT_PRESS, ""),
        },
    )

    try:
        await runtime.async_start()
    except Exception as exc:  # pragma: no cover - defensive log
        await runtime.async_stop()
        raise ConfigEntryNotReady(f"Failed to start Ecowitt bridge: {exc}") from exc

    unsub_update = entry.add_update_listener(_async_entry_updated)
    hass.data[DOMAIN][entry.entry_id] = {
        "runtime": runtime,
        "unsub_update": unsub_update,
    }

    _LOGGER.info("ecowitt_mqtt_bridge: setup entry OK (title=%s)", entry.title)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Stop the runtime when a config entry is removed or reloaded."""

    entry_data = hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    if not entry_data:
        return True

    if (unsub := entry_data.get("unsub_update")) is not None:
        unsub()

    runtime: EcowittBridgeRuntime | None = entry_data.get("runtime")
    if runtime:
        await runtime.async_stop()

    _LOGGER.info("ecowitt_mqtt_bridge: unload entry OK (title=%s)", entry.title)
    return True


async def _async_entry_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle runtime reload when the entry is updated via the UI."""

    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
