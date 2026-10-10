"""Fan entity for 352 Air Purifier."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util.percentage import (
    percentage_to_ranged_value,
    ranged_value_to_percentage,
)

from . import Ailink352DataUpdateCoordinator
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Z90 风速：0=关, 1-5 档
SPEED_RANGE = (1, 5)

# 模式映射
MODE_MAP = {
    0: "auto",      # 手动/自动
    1: "sleep",
    2: "manual",
}
MODE_REVERSE = {v: k for k, v in MODE_MAP.items()}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: Ailink352DataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    entities = []
    for device in coordinator.data.get("devices", []):
        entities.append(Ailink352Fan(coordinator, device["iotId"], device["name"]))
    async_add_entities(entities)


class Ailink352Fan(CoordinatorEntity, FanEntity):
    """352 Air Purifier as a Fan entity."""

    _attr_supported_features = (
        FanEntityFeature.SET_SPEED
        | FanEntityFeature.PRESET_MODE
        | FanEntityFeature.TURN_ON
        | FanEntityFeature.TURN_OFF
    )
    _attr_preset_modes = ["auto", "manual", "sleep"]
    _attr_speed_count = 5

    def __init__(
        self,
        coordinator: Ailink352DataUpdateCoordinator,
        iot_id: str,
        name: str,
    ) -> None:
        super().__init__(coordinator)
        self._iot_id = iot_id
        self._attr_name = name
        self._attr_unique_id = f"352_{iot_id[-8:]}"

    @property
    def _raw(self) -> dict:
        return self.coordinator.data.get("device_statuses", {}).get(self._iot_id, {})

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._iot_id)},
            "name": self._attr_name,
            "manufacturer": "352",
        }

    @property
    def is_on(self) -> bool:
        return self._raw.get("PowerSwitch") == 1

    @property
    def percentage(self) -> int | None:
        """Speed as percentage 0-100."""
        speed = self._raw.get("WindSpeed", 0)
        if speed == 0:
            return 0
        return ranged_value_to_percentage(SPEED_RANGE, speed)

    @property
    def preset_mode(self) -> str | None:
        mode = self._raw.get("WorkMode", 0)
        return MODE_MAP.get(mode)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        raw = self._raw
        return {
            "device_mode": raw.get("DeviceMode"),
            "child_lock": raw.get("ChildLockSwitch") == 1,
            "uv_led": raw.get("UVLEDSwitch") == 1,
            "pci": raw.get("PCISwitch") == 1,
            "smart_mode": raw.get("SmartModeSwitch") == 1,
            "voice": raw.get("voicesettings"),
            "wifi_rssi": raw.get("WiFI_RSSI"),
            "total_run_time": raw.get("TotalRunTime"),
            "air_quality_grade": raw.get("airQualityGrade"),
        }

    async def async_turn_on(self, percentage=None, preset_mode=None, **kwargs):
        if percentage is None:
            percentage = 50
        items = {"PowerSwitch": 1}
        if preset_mode:
            items["WorkMode"] = MODE_REVERSE.get(preset_mode, 0)
        await self.coordinator.api.set_properties(self._iot_id, items)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs):
        await self.coordinator.api.set_properties(self._iot_id, {"PowerSwitch": 0})
        await self.coordinator.async_request_refresh()

    async def async_set_percentage(self, percentage: int):
        speed = int(round(percentage_to_ranged_value(SPEED_RANGE, percentage)))
        items = {"WindSpeed": speed}
        if self._raw.get("PowerSwitch") != 1:
            items["PowerSwitch"] = 1
        await self.coordinator.api.set_properties(self._iot_id, items)
        await self.coordinator.async_request_refresh()

    async def async_set_preset_mode(self, preset_mode: str):
        mode = MODE_REVERSE.get(preset_mode, 0)
        await self.coordinator.api.set_properties(self._iot_id, {"WorkMode": mode})
        await self.coordinator.async_request_refresh()
