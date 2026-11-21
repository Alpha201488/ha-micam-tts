"""Constants for the Micam Web TTS integration."""

DOMAIN = "micam_tts"

CONF_HOST = "host"
CONF_PORT = "port"
CONF_SSL = "ssl"
CONF_VERIFY_SSL = "verify_ssl"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_VOICE = "voice"
CONF_RATE = "rate"
CONF_STREAM = "stream"

DEFAULT_PORT = 8080
DEFAULT_SSL = False
DEFAULT_VERIFY_SSL = True
DEFAULT_VOICE = "zh-CN-XiaoxiaoNeural"
DEFAULT_RATE = "+0%"

RATE_OPTIONS = ["-20%", "-10%", "+0%", "+10%", "+20%", "+30%"]

SERVICE_SPEAK = "speak"
SERVICE_STOP = "stop"

ATTR_TEXT = "text"
ATTR_VOICE = "voice"
ATTR_RATE = "rate"
ATTR_ENTRY_ID = "entry_id"

MAX_TEXT_LEN = 200
