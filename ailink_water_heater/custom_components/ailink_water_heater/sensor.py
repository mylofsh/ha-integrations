"""Sensor entities for AI-LiNK water heater metrics."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import AilinkDataUpdateCoordinator
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# 传感器定义: (key, name, unit, device_class, state_class, icon)
SENSOR_DEFS = [
    ("outWaterTemp", "出水温度", UnitOfTemperature.CELSIUS, SensorDeviceClass.TEMPERATURE, SensorStateClass.MEASUREMENT, None),
    ("inWaterTemp", "进水温度", UnitOfTemperature.CELSIUS, SensorDeviceClass.TEMPERATURE, SensorStateClass.MEASUREMENT, None),
    ("waterFlow", "水流量", "L/min", None, SensorStateClass.MEASUREMENT, "mdi:water"),
    ("fanSpeed", "风机转速", "rpm", None, SensorStateClass.MEASUREMENT, "mdi:fan"),
    ("fireTimes", "点火次数", "次", None, SensorStateClass.TOTAL_INCREASING, "mdi:fire"),
    ("fireWorkTime", "累计运行时间", None, None, SensorStateClass.TOTAL_INCREASING, "mdi:timer"),
    ("totalGasNum", "累计用气量", None, None, SensorStateClass.TOTAL_INCREASING, "mdi:gas-burner"),
    ("totalWaterNum", "累计用水量", "L", None, SensorStateClass.TOTAL_INCREASING, "mdi:water-plus"),
    ("cOConcentration", "CO浓度", "ppm", SensorDeviceClass.CO, SensorStateClass.MEASUREMENT, None),
    ("neutralizerLife", "中和器寿命", "%", None, SensorStateClass.MEASUREMENT, "mdi:percent"),
    ("remainingDays", "滤芯剩余天数", "天", None, SensorStateClass.MEASUREMENT, "mdi:calendar"),
    ("cruisingTotalGasNum", "巡航累计用气", None, None, SensorStateClass.TOTAL_INCREASING, "mdi:gas-burner"),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensors."""
    coordinator: AilinkDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    entities = []
    for device in coordinator.data.get("devices", []):
        device_id = device["deviceId"]
        for key, name, unit, dev_cls, state_cls, icon in SENSOR_DEFS:
            entities.append(
                AilinkSensor(coordinator, device_id, key, name, unit, dev_cls, state_cls, icon)
            )
    async_add_entities(entities)


class AilinkSensor(CoordinatorEntity, SensorEntity):
    """Sensor for a single device metric."""

    def __init__(
        self,
        coordinator: AilinkDataUpdateCoordinator,
        device_id: str,
        key: str,
        name: str,
        unit: str | None,
        device_class: SensorDeviceClass | None,
        state_class: SensorStateClass | None,
        icon: str | None,
    ) -> None:
        super().__init__(coordinator)
        self._device_id = device_id
        self._key = key
        self._attr_name = name
        self._attr_unique_id = f"ailink_{device_id}_{key}"
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class
        self._attr_state_class = state_class
        if icon:
            self._attr_icon = icon

    @property
    def native_value(self) -> str | float | None:
        statuses = self.coordinator.data.get("device_statuses", {})
        raw = statuses.get(self._device_id, {})
        val = raw.get(self._key)
        if val is not None and val != "":
            try:
                return float(val)
            except (ValueError, TypeError):
                return str(val)
        return None

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._device_id)},
        }
