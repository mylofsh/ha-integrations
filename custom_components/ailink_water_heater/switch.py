"""Switch entities for cruise, half-pipe circulation, and pressurize functions.

Uses a button entity for fire-and-forget commands + a switch for actual state.
Button provides instant UI feedback; switch syncs from coordinator.
"""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import AilinkDataUpdateCoordinator
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# 需要双实体（开关用 switch 显示状态，按钮用 button 触发指令）
SWITCH_CONFIGS = [
    ("cruiseStatus", "零冷水巡航", "mdi:water-sync", "set_cruise"),
    ("halfPipeCirclelStatus", "节能半管零冷水", "mdi:pipe", "set_half_pipe_circle"),
    ("pressurize", "增压", "mdi:water-booster", "set_pressurize"),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: AilinkDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    entities = []
    for device in coordinator.data.get("devices", []):
        device_id = device["deviceId"]
        for key, name, icon, _api_method in SWITCH_CONFIGS:
            entities.append(AilinkReadOnlySwitch(coordinator, device_id, key, name, icon))
            entities.append(AilinkCommandButton(coordinator, device_id, key, name, icon))
    async_add_entities(entities)


class AilinkReadOnlySwitch(CoordinatorEntity, SwitchEntity):
    """Read-only switch showing actual device state from coordinator."""

    _attr_should_poll = False
    _attr_assumed_state = False

    def __init__(self, coordinator, device_id, key, name, icon):
        super().__init__(coordinator)
        self._device_id = device_id
        self._key = key
        self._attr_name = name
        self._attr_icon = icon
        self._attr_unique_id = f"ailink_{device_id}_{key}"

    @property
    def _raw(self):
        statuses = self.coordinator.data.get("device_statuses", {})
        return statuses.get(self._device_id, {})

    @property
    def is_on(self):
        return self._raw.get(self._key, "0") == "1"

    @property
    def device_info(self):
        return {"identifiers": {(DOMAIN, self._device_id)}}

    # 不可操作——只读
    async def async_turn_on(self, **kwargs):
        pass

    async def async_turn_off(self, **kwargs):
        pass


class AilinkCommandButton(ButtonEntity):
    """Button that triggers the command — provides instant press feedback."""

    _attr_should_poll = False

    def __init__(self, coordinator, device_id, key, name, icon):
        self._coordinator = coordinator
        self._device_id = device_id
        self._key = key
        self._attr_name = f"{name} 触发"
        self._attr_icon = icon
        self._attr_unique_id = f"ailink_{device_id}_{key}_btn"

    @property
    def device_info(self):
        return {"identifiers": {(DOMAIN, self._device_id)}}

    async def async_press(self) -> None:
        """Toggle the switch: read current state, invert, send command."""
        statuses = self._coordinator.data.get("device_statuses", {})
        raw = statuses.get(self._device_id, {})
        current_on = raw.get(self._key, "0") == "1"

        api = self._coordinator.api

        if self._key == "cruiseStatus":
            await api.set_cruise(self._device_id, not current_on)
        elif self._key == "halfPipeCirclelStatus":
            await api.set_half_pipe_circle(self._device_id, not current_on)
        elif self._key == "pressurize":
            await api.set_pressurize(self._device_id, not current_on)

        await self._coordinator.async_request_refresh()
