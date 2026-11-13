"""Tests of the script playback via TTS."""

import asyncio
from types import SimpleNamespace

import pytest
from conftest import FakeState

from custom_components.buenosdias import speak
from custom_components.buenosdias.const import CONF_TTS


def _run(coro):
    return asyncio.run(coro)


def _config(**tts):
    cfg = {
        CONF_TTS: {
            "entity_id": "tts.piper",
            "media_player": "media_player.sala",
            "language": "es-ES",
            "volume": 0.6,
            "restore_volume": True,
        }
    }
    cfg[CONF_TTS].update(tts)
    return cfg


def _mp_state(state="on", volume=0.8):
    from conftest import FakeState
    from homeassistant.components.media_player import MediaPlayerEntityFeature

    return FakeState(
        state,
        {
            "volume_level": volume,
            "supported_features": int(
                MediaPlayerEntityFeature.TURN_ON | MediaPlayerEntityFeature.VOLUME_SET
            ),
        },
    )


def test_async_speak_sets_and_restores_volume(fake_hass):
    hass, _ = fake_hass({"media_player.sala": _mp_state(state="on", volume=0.8)})
    _run(speak.async_speak(hass, _config(), "Good morning."))

    assert (
        (
            "media_player",
            "volume_set",
            {"entity_id": "media_player.sala", "volume_level": 0.6},
        )
    ) in hass.calls
    tts_call = next(c for c in hass.calls if c[0] == "tts")
    assert tts_call[1] == "speak"
    assert tts_call[2]["message"] == "Good morning."
    assert tts_call[2]["language"] == "es-ES"
    assert tts_call[2]["entity_id"] == "tts.piper"
    assert tts_call[2]["media_player_entity_id"] == "media_player.sala"
    assert hass.calls[-1] == (
        "media_player",
        "volume_set",
        {"entity_id": "media_player.sala", "volume_level": 0.8},
    )


def test_async_speak_turns_on_off_media_player(fake_hass):
    hass, _ = fake_hass({"media_player.sala": _mp_state(state="off", volume=0.8)})
    _run(speak.async_speak(hass, _config(), "Hello"))
    assert ("media_player", "turn_on", {"entity_id": "media_player.sala"}) in hass.calls


def test_async_speak_does_not_turn_on_playing(fake_hass):
    hass, _ = fake_hass({"media_player.sala": _mp_state(state="on", volume=0.8)})
    _run(speak.async_speak(hass, _config(), "Hello"))
    assert not any(c[1] == "turn_on" for c in hass.calls)


def test_async_speak_does_not_restore_if_restore_false(fake_hass):
    hass, _ = fake_hass({"media_player.sala": _mp_state(state="on", volume=0.8)})
    _run(speak.async_speak(hass, _config(restore_volume=False), "Hello"))
    assert not any(
        c[1] == "volume_set" and c[2]["volume_level"] == 0.8 for c in hass.calls
    )


def test_async_speak_skips_volume_if_matching(fake_hass):
    hass, _ = fake_hass({"media_player.sala": _mp_state(state="on", volume=0.6)})
    _run(speak.async_speak(hass, _config(), "Hello"))
    assert not any(
        c[1] == "volume_set" and c[2]["volume_level"] == 0.6 for c in hass.calls
    )


def test_async_speak_requires_entity_and_media_player(fake_hass):
    hass, _ = fake_hass()
    with pytest.raises(speak.SpeakError):
        _run(speak.async_speak(hass, {CONF_TTS: {}}, "Hello"))


def test_async_speak_service_error(fake_hass, monkeypatch):
    hass, _ = fake_hass({"media_player.sala": _mp_state(state="off")})

    async def fail_call(domain, service, data=None, blocking=False):
        raise RuntimeError("boom")

    monkeypatch.setattr(hass.services, "async_call", fail_call)
    with pytest.raises(speak.SpeakError):
        _run(speak.async_speak(hass, _config(), "Hello"))


def test_media_player_volume_unknown_is_none(fake_hass):
    hass, _ = fake_hass()
    assert speak.media_player_volume(hass, "media_player.sala") is None


def test_async_speak_skips_volume_without_volume_set_feature(fake_hass):
    from conftest import FakeState

    hass, _ = fake_hass(
        {
            "media_player.sala": FakeState(
                "on", {"volume_level": 0.8, "supported_features": 0}
            )
        }
    )
    _run(speak.async_speak(hass, _config(), "Hello"))
    assert not any(c[1] == "volume_set" for c in hass.calls)


# ---------- PlaybackWatcher ----------


def _watcher(fake_trackers, state="idle", **kwargs):
    hass = SimpleNamespace(states=SimpleNamespace(get=lambda _eid: FakeState(state)))
    watcher = speak.PlaybackWatcher(hass, "media_player.sala", **kwargs)
    watcher.async_start()
    action = fake_trackers.state_change_calls[-1]["action"]
    return watcher, action


def _event(new_state):
    return SimpleNamespace(data={"new_state": new_state})


def test_watcher_resolves_when_playback_stops(fake_trackers):
    watcher, action = _watcher(fake_trackers, start_grace=0.5, timeout=0.5)

    async def scenario():
        action(_event(FakeState("playing")))
        asyncio.get_running_loop().call_soon(
            action,
            _event(FakeState("idle")),
        )
        return await watcher.async_wait()

    assert _run(scenario()) is True
    assert watcher._unsub is None


def test_watcher_gives_up_when_never_playing(fake_trackers):
    watcher, _ = _watcher(fake_trackers, state="idle", start_grace=0.01, timeout=5)
    assert _run(watcher.async_wait()) is False
    assert watcher._unsub is None


def test_watcher_gives_up_on_timeout(fake_trackers):
    watcher, _ = _watcher(
        fake_trackers, state="playing", start_grace=0.01, timeout=0.05
    )
    assert _run(watcher.async_wait()) is False
    assert watcher._unsub is None


def test_watcher_resolves_on_unavailable(fake_trackers):
    watcher, action = _watcher(fake_trackers, start_grace=5, timeout=5)

    async def scenario():
        action(_event(FakeState("playing")))
        asyncio.get_running_loop().call_soon(
            action,
            _event(FakeState("unavailable")),
        )
        return await watcher.async_wait()

    assert _run(scenario()) is True


def test_watcher_already_playing_skips_the_start_grace(fake_trackers):
    watcher, _ = _watcher(fake_trackers, state="playing", start_grace=5, timeout=0.05)
    assert watcher._saw_playing is True
    assert _run(watcher.async_wait()) is False
    assert watcher._unsub is None
