"""DataUpdateCoordinator and integration setup for AI-LiNK."""
from __future__ import annotations

import logging
from datetime import timedelta

import async_timeout

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import AilinkApiClient
from .const import DOMAIN, DEFAULT_SCAN_INTERVAL, CONF_TOKEN, CONF_USER_ID, CONF_FAMILY_ID

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["water_heater", "switch", "sensor", "number"]


class AilinkDataUpdateCoordinator(DataUpdateCoordinator):
    """Coordinator to fetch data from AI-LiNK API."""

    def __init__(self, hass: HomeAssistant, api: AilinkApiClient, scan_interval: int) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )
        self.api = api

    async def _async_update_data(self) -> dict:
        """Fetch latest data."""
        try:
            async with async_timeout.timeout(15):
                homepage = await self.api.get_homepage()

            if homepage.get("status") != 200:
                raise UpdateFailed(
                    f"API returned status {homepage.get('status')}: {homepage.get('msg')}"
                )

            info = homepage.get("info", {})
            devices = info.get("devInfoItemInfoList", [])

            # 解析每个设备的状态
            device_statuses = {}
            for device in devices:
                did = device.get("deviceId", "")
                raw = device.get("statusInfo", "{}")
                from .api import parse_device_status
                device_statuses[did] = parse_device_status(raw)

            return {
                "homepage": info,
                "devices": devices,
                "device_statuses": device_statuses,
                "rooms": info.get("roomInfoItemInfoList", []),
                "systems": info.get("homePageSysInfoList", []),
            }
        except Exception as err:
            raise UpdateFailed(f"Error fetching data: {err}") from err


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up AI-LiNK from a config entry."""
    session = async_get_clientsession(hass)

    api = AilinkApiClient(
        session=session,
        token=entry.data[CONF_TOKEN],
        user_id=entry.data[CONF_USER_ID],
        family_id=entry.data[CONF_FAMILY_ID],
    )

    coordinator = AilinkDataUpdateCoordinator(
        hass, api,
        scan_interval=entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    )
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "api": api,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
