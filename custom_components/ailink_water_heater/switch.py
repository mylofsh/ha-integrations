"""Switch entities for cruise, half-pipe circulation, and pressurize functions."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import AilinkDataUpdateCoordinator
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: AilinkDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    entities = []
    for device in coordinator.data.get("devices", []):
        device_id = device["deviceId"]
        entities.append(AilinkCruiseSwitch(coordinator, device_id))
        entities.append(AilinkHalfPipeCircleSwitch(coordinator, device_id))
        entities.append(AilinkPressurizeSwitch(coordinator, device_id))
    async_add_entities(entities)


class AilinkBaseSwitch(SwitchEntity):
    """Switch: click → immediately shows new state → syncs from server on next poll."""

    _key: str = ""

    def __init__(self, coordinator: AilinkDataUpdateCoordinator, device_id: str) -> None:
        self._coordinator = coordinator
        self._device_id = device_id
        self._attr_unique_id = f"ailink_{device_id}_{self._key}"
        statuses = coordinator.data.get("device_statuses", {})
        raw = statuses.get(device_id, {})
        self._attr_is_on = raw.get(self._key, "0") == "1"

    @property
    def _raw(self) -> dict:
        statuses = self._coordinator.data.get("device_statuses", {})
        return statuses.get(self._device_id, {})

    @property
    def available(self) -> bool:
        return self._coordinator.last_update_success

    @property
    def should_poll(self) -> bool:
        return False

    @property
    def device_info(self):
        return {"identifiers": {(DOMAIN, self._device_id)}}

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            self._coordinator.async_add_listener(self._on_coordinator_update)
        )

    @callback
    def _on_coordinator_update(self) -> None:
        """Sync actual state from server on next poll."""
        self._attr_is_on = self._raw.get(self._key, "0") == "1"
        self.async_write_ha_state()

    async def async_turn_on(self, **kwargs: Any) -> None:
        # 立即乐观更新
        self._attr_is_on = True
        self.async_write_ha_state()
        # 后台发指令
        self.hass.async_create_task(self._send_and_sync(True))

    async def async_turn_off(self, **kwargs: Any) -> None:
        self._attr_is_on = False
        self.async_write_ha_state()
        self.hass.async_create_task(self._send_and_sync(False))

    async def _send_and_sync(self, on: bool) -> None:
        """Send command in background, then refresh."""
        try:
            await self._send_command(on)
        except Exception:
            # 失败回退到服务器状态
            self._attr_is_on = self._raw.get(self._key, "0") == "1"
            self.async_write_ha_state()
            raise
        await self._coordinator.async_request_refresh()

    async def _send_command(self, on: bool) -> None:
        raise NotImplementedError


class AilinkCruiseSwitch(AilinkBaseSwitch):
    _key = "cruiseStatus"
    _attr_name = "零冷水巡航"
    _attr_icon = "mdi:water-sync"

    async def _send_command(self, on: bool) -> None:
        await self._coordinator.api.set_cruise(self._device_id, on)


class AilinkHalfPipeCircleSwitch(AilinkBaseSwitch):
    _key = "halfPipeCirclelStatus"
    _attr_name = "节能半管零冷水"
    _attr_icon = "mdi:pipe"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"half_pipe_circle_show": self._raw.get("halfPipeCirculShow", "0")}

    async def _send_command(self, on: bool) -> None:
        await self._coordinator.api.set_half_pipe_circle(self._device_id, on)


class AilinkPressurizeSwitch(AilinkBaseSwitch):
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
        await self._coordinator.api.set_pressurize(self._device_id, on)
