"""Constants for AI-LiNK Water Heater integration."""
DOMAIN = "ailink_water_heater"

BASE_URL = "https://ailink-api.hotwater.com.cn"

# 认证
CONF_TOKEN = "token"
CONF_USER_ID = "user_id"
CONF_FAMILY_ID = "family_id"
CONF_REFRESH_TOKEN = "refresh_token"

# 轮询
DEFAULT_SCAN_INTERVAL = 60  # 秒

# API 端点
API_LOGIN = "/AiLinkService/user/login"  # 需要逆向确认
API_HOMEPAGE = "/AiLinkService/appDevice/getHomepageV2"
API_INVOKE = "/AiLinkService/device/invokeMethod"
API_DEVICE_INFO = "/AiLinkService/appDevice/getDeviceCurrInfo"
API_OPEN_APP = "/AiLinkService/deviceEnergy/openAPP"
API_CLOSE_APP = "/AiLinkService/deviceEnergy/closeAPP"

# 产品类型
PRODUCT_TYPE_WATER_HEATER = "19"
DEVICE_TYPE_JSQ48 = "JSQ48-SJS"

# 设备指令
SERVICE_SET_POWER = "SetDeviceOnOff"
SERVICE_SET_TEMP = "WaterTempSet"
SERVICE_SET_CRUISE = "WaterCruiseOnOff"
SERVICE_SET_PRESSURIZE = "PressurizeOnOff"
