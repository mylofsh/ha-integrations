"""Water Heater entity for AI-LiNK gas water heater."""
from __future__ import annotations

import json
import logging
from typing import Any

from homeassistant.components.water_heater import (
    WaterHeaterEntity,
    WaterHeaterEntityFeature,
    STATE_GAS,
    STATE_OFF,
    STATE_ELECTRIC,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_TEMPERATURE,
    PRECISION_WHOLE,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
)

from . import AilinkDataUpdateCoordinator
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

STATUS_KEYS = [
    "powerOn", "powerStatus", "waterTemp", "outWaterTemp", "inWaterTemp",
    "waterFlow", "cruiseStatus", "pressurize", "pressurizeLevel",
    "mute", "antifreeze", "fireTimes", "fireWorkTime",
    "totalGasNum", "totalWaterNum", "errorCode", "cOConcentration",
    "workStatus", "fanSpeed", "boiling",
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up AI-LiNK water heater from config entry."""
    coordinator: AilinkDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    entities = []
    for device in coordinator.data.get("devices", []):
        entities.append(AilinkWaterHeater(coordinator, device))
    async_add_entities(entities)


class AilinkWaterHeater(CoordinatorEntity, WaterHeaterEntity):
    """Representation of an AI-LiNK gas water heater."""

    _attr_supported_features = (
        WaterHeaterEntityFeature.TARGET_TEMPERATURE
        | WaterHeaterEntityFeature.ON_OFF
        | WaterHeaterEntityFeature.OPERATION_MODE
    )
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_precision = PRECISION_WHOLE
    _attr_min_temp = 35
    _attr_max_temp = 60

    def __init__(self, coordinator: AilinkDataUpdateCoordinator, device_info: dict) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._device_info = device_info
        self._device_id = device_info["deviceId"]
        product_name = device_info.get("productName", "热水器")
        room_name = device_info.get("roomName", "")
        self._attr_name = f"{product_name} {room_name}" if room_name else product_name
        self._attr_unique_id = f"ailink_{self._device_id}"
        self._product_img = device_info.get("productImg", "")
        # 乐观状态
        self._optimistic_power: bool | None = None
        self._optimistic_temp: float | None = None

    @property
    def entity_picture(self) -> str | None:
        return self._product_img or None

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._device_id)},
            "name": self._attr_name,
            "manufacturer": "A.O.Smith",
            "model": self._raw_status.get("deviceModel", self._device_info.get("deviceType", "")),
            "sw_version": self._raw_status.get("displayVersion", ""),
        }

    @property
    def _raw_status(self) -> dict:
        statuses = self.coordinator.data.get("device_statuses", {})
        return statuses.get(self._device_id, {})

    @property
    def current_temperature(self) -> float | None:
        val = self._raw_status.get("outWaterTemp")
        if val is not None:
            try:
                return float(val)
            except (ValueError, TypeError):
                pass
        return None

    @property
    def target_temperature(self) -> float | None:
        if self._optimistic_temp is not None:
            return self._optimistic_temp
        val = self._raw_status.get("waterTemp")
        if val is not None:
            try:
                return float(val)
            except (ValueError, TypeError):
                pass
        return None

    @property
    def current_operation(self) -> str:
        if self._optimistic_power is not None:
            if not self._optimistic_power:
                return STATE_OFF
            return STATE_ELECTRIC
        power = self._raw_status.get("powerStatus", "0")
        if power == "0":
            return STATE_OFF
        work = self._raw_status.get("workStatus", 0)
        if work and int(work) > 0:
            return STATE_GAS
        return STATE_ELECTRIC

    @property
    def operation_list(self) -> list[str]:
        return [STATE_GAS, STATE_ELECTRIC, STATE_OFF]

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        attrs = {}
        raw = self._raw_status
        for key in STATUS_KEYS:
            if key in raw:
                attrs[key] = raw[key]
        attrs["device_id"] = self._device_id
        attrs["product_name"] = self._device_info.get("productName", "")
        attrs["room_name"] = self._device_info.get("roomName", "")
        attrs["error_count"] = self._device_info.get("errorCount", 0)
        attrs["dev_state"] = self._device_info.get("devState", 0)
        error_code = raw.get("errorCode", "00")
        attrs["fault_code"] = error_code
        attrs["fault_text"] = self._error_text(error_code)
        return attrs

    @staticmethod
    def _error_text(code: str) -> str:
        error_map = {
            "00": "正常", "E1": "点火失败", "E2": "意外熄火",
            "E3": "超温保护", "E4": "风机故障", "E5": "风压开关故障",
            "E6": "出水温度传感器故障", "E7": "进水温度传感器故障",
            "E8": "火焰检测故障", "F1": "燃气阀故障", "F2": "通讯故障",
            "F3": "水流量传感器故障", "F4": "CO报警", "F6": "EEPROM故障",
        }
        return error_map.get(code, f"未知故障({code})")

    def _handle_coordinator_update(self) -> None:
        """Clear optimistic state when coordinator refreshes."""
        self._optimistic_power = None
        self._optimistic_temp = None
        super()._handle_coordinator_update()

    async def async_set_temperature(self, **kwargs: Any) -> None:
        temp = kwargs.get(ATTR_TEMPERATURE)
        if temp is None:
            return
        temp_int = int(round(float(temp)))
        self._optimistic_temp = float(temp_int)
        self.async_write_ha_state()
        try:
            await self.coordinator.api.set_temperature(self._device_id, temp_int)
        except Exception:
            self._optimistic_temp = None
            self.async_write_ha_state()
            raise
        await self.coordinator.async_request_refresh()

    async def async_set_operation_mode(self, operation_mode: str) -> None:
        if operation_mode == STATE_OFF:
            await self._set_power(False)
        else:
            await self._set_power(True)

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._set_power(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._set_power(False)

    async def _set_power(self, on: bool) -> None:
        self._optimistic_power = on
        self.async_write_ha_state()
        try:
            await self.coordinator.api.set_power(self._device_id, on)
        except Exception:
            self._optimistic_power = None
            self.async_write_ha_state()
            raise
        await self.coordinator.async_request_refresh()
