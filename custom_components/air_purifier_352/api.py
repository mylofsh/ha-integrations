"""API client for 352 Air Purifier via Aliyun IoT."""
from __future__ import annotations

import json
import time
import uuid
from typing import Any

import aiohttp

from .const import ALIYUN_BASE, APP_KEY


class AilinkApiClient:
    """Async API client for 352 air purifier."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        access_token: str,
        iot_token: str,
    ):
        self._session = session
        self._access_token = access_token
        self._iot_token = iot_token

    def _iot_headers(self) -> dict:
        return {
            "Content-Type": "application/json",
        }

    def _iot_body(self, path: str, params: dict) -> dict:
        return {
            "id": str(uuid.uuid4()).upper(),
            "params": params,
            "request": {
                "language": "zh-CN",
                "appKey": APP_KEY,
                "iotToken": self._iot_token,
                "apiVer": "1.0.4",
            },
        }

    # ---- 阿里云 IoT API ----

    async def list_devices(self) -> list[dict]:
        """List bound devices."""
        body = self._iot_body(
            "/uc/listBindingByAccount",
            {"pageSize": 50, "pageNo": 1},
        )
        async with self._session.post(
            f"{ALIYUN_BASE}/uc/listBindingByAccount",
            json=body, headers=self._iot_headers(),
        ) as resp:
            data = await resp.json()
            if data.get("code") == 200:
                return data["data"]["data"]
            return []

    async def get_properties(self, iot_id: str) -> dict:
        """Get all device properties."""
        body = self._iot_body(
            "/thing/properties/get",
            {"iotId": iot_id},
        )
        async with self._session.post(
            f"{ALIYUN_BASE}/thing/properties/get",
            json=body, headers=self._iot_headers(),
        ) as resp:
            data = await resp.json()
            if data.get("code") == 200:
                result = {}
                for key, val in data["data"].items():
                    result[key] = val.get("value")
                return result
            return {}

    async def set_properties(self, iot_id: str, items: dict[str, Any]) -> dict:
        """Set device properties."""
        body = self._iot_body(
            "/thing/properties/set",
            {"iotId": iot_id, "items": items},
        )
        async with self._session.post(
            f"{ALIYUN_BASE}/thing/properties/set",
            json=body, headers=self._iot_headers(),
        ) as resp:
            return await resp.json()

    # ---- 352 自有 API ----

    async def get_device_info(self, iot_id: str) -> dict:
        """Get device info from 352 API."""
        headers = {
            "Authorization": f"Token {self._access_token}",
        }
        async with self._session.get(
            f"https://app.352air.com/api/device/info/{iot_id}",
            headers=headers,
        ) as resp:
            data = await resp.json()
            if data.get("code") == 0:
                return data.get("data", {})
            return {}
