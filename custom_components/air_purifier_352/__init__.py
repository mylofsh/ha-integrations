"""DataUpdateCoordinator and setup for 352 Air Purifier."""
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
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["fan", "sensor", "switch", "select"]


class Ailink352DataUpdateCoordinator(DataUpdateCoordinator):
    """Coordinator to fetch data from 352 API."""

    def __init__(
        self, hass: HomeAssistant, api: AilinkApiClient, scan_interval: int
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )
        self.api = api

    async def _async_update_data(self) -> dict:
        """Fetch data from API."""
        try:
            async with async_timeout.timeout(15):
                devices_raw = await self.api.list_devices()
                devices = []
                device_statuses = {}
                for dev in devices_raw:
                    iot_id = dev["iotId"]
                    # 只处理空气净化器
                    if "净化" not in dev.get("productName", "") and "净化器" not in dev.get("productModel", ""):
                        continue
                    props = await self.api.get_properties(iot_id)
                    if props:
                        device_statuses[iot_id] = props
                        devices.append({
                            "iotId": iot_id,
                            "name": dev.get("nickname") or dev.get("productName", "空气净化器"),
                            "productName": dev.get("productName", ""),
                            "productModel": dev.get("productModel", ""),
                        })
                return {
                    "devices": devices,
                    "device_statuses": device_statuses,
                }
        except Exception as err:
            raise UpdateFailed(f"Error fetching data: {err}") from err


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up 352 Air Purifier from a config entry."""
    session = async_get_clientsession(hass)
    api = AilinkApiClient(
        session=session,
        access_token=entry.data["access_token"],
        iot_token=entry.data["iot_token"],
    )

    coordinator = Ailink352DataUpdateCoordinator(
        hass, api,
        scan_interval=entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
    )
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {"coordinator": coordinator}

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
