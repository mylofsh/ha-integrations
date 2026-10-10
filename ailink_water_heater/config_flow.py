"""AI-LiNK Water Heater - Config Flow & Options Flow.

首次添加集成走 async_step_user（原有逻辑不变）。
添加后可通过「配置 → 选项」单独更新 token，无需删除重建集成。
"""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import AilinkApiClient
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required("token"): str,
        vol.Required("user_id"): str,
        vol.Required("family_id"): str,
        vol.Required("device_id"): str,
        vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): vol.All(
            vol.Coerce(int), vol.Range(min=10, max=600)
        ),
    }
)

# 选项表单：仅暴露需要手动维护的字段（token 更新为主）
STEP_OPTIONS_SCHEMA = vol.Schema(
    {
        vol.Required("token"): str,
        vol.Optional("user_id"): str,
        vol.Optional("family_id"): str,
        vol.Optional("device_id"): str,
        vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): vol.All(
            vol.Coerce(int), vol.Range(min=10, max=600)
        ),
    }
)


class AilinkConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for AI-LiNK Water Heater."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                session = async_get_clientsession(self.hass)
                api = AilinkApiClient(
                    session=session,
                    token=user_input["token"],
                    user_id=user_input["user_id"],
                    family_id=user_input["family_id"],
                )
                # 验证：用 device_id 调 getDeviceCurrInfo 是否成功
                result = await api.get_device_curr_info(user_input["device_id"])
                if result.get("status") == 200:
                    return self.async_create_entry(
                        title=f"AI-LiNK 燃气热水器 ({user_input['device_id']})",
                        data={
                            "token": user_input["token"],
                            "user_id": user_input["user_id"],
                            "family_id": user_input["family_id"],
                            "device_id": user_input["device_id"],
                            CONF_SCAN_INTERVAL: user_input.get(
                                CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                            ),
                        },
                    )
                errors["base"] = "auth_failed"
            except Exception:
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> "AilinkOptionsFlow":
        """Register the options flow."""
        return AilinkOptionsFlow()


class AilinkOptionsFlow(config_entries.OptionsFlow):
    """更新 token 等凭据，无需删除重建集成。

    进入路径：设置 → 设备与服务 → AI-LiNK 燃气热水器 → 配置 → 选项
    填入新 token 后保存即生效，集成会自动重载。
    """

    def __init__(self) -> None:
        self._errors: dict[str, str] = {}

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """显示并处理 token 更新表单。"""
        # 当前生效值 = options 覆盖 data（options 优先）
        current = {**self.config_entry.data, **self.config_entry.options}

        if user_input is not None:
            # 空字符串视为「不修改」，保留原值
            new_data = dict(current)
            for key in ("token", "user_id", "family_id", "device_id"):
                val = (user_input.get(key) or "").strip()
                if val:
                    new_data[key] = val
            if CONF_SCAN_INTERVAL in user_input:
                new_data[CONF_SCAN_INTERVAL] = user_input[CONF_SCAN_INTERVAL]

            try:
                session = async_get_clientsession(self.hass)
                api = AilinkApiClient(
                    session=session,
                    token=new_data["token"],
                    user_id=new_data["user_id"],
                    family_id=new_data["family_id"],
                )
                result = await api.get_device_curr_info(new_data["device_id"])
                if result.get("status") != 200:
                    self._errors["base"] = "auth_failed"
                else:
                    # 写入 options 并触发重载，使新 token 立即生效。
                    # 关键：只把**非空**字段写入 options，空值会在下次
                    # 合并 {**data, **options} 时覆盖掉 data 中的有效值。
                    new_options = {
                        k: v
                        for k, v in new_data.items()
                        if k != "token" and v not in (None, "")
                    }
                    self.hass.config_entries.async_update_entry(
                        self.config_entry,
                        data={**self.config_entry.data, "token": new_data["token"]},
                        options=new_options,
                    )
                    await self.hass.config_entries.async_reload(
                        self.config_entry.entry_id
                    )
                    return self.async_create_entry(title="", data={})
            except Exception:
                self._errors["base"] = "unknown"

        schema = self.add_suggested_values_to_schema(
            STEP_OPTIONS_SCHEMA,
            {
                "token": current.get("token", ""),
                "user_id": current.get("user_id", ""),
                "family_id": current.get("family_id", ""),
                "device_id": current.get("device_id", ""),
                CONF_SCAN_INTERVAL: current.get(
                    CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                ),
            },
        )

        return self.async_show_form(
            step_id="init",
            data_schema=schema,
            errors=self._errors,
            description_placeholders={
                "device_id": current.get("device_id", ""),
            },
        )
