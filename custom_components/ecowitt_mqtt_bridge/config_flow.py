from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.selector import (
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    BooleanSelector,
)

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
    CONF_UNIT_TEMP,
    CONF_UNIT_WIND,
    CONF_UNIT_RAIN,
    CONF_UNIT_PRESS,
    CONF_CUSTOM_SENSORS,
)

# map_refresh_sec renamed constant in config schema
CONF_MAP_REFRESH_SEC = CONF_MAP_REFRESH
CONF_UNIT_TEMPERATURE = CONF_UNIT_TEMP
CONF_UNIT_PRESSURE = CONF_UNIT_PRESS


def _coerce_config(user_input: dict) -> dict:
    """Cast config flow input into the stored schema types."""

    return {
        CONF_IN_TOPIC: str(user_input.get(CONF_IN_TOPIC, DEFAULTS[CONF_IN_TOPIC])),
        CONF_DISCOVERY_PREFIX: str(
            user_input.get(CONF_DISCOVERY_PREFIX, DEFAULTS[CONF_DISCOVERY_PREFIX])
        ),
        CONF_STATE_PREFIX: str(user_input.get(CONF_STATE_PREFIX, DEFAULTS[CONF_STATE_PREFIX])),
        CONF_USE_LOCAL_API: bool(user_input.get(CONF_USE_LOCAL_API, DEFAULTS[CONF_USE_LOCAL_API])),
        CONF_BASE_URL: str(user_input.get(CONF_BASE_URL, DEFAULTS[CONF_BASE_URL])),
        CONF_LAN_TIMEOUT: float(user_input.get(CONF_LAN_TIMEOUT, DEFAULTS[CONF_LAN_TIMEOUT])),
        CONF_MAP_REFRESH_SEC: int(user_input.get(CONF_MAP_REFRESH_SEC, DEFAULTS[CONF_MAP_REFRESH_SEC])),
        CONF_PUBLISH_LAN_COMMON: bool(
            user_input.get(CONF_PUBLISH_LAN_COMMON, DEFAULTS[CONF_PUBLISH_LAN_COMMON])
        ),
        CONF_UNIT_TEMPERATURE: str(
            user_input.get(CONF_UNIT_TEMPERATURE, DEFAULTS[CONF_UNIT_TEMPERATURE])
        ),
        CONF_UNIT_WIND: str(user_input.get(CONF_UNIT_WIND, DEFAULTS[CONF_UNIT_WIND])),
        CONF_UNIT_RAIN: str(user_input.get(CONF_UNIT_RAIN, DEFAULTS[CONF_UNIT_RAIN])),
        CONF_UNIT_PRESSURE: str(user_input.get(CONF_UNIT_PRESSURE, DEFAULTS[CONF_UNIT_PRESSURE])),
        CONF_CUSTOM_SENSORS: str(
            user_input.get(CONF_CUSTOM_SENSORS, DEFAULTS[CONF_CUSTOM_SENSORS])
        ),
    }


def _schema_with_defaults(current: dict) -> vol.Schema:
    """Build the selector schema with the provided defaults."""

    return vol.Schema(
        {
            vol.Optional(CONF_IN_TOPIC, default=current[CONF_IN_TOPIC]): TextSelector(
                TextSelectorConfig(type=TextSelectorType.TEXT)
            ),
            vol.Optional(
                CONF_DISCOVERY_PREFIX, default=current[CONF_DISCOVERY_PREFIX]
            ): TextSelector(TextSelectorConfig(type=TextSelectorType.TEXT)),
            vol.Optional(CONF_STATE_PREFIX, default=current[CONF_STATE_PREFIX]): TextSelector(
                TextSelectorConfig(type=TextSelectorType.TEXT)
            ),
            vol.Optional(
                CONF_USE_LOCAL_API, default=current[CONF_USE_LOCAL_API]
            ): BooleanSelector(),
            vol.Optional(CONF_BASE_URL, default=current[CONF_BASE_URL]): TextSelector(
                TextSelectorConfig(type=TextSelectorType.URL)
            ),
            vol.Optional(CONF_LAN_TIMEOUT, default=current[CONF_LAN_TIMEOUT]): NumberSelector(
                NumberSelectorConfig(mode=NumberSelectorMode.BOX, min=1, max=120, step=1)
            ),
            vol.Optional(
                CONF_MAP_REFRESH_SEC, default=current[CONF_MAP_REFRESH_SEC]
            ): NumberSelector(
                NumberSelectorConfig(mode=NumberSelectorMode.BOX, min=60, max=3600, step=1)
            ),
            vol.Optional(
                CONF_PUBLISH_LAN_COMMON, default=current[CONF_PUBLISH_LAN_COMMON]
            ): BooleanSelector(),
            vol.Optional(CONF_UNIT_TEMPERATURE, default=current[CONF_UNIT_TEMPERATURE]): TextSelector(
                TextSelectorConfig(type=TextSelectorType.TEXT)
            ),
            vol.Optional(CONF_UNIT_WIND, default=current[CONF_UNIT_WIND]): TextSelector(
                TextSelectorConfig(type=TextSelectorType.TEXT)
            ),
            vol.Optional(CONF_UNIT_RAIN, default=current[CONF_UNIT_RAIN]): TextSelector(
                TextSelectorConfig(type=TextSelectorType.TEXT)
            ),
            vol.Optional(CONF_UNIT_PRESSURE, default=current[CONF_UNIT_PRESSURE]): TextSelector(
                TextSelectorConfig(type=TextSelectorType.TEXT)
            ),
            vol.Optional(CONF_CUSTOM_SENSORS, default=current[CONF_CUSTOM_SENSORS]): TextSelector(
                TextSelectorConfig(type=TextSelectorType.TEXT, multiline=True)
            ),
        }
    )


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Ecowitt MQTT Bridge."""

    VERSION = 1

    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        await self.async_set_unique_id(DOMAIN, raise_on_progress=False)
        self._abort_if_unique_id_configured()

        if user_input is not None:
            data = _coerce_config(user_input)
            return self.async_create_entry(title="Ecowitt MQTT Bridge", data=data)

        defaults = DEFAULTS.copy()
        return self.async_show_form(
            step_id="user",
            data_schema=_schema_with_defaults(defaults),
        )


class EcowittOptionsFlow(config_entries.OptionsFlow):
    """Allow editing the Ecowitt bridge settings via the options flow."""

    def __init__(self, entry: ConfigEntry) -> None:
        self._entry = entry

    async def async_step_init(self, user_input: dict | None = None) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=_coerce_config(user_input))

        current = {**DEFAULTS, **self._entry.data, **self._entry.options}
        return self.async_show_form(
            step_id="init",
            data_schema=_schema_with_defaults(current),
        )


@callback
def async_get_options_flow(config_entry: ConfigEntry) -> config_entries.OptionsFlow:
    return EcowittOptionsFlow(config_entry)
