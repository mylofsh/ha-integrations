"""Switch entities for cruise, half-pipe circulation, and pressurize functions."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
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
    """Set up switches."""
    coordinator: AilinkDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    entities = []
    for device in coordinator.data.get("devices", []):
        device_id = device["deviceId"]
        entities.append(AilinkCruiseSwitch(coordinator, device_id))
        entities.append(AilinkHalfPipeCircleSwitch(coordinator, device_id))
        entities.append(AilinkPressurizeSwitch(coordinator, device_id))
    async_add_entities(entities)


class AilinkBaseSwitch(CoordinatorEntity, SwitchEntity):
    """Base switch for AI-LiNK functions."""

    _key: str = ""

    def __init__(self, coordinator: AilinkDataUpdateCoordinator, device_id: str) -> None:
        super().__init__(coordinator)
        self._device_id = device_id
        self._attr_unique_id = f"ailink_{device_id}_{self._key}"

    @property
    def _raw(self) -> dict:
        statuses = self.coordinator.data.get("device_statuses", {})
        return statuses.get(self._device_id, {})

    @property
    def is_on(self) -> bool:
        return self._raw.get(self._key, "0") == "1"

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._device_id)},
        }

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._send_command(True)
        await self._refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._send_command(False)
        await self._refresh()

    async def _refresh(self) -> None:
        """Force refresh coordinator data and update entity state."""
        await self.coordinator.async_request_refresh()
        # 等一小会儿让 refresh 完成后再触发状态更新
        self.async_write_ha_state()

    async def _send_command(self, on: bool) -> None:
        """Override in subclass."""
        raise NotImplementedError


class AilinkCruiseSwitch(AilinkBaseSwitch):
    """Switch for zero-cold-water cruise mode."""

    _key = "cruiseStatus"

    _attr_name = "零冷水巡航"
    _attr_icon = "mdi:water-sync"

    async def _send_command(self, on: bool) -> None:
        await self.coordinator.api.set_cruise(self._device_id, on)


class AilinkHalfPipeCircleSwitch(AilinkBaseSwitch):
    """Switch for energy-saving half-pipe circulation."""

    _key = "halfPipeCirclelStatus"

    _attr_name = "节能半管零冷水"
    _attr_icon = "mdi:pipe"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "half_pipe_circle_show": self._raw.get("halfPipeCirculShow", "0"),
        }

    async def _send_command(self, on: bool) -> None:
        await self.coordinator.api.set_half_pipe_circle(self._device_id, on)


class AilinkPressurizeSwitch(AilinkBaseSwitch):
    """Switch for pressurize function."""

    _key = "pressurize"

    _attr_name = "增压"
    _attr_icon = "mdi:water-booster"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "pressurize_level": self._raw.get("pressurizeLevel", "0"),
            "pressurize_level_show": self._raw.get("pressurizeLevelShow", "0"),
        }

    async def _send_command(self, on: bool) -> None:
        await self.coordinator.api.set_pressurize(self._device_id, on)
