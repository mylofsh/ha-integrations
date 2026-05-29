"""352 Air Purifier - Config Flow."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import AilinkApiClient
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required("access_token"): str,
        vol.Required("iot_token"): str,
        vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): vol.All(
            vol.Coerce(int), vol.Range(min=10, max=600)
        ),
    }
)


class Ailink352ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle config flow for 352 Air Purifier."""

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
                    access_token=user_input["access_token"],
                    iot_token=user_input["iot_token"],
                )
                devices = await api.list_devices()
                if devices:
                    device_names = []
                    for dev in devices:
                        name = dev.get("nickname") or dev.get("productName", "")
                        device_names.append(name)
                    title = "352 " + ", ".join(device_names[:3])
                    if len(device_names) > 3:
                        title += f" +{len(device_names)-3}"

                    return self.async_create_entry(
                        title=title,
                        data={
                            "access_token": user_input["access_token"],
                            "iot_token": user_input["iot_token"],
                            CONF_SCAN_INTERVAL: user_input.get(
                                CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                            ),
                        },
                    )
                errors["base"] = "no_devices"
            except Exception:
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )
