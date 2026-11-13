"""Orchestration of the full good-morning pipeline.

:func:`async_run` runs Context → Script → TTS. With ``emit=False`` it
dry-runs (generates the script without playing audio). Used by the
``buenosdias.generate``/``buenosdias.emit`` services and the daily alarm in
:mod:`__init__`.

:func:`async_emit_script` is the playback half: it wraps :func:`speak` with the
optional follow-up action (before the announcement, after it, or both) and is
shared with the preloaded-script path of the alarm so both behave the same.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from . import followup, script, sources
from .const import CONF_MEDIA_PLAYER, CONF_TTS
from .speak import (
    PlaybackWatcher,
    SpeakError,
    async_announce,
    async_preload,
    async_speak,
    can_announce,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


class PipelineError(Exception):
    """Error in the good-morning pipeline."""


async def async_emit_script(
    hass: HomeAssistant,
    config: dict,
    text: str,
) -> None:
    """Play *text* and run the follow-up action around the announcement.

    Two orderings:

    - ``before``: start the media, then greet over it. With a Music Assistant
      player the greeting is played as an announcement, so the queue ducks and
      resumes and the music keeps running.
    - ``after``: greet, wait for the announcement to end (``PlaybackWatcher``)
      and only then start the media.

    Raises :class:`SpeakError` when the greeting itself fails; the follow-up
    never fails.
    """
    follow = followup.resolve(config)
    if follow.before:
        await followup.async_run(hass, config)
        await _async_greet_over_media(hass, config, text, follow)
        return

    media_player = config.get(CONF_TTS, {}).get(CONF_MEDIA_PLAYER, "")
    watcher = None
    if follow.after and follow.wait and media_player:
        watcher = PlaybackWatcher(
            hass,
            media_player,
            timeout=follow.timeout,
        ).async_start()

    try:
        await async_speak(hass, config, text)
        if watcher is not None:
            await watcher.async_wait()
    finally:
        if watcher is not None:
            watcher.async_stop()

    if follow.after:
        await followup.async_run(hass, config)


async def _async_greet_over_media(
    hass: HomeAssistant,
    config: dict,
    text: str,
    follow: followup.Followup,
) -> None:
    """Speak the greeting without cutting the media the action started.

    Music Assistant can mix an announcement over its own queue; any other
    player simply replaces what it is playing, so the follow-up has no way to
    keep the music running. In that case the greeting still plays (with the
    volume left alone) and the misconfiguration is logged.
    """
    player = config.get(CONF_TTS, {}).get(CONF_MEDIA_PLAYER, "")
    if can_announce(hass, player):
        await async_announce(
            hass,
            config,
            text,
            player=player,
            volume=follow.announce_volume,
        )
        return
    _LOGGER.warning(
        "follow-up 'before' runs on %s, which cannot play announcements; "
        "the greeting will interrupt the media instead of mixing over it",
        player or "the configured media player",
    )
    await async_speak(hass, config, text, manage_volume=False)


async def async_run(
    hass: HomeAssistant,
    config: dict,
    emit: bool = True,
) -> dict:
    """Run the pipeline: context → script → TTS.

    With ``emit=False`` it generates the script without playing audio (dry-run).
    """
    context = await sources.async_gather_context(hass, config)
    try:
        script_text = await script.async_generate_script(hass, config, context)
    except Exception as err:
        msg = f"script generation failed: {err}"
        raise PipelineError(msg) from err

    if emit:
        try:
            await async_emit_script(hass, config, script_text)
        except SpeakError as err:
            msg = f"script playback failed: {err}"
            raise PipelineError(msg) from err

    return {"script": script_text, "context": context}


async def async_preload_run(
    hass: HomeAssistant,
    config: dict,
) -> dict:
    """Run context → script → silent TTS cache warm.

    Used by the preload timer ``2-3`` minutes before the alarm so the
    subsequent ``async_speak`` at alarm time is a cache hit (file +
    memory cache). Never raises ``SpeakError`` - TTS warm failures are
    logged and ignored; the caller can still play via a normal run.
    """
    context = await sources.async_gather_context(hass, config)
    try:
        script_text = await script.async_generate_script(hass, config, context)
    except Exception as err:
        msg = f"script generation failed: {err}"
        raise PipelineError(msg) from err

    # Warm the TTS cache silently. Failures are non-fatal.
    try:
        await async_preload(hass, config, script_text)
    except Exception as err:  # pragma: no cover - defensive
        _LOGGER.debug("preload TTS warm failed: %s", err)

    return {"script": script_text, "context": context}
