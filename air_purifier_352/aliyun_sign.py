"""阿里云 IoT 网关签名模块（352 净化器 / AI-LiNK 共用）。

阿里云 API 网关要求 x-ca-signature，算法为 HmacSHA1。
签名所需的 appSecret 为 App 内置常量，无法从抓包流量中获得，
因此通过 HA 配置项传入。

签名规范（已用真实抓包逐字段验证）：
    content-md5 = base64(md5(raw_body))
    string_to_sign = METHOD\n
                     ACCEPT\n
                     CONTENT-MD5\n
                     CONTENT-TYPE\n
                     DATE\n
                     <signed headers, 每行 "Name:Value">\n
                     PATH
    signature = base64(HmacSHA1(appSecret, string_to_sign))

X-Ca-Signature-Headers 固定为：
    X-Ca-Version,X-Ca-Nonce,X-Ca-Timestamp,X-Ca-Stage,X-Ca-Key
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import time
import uuid


SIGNED_HEADERS = "X-Ca-Version,X-Ca-Nonce,X-Ca-Timestamp,X-Ca-Stage,X-Ca-Key"


def content_md5(body: bytes) -> str:
    """base64(md5(body))，用于 content-md5 头。"""
    return base64.b64encode(hashlib.md5(body).digest()).decode()


def build_headers(
    app_key: str,
    app_secret: str,
    method: str,
    path: str,
    body: bytes,
    accept: str = "application/json; charset=UTF-8",
    content_type: str = "application/json; charset=UTF-8",
    stage: str = "RELEASE",
    version: str = "1",
    extra: dict | None = None,
) -> dict:
    """构造带签名的完整请求头。

    path 必须是不含 query 的路径部分（网关只签 path）。
    app_secret 为空时返回不带签名的基础头（用于调试定位）。
    """
    ts = str(int(time.time() * 1000))
    nonce = str(uuid.uuid4()).upper()
    # HTTP Date 头，格式如 Wed, 07 Oct 2026 15:20:32 GMT+8
    date = time.strftime("%a, %d %b %Y %H:%M:%S GMT+8", time.localtime())

    md5 = content_md5(body)

    headers = {
        "x-ca-key": app_key,
        "x-ca-nonce": nonce,
        "x-ca-timestamp": ts,
        "x-ca-stage": stage,
        "x-ca-version": version,
        "x-ca-signature-method": "HmacSHA1",
        "x-ca-signature-headers": SIGNED_HEADERS,
        "content-md5": md5,
        "accept": accept,
        "content-type": content_type,
        "date": date,
    }
    if extra:
        headers.update(extra)

    if not app_secret:
        return headers

    signed_lines = "\n".join(
        f"{name}:{headers[name.lower()]}"
        for name in SIGNED_HEADERS.split(",")
    )
    string_to_sign = (
        method + "\n" +
        accept + "\n" +
        md5 + "\n" +
        content_type + "\n" +
        date + "\n" +
        signed_lines + "\n" +
        path
    )
    signature = base64.b64encode(
        hmac.new(app_secret.encode(), string_to_sign.encode(), hashlib.sha1).digest()
    ).decode()
    headers["x-ca-signature"] = signature
    return headers


def string_to_sign(
    method: str,
    path: str,
    body: bytes,
    accept: str = "application/json; charset=UTF-8",
    content_type: str = "application/json; charset=UTF-8",
    date: str = "",
    nonce: str = "",
    timestamp: str = "",
    app_key: str = "",
    stage: str = "RELEASE",
    version: str = "1",
) -> str:
    """单独暴露 string_to_sign，便于用抓包样本回归验证。"""
    md5 = content_md5(body)
    signed_lines = (
        f"X-Ca-Version:{version}\n"
        f"X-Ca-Nonce:{nonce}\n"
        f"X-Ca-Timestamp:{timestamp}\n"
        f"X-Ca-Stage:{stage}\n"
        f"X-Ca-Key:{app_key}"
    )
    return (
        method + "\n" +
        accept + "\n" +
        md5 + "\n" +
        content_type + "\n" +
        date + "\n" +
        signed_lines + "\n" +
        path
    )
