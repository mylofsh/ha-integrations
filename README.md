# A.O.史密斯 & 352 智能家居 Home Assistant 集成

两个独立的 Home Assistant 集成，直接位于仓库根目录：

| 集成 | 目录 | 说明 |
|---|---|---|
| AI-LiNK Water Heater | [`ailink_water_heater/`](ailink_water_heater/) | A.O.史密斯 AI-LiNK 智慧家燃气热水器 |
| 352 Air Purifier | [`air_purifier_352/`](air_purifier_352/) | 352 Z90 空气净化器 |

## HACS 安装

1. HACS → 右上角三个点 → **自定义仓库**
2. 仓库地址：`https://github.com/mylofsh/ha-integrations`
3. 类别选 **集成（Integration）**
4. 搜索 **AI-LiNK** 或 **352** 安装

## 手动安装

把对应目录复制到 HA 配置目录下的 `custom_components/`：

```bash
# 只装热水器
cp -r ailink_water_heater /path/to/ha/config/custom_components/

# 只装净化器
cp -r air_purifier_352 /path/to/ha/config/custom_components/
```

重启 Home Assistant 后，在 **设置 → 设备与服务 → 添加集成** 中搜索对应名称。

---

## AI-LiNK 燃气热水器

控制 A.O.史密斯 AI-LiNK 智慧家燃气热水器（型号 JSQ48-SJS 等）。

### 支持的实体

| 平台 | 功能 |
|---|---|
| `water_heater` | 开关机、目标温度 |
| `switch` | 零冷水巡航、增压、半管循环 |
| `number` | 巡航定时 |
| `sensor` | 运行状态、故障信息 |

### 首次添加

需要提供四个参数，可从 App 抓包（Stream / Charles）中提取：

| 参数 | 说明 |
|---|---|
| `token` | 访问令牌（Bearer Token） |
| `user_id` | 用户 ID |
| `family_id` | 家庭 ID |
| `device_id` | 设备 ID |

### 更新令牌（重要）

AI-LiNK 的访问令牌会过期。**令牌失效后无需删除并重新添加集成**，直接更新即可：

> **设置 → 设备与服务 → AI-LiNK 燃气热水器 → 配置 → 选项**

在弹出的表单中填入新的 Token，保存后集成会自动重载并立即使用新令牌。

- 留空的字段表示**保持原值不变**（只改 Token 时，其他三项不用动）
- 保存前会校验新凭据，校验失败会提示 `认证失败`，原配置不受影响

### 实现说明

- 走 **H5 Web 路径**（请求头 `source: Web`），该路径不校验 `sign` / `md5data`
- 状态轮询：`POST /AiLinkService/appDevice/getDeviceCurrInfo`
- 设备控制：`POST /AiLinkService/device/invokeMethod`
- 默认轮询间隔 60 秒，可在选项中以 10–600 秒调整

---

## 352 空气净化器

控制 352 Z90 空气净化器，走**阿里云 IoT 平台**（`api.link.aliyun.com`）。

### 双令牌机制

| 令牌 | 有效期 | 用途 |
|---|---|---|
| `access_token` | 长期 | 352 自有 API（`app.352air.com`），请求头 `Authorization: Token xxx` |
| `iot_token` | **约 20 小时** | 阿里云 IoT 接口，放在请求体 `request.iotToken` |
| `refresh_token` | 约 200 小时 | 换取新的 iot_token |

### 阿里云网关签名

阿里云 API 网关强制校验 `x-ca-signature`，算法为 **HmacSHA1**：

```
content-md5    = base64(md5(raw_body))
string_to_sign = METHOD \n ACCEPT \n CONTENT-MD5 \n CONTENT-TYPE \n DATE \n
                 X-Ca-Version:1 \n X-Ca-Nonce:<uuid> \n X-Ca-Timestamp:<ms> \n
                 X-Ca-Stage:RELEASE \n X-Ca-Key:<appKey> \n PATH
signature      = base64(HmacSHA1(appSecret, string_to_sign))
```

签名实现见 [`air_purifier_352/aliyun_sign.py`](air_purifier_352/aliyun_sign.py)，
回归验证脚本见 [`air_purifier_352/verify_sign.py`](air_purifier_352/verify_sign.py)。

> **关于 `appSecret`**：它是 352 App 的内置常量，**不会出现在抓包流量中**，
> 需要通过反编译 App 获取。在配置集成时填入。

### 支持的实体

| 平台 | 功能 |
|---|---|
| `fan` | 开关、风速档位 |
| `select` | 工作模式 |
| `switch` | 童锁、UV LED、除菌、智能模式、待机传感器 |
| `sensor` | PM2.5、PM10、甲醛、TVOC、温湿度、滤芯寿命、净化量、运行时长 |

---

## 故障排查

| 现象 | 处理 |
|---|---|
| 热水器提示 `认证失败` | Token 已过期，去 **配置 → 选项** 更新 Token |
| 352 返回 `Header X-Ca-Signature is Required` | 未填 `appSecret` |
| 352 返回签名错误 | 检查 `appSecret` 是否正确；确认 `date` 头格式为 `GMT+8` |
| 实体状态不更新 | 检查轮询间隔设置，或查看 HA 日志中的 `UpdateFailed` 详情 |

## 许可

MIT
