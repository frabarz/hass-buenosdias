"""Constants of the buenosdias integration."""

DOMAIN = "buenosdias"
VERSION = "0.3.2"

CONF_LLM = "llm"
CONF_TTS = "tts"
CONF_SOURCES = "sources"
CONF_SCHEDULE = "schedule"
CONF_PERSONA = "persona"

CONF_MODE = "mode"
CONF_AGENT = "agent"
CONF_MAX_CHARS = "max_chars"
CONF_OPENAI = "openai"
CONF_BASE_URL = "base_url"
CONF_API_KEY = "api_key"
CONF_MODEL = "model"

CONF_ENTITY_ID = "entity_id"
CONF_MEDIA_PLAYER = "media_player"
CONF_LANGUAGE = "language"
CONF_VOLUME = "volume"
CONF_RESTORE_VOLUME = "restore_volume"

CONF_WEATHER = "weather"
CONF_CALENDAR = "calendar"
CONF_SENSORS = "sensors"
CONF_FORECAST_TYPE = "forecast_type"
CONF_FORECAST_LIMIT = "forecast_limit"

FORECAST_NONE = "none"
FORECAST_HOURLY = "hourly"
FORECAST_DAILY = "daily"
FORECAST_TYPES = [FORECAST_HOURLY, FORECAST_DAILY]
DEFAULT_FORECAST_LIMIT = 12
MAX_FORECAST_LIMIT = 48

CONF_RSS = "rss"
CONF_FEEDS = "feeds"
CONF_URL = "url"
CONF_KIND = "kind"
CONF_MAX_AGE_HOURS = "max_age_hours"
CONF_MAX_ITEMS = "max_items"
CONF_TAGS = "tags"
CONF_EXCLUDE = "exclude"
CONF_CONFIRM_REMOVE = "confirm_remove"

KIND_NEWS = "news"
KIND_EVENTS = "events"

CONF_FOLLOWUP = "followup"
CONF_ENABLED = "enabled"
CONF_WHEN = "when"
CONF_TYPE = "type"
CONF_PLAYER = "player"
CONF_MEDIA_ID = "media_id"
CONF_MEDIA_TYPE = "media_type"
CONF_ENQUEUE = "enqueue"
CONF_MEDIA_CONTENT_ID = "media_content_id"
CONF_MEDIA_CONTENT_TYPE = "media_content_type"
CONF_SCRIPT = "script"
CONF_WAIT = "wait"
CONF_TIMEOUT = "timeout"
CONF_ANNOUNCE_VOLUME = "announce_volume"

WHEN_AFTER = "after"
WHEN_BEFORE = "before"

FOLLOWUP_NONE = "none"
FOLLOWUP_SCRIPT = "script"
FOLLOWUP_MUSIC_ASSISTANT = "music_assistant"
FOLLOWUP_MEDIA_PLAYER = "media_player"

MEDIA_TYPE_PLAYLIST = "playlist"
MEDIA_TYPES = [
    MEDIA_TYPE_PLAYLIST,
    "album",
    "track",
    "artist",
    "radio",
    "audiobook",
    "podcast",
]

ENQUEUE_PLAY = "play"
ENQUEUE_REPLACE = "replace"
ENQUEUE_VALUES = [ENQUEUE_PLAY, ENQUEUE_REPLACE, "next", "add"]

DEFAULT_FOLLOWUP_TIMEOUT = 180
MAX_FOLLOWUP_TIMEOUT = 1800
DEFAULT_PLAYBACK_GRACE = 20

CONF_TIME = "time"
CONF_TIME_ENTITY = "time_entity"
CONF_SKIP_DAYS = "skip_days"
CONF_FERIADOS = "feriados"
CONF_HOLIDAY_CALENDAR = "holiday_calendar"
CONF_SKIP_IF_EMITTED = "skip_if_emitted"
CONF_PRELOAD_MINUTES = "preload_minutes"

MODE_HA_CONVERSATION = "ha_conversation"
MODE_OPENAI_COMPATIBLE = "openai_compatible"
