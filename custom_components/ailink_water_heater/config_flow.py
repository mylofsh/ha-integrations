"""AI-LiNK Water Heater - Config Flow."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import AilinkApiClient
from .const import BASE_URL, DOMAIN

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required("token"): str,
        vol.Required("user_id"): str,
        vol.Required("family_id"): str,
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
                # 用提供的 token 尝试获取首页数据来验证
                session = async_get_clientsession(self.hass)
                api = AilinkApiClient(
                    session=session,
                    base_url=BASE_URL,
                    token=user_input["token"],
                    user_id=user_input["user_id"],
                    family_id=user_input["family_id"],
                )
                result = await api.get_homepage()
                if result.get("status") == 200:
                    devices = result.get("info", {}).get("devInfoItemInfoList", [])
                    device_names = [d.get("productName", d.get("deviceId", "")) for d in devices]
                    title = "AI-LiNK " + ", ".join(device_names) if device_names else f"AI-LiNK ({user_input['user_id']})"

                    return self.async_create_entry(
                        title=title,
                        data={
                            "token": user_input["token"],
                            "user_id": user_input["user_id"],
                            "family_id": user_input["family_id"],
                        },
                    )
                errors["base"] = "auth_failed"
            except Exception as e:
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
            description_placeholders={
                "token_hint": "从抓包中获取 Authorization: Bearer 后面的值",
                "user_id_hint": "抓包 body 中的 userId",
                "family_id_hint": "抓包 body 中的 familyId",
            },
        )
