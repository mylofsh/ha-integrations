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
    """Base switch for AI-LiNK functions.

    Uses optimistic state: immediately updates the switch UI after sending
    the command, then lets the next coordinator poll cycle sync from the API.
    """

    _key: str = ""
    _optimistic: bool | None = None

    def __init__(self, coordinator: AilinkDataUpdateCoordinator, device_id: str) -> None:
        super().__init__(coordinator)
        self._device_id = device_id
        self._attr_unique_id = f"ailink_{device_id}_{self._key}"
        # 确保 is_on 不走 cache
        self._attr_assumed_state = True

    @property
    def _raw(self) -> dict:
        statuses = self.coordinator.data.get("device_statuses", {})
        return statuses.get(self._device_id, {})

    @property
    def is_on(self) -> bool:
        # 有未同步的乐观状态，直接用乐观值
        if self._optimistic is not None:
            return self._optimistic
        return self._raw.get(self._key, "0") == "1"

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._device_id)},
        }

    async def async_turn_on(self, **kwargs: Any) -> None:
        self._optimistic = True
        self.async_write_ha_state()
        try:
            await self._send_command(True)
        except Exception:
            self._optimistic = None
            self.async_write_ha_state()
            raise
        # 后台刷新，下一个周期会自动同步
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        self._optimistic = False
        self.async_write_ha_state()
        try:
            await self._send_command(False)
        except Exception:
            self._optimistic = None
            self.async_write_ha_state()
            raise
        await self.coordinator.async_request_refresh()

    def _handle_coordinator_update(self) -> None:
        """Clear optimistic state when coordinator updates."""
        self._optimistic = None
        super()._handle_coordinator_update()

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
