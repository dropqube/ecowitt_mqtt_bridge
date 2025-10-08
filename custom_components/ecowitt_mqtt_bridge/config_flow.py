from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.selector import (
    TextSelector, TextSelectorConfig, TextSelectorType,
    NumberSelector, NumberSelectorConfig, NumberSelectorMode,
    BooleanSelector
)

from .const import DOMAIN

# Keys (falls noch nicht in const.py)
CONF_IN_TOPIC = "in_topic"
CONF_DISCOVERY_PREFIX = "discovery_prefix"
CONF_STATE_PREFIX = "state_prefix"
CONF_USE_LOCAL_API = "use_local_api"
CONF_BASE_URL = "base_url"
CONF_LAN_TIMEOUT = "lan_timeout"
CONF_MAP_REFRESH_SEC = "map_refresh_sec"
CONF_PUBLISH_LAN_COMMON = "publish_lan_common"
CONF_UNIT_TEMPERATURE = "unit_temperature"
CONF_UNIT_WIND = "unit_wind"
CONF_UNIT_RAIN = "unit_rain"
CONF_UNIT_PRESSURE = "unit_pressure"

DEFAULTS = {
    CONF_IN_TOPIC: "ecowitt/#",
    CONF_DISCOVERY_PREFIX: "homeassistant",
    CONF_STATE_PREFIX: "ecowitt_ha",
    CONF_USE_LOCAL_API: False,
    CONF_BASE_URL: "",
    CONF_LAN_TIMEOUT: 5.0,        # float!
    CONF_MAP_REFRESH_SEC: 600,     # int
    CONF_PUBLISH_LAN_COMMON: False,
    CONF_UNIT_TEMPERATURE: "",
    CONF_UNIT_WIND: "",
    CONF_UNIT_RAIN: "",
    CONF_UNIT_PRESSURE: "",
}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Ecowitt MQTT Bridge."""

    VERSION = 1

    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        if user_input is not None:
            # Tolerant casten – verhindert "expected float"
            data = {
                CONF_IN_TOPIC: str(user_input.get(CONF_IN_TOPIC, DEFAULTS[CONF_IN_TOPIC])),
                CONF_DISCOVERY_PREFIX: str(user_input.get(CONF_DISCOVERY_PREFIX, DEFAULTS[CONF_DISCOVERY_PREFIX])),
                CONF_STATE_PREFIX: str(user_input.get(CONF_STATE_PREFIX, DEFAULTS[CONF_STATE_PREFIX])),
                CONF_USE_LOCAL_API: bool(user_input.get(CONF_USE_LOCAL_API, DEFAULTS[CONF_USE_LOCAL_API])),
                CONF_BASE_URL: str(user_input.get(CONF_BASE_URL, DEFAULTS[CONF_BASE_URL])),
                CONF_LAN_TIMEOUT: float(user_input.get(CONF_LAN_TIMEOUT, DEFAULTS[CONF_LAN_TIMEOUT])),
                CONF_MAP_REFRESH_SEC: int(user_input.get(CONF_MAP_REFRESH_SEC, DEFAULTS[CONF_MAP_REFRESH_SEC])),
                CONF_PUBLISH_LAN_COMMON: bool(user_input.get(CONF_PUBLISH_LAN_COMMON, DEFAULTS[CONF_PUBLISH_LAN_COMMON])),
                CONF_UNIT_TEMPERATURE: str(user_input.get(CONF_UNIT_TEMPERATURE, "")),
                CONF_UNIT_WIND: str(user_input.get(CONF_UNIT_WIND, "")),
                CONF_UNIT_RAIN: str(user_input.get(CONF_UNIT_RAIN, "")),
                CONF_UNIT_PRESSURE: str(user_input.get(CONF_UNIT_PRESSURE, "")),
            }
            return self.async_create_entry(title="Ecowitt MQTT Bridge", data=data)

        # UI mit Selectors (nutzerfreundlich) + darunterliegendes Voluptuous
        schema = vol.Schema({
            vol.Optional(CONF_IN_TOPIC, default=DEFAULTS[CONF_IN_TOPIC]):
                TextSelector(TextSelectorConfig(type=TextSelectorType.TEXT)),
            vol.Optional(CONF_DISCOVERY_PREFIX, default=DEFAULTS[CONF_DISCOVERY_PREFIX]):
                TextSelector(TextSelectorConfig(type=TextSelectorType.TEXT)),
            vol.Optional(CONF_STATE_PREFIX, default=DEFAULTS[CONF_STATE_PREFIX]):
                TextSelector(TextSelectorConfig(type=TextSelectorType.TEXT)),

            vol.Optional(CONF_USE_LOCAL_API, default=DEFAULTS[CONF_USE_LOCAL_API]): BooleanSelector(),
            vol.Optional(CONF_BASE_URL, default=DEFAULTS[CONF_BASE_URL]):
                TextSelector(TextSelectorConfig(type=TextSelectorType.URL)),

            # WICHTIG: tolerant casten
            vol.Optional(CONF_LAN_TIMEOUT, default=DEFAULTS[CONF_LAN_TIMEOUT]):
                NumberSelector(NumberSelectorConfig(mode=NumberSelectorMode.BOX, min=1, max=120, step=1)),
            vol.Optional(CONF_MAP_REFRESH_SEC, default=DEFAULTS[CONF_MAP_REFRESH_SEC]):
                NumberSelector(NumberSelectorConfig(mode=NumberSelectorMode.BOX, min=60, max=3600, step=1)),

            vol.Optional(CONF_PUBLISH_LAN_COMMON, default=DEFAULTS[CONF_PUBLISH_LAN_COMMON]): BooleanSelector(),

            # optionale Override-Strings (leer = HA-Systemeinheiten)
            vol.Optional(CONF_UNIT_TEMPERATURE, default=""):
                TextSelector(TextSelectorConfig(type=TextSelectorType.TEXT)),
            vol.Optional(CONF_UNIT_WIND, default=""):
                TextSelector(TextSelectorConfig(type=TextSelectorType.TEXT)),
            vol.Optional(CONF_UNIT_RAIN, default=""):
                TextSelector(TextSelectorConfig(type=TextSelectorType.TEXT)),
            vol.Optional(CONF_UNIT_PRESSURE, default=""):
                TextSelector(TextSelectorConfig(type=TextSelectorType.TEXT)),
        })

        return self.async_show_form(step_id="user", data_schema=schema)
