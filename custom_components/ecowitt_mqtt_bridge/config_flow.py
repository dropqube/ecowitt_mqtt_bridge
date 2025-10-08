from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from .const import (
    DOMAIN, DEFAULTS,
    CONF_DISCOVERY_PREFIX, CONF_STATE_PREFIX, CONF_IN_TOPIC,
    CONF_USE_LOCAL_API, CONF_BASE_URL, CONF_LAN_TIMEOUT, CONF_MAP_REFRESH,
    CONF_PUBLISH_LAN_COMMON,
    CONF_UNIT_TEMP, CONF_UNIT_WIND, CONF_UNIT_RAIN, CONF_UNIT_PRESS
)


class EcowittBridgeConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None) -> FlowResult:
        if user_input is not None:
            # leere Strings -> None für Unit-Overrides
            for k in (CONF_UNIT_TEMP, CONF_UNIT_WIND, CONF_UNIT_RAIN, CONF_UNIT_PRESS):
                if user_input.get(k) == "":
                    user_input[k] = None
            return self.async_create_entry(title="Ecowitt MQTT Bridge", data=user_input)

        schema = vol.Schema({
            vol.Optional(CONF_IN_TOPIC, default=DEFAULTS[CONF_IN_TOPIC]): str,
            vol.Optional(CONF_DISCOVERY_PREFIX, default=DEFAULTS[CONF_DISCOVERY_PREFIX]): str,
            vol.Optional(CONF_STATE_PREFIX, default=DEFAULTS[CONF_STATE_PREFIX]): str,
            vol.Optional(CONF_USE_LOCAL_API, default=DEFAULTS[CONF_USE_LOCAL_API]): bool,
            vol.Optional(CONF_BASE_URL, default=DEFAULTS[CONF_BASE_URL]): str,
            vol.Optional(CONF_LAN_TIMEOUT, default=DEFAULTS[CONF_LAN_TIMEOUT]): float,
            vol.Optional(CONF_MAP_REFRESH, default=DEFAULTS[CONF_MAP_REFRESH]): int,
            vol.Optional(CONF_PUBLISH_LAN_COMMON, default=DEFAULTS[CONF_PUBLISH_LAN_COMMON]): bool,
            vol.Optional(CONF_UNIT_TEMP, default=""): str,   # "", "C", "F"
            vol.Optional(CONF_UNIT_WIND, default=""): str,   # "", "m/s", "km/h", "mph"
            vol.Optional(CONF_UNIT_RAIN, default=""): str,   # "", "mm", "in"
            vol.Optional(CONF_UNIT_PRESS, default=""): str,  # "", "hPa", "inHg"
        })
        return self.async_show_form(step_id="user", data_schema=schema)
