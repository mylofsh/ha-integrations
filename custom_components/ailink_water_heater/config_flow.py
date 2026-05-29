"""AI-LiNK Water Heater - Config Flow."""
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
                            CONF_SCAN_INTERVAL: user_input.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
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
