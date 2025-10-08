from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .const import (
    DOMAIN, PLATFORMS, DEFAULTS,
    CONF_DISCOVERY_PREFIX, CONF_STATE_PREFIX, CONF_IN_TOPIC,
    CONF_USE_LOCAL_API, CONF_BASE_URL, CONF_LAN_TIMEOUT, CONF_MAP_REFRESH,
    CONF_PUBLISH_LAN_COMMON, CONF_UNIT_TEMP, CONF_UNIT_WIND, CONF_UNIT_RAIN, CONF_UNIT_PRESS
)
from .mqtt_handler import EcowittBridgeRuntime

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    data = {**DEFAULTS, **entry.data}
    rt = EcowittBridgeRuntime(
        hass=hass,
        discovery_prefix=data[CONF_DISCOVERY_PREFIX],
        state_prefix=data[CONF_STATE_PREFIX],
        in_topic=data[CONF_IN_TOPIC],
        use_local_api=data[CONF_USE_LOCAL_API],
        gateway_base_url=data[CONF_BASE_URL],
        lan_timeout=float(data[CONF_LAN_TIMEOUT]),
        map_refresh_sec=int(data[CONF_MAP_REFRESH]),
        publish_lan_common=bool(data[CONF_PUBLISH_LAN_COMMON]),
        unit_temp=data.get(CONF_UNIT_TEMP),
        unit_wind=data.get(CONF_UNIT_WIND),
        unit_rain=data.get(CONF_UNIT_RAIN),
        unit_press=data.get(CONF_UNIT_PRESS),
    )
    await rt.async_start()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = rt

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    rt: EcowittBridgeRuntime = hass.data[DOMAIN].pop(entry.entry_id, None)
    if rt:
        await rt.async_stop()
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    return unload_ok
