"""Tests of the buenosdias configuration schema."""

import pytest
import voluptuous as vol

from custom_components.buenosdias.config_schema import CONFIG_SCHEMA
from custom_components.buenosdias.const import (
    CONF_ENABLED,
    CONF_ENQUEUE,
    CONF_FOLLOWUP,
    CONF_FORECAST_LIMIT,
    CONF_FORECAST_TYPE,
    CONF_HOLIDAY_CALENDAR,
    CONF_LLM,
    CONF_MEDIA_ID,
    CONF_MODE,
    CONF_PLAYER,
    CONF_RSS,
    CONF_SCHEDULE,
    CONF_SCRIPT,
    CONF_SOURCES,
    CONF_TIME,
    CONF_TIME_ENTITY,
    CONF_TIMEOUT,
    CONF_TTS,
    CONF_TYPE,
    CONF_URL,
    CONF_WAIT,
    CONF_WHEN,
    DOMAIN,
    ENQUEUE_REPLACE,
    FOLLOWUP_MUSIC_ASSISTANT,
    FOLLOWUP_NONE,
    FOLLOWUP_SCRIPT,
    FORECAST_DAILY,
    FORECAST_NONE,
    KIND_EVENTS,
    MEDIA_TYPE_PLAYLIST,
    MODE_HA_CONVERSATION,
    WHEN_AFTER,
)


def test_schema_accepts_full_configuration():
    config = {
        DOMAIN: {
            "llm": {"mode": "openai_compatible", "max_chars": 1500},
            "tts": {"entity_id": "tts.piper", "media_player": "media_player.sala"},
            "sources": {"weather": ["weather.casa"], "sensors": ["sensor.x"]},
            "schedule": {"time": "06:30", "skip_days": ["sat", "sun"]},
            "persona": "You are a radio host.",
        },
    }
    validated = CONFIG_SCHEMA(config)
    assert validated[DOMAIN]["llm"][CONF_MODE] == "openai_compatible"
    assert validated[DOMAIN]["schedule"]["time"] == "06:30"


def test_schema_applies_defaults():
    validated = CONFIG_SCHEMA({DOMAIN: {}})
    conf = validated[DOMAIN]
    assert conf[CONF_LLM][CONF_MODE] == MODE_HA_CONVERSATION
    assert conf[CONF_LLM]["max_chars"] == 2000
    assert conf[CONF_TTS]["language"] == "es-ES"
    assert conf[CONF_TTS]["volume"] == 0.6
    assert conf[CONF_SOURCES]["weather"] == []
    assert conf[CONF_SOURCES][CONF_FORECAST_TYPE] == FORECAST_NONE
    assert conf[CONF_SOURCES][CONF_FORECAST_LIMIT] == 12
    assert conf[CONF_SCHEDULE][CONF_TIME] == "07:00"


def test_schema_accepts_time_entity():
    config = {DOMAIN: {"schedule": {CONF_TIME_ENTITY: "sensor.phone_alarm"}}}
    validated = CONFIG_SCHEMA(config)
    assert validated[DOMAIN][CONF_SCHEDULE][CONF_TIME_ENTITY] == "sensor.phone_alarm"


def test_schema_default_time_entity():
    validated = CONFIG_SCHEMA({DOMAIN: {}})
    assert validated[DOMAIN][CONF_SCHEDULE][CONF_TIME_ENTITY] == ""


def test_schema_accepts_holiday_calendar():
    config = {DOMAIN: {"schedule": {CONF_HOLIDAY_CALENDAR: "calendar.chile"}}}
    validated = CONFIG_SCHEMA(config)
    assert validated[DOMAIN][CONF_SCHEDULE][CONF_HOLIDAY_CALENDAR] == "calendar.chile"


def test_schema_default_holiday_calendar():
    validated = CONFIG_SCHEMA({DOMAIN: {}})
    assert validated[DOMAIN][CONF_SCHEDULE][CONF_HOLIDAY_CALENDAR] == ""


def test_schema_allows_section_absence():
    validated = CONFIG_SCHEMA({"other_integration": {}})
    assert DOMAIN not in validated


def test_schema_allows_extra_top_level_keys():
    validated = CONFIG_SCHEMA({DOMAIN: {}, "other_integration": {"a": 1}})
    assert DOMAIN in validated


def test_schema_accepts_rss_feeds():
    config = {
        DOMAIN: {
            "sources": {
                "rss": {
                    "feeds": [
                        {
                            CONF_URL: "https://example.org/news.xml",
                            "kind": "news",
                            "max_age_hours": 24,
                            "max_items": 5,
                            "tags": ["city"],
                        },
                        {
                            CONF_URL: "https://example.org/agenda.xml",
                            "kind": "events",
                        },
                    ],
                },
            },
        },
    }
    validated = CONFIG_SCHEMA(config)
    feeds = validated[DOMAIN][CONF_SOURCES][CONF_RSS]["feeds"]
    assert feeds[0]["kind"] == "news"
    assert feeds[0]["tags"] == ["city"]
    assert feeds[1]["kind"] == KIND_EVENTS
    assert feeds[1]["max_items"] == 5  # default applied


def test_schema_applies_rss_defaults():
    validated = CONFIG_SCHEMA({DOMAIN: {}})
    assert validated[DOMAIN][CONF_SOURCES][CONF_RSS]["feeds"] == []


@pytest.mark.parametrize(
    "bad_config",
    [
        {DOMAIN: {"schedule": {"time": "25:00"}}},
        {DOMAIN: {"schedule": {"skip_days": ["monday"]}}},
        {DOMAIN: {"schedule": {"feriados": ["01-01-2026"]}}},
        {DOMAIN: {"tts": {"volume": 1.5}}},
        {DOMAIN: {"llm": {"mode": "does_not_exist"}}},
        {DOMAIN: {"llm": {"max_chars": 5}}},
        {DOMAIN: {"sources": {"rss": {"feeds": [{"url": ""}]}}}},
        {
            DOMAIN: {
                "sources": {
                    "rss": {"feeds": [{"url": "https://x.es", "kind": "sports"}]},
                },
            },
        },
        {
            DOMAIN: {
                "sources": {
                    "rss": {"feeds": [{"url": "https://x.es", "max_age_hours": 0}]},
                },
            },
        },
        {DOMAIN: {"sources": {"forecast_type": "weekly"}}},
        {DOMAIN: {"sources": {"forecast_limit": 0}}},
        {DOMAIN: {"sources": {"forecast_limit": 100}}},
        {DOMAIN: {CONF_FOLLOWUP: {CONF_TYPE: "playlist"}}},
        {DOMAIN: {CONF_FOLLOWUP: {CONF_WHEN: "during"}}},
        {DOMAIN: {CONF_FOLLOWUP: {CONF_TIMEOUT: 0}}},
        {DOMAIN: {CONF_FOLLOWUP: {"volume": 2}}},
        {DOMAIN: {CONF_FOLLOWUP: {CONF_ENQUEUE: "append"}}},
    ],
)
def test_schema_rejects_invalid_configuration(bad_config):
    with pytest.raises(vol.Invalid):
        CONFIG_SCHEMA(bad_config)


def test_schema_followup_defaults_to_disabled():
    validated = CONFIG_SCHEMA({DOMAIN: {}})
    followup = validated[DOMAIN][CONF_FOLLOWUP]
    assert followup[CONF_ENABLED] is False
    assert followup[CONF_TYPE] == FOLLOWUP_NONE
    assert followup[CONF_WHEN] == WHEN_AFTER
    assert followup[CONF_WAIT] is True
    assert followup[CONF_TIMEOUT] == 180
    assert followup["volume"] is None


def test_schema_accepts_music_assistant_followup():
    validated = CONFIG_SCHEMA(
        {
            DOMAIN: {
                CONF_FOLLOWUP: {
                    CONF_ENABLED: True,
                    CONF_TYPE: FOLLOWUP_MUSIC_ASSISTANT,
                    CONF_PLAYER: "media_player.cocina",
                    CONF_MEDIA_ID: "library://playlist/3",
                },
            },
        },
    )
    followup = validated[DOMAIN][CONF_FOLLOWUP]
    assert followup[CONF_TYPE] == FOLLOWUP_MUSIC_ASSISTANT
    assert followup[CONF_PLAYER] == "media_player.cocina"
    assert followup[CONF_MEDIA_ID] == "library://playlist/3"
    assert followup["media_type"] == MEDIA_TYPE_PLAYLIST
    assert followup[CONF_ENQUEUE] == ENQUEUE_REPLACE


def test_schema_accepts_script_followup():
    validated = CONFIG_SCHEMA(
        {
            DOMAIN: {
                CONF_FOLLOWUP: {
                    CONF_ENABLED: True,
                    CONF_TYPE: FOLLOWUP_SCRIPT,
                    CONF_SCRIPT: "script.morning_music",
                },
            },
        },
    )
    assert validated[DOMAIN][CONF_FOLLOWUP][CONF_SCRIPT] == "script.morning_music"


def test_schema_accepts_forecast_options():
    validated = CONFIG_SCHEMA(
        {
            DOMAIN: {
                "sources": {
                    CONF_FORECAST_TYPE: FORECAST_DAILY,
                    CONF_FORECAST_LIMIT: 3,
                },
            },
        },
    )
    sources = validated[DOMAIN][CONF_SOURCES]
    assert sources[CONF_FORECAST_TYPE] == FORECAST_DAILY
    assert sources[CONF_FORECAST_LIMIT] == 3
