# A.O.史密斯 & 352 智能家居 Home Assistant 集成

包含两个集成：

## 1. AI-LiNK Water Heater（燃气热水器）

适配 A.O.史密斯 JSQ48-SJS 等 AI-LiNK 智慧家系列燃气热水器。

**获取配置：** Stream 抓包 App，取任意请求的 `Authorization: Bearer xxx`（Token）、`userId`、`familyId`。

### 实体

| 类型 | 实体 | 说明 |
|---|---|---|
| water_heater | 热水器 | 开关机、设定温度 35-60℃、出水温度 |
| switch | 零冷水巡航 | 一键循环预热 |
| switch | 节能半管零冷水 | 半管循环节能模式 |
| switch | 增压 | 水压增强 |
| number | 一键零冷水时长 | 1-120 分钟 |
| sensor × 12 | 温度/流量/统计 | 进出水温、水流量、风机转速、点火次数、累计用气/用水、CO浓度等 |

---

## 2. 352 Air Purifier（空气净化器）

适配 352 Z90 等走阿里云 IoT 平台的空气净化器。

**获取配置：**  
抓包 352Life App，需要两个 Token：
- **352 access_token**: 请求 header `Authorization: Token xxx` 中的值
- **aliyun iot_token**: 请求 body 中的 `iotToken` 字段

⚠️ `iot_token` 有效期约 20 小时，过期需重新抓包。

### 实体

| 类型 | 实体 | 说明 |
|---|---|---|
| fan | 空气净化器 | 开关、5 档风速、自动/手动/睡眠模式 |
| switch × 6 | UV LED/等离子/童锁/智能/传感器 | 各功能开关 |
| sensor × 14 | PM2.5/PM10/甲醛/TVOC/温湿度/滤芯 | 空气质量监测 |

---

## 安装

> HACS 自定义存储库：`https://github.com/mylofsh/ha-ailink-water-heater`，类别选「集成」

或手动安装：

1. 复制 `custom_components/ailink_water_heater` 和 `custom_components/air_purifier_352` 到 HA 的 `custom_components` 目录
2. 重启 Home Assistant
3. 「设置 → 设备与服务 → 添加集成」搜索 **AI-LiNK** 或 **352 Air Purifier**
