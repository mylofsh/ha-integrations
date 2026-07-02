"""API client for 352 Air Purifier via Aliyun IoT."""
from __future__ import annotations

import json
import time
import uuid
from typing import Any

import aiohttp

from .const import ALIYUN_BASE, APP_KEY

API_352_BASE = "https://app.352air.com"


class AilinkApiClient:
    """Async API client for 352 air purifier."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        access_token: str,
        refresh_token: str,
        iot_token: str,
    ):
        self._session = session
        self._access_token = access_token
        self._refresh_token = refresh_token
        self._iot_token = iot_token

    # ---- Token 刷新 ----

    async def refresh_access_token(self) -> bool:
        """Refresh the 352 access_token using refresh_token."""
        resp = await self._post_json(
            f"{API_352_BASE}/api/v1/enduser/refresh_token",
            {"refresh_token": self._refresh_token},
            {"Authorization": f"Token {self._access_token}"},
        )
        if resp.get("code") == 0:
            data = resp["data"]
            self._access_token = data["access_token"]
            self._refresh_token = data.get("refresh_token", self._refresh_token)
            return True
        return False

    # ---- 阿里云 IoT ----

    def _iot_headers(self) -> dict:
        return {"Content-Type": "application/json"}

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

    async def list_devices(self) -> list[dict]:
        body = self._iot_body("/uc/listBindingByAccount", {"pageSize": 50, "pageNo": 1})
        resp = await self._post_json(f"{ALIYUN_BASE}/uc/listBindingByAccount", body, self._iot_headers())
        if resp.get("code") == 200:
            return resp["data"]["data"]
        return []

    async def get_properties(self, iot_id: str) -> dict:
        body = self._iot_body("/thing/properties/get", {"iotId": iot_id})
        resp = await self._post_json(f"{ALIYUN_BASE}/thing/properties/get", body, self._iot_headers())
        if resp.get("code") == 200:
            result = {}
            for key, val in resp["data"].items():
                result[key] = val.get("value")
            return result
        return {}

    async def set_properties(self, iot_id: str, items: dict[str, Any]) -> dict:
        body = self._iot_body("/thing/properties/set", {"iotId": iot_id, "items": items})
        return await self._post_json(f"{ALIYUN_BASE}/thing/properties/set", body, self._iot_headers())

    # ---- 352 自有 ----

    async def get_device_info(self, iot_id: str) -> dict:
        resp = await self._get_json(
            f"{API_352_BASE}/api/device/info/{iot_id}",
            {"Authorization": f"Token {self._access_token}"},
        )
        if resp.get("code") == 0:
            return resp.get("data", {})
        return {}

    # ---- HTTP helpers ----

    async def _post_json(self, url: str, body: dict, headers: dict) -> dict:
        headers.setdefault("Content-Type", "application/json")
        async with self._session.post(url, json=body, headers=headers) as resp:
            return await resp.json()

    async def _get_json(self, url: str, headers: dict) -> dict:
        async with self._session.get(url, headers=headers) as resp:
            return await resp.json()
