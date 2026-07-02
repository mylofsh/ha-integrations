# 352 Air Purifier

352空气净化器 Home Assistant 集成。

适配 Z90 等走阿里云 IoT 平台（`api.link.aliyun.com`）的 352 空气净化器。

## 安装

### HACS（推荐）
1. HACS → 右上角三个点 → 自定义仓库
2. 仓库地址：`https://github.com/mylofsh/ha-ailink-water-heater`
3. 类别选 **集成**
4. 搜索 "352 Air Purifier" 安装

### 手动
复制 `custom_components/air_purifier_352/` 到 HA 的 `custom_components/` 目录，重启 HA。

## 配置

### 获取参数
抓包 352Life App，需要两个 Token：

| 参数 | 说明 |
|---|---|
| `access_token` | 请求 header `Authorization: Token xxx` |
| `iot_token` | 请求 body 中的 `iotToken`（有效期约20h） |

### 添加集成
设置 → 设备与服务 → 添加集成 → 搜索 **352 Air Purifier**

## 实体

| 类型 | 实体 | 说明 |
|---|---|---|
| fan | 空气净化器 | 开关、5档风速、自动/手动/睡眠模式 |
| switch × 6 | UV/等离子/童锁/智能场景/传感器灯 | 各功能开关 |
| sensor × N | PM2.5/PM10/甲醛/TVOC/温湿度/滤芯寿命 | 环境监测 |
