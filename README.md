# AI-LiNK 水 heater Home Assistant 集成

基于 A.O.史密斯 AI-LiNK 智慧家 App (v2.3.2) 抓包分析实现的 HA custom component。

## 获取配置信息

需要从 Stream 抓包中获取三个值：

1. **Token**: 任意请求 header 中 `Authorization: Bearer ` 后面的完整 JWT
2. **UserId**: 请求 body 中的 `userId`
3. **FamilyId**: 请求 body 中的 `familyId`

Token 长期有效，无需定期刷新。

## 安装

1. 复制 `custom_components/ailink_water_heater` 到 HA 的 `custom_components` 目录
2. 重启 Home Assistant
3. 在"设置 → 设备与服务 → 添加集成"中搜索 "AI-LiNK"
4. 填入上述三个值

## 提供的实体

### water_heater
- 开关机、设定温度 (35-60℃)
- 当前出水温度、运行状态（待机/燃烧/关机）
- 全量属性：故障码、防冻、增压档位、燃烧统计等 50+ 字段

### switch
- 零冷水巡航 开关
- 增压 开关（含增压档位属性）

### sensor (12个)
- 出水温度、进水温度
- 水流量、风机转速
- 点火次数、累计运行时间
- 累计用气量、累计用水量
- 巡航累计用气
- CO 浓度、中和器寿命、滤芯剩余天数

## 注意事项

- `encode` 值从抓包中提取，与账号绑定。如果服务端更新了 encode 算法或换了账号，需要重新抓包更新 `api.py` 中的 `ENCODE_MAP`
- sign 签名先用 md5data 代替，如果服务端做严格校验可能需要逆向完整签名算法
