from __future__ import annotations
import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    # nichts weiter nötig – Discovery kommt über MQTT
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    # KEIN forward_entry_setups, da wir keine sensor.py etc. haben
    _LOGGER.info("ecowitt_mqtt_bridge: setup entry OK (title=%s)", entry.title)
    # Wenn du später Logik/Listener brauchst, hier starten und Referenzen in hass.data[DOMAIN] ablegen.
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}
    hass.data[DOMAIN][entry.entry_id] = dict(entry_data=entry.data)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    _LOGGER.info("ecowitt_mqtt_bridge: unload entry OK (title=%s)", entry.title)
    hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    return True
