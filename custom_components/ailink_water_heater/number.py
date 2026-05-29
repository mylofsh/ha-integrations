"""Number entity for one-key cruise timer duration."""
from __future__ import annotations

import logging

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import AilinkDataUpdateCoordinator
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up number entities."""
    coordinator: AilinkDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    entities = []
    for device in coordinator.data.get("devices", []):
        entities.append(AilinkCruiseTimer(coordinator, device["deviceId"]))
    async_add_entities(entities)


class AilinkCruiseTimer(CoordinatorEntity, NumberEntity):
    """One-key zero-cold-water cruise timer duration (minutes)."""

    _attr_name = "一键零冷水时长"
    _attr_icon = "mdi:timer-outline"
    _attr_native_unit_of_measurement = "分钟"
    _attr_native_min_value = 1
    _attr_native_max_value = 120
    _attr_native_step = 1
    _attr_mode = NumberMode.SLIDER

    def __init__(self, coordinator: AilinkDataUpdateCoordinator, device_id: str) -> None:
        super().__init__(coordinator)
        self._device_id = device_id
        self._attr_unique_id = f"ailink_{device_id}_cruise_timer"

    @property
    def native_value(self) -> float | None:
        statuses = self.coordinator.data.get("device_statuses", {})
        raw = statuses.get(self._device_id, {})
        val = raw.get("WaterCruiseTimer")
        if val is not None and val != "":
            try:
                return float(val)
            except (ValueError, TypeError):
                pass
        return None

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._device_id)},
        }

    async def async_set_native_value(self, value: float) -> None:
        """Set timer duration."""
        minutes = int(value)
        await self.coordinator.api.set_cruise_timer(self._device_id, minutes)
