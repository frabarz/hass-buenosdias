"""Tests of the full pipeline (context → script → TTS)."""

import asyncio

import pytest

from custom_components.buenosdias import coordinator, followup, script
from custom_components.buenosdias.const import (
    CONF_ANNOUNCE_VOLUME,
    CONF_ENABLED,
    CONF_ENTITY_ID,
    CONF_FOLLOWUP,
    CONF_MEDIA_ID,
    CONF_MEDIA_PLAYER,
    CONF_PLAYER,
    CONF_SCRIPT,
    CONF_SOURCES,
    CONF_TTS,
    CONF_TYPE,
    CONF_WAIT,
    CONF_WEATHER,
    FOLLOWUP_MUSIC_ASSISTANT,
    FOLLOWUP_SCRIPT,
)
from custom_components.buenosdias.coordinator import PipelineError
from custom_components.buenosdias.llm import LLMClient
from custom_components.buenosdias.speak import SpeakError


class _FixedLLM(LLMClient):
    async def async_complete(self, system, user):
        return "Good morning, it is sunny today."


def _run(coro):
    return asyncio.run(coro)


def _make_hass():
    from types import SimpleNamespace

    from conftest import FakeState

    states = {"weather.casa": FakeState("sunny", {"temperature": 21.5})}
    return SimpleNamespace(
        states=SimpleNamespace(get=lambda eid: states.get(eid)),
        services=SimpleNamespace(async_call=lambda *a, **k: None),
    )


def _config():
    return {CONF_SOURCES: {CONF_WEATHER: ["weather.casa"]}}


def test_async_run_generates_and_plays(monkeypatch):
    spoken = {}

    async def fake_speak(hass, config, text):
        spoken["text"] = text

    monkeypatch.setattr(coordinator, "async_speak", fake_speak)
    monkeypatch.setattr(script, "build_llm", lambda hass, config: _FixedLLM())

    result = _run(coordinator.async_run(_make_hass(), _config()))
    assert result["script"] == "Good morning, it is sunny today."
    assert spoken["text"] == "Good morning, it is sunny today."


def test_async_run_emit_false_does_not_play(monkeypatch):
    spoken = []

    async def fake_speak(hass, config, text):
        spoken.append(text)

    monkeypatch.setattr(coordinator, "async_speak", fake_speak)
    monkeypatch.setattr(script, "build_llm", lambda hass, config: _FixedLLM())

    result = _run(coordinator.async_run(_make_hass(), _config(), emit=False))
    assert result["script"] == "Good morning, it is sunny today."
    assert spoken == []


def test_async_run_speak_failure_raises_pipeline_error(monkeypatch):
    async def fake_speak(hass, config, text):
        raise SpeakError("tts broken")

    monkeypatch.setattr(coordinator, "async_speak", fake_speak)
    monkeypatch.setattr(script, "build_llm", lambda hass, config: _FixedLLM())

    with pytest.raises(PipelineError):
        _run(coordinator.async_run(_make_hass(), _config()))


def test_async_run_script_failure_raises_pipeline_error(monkeypatch):
    async def bad_complete(system, user):
        raise RuntimeError("llm down")

    class _BadLLM(LLMClient):
        async def async_complete(self, system, user):
            return await bad_complete(system, user)

    monkeypatch.setattr(script, "build_llm", lambda hass, config: _BadLLM())

    with pytest.raises(PipelineError):
        _run(coordinator.async_run(_make_hass(), _config()))


# ---------- follow-up hook around the announcement ----------


def _emit_config(**followup_section):
    return {
        CONF_TTS: {
            CONF_ENTITY_ID: "tts.piper",
            CONF_MEDIA_PLAYER: "media_player.sala",
        },
        CONF_FOLLOWUP: {CONF_ENABLED: True, **followup_section},
    }


class _FakeWatcher:
    """Record the PlaybackWatcher lifecycle without touching real states."""

    instances: list = []

    def __init__(self, hass, entity_id, *, timeout):
        self.entity_id = entity_id
        self.timeout = timeout
        self.events = []
        _FakeWatcher.instances.append(self)

    def async_start(self):
        self.events.append("start")
        return self

    async def async_wait(self):
        self.events.append("wait")

    def async_stop(self):
        self.events.append("stop")


@pytest.fixture
def emit_order(fake_hass, monkeypatch):
    """Patch speak/followup so the tests see the call order only."""
    hass, _ = fake_hass()
    order: list[str] = []
    speak_kwargs: list[dict] = []

    async def fake_speak(_hass, _config, text, **kwargs):
        order.append("speak")
        speak_kwargs.append(kwargs)

    async def fake_followup(_hass, _config):
        order.append("followup")
        return True

    async def fake_announce(_hass, _config, text, *, player, volume=None):
        order.append("announce")
        speak_kwargs.append({"player": player, "volume": volume})

    monkeypatch.setattr(coordinator, "async_speak", fake_speak)
    monkeypatch.setattr(coordinator, "async_announce", fake_announce)
    monkeypatch.setattr(coordinator, "can_announce", lambda _hass, _player: False)
    monkeypatch.setattr(followup, "async_run", fake_followup)
    _FakeWatcher.instances.clear()
    monkeypatch.setattr(coordinator, "PlaybackWatcher", _FakeWatcher)
    return hass, order, speak_kwargs


def test_emit_runs_the_followup_after_the_announcement(emit_order):
    hass, order, _kwargs = emit_order
    _run(
        coordinator.async_emit_script(
            hass,
            _emit_config(**{CONF_TYPE: FOLLOWUP_SCRIPT, CONF_SCRIPT: "script.music"}),
            "Buenos días",
        ),
    )
    assert order == ["speak", "followup"]


def test_emit_waits_for_the_announcement_before_the_followup(emit_order):
    hass, _order, _kwargs = emit_order
    _run(
        coordinator.async_emit_script(
            hass,
            _emit_config(**{CONF_TYPE: FOLLOWUP_SCRIPT, CONF_SCRIPT: "script.music"}),
            "Buenos días",
        ),
    )
    watcher = _FakeWatcher.instances[0]
    assert watcher.entity_id == "media_player.sala"
    assert watcher.events == ["start", "wait", "stop"]


def test_emit_runs_the_followup_before_the_announcement(emit_order):
    hass, order, speak_kwargs = emit_order
    _run(
        coordinator.async_emit_script(
            hass,
            _emit_config(
                **{
                    CONF_TYPE: FOLLOWUP_SCRIPT,
                    CONF_SCRIPT: "script.music",
                    "when": "before",
                },
            ),
            "Buenos días",
        ),
    )
    assert order == ["followup", "speak"]
    # The greeting must not touch the volume of the media already playing.
    assert speak_kwargs[-1]["manage_volume"] is False


def test_emit_skips_the_wait_when_disabled(emit_order):
    hass, order, _kwargs = emit_order
    _run(
        coordinator.async_emit_script(
            hass,
            _emit_config(
                **{
                    CONF_TYPE: FOLLOWUP_SCRIPT,
                    CONF_SCRIPT: "script.music",
                    CONF_WAIT: False,
                },
            ),
            "Buenos días",
        ),
    )
    assert order == ["speak", "followup"]
    assert _FakeWatcher.instances == []


def test_emit_without_followup_only_speaks(fake_hass, monkeypatch):
    hass, _ = fake_hass()
    order = []

    async def fake_speak(_hass, _config, text):
        order.append("speak")

    monkeypatch.setattr(coordinator, "async_speak", fake_speak)
    monkeypatch.setattr(
        followup,
        "async_run",
        lambda *_a, **_k: pytest.fail("followup must not run"),
    )
    monkeypatch.setattr(
        coordinator,
        "PlaybackWatcher",
        lambda *_a, **_k: pytest.fail("no watcher without a followup"),
    )

    _run(coordinator.async_emit_script(hass, _emit_config(), "Buenos días"))
    assert order == ["speak"]


def test_emit_propagates_speak_errors(emit_order, monkeypatch):
    hass, order, _kwargs = emit_order

    async def broken_speak(_hass, _config, text):
        order.append("speak")
        msg = "tts broken"
        raise SpeakError(msg)

    monkeypatch.setattr(coordinator, "async_speak", broken_speak)

    with pytest.raises(SpeakError):
        _run(
            coordinator.async_emit_script(
                hass,
                _emit_config(
                    **{CONF_TYPE: FOLLOWUP_SCRIPT, CONF_SCRIPT: "script.music"}
                ),
                "Buenos días",
            ),
        )
    assert order == ["speak"]


def test_emit_before_announces_over_music_assistant(emit_order, monkeypatch):
    hass, order, speak_kwargs = emit_order
    monkeypatch.setattr(coordinator, "can_announce", lambda _hass, _player: True)

    _run(
        coordinator.async_emit_script(
            hass,
            _emit_config(
                **{
                    CONF_TYPE: FOLLOWUP_MUSIC_ASSISTANT,
                    CONF_PLAYER: "media_player.cocina",
                    CONF_MEDIA_ID: "library://playlist/3",
                    CONF_ANNOUNCE_VOLUME: 35,
                    "when": "before",
                },
            ),
            "Buenos días",
        ),
    )

    assert order == ["followup", "announce"]
    assert speak_kwargs[-1] == {"player": "media_player.sala", "volume": 35}


def test_emit_before_falls_back_without_announce_support(emit_order, monkeypatch):
    hass, order, speak_kwargs = emit_order
    monkeypatch.setattr(coordinator, "can_announce", lambda _hass, _player: False)

    _run(
        coordinator.async_emit_script(
            hass,
            _emit_config(
                **{
                    CONF_TYPE: FOLLOWUP_MUSIC_ASSISTANT,
                    CONF_PLAYER: "media_player.cocina",
                    CONF_MEDIA_ID: "library://playlist/3",
                    "when": "before",
                },
            ),
            "Buenos días",
        ),
    )

    assert order == ["followup", "speak"]
    assert speak_kwargs[-1]["manage_volume"] is False


def test_emit_after_does_not_announce(emit_order, monkeypatch):
    hass, order, speak_kwargs = emit_order
    monkeypatch.setattr(coordinator, "can_announce", lambda _hass, _player: True)

    _run(
        coordinator.async_emit_script(
            hass,
            _emit_config(**{CONF_TYPE: FOLLOWUP_SCRIPT, CONF_SCRIPT: "script.music"}),
            "Buenos días",
        ),
    )

    assert order == ["speak", "followup"]
    assert "manage_volume" not in speak_kwargs[-1]
