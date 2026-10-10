"""离线自测：验证 options flow 的合并逻辑（不依赖 HA 运行时）。

验证点：
1. options 覆盖 data（新 token 生效）
2. 留空字段保持原值
3. 只改 token 时其他字段不动
"""
from __future__ import annotations


def merge_config(entry_data: dict, entry_options: dict) -> dict:
    """复刻 __init__.py 中的合并逻辑。"""
    return {**entry_data, **entry_options}


def apply_options(
    current: dict,
    user_input: dict,
    keys=("token", "user_id", "family_id", "device_id"),
) -> dict:
    """复刻 AilinkOptionsFlow.async_step_init 的合并逻辑。"""
    new_data = dict(current)
    for key in keys:
        val = (user_input.get(key) or "").strip()
        if val:                      # 留空 = 不修改
            new_data[key] = val
    if "scan_interval" in user_input:
        new_data["scan_interval"] = user_input["scan_interval"]
    return new_data


def build_options(new_data: dict, keys=("token", "user_id", "family_id", "device_id")) -> dict:
    """复刻 options flow 写入 options 的逻辑。

    关键：只写入 user_input 中**确实提供了值**的字段，
    不要把空值写进 options —— 否则空值会在下次合并时覆盖掉 data 中的有效值。
    """
    return {
        k: v for k, v in new_data.items()
        if k != "token" and v not in (None, "")
    }


def test(name: str, got, want) -> bool:
    ok = got == want
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
    if not ok:
        print(f"         got  = {got}")
        print(f"         want = {want}")
    return ok


results = []

print("=" * 68)
print("场景 1：首次添加后，options 为空")
data = {"token": "OLD_TOKEN", "user_id": "u1", "family_id": "f1",
        "device_id": "d1", "scan_interval": 60}
opts = {}
results.append(test("token 取自 data", merge_config(data, opts)["token"], "OLD_TOKEN"))

print()
print("=" * 68)
print("场景 2：只更新 token，其他字段留空")
opts = {}
current = merge_config(data, opts)
new_data = apply_options(current, {"token": "NEW_TOKEN", "user_id": "",
                                   "family_id": "", "device_id": "",
                                   "scan_interval": 60})
results.append(test("新 token 生效", new_data["token"], "NEW_TOKEN"))
results.append(test("user_id 保持原值", new_data["user_id"], "u1"))
results.append(test("family_id 保持原值", new_data["family_id"], "f1"))
results.append(test("device_id 保持原值", new_data["device_id"], "d1"))

saved_opts = build_options(new_data)
# options 会保留所有非空字段（供表单预填），但不得含空值
results.append(test("options 不含空值", all(v != "" for v in saved_opts.values()), True))
results.append(test("options 不含 token", "token" not in saved_opts, True))
# 模拟下次加载：options 不应把 data 的值弄丢
reloaded = merge_config({**data, "token": "NEW_TOKEN"}, saved_opts)
results.append(test("重新加载后 user_id 未丢失", reloaded["user_id"], "u1"))
results.append(test("重新加载后 token 为新的", reloaded["token"], "NEW_TOKEN"))

print()
print("=" * 68)
print("场景 3：同时更新 token 和 device_id")
new_data = apply_options(merge_config(data, {}), {"token": "NEW2", "user_id": "",
                                                  "family_id": "", "device_id": "d2",
                                                  "scan_interval": 60})
results.append(test("token 更新", new_data["token"], "NEW2"))
results.append(test("device_id 更新", new_data["device_id"], "d2"))
results.append(test("user_id 仍未动", new_data["user_id"], "u1"))
saved_opts = build_options(new_data)
results.append(test("options 不含 token", "token" not in saved_opts, True))
results.append(test("options 含更新后的 device_id", saved_opts.get("device_id"), "d2"))

print()
print("=" * 68)
print("场景 4：options 中的 token 覆盖 data（合并优先级）")
data2 = {"token": "OLD", "user_id": "u1", "family_id": "f1", "device_id": "d1"}
opts2 = {"token": "FROM_OPTIONS"}
results.append(test("options 优先", merge_config(data2, opts2)["token"], "FROM_OPTIONS"))
results.append(test("未覆盖字段保留", merge_config(data2, opts2)["user_id"], "u1"))

print()
print("=" * 68)
print("场景 5：空白字符串视为不修改（防误清空）")
new_data = apply_options({"token": "KEEPME", "user_id": "u1"},
                         {"token": "   ", "user_id": "\t"})
results.append(test("空格不覆盖 token", new_data["token"], "KEEPME"))
results.append(test("tab 不覆盖 user_id", new_data["user_id"], "u1"))

print()
print("=" * 68)
passed = sum(1 for r in results if r)
print(f"结果: {passed}/{len(results)} 通过")
raise SystemExit(0 if passed == len(results) else 1)
