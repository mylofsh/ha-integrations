"""Sensor entities for 352 Air Purifier."""
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
    CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
    PERCENTAGE,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import Ailink352DataUpdateCoordinator
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

SENSOR_DEFS = [
    ("PM25", "PM2.5", CONCENTRATION_MICROGRAMS_PER_CUBIC_METER, SensorDeviceClass.PM25, SensorStateClass.MEASUREMENT),
    ("PM10", "PM10", CONCENTRATION_MICROGRAMS_PER_CUBIC_METER, SensorDeviceClass.PM10, SensorStateClass.MEASUREMENT),
    ("HCHO", "甲醛", CONCENTRATION_MICROGRAMS_PER_CUBIC_METER, None, SensorStateClass.MEASUREMENT),
    ("TVOC", "TVOC", CONCENTRATION_MICROGRAMS_PER_CUBIC_METER, SensorDeviceClass.VOLATILE_ORGANIC_COMPOUNDS, SensorStateClass.MEASUREMENT),
    ("CurrentTemperature", "温度", UnitOfTemperature.CELSIUS, SensorDeviceClass.TEMPERATURE, SensorStateClass.MEASUREMENT),
    ("RelativeHumidity", "湿度", PERCENTAGE, SensorDeviceClass.HUMIDITY, SensorStateClass.MEASUREMENT),
    ("TotalRunTime", "累计运行时间", "h", None, SensorStateClass.TOTAL_INCREASING),
    ("TotalPurAirV", "累计净化量", "m³", None, SensorStateClass.TOTAL_INCREASING),
    ("FilterLifeTimeDays_1", "滤芯1剩余天数", "天", None, SensorStateClass.MEASUREMENT),
    ("FilterLifeTimeDays_2", "滤芯2剩余天数", "天", None, SensorStateClass.MEASUREMENT),
    ("FilterLifeTimeDays_3", "滤芯3剩余天数", "天", None, SensorStateClass.MEASUREMENT),
    ("FilterLifeTimePercent_1", "滤芯1剩余", PERCENTAGE, None, SensorStateClass.MEASUREMENT),
    ("FilterLifeTimePercent_2", "滤芯2剩余", PERCENTAGE, None, SensorStateClass.MEASUREMENT),
    ("FilterLifeTimePercent_3", "滤芯3剩余", PERCENTAGE, None, SensorStateClass.MEASUREMENT),
]

# 需要转换的值（原始值除以10或100）
DIV_FIELDS = {
    "CurrentTemperature": 10,   # 327.6 -> 32.8℃
    "RelativeHumidity": 10,     # 327.6 -> 32.8%
    "TotalPurAirV": 100,        # 32765 -> 327.65 m³
}

# 65535 = 传感器离线/无效
INVALID_VALUES = {65535, 255, 327.6}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: Ailink352DataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    entities = []
    for device in coordinator.data.get("devices", []):
        iot_id = device["iotId"]
        for key, name, unit, dev_class, state_class in SENSOR_DEFS:
            entities.append(Ailink352Sensor(
                coordinator, iot_id, key, name, unit, dev_class, state_class,
            ))
    async_add_entities(entities)


class Ailink352Sensor(CoordinatorEntity, SensorEntity):
    """Sensor for 352 air purifier metrics."""

    def __init__(
        self,
        coordinator: Ailink352DataUpdateCoordinator,
        iot_id: str,
        key: str,
        name: str,
        unit: str | None,
        device_class: str | None,
        state_class: str | None,
    ) -> None:
        super().__init__(coordinator)
        self._iot_id = iot_id
        self._key = key
        self._attr_name = name
        self._attr_unique_id = f"352_{iot_id[-8:]}_{key}"
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class
        self._attr_state_class = state_class

    @property
    def _raw(self) -> dict:
        return self.coordinator.data.get("device_statuses", {}).get(self._iot_id, {})

    @property
    def native_value(self) -> float | int | None:
        val = self._raw.get(self._key)
        if val is None:
            return None
        try:
            num = float(val)
        except (ValueError, TypeError):
            return val  # string values

        # 65535/255 = 传感器离线
        if num in INVALID_VALUES or num >= 65535:
            return None

        # 某些字段需要除以 10 得到真实值
        if self._key in DIV_FIELDS:
            num /= DIV_FIELDS[self._key]

        if self._attr_device_class == SensorDeviceClass.TEMPERATURE:
            return round(num, 1)
        return round(num)

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._iot_id)},
        }
