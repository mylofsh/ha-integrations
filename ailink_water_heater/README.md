# AI-LiNK Water Heater

A.O.史密斯 AI-LiNK 燃气热水器 Home Assistant 集成。

适配 JSQ48-SJS 等走 `ailink-api.hotwater.com.cn` 的 AI-LiNK 智慧家系列燃气热水器。

## 安装

### HACS（推荐）
1. HACS → 右上角三个点 → 自定义仓库
2. 仓库地址：`https://github.com/mylofsh/ha-ailink-water-heater`
3. 类别选 **集成**
4. 搜索 "AI-LiNK Water Heater" 安装

### 手动
复制 `custom_components/ailink_water_heater/` 到 HA 的 `custom_components/` 目录，重启 HA。

## 配置

### 获取参数
用 Stream App 抓包 AI-LiNK 智慧家 App，在任意请求中找到：

| 参数 | 说明 |
|---|---|
| `token` | Header `Authorization: Bearer xxx` 中的值 |
| `user_id` | Header `UserId` 或 body 中的 `userId` |
| `family_id` | Body 中的 `familyId` |
| `device_id` | Body 中的 `deviceId`（如 `849DC2CF6772`） |

### 添加集成
设置 → 设备与服务 → 添加集成 → 搜索 **AI-LiNK**

## 实体

| 类型 | 实体 | 说明 |
|---|---|---|
| water_heater | 热水器 | 开关机、设定温度 35-60℃ |
| switch | 零冷水巡航 | 一键循环预热 |
| switch | 节能半管零冷水 | 半管循环节能模式 |
| switch | 增压 | 水压增强 |
| number | 一键零冷水时长 | 1-120 分钟 |
| sensor × N | 进出水温/流量/统计 | 各传感器数据 |
