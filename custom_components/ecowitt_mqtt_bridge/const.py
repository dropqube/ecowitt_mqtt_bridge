from __future__ import annotations

from homeassistant.const import (
    UnitOfTemperature, UnitOfSpeed, UnitOfPressure, UnitOfLength
)

DOMAIN = "ecowitt_mqtt_bridge"
PLATFORMS: list[str] = ["sensor", "binary_sensor"]

CONF_BROKER = "broker"
CONF_PORT = "port"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_IN_TOPIC = "in_topic"
CONF_DISCOVERY_PREFIX = "discovery_prefix"
CONF_STATE_PREFIX = "state_prefix"
CONF_CLIENT_ID = "client_id"
CONF_CLEANUP = "cleanup"
CONF_USE_LOCAL_API = "use_local_api"
CONF_BASE_URL = "base_url"
CONF_LAN_TIMEOUT = "lan_timeout"
CONF_MAP_REFRESH = "map_refresh_sec"
CONF_PUBLISH_LAN_COMMON = "publish_lan_common"

# Unit-Overrides (leer/None = HA-Systemeinheiten übernehmen)
CONF_UNIT_TEMP = "unit_temperature"      # "C" | "F" | None
CONF_UNIT_WIND = "unit_wind"             # "m/s" | "km/h" | "mph" | None
CONF_UNIT_RAIN = "unit_rain"             # "mm" | "in" | None
CONF_UNIT_PRESS = "unit_pressure"        # "hPa" | "inHg" | None

DEFAULTS = {
    CONF_BROKER: "mqtt",
    CONF_PORT: 1883,
    CONF_USERNAME: "",
    CONF_PASSWORD: "",
    CONF_IN_TOPIC: "ecowitt/#",
    CONF_DISCOVERY_PREFIX: "homeassistant",
    CONF_STATE_PREFIX: "ecowitt_ha",
    CONF_CLIENT_ID: "ecowitt-bridge",
    CONF_CLEANUP: False,
    CONF_USE_LOCAL_API: False,        # LAN folgt später; hier Fokus auf MQTT-Uploads
    CONF_BASE_URL: "http://192.168.0.46",
    CONF_LAN_TIMEOUT: 5.0,
    CONF_MAP_REFRESH: 600,
    CONF_PUBLISH_LAN_COMMON: False,
    CONF_UNIT_TEMP: None,
    CONF_UNIT_WIND: None,
    CONF_UNIT_RAIN: None,
    CONF_UNIT_PRESS: None,
}

