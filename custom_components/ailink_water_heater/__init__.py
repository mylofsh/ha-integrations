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

from .api import AilinkApiClient, parse_device_status
from .const import DOMAIN, DEFAULT_SCAN_INTERVAL, CONF_TOKEN, CONF_USER_ID, CONF_FAMILY_ID, CONF_DEVICE_ID

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["water_heater", "switch", "sensor", "number"]


class AilinkDataUpdateCoordinator(DataUpdateCoordinator):
    """Coordinator to fetch data from AI-LiNK API via getDeviceCurrInfo."""

    def __init__(self, hass: HomeAssistant, api: AilinkApiClient, device_id: str, scan_interval: int) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )
        self.api = api
        self._device_id = device_id

    async def _async_update_data(self) -> dict:
        """Fetch latest device info."""
        try:
            async with async_timeout.timeout(15):
                raw = await self.api.get_device_curr_info(self._device_id)

            if raw.get("status") != 200:
                raise UpdateFailed(
                    f"API returned status {raw.get('status')}: {raw.get('msg')}"
                )

            info = raw.get("info", {})
            mapping = info.get("appSpaceDeviceMappingEntity", {})
            status_entity = info.get("appDeviceStatusInfoEntity", {})

            device_info = {
                "deviceId": self._device_id,
                "productName": mapping.get("deviceName", "燃气热水器"),
                "roomName": mapping.get("roomName", ""),
                "productModel": info.get("productModel", ""),
                "productMajorClassCode": info.get("productMajorClassCode", "19"),
                "devState": info.get("devState", 0),
                "productImg": info.get("productImageUrl", ""),
                "errorCount": len(info.get("errorCodeData", {}).get("errorWxData", [])),
            }

            status_raw = status_entity.get("statusInfo", "{}")
            device_statuses = {self._device_id: parse_device_status(status_raw)}

            return {
                "homepage": info,
                "devices": [device_info],
                "device_statuses": device_statuses,
                "rooms": [],
                "systems": [],
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

    device_id = entry.data.get(CONF_DEVICE_ID, "")

    coordinator = AilinkDataUpdateCoordinator(
        hass, api, device_id,
        scan_interval=entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
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
