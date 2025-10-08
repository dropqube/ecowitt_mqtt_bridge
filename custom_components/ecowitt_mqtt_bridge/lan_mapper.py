from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Dict, Optional

from aiohttp import ClientSession, ClientTimeout
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_create_clientsession

_LOGGER = logging.getLogger(__name__)

SENSOR_INFO_EP = "/get_sensors_info?page=1"
LIVE_DATA_EP = "/get_livedata_info"


@dataclass
class SensorItem:
    img: str        # z.B. "wh90", "wh69"
    typ: str        # typ-id laut API
    name: str       # sprechender Name
    hwid: str       # stabile HW-ID, z.B. "B708"
    idst: str       # "1" = outdoor, "0" = indoor


class EcowittLanMapper:
    """Holt periodisch die Sensorliste (und pingt live-data), damit wir
    pro Outdoor-Sensor (WH90/WH69) ein eigenes Gerät in HA erzeugen können.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        base_url: str,
        timeout_sec: float,
        refresh_sec: int,
    ) -> None:
        self._hass = hass
        self._base = base_url.rstrip("/")
        self._timeout = ClientTimeout(total=timeout_sec)
        self._refresh = max(60, int(refresh_sec))
        self._task: Optional[asyncio.Task] = None
        self._session: Optional[ClientSession] = None
        self._sensors: Dict[str, SensorItem] = {}  # hwid -> SensorItem

    async def async_start(self) -> None:
        if self._task:
            return
        self._session = async_create_clientsession(self._hass, timeout=self._timeout)
        self._task = asyncio.create_task(self._runner())

    async def async_stop(self) -> None:
        task = self._task
        self._task = None
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        if self._session:
            await self._session.close()
            self._session = None

    def sensors(self) -> Dict[str, SensorItem]:
        return dict(self._sensors)

    def lookup(self, hwid: str) -> Optional[SensorItem]:
        if not hwid:
            return None
        return self._sensors.get(hwid.upper())

    async def _runner(self) -> None:
        try:
            while True:
                await self._refresh_map()
                await asyncio.sleep(self._refresh)
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            _LOGGER.exception("LAN mapper crashed: %s", exc)

    async def _refresh_map(self) -> None:
        sess = self._session
        if not sess:
            return

        # 1) Sensorliste laden
        url = f"{self._base}{SENSOR_INFO_EP}"
        try:
            async with sess.get(url) as resp:
                if resp.status != 200:
                    _LOGGER.debug("[LAN] GET %s -> %s", url, resp.status)
                    return
                data = await resp.json(content_type=None)
        except Exception as exc:
            _LOGGER.debug("[LAN] GET %s failed: %s", url, exc)
            return

        sensors: Dict[str, SensorItem] = {}
        for item in data or []:
            hwid = str(item.get("id") or "").upper()
            if not hwid or hwid in ("FFFFFFFF", "FFFFFFFE"):
                continue  # Platzhalter ignorieren
            sensors[hwid] = SensorItem(
                img=str(item.get("img") or ""),
                typ=str(item.get("type") or ""),
                name=str(item.get("name") or ""),
                hwid=hwid,
                idst=str(item.get("idst") or ""),
            )

        # 2) live-data „anpingen“ (nur zur Verbindungsprüfung/Logging)
        live_url = f"{self._base}{LIVE_DATA_EP}"
        try:
            async with sess.get(live_url) as resp:
                _ = await resp.text()
                _LOGGER.debug("[LAN] GET %s -> %s", live_url, resp.status)
        except Exception:
            pass

        if sensors:
            self._sensors = sensors
            _LOGGER.info(
                "[LAN] mapped %d sensors: %s",
                len(sensors),
                ", ".join(sorted(sensors.keys())),
            )
        elif self._sensors:
            _LOGGER.debug("[LAN] No sensors returned, keeping previous map")
