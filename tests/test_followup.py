"""Tests of the follow-up action (music/scripts around the announcement)."""

import asyncio

import pytest

from custom_components.buenosdias import followup
from custom_components.buenosdias.const import (
    CONF_ENABLED,
    CONF_ENQUEUE,
    CONF_FOLLOWUP,
    CONF_MEDIA_CONTENT_ID,
    CONF_MEDIA_CONTENT_TYPE,
    CONF_MEDIA_ID,
    CONF_PLAYER,
    CONF_SCRIPT,
    CONF_TIMEOUT,
    CONF_TYPE,
    CONF_VOLUME,
    CONF_WAIT,
    CONF_WHEN,
    FOLLOWUP_MEDIA_PLAYER,
    FOLLOWUP_MUSIC_ASSISTANT,
    FOLLOWUP_NONE,
    FOLLOWUP_SCRIPT,
    WHEN_BEFORE,
)


def _run(coro):
    return asyncio.run(coro)


def _config(**section):
    return {CONF_FOLLOWUP: {CONF_ENABLED: True, **section}}


def _state(state="idle", features=0):
    from conftest import FakeState

    return FakeState(state, {"supported_features": features})


def test_resolve_defaults_to_disabled():
    settings = followup.resolve({})
    assert settings.enabled is False
    assert settings.type == FOLLOWUP_NONE
    assert settings.runs is False
    assert settings.wait is True
    assert settings.timeout == 180


def test_resolve_reads_the_section():
    settings = followup.resolve(
        _config(
            **{
                CONF_TYPE: FOLLOWUP_MUSIC_ASSISTANT,
                CONF_WHEN: WHEN_BEFORE,
                CONF_PLAYER: "media_player.cocina",
                CONF_VOLUME: "0.35",
                CONF_WAIT: False,
                CONF_TIMEOUT: 45,
            },
        ),
    )
    assert settings.runs is True
    assert settings.before is True
    assert settings.after is False
    assert settings.player == "media_player.cocina"
    assert settings.volume == 0.35
    assert settings.wait is False
    assert settings.timeout == 45.0


def test_resolve_ignores_invalid_volume_and_timeout():
    settings = followup.resolve(_config(**{CONF_VOLUME: "loud", CONF_TIMEOUT: "soon"}))
    assert settings.volume is None
    assert settings.timeout == 180


def test_resolve_tolerates_a_non_dict_section():
    assert followup.resolve({CONF_FOLLOWUP: "yes"}).runs is False
    assert followup.build_calls({CONF_FOLLOWUP: ["nope"]}) == []


def test_build_calls_disabled_returns_nothing():
    assert followup.build_calls({}) == []
    assert followup.build_calls({CONF_FOLLOWUP: {CONF_ENABLED: False}}) == []


def test_build_calls_script():
    calls = followup.build_calls(
        _config(**{CONF_TYPE: FOLLOWUP_SCRIPT, CONF_SCRIPT: "script.music"}),
    )
    assert calls == [("script", "turn_on", {"entity_id": "script.music"})]


def test_build_calls_music_assistant():
    calls = followup.build_calls(
        _config(
            **{
                CONF_TYPE: FOLLOWUP_MUSIC_ASSISTANT,
                CONF_PLAYER: "media_player.cocina",
                CONF_MEDIA_ID: "library://playlist/3",
                "media_type": "playlist",
                CONF_ENQUEUE: "play",
            },
        ),
    )
    assert calls == [
        (
            "music_assistant",
            "play_media",
            {
                "entity_id": "media_player.cocina",
                "media_id": "library://playlist/3",
                "media_type": "playlist",
                "enqueue": "play",
            },
        ),
    ]


def test_build_calls_media_player():
    calls = followup.build_calls(
        _config(
            **{
                CONF_TYPE: FOLLOWUP_MEDIA_PLAYER,
                CONF_PLAYER: "media_player.salon",
                CONF_MEDIA_CONTENT_ID: "http://radio/stream.mp3",
                CONF_MEDIA_CONTENT_TYPE: "music",
            },
        ),
    )
    assert calls == [
        (
            "media_player",
            "play_media",
            {
                "entity_id": "media_player.salon",
                "media_content_id": "http://radio/stream.mp3",
                "media_content_type": "music",
            },
        ),
    ]


@pytest.mark.parametrize(
    "section",
    [
        {CONF_TYPE: FOLLOWUP_SCRIPT},
        {CONF_TYPE: FOLLOWUP_MUSIC_ASSISTANT, CONF_PLAYER: "media_player.cocina"},
        {CONF_TYPE: FOLLOWUP_MUSIC_ASSISTANT, CONF_MEDIA_ID: "library://playlist/3"},
        {CONF_TYPE: FOLLOWUP_MEDIA_PLAYER, CONF_PLAYER: "media_player.salon"},
        {CONF_TYPE: "does_not_exist"},
    ],
)
def test_build_calls_skips_incomplete_configuration(section):
    assert followup.build_calls(_config(**section)) == []


def test_async_run_calls_the_service(fake_hass):
    hass, _ = fake_hass()
    ran = _run(
        followup.async_run(
            hass,
            _config(**{CONF_TYPE: FOLLOWUP_SCRIPT, CONF_SCRIPT: "script.music"}),
        ),
    )
    assert ran is True
    assert hass.calls == [("script", "turn_on", {"entity_id": "script.music"})]


def test_async_run_sets_the_volume_first(fake_hass):
    from homeassistant.components.media_player import MediaPlayerEntityFeature

    hass, _ = fake_hass(
        {
            "media_player.cocina": _state(
                "idle",
                int(MediaPlayerEntityFeature.VOLUME_SET),
            ),
        },
    )
    _run(
        followup.async_run(
            hass,
            _config(
                **{
                    CONF_TYPE: FOLLOWUP_MUSIC_ASSISTANT,
                    CONF_PLAYER: "media_player.cocina",
                    CONF_MEDIA_ID: "library://playlist/3",
                    CONF_VOLUME: 0.3,
                },
            ),
        ),
    )
    assert hass.calls[0] == (
        "media_player",
        "volume_set",
        {"entity_id": "media_player.cocina", "volume_level": 0.3},
    )
    assert hass.calls[1][0] == "music_assistant"


def test_async_run_without_service_support_skips_volume(fake_hass):
    hass, _ = fake_hass({"media_player.cocina": _state("idle", 0)})
    _run(
        followup.async_run(
            hass,
            _config(
                **{
                    CONF_TYPE: FOLLOWUP_MUSIC_ASSISTANT,
                    CONF_PLAYER: "media_player.cocina",
                    CONF_MEDIA_ID: "library://playlist/3",
                    CONF_VOLUME: 0.3,
                },
            ),
        ),
    )
    assert [call[1] for call in hass.calls] == ["play_media"]


def test_async_run_swallows_service_errors(fake_hass):
    hass, _ = fake_hass()

    async def fail_call(domain, service, data=None, blocking=False):
        msg = "boom"
        raise RuntimeError(msg)

    hass.services.async_call = fail_call
    ran = _run(
        followup.async_run(
            hass,
            _config(**{CONF_TYPE: FOLLOWUP_SCRIPT, CONF_SCRIPT: "script.music"}),
        ),
    )
    assert ran is False


def test_async_run_does_nothing_when_disabled(fake_hass):
    hass, _ = fake_hass()
    assert _run(followup.async_run(hass, {})) is False
    assert hass.calls == []
