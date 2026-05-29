"""Switch entities for 352 Air Purifier: UV LED, PCI, Child Lock."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import Ailink352DataUpdateCoordinator
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

SWITCH_DEFS = [
    ("UVLEDSwitch", "UV LED灯", "mdi:uv-ray"),
    ("PCISwitch", "等离子", "mdi:lightning-bolt"),
    ("ChildLockSwitch", "童锁", "mdi:lock"),
    ("SmartModeSwitch", "智能模式", "mdi:brain"),
    ("StandbySensorSwitch", "待机传感器", "mdi:motion-sensor"),
    ("MicrowaveSensor", "微波传感器", "mdi:radar"),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: Ailink352DataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    entities = []
    for device in coordinator.data.get("devices", []):
        iot_id = device["iotId"]
        for key, name, icon in SWITCH_DEFS:
            entities.append(Ailink352Switch(coordinator, iot_id, key, name, icon))
    async_add_entities(entities)


class Ailink352Switch(CoordinatorEntity, SwitchEntity):
    """Switch for 352 purifier functions."""

    def __init__(
        self,
        coordinator: Ailink352DataUpdateCoordinator,
        iot_id: str,
        key: str,
        name: str,
        icon: str,
    ) -> None:
        super().__init__(coordinator)
        self._iot_id = iot_id
        self._key = key
        self._attr_name = name
        self._attr_icon = icon
        self._attr_unique_id = f"352_{iot_id[-8:]}_{key}"

    @property
    def _raw(self) -> dict:
        return self.coordinator.data.get("device_statuses", {}).get(self._iot_id, {})

    @property
    def is_on(self) -> bool:
        return self._raw.get(self._key) == 1

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._iot_id)},
        }

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.api.set_properties(self._iot_id, {self._key: 1})

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.api.set_properties(self._iot_id, {self._key: 0})
