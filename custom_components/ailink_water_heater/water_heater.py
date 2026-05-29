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

# 将设备状态字段映射到 HA 属性
STATUS_KEYS = [
    "powerOn",         # 通电状态
    "powerStatus",     # 开关机
    "waterTemp",       # 设定水温
    "outWaterTemp",    # 出水温度
    "inWaterTemp",     # 进水温度
    "waterFlow",       # 水流量
    "cruiseStatus",    # 零冷水巡航
    "pressurize",      # 增压
    "pressurizeLevel", # 增压档位
    "mute",            # 静音
    "antifreeze",      # 防冻
    "fireTimes",       # 点火次数
    "fireWorkTime",    # 运行时间
    "totalGasNum",     # 累计用气
    "totalWaterNum",   # 累计用水
    "errorCode",       # 故障码
    "cOConcentration", # CO浓度
    "workStatus",      # 工作状态
    "fanSpeed",        # 风机转速
    "boiling",         # 沸腾状态
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
    _attr_max_temp = 60  # JSQ48 系列通常 35-60℃

    def __init__(self, coordinator: AilinkDataUpdateCoordinator, device_info: dict) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._device_info = device_info
        self._device_id = device_info["deviceId"]
        product_name = device_info.get("productName", "热水器")
        room_name = device_info.get("roomName", "")
        self._attr_name = f"{product_name} {room_name}" if room_name else product_name
        self._attr_unique_id = f"ailink_{self._device_id}"
        # 设备产品图片
        self._product_img = device_info.get("productImg", "")

    @property
    def entity_picture(self) -> str | None:
        """Return entity picture URL."""
        return self._product_img or None

    @property
    def device_info(self):
        """Return device info."""
        return {
            "identifiers": {(DOMAIN, self._device_id)},
            "name": self._attr_name,
            "manufacturer": "A.O.Smith",
            "model": self._raw_status.get("deviceModel", self._device_info.get("deviceType", "")),
            "sw_version": self._raw_status.get("displayVersion", ""),
        }

    @property
    def _raw_status(self) -> dict:
        """Get raw device status from coordinator data."""
        statuses = self.coordinator.data.get("device_statuses", {})
        return statuses.get(self._device_id, {})

    @property
    def current_temperature(self) -> float | None:
        """Return current outlet water temperature."""
        val = self._raw_status.get("outWaterTemp")
        if val is not None:
            try:
                return float(val)
            except (ValueError, TypeError):
                pass
        return None

    @property
    def target_temperature(self) -> float | None:
        """Return target water temperature."""
        val = self._raw_status.get("waterTemp")
        if val is not None:
            try:
                return float(val)
            except (ValueError, TypeError):
                pass
        return None

    @property
    def current_operation(self) -> str:
        """Return current operation."""
        power = self._raw_status.get("powerStatus", "0")
        if power == "0":
            return STATE_OFF
        work = self._raw_status.get("workStatus", 0)
        if work and int(work) > 0:
            return STATE_GAS  # 正在燃烧
        return STATE_ELECTRIC  # 待机

    @property
    def operation_list(self) -> list[str]:
        """List of available operation modes."""
        return [STATE_GAS, STATE_ELECTRIC, STATE_OFF]

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        attrs = {}
        raw = self._raw_status
        for key in STATUS_KEYS:
            if key in raw:
                attrs[key] = raw[key]

        # 加入设备基础信息
        attrs["device_id"] = self._device_id
        attrs["product_name"] = self._device_info.get("productName", "")
        attrs["room_name"] = self._device_info.get("roomName", "")
        attrs["error_count"] = self._device_info.get("errorCount", 0)
        attrs["dev_state"] = self._device_info.get("devState", 0)

        # 解析故障码
        error_code = raw.get("errorCode", "00")
        attrs["fault_code"] = error_code
        attrs["fault_text"] = self._error_text(error_code)

        return attrs

    @staticmethod
    def _error_text(code: str) -> str:
        """Translate error code to human-readable text."""
        error_map = {
            "00": "正常",
            "E1": "点火失败",
            "E2": "意外熄火",
            "E3": "超温保护",
            "E4": "风机故障",
            "E5": "风压开关故障",
            "E6": "出水温度传感器故障",
            "E7": "进水温度传感器故障",
            "E8": "火焰检测故障",
            "F1": "燃气阀故障",
            "F2": "通讯故障",
            "F3": "水流量传感器故障",
            "F4": "CO报警",
            "F6": "EEPROM故障",
        }
        return error_map.get(code, f"未知故障({code})")

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set target temperature."""
        temp = kwargs.get(ATTR_TEMPERATURE)
        if temp is None:
            return
        temp_int = int(round(float(temp)))
        await self.coordinator.api.set_temperature(self._device_id, temp_int)

    async def async_set_operation_mode(self, operation_mode: str) -> None:
        """Set operation mode."""
        if operation_mode == STATE_OFF:
            await self.coordinator.api.set_power(self._device_id, False)
        else:
            await self.coordinator.api.set_power(self._device_id, True)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on."""
        await self.coordinator.api.set_power(self._device_id, True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off."""
        await self.coordinator.api.set_power(self._device_id, False)
