"""API client for AI-LiNK water heater."""
from __future__ import annotations

import json
import time
import uuid
from typing import Any

import aiohttp


class AilinkApiClient:
    """Async API client for AI-LiNK platform."""

    BASE_URL = "https://ailink-api.hotwater.com.cn"

    # 每个 API 端点的固定 encode 值（从抓包中提取，与 userId+familyId 绑定）
    # 如果你换了账号，需要重新抓包获取这些值
    ENCODE_MAP = {
        "getHomepageV2": "ef32c8cf8842833b27c555532c7659d5",
        "getDeviceCurrInfo": "a9b3377c7c2905f9d1f4a8f62fbb06e3",
        "getFamilyErrorInfo": "8212801857d157e9c34441dd95ee07b1",
    }

    def __init__(
        self,
        session: aiohttp.ClientSession,
        token: str,
        user_id: str,
        family_id: str,
    ):
        self._session = session
        self._token = token
        self._user_id = user_id
        self._family_id = family_id

    def _make_trace_id(self) -> str:
        """Generate traceId matching App format."""
        ts = str(int(time.time() * 1000))
        rand_part = str(uuid.uuid4().int % 100000).zfill(5)
        return f"{ts}-{rand_part}-{self._user_id}-00"

    def _headers(self, source: str = "IOS") -> dict:
        """Build common request headers."""
        ts = str(int(time.time() * 1000))
        return {
            "Host": "ailink-api.hotwater.com.cn",
            "Authorization": f"Bearer {self._token}",
            "version": "V1.0.1",
            "UserId": self._user_id,
            "familyUk": "",
            "source": source,
            "timestamp": ts,
            "nonce": str(uuid.uuid4()).upper(),
            "traceId": self._make_trace_id(),
            "Content-Type": "application/json;charset=UTF-8",
            "Accept": "application/json, text/plain, */*",
            "familyId": self._family_id,
            "userId": self._user_id,
        }

    async def _post(
        self, path: str, body: dict, source: str = "IOS"
    ) -> dict:
        """POST request."""
        url = f"{self.BASE_URL}{path}"
        headers = self._headers(source)

        # 服务器在校验 sign 时：不传 sign/md5data → 跳过校验；传了错误 → 拒绝
        # 所以干脆不传这两个字段
        async with self._session.post(url, json=body, headers=headers) as resp:
            return await resp.json()

    async def get_homepage(self) -> dict:
        """Get homepage V2 — returns device list + status."""
        body = {
            "encode": self.ENCODE_MAP["getHomepageV2"],
            "homePageVersion": "3",
            "userId": self._user_id,
            "familyId": self._family_id,
        }
        return await self._post("/AiLinkService/appDevice/getHomepageV2", body)

    async def invoke_method(
        self,
        device_id: str,
        product_type: str,
        device_type: str,
        identifier: str,
        input_data: dict[str, str],
    ) -> dict:
        """Send device control command (via Web H5 path, no encode)."""
        pay_load = {
            "profile": {
                "deviceId": device_id,
                "productType": product_type,
                "deviceType": device_type,
            },
            "service": {
                "identifier": identifier,
                "inputData": input_data,
            },
        }
        body = {
            "userId": self._user_id,
            "familyId": self._family_id,
            "appSource": 2,       # 2=H5 Web
            "commandSource": 1,
            "invokeTime": time.strftime("%Y-%m-%d %H:%M:%S"),
            "payLoad": json.dumps(pay_load, separators=(",", ":")),
        }
        # H5 Web source 的额外 headers
        headers = self._headers("Web")
        headers["Referer"] = "https://ailink-appservice-h5-prd.hotwater.com.cn/"
        headers["Origin"] = "https://ailink-appservice-h5-prd.hotwater.com.cn"
        headers["X-Requested-With"] = "XMLHttpRequest"

        url = f"{self.BASE_URL}/AiLinkService/device/invokeMethod"
        async with self._session.post(url, json=body, headers=headers) as resp:
            return await resp.json()

    # ---------- 便捷方法 ----------

    async def set_power(self, device_id: str, on: bool) -> dict:
        return await self.invoke_method(
            device_id, "19", "JSQ48-SJS",
            "SetDeviceOnOff",
            {"powerStatus": "1" if on else "0"},
        )

    async def set_temperature(self, device_id: str, temp: int) -> dict:
        return await self.invoke_method(
            device_id, "19", "JSQ48-SJS",
            "WaterTempSet",
            {"waterTemp": str(temp)},
        )

    async def set_cruise(self, device_id: str, on: bool) -> dict:
        return await self.invoke_method(
            device_id, "19", "JSQ48-SJS",
            "WaterCruiseOnOff",
            {"cruiseStatus": "1" if on else "0"},
        )

    async def set_cruise_timer(self, device_id: str, minutes: int) -> dict:
        """Set one-key cruise timer duration (minutes)."""
        return await self.invoke_method(
            device_id, "19", "JSQ48-SJS",
            "WaterCruiseTimer",
            {"WaterCruiseTimer": str(minutes)},
        )

    async def set_half_pipe_circle(self, device_id: str, on: bool) -> dict:
        """Turn energy-saving half-pipe circulation on/off."""
        return await self.invoke_method(
            device_id, "19", "JSQ48-SJS",
            "setHalfPipeCircle",
            {"setHalfPipeCircle": "1" if on else "0"},
        )

    async def set_pressurize(self, device_id: str, on: bool) -> dict:
        return await self.invoke_method(
            device_id, "19", "JSQ48-SJS",
            "PressurizeOnOff",
            {"pressurize": "1" if on else "0"},
        )


def parse_device_status(status_info_raw: str) -> dict:
    """Parse the statusInfo JSON string into a flat dict."""
    try:
        status_info = json.loads(status_info_raw)
    except (json.JSONDecodeError, TypeError):
        return {}

    result = {}
    for event in status_info.get("events", []):
        od = event.get("outputData")
        if isinstance(od, dict):
            result.update(od)
        elif isinstance(od, list):
            for item in od:
                if isinstance(item, dict):
                    result.update(item)

    profile = status_info.get("profile", {})
    result["_profile"] = profile
    return result
