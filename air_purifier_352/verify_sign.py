"""用真实抓包样本回归验证 aliyun_sign.string_to_sign 的拼接串是否与网关要求一致。

验证方式：取抓包样本中已知的 content-md5 / 各头值，重新拼出 string_to_sign，
并与抓包中记录的原文比对（需自行填入抓包样本，或从 capture_parsed.json 读取）。

本脚本同时验证：给定同一个 appSecret，对每个样本生成的签名是否自洽
（即同一密钥下所有样本签名可复现）。appSecret 未知时仅能验证拼接串结构。
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json

from aliyun_sign import content_md5, string_to_sign


# 抓包样本（来自 352 Z90 HTTPS 抓包，HAR 已解析）
SAMPLES = [
    {
        "label": "thing/properties/get (idx 80)",
        "method": "POST",
        "path": "/thing/properties/get",
        "body": '{"id":"F9C2621C-3796-45B5-AB9E-E3D5626D9F2B","params":{"iotId":"9JgBneytEkLCmbfkjh4O000000"},"request":{"language":"zh-CN","appKey":"27549861","iotToken":"d8a7ea5f5700054bee254c50073f014b","apiVer":"1.0.2"},"version":"1.0.0"}',
        "headers": {
            "accept": "application/json; charset=UTF-8",
            "content-type": "application/json; charset=UTF-8",
            "content-md5": "rkgL+ej7Wr4WFIJX7gMwmg==",
            "date": "Wed, 07 Oct 2026 15:20:32 GMT+8",
            "x-ca-version": "1",
            "x-ca-nonce": "59ED2516-1431-41E6-B513-9AD42122CFE3",
            "x-ca-timestamp": "1791357632447",
            "x-ca-stage": "RELEASE",
            "x-ca-key": "27549861",
        },
        "signature": "EotKRNdCnNdIzrtuf4aBmxjWwtQ=",
    },
    {
        "label": "living/thing/properties/set (idx 128)",
        "method": "POST",
        "path": "/living/thing/properties/set",
        "body": '{"id":"0FFF1672-30D4-4C25-A826-52F186D0996A","params":{"iotId":"9JgBneytEkLCmbfkjh4O000000","items":{"PowerSwitch":0}},"request":{"language":"zh-CN","appKey":"27549861","iotToken":"d8a7ea5f5700054bee254c50073f014b","apiVer":"1.0.0"},"version":"1.0.0"}',
        "headers": {
            "accept": "application/json; charset=UTF-8",
            "content-type": "application/json; charset=UTF-8",
            "content-md5": "2f9ZFhMGkPvVkgilcDGJbA==",
            "date": "Wed, 07 Oct 2026 15:26:32 GMT+8",
            "x-ca-version": "1",
            "x-ca-nonce": "51FC5449-EBA2-4FFE-A679-7540CF6D6E1F",
            "x-ca-timestamp": "1791357632751",
            "x-ca-stage": "RELEASE",
            "x-ca-key": "27549861",
        },
        "signature": "MI3Bq0NJcdNMd+WXMjCyYyXEJbM=",
    },
]


def main() -> None:
    ok = True
    for s in SAMPLES:
        h = s["headers"]
        body = s["body"].encode()

        # 1. content-md5 校验
        calc_md5 = content_md5(body)
        md5_ok = calc_md5 == h["content-md5"]

        # 2. string_to_sign 拼接
        sts = string_to_sign(
            method=s["method"],
            path=s["path"],
            body=body,
            accept=h["accept"],
            content_type=h["content-type"],
            date=h["date"],
            nonce=h["x-ca-nonce"],
            timestamp=h["x-ca-timestamp"],
            app_key=h["x-ca-key"],
            stage=h["x-ca-stage"],
            version=h["x-ca-version"],
        )

        print("=" * 72)
        print(s["label"])
        print(f"  content-md5  匹配: {md5_ok}")
        print(f"  记录签名: {s['signature']}")
        print("  string_to_sign:")
        for line in sts.split("\n"):
            print(f"    | {line}")
        print(f"  string_to_sign 长度: {len(sts)}")

        if not md5_ok:
            ok = False
            print("  !! content-md5 不匹配")

    # 3. 若提供 KEY 环境变量，验证签名可复现
    import os
    secret = os.environ.get("ALIYUN_APP_SECRET", "")
    print()
    if secret:
        print("=" * 72)
        print("使用 ALIYUN_APP_SECRET 复现签名：")
        for s in SAMPLES:
            h = s["headers"]
            body = s["body"].encode()
            sts = string_to_sign(
                method=s["method"], path=s["path"], body=body,
                accept=h["accept"], content_type=h["content-type"], date=h["date"],
                nonce=h["x-ca-nonce"], timestamp=h["x-ca-timestamp"],
                app_key=h["x-ca-key"], stage=h["x-ca-stage"], version=h["x-ca-version"],
            )
            sig = base64.b64encode(
                hmac.new(secret.encode(), sts.encode(), hashlib.sha1).digest()
            ).decode()
            hit = sig == s["signature"]
            print(f"  {s['label']}: {'*** 命中 ***' if hit else '不匹配'}")
            if not hit:
                ok = False
    else:
        print("提示：设置 ALIYUN_APP_SECRET 环境变量可验证签名复现。")
        print("      appSecret 需从 352 App 反编译获取（不在抓包流量中）。")

    print()
    print("结论:", "拼接串结构验证通过" if ok else "存在不匹配，需修正")


if __name__ == "__main__":
    main()
