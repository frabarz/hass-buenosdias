"""Action that runs around the TTS announcement.

The ``followup`` options section is a single hook with two knobs:

- ``when``: ``after`` runs the action once the announcement is over (the
  sequential case: greeting first, then music), ``before`` runs it first and
  lets the announcement play on top (Music Assistant ducks its own queue when
  ``tts.speak`` sends ``announce=True``, so the music keeps playing).
- ``type``: ``script`` (any Home Assistant action), ``music_assistant``
  (``music_assistant.play_media`` with a playlist/album/track URI) or
  ``media_player`` (generic ``media_player.play_media``).

:func:`build_calls` is the pure part - it turns the options into the service
calls to make, so the dispatch table is testable without a running hass.
:func:`async_run` executes them.

Nothing here raises: the morning greeting already played, so a broken
playlist is a warning, never a failed emission.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from .const import (
    CONF_ANNOUNCE_VOLUME,
    CONF_ENABLED,
    CONF_ENQUEUE,
    CONF_FOLLOWUP,
    CONF_MEDIA_CONTENT_ID,
    CONF_MEDIA_CONTENT_TYPE,
    CONF_MEDIA_ID,
    CONF_MEDIA_TYPE,
    CONF_PLAYER,
    CONF_SCRIPT,
    CONF_TIMEOUT,
    CONF_TYPE,
    CONF_VOLUME,
    CONF_WAIT,
    CONF_WHEN,
    DEFAULT_FOLLOWUP_TIMEOUT,
    ENQUEUE_REPLACE,
    FOLLOWUP_MEDIA_PLAYER,
    FOLLOWUP_MUSIC_ASSISTANT,
    FOLLOWUP_NONE,
    FOLLOWUP_SCRIPT,
    MEDIA_TYPE_PLAYLIST,
    WHEN_AFTER,
    WHEN_BEFORE,
)
from .speak import async_set_volume

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

ServiceCall = tuple[str, str, dict[str, Any]]


@dataclass(frozen=True)
class Followup:
    """Resolved follow-up settings of the current configuration."""

    enabled: bool = False
    when: str = WHEN_AFTER
    type: str = FOLLOWUP_NONE
    player: str = ""
    volume: float | None = None
    wait: bool = True
    timeout: float = DEFAULT_FOLLOWUP_TIMEOUT
    announce_volume: int | None = None

    @property
    def runs(self) -> bool:
        """Return True when an action is configured and enabled."""
        return self.enabled and self.type != FOLLOWUP_NONE

    @property
    def before(self) -> bool:
        """Return True when the action starts before the announcement."""
        return self.runs and self.when == WHEN_BEFORE

    @property
    def after(self) -> bool:
        """Return True when the action runs after the announcement."""
        return self.runs and self.when == WHEN_AFTER


def _section(config: dict) -> dict:
    """Return the followup section as a dict, whatever the options hold."""
    section = config.get(CONF_FOLLOWUP)
    return section if isinstance(section, dict) else {}


def resolve(config: dict) -> Followup:
    """Read the ``followup`` section, tolerating missing or partial options."""
    section = _section(config)
    raw_volume = section.get(CONF_VOLUME)
    volume = None
    if raw_volume not in (None, ""):
        try:
            volume = float(raw_volume)
        except (TypeError, ValueError):
            _LOGGER.warning("ignoring invalid followup volume %r", raw_volume)
    timeout = DEFAULT_FOLLOWUP_TIMEOUT
    raw_timeout = section.get(CONF_TIMEOUT, DEFAULT_FOLLOWUP_TIMEOUT)
    try:
        timeout = float(raw_timeout)
    except (TypeError, ValueError):
        _LOGGER.warning("ignoring invalid followup timeout %r", raw_timeout)
    announce_volume = None
    raw_announce = section.get(CONF_ANNOUNCE_VOLUME)
    if raw_announce not in (None, ""):
        try:
            announce_volume = int(raw_announce)
        except (TypeError, ValueError):
            _LOGGER.warning("ignoring invalid announce volume %r", raw_announce)
    return Followup(
        enabled=bool(section.get(CONF_ENABLED)),
        when=str(section.get(CONF_WHEN) or WHEN_AFTER),
        type=str(section.get(CONF_TYPE) or FOLLOWUP_NONE),
        player=str(section.get(CONF_PLAYER) or "").strip(),
        volume=volume,
        wait=bool(section.get(CONF_WAIT, True)),
        timeout=timeout,
        announce_volume=announce_volume,
    )


def build_calls(config: dict) -> list[ServiceCall]:
    """Translate the options into the service calls the action needs."""
    settings = resolve(config)
    if not settings.runs:
        return []
    section = _section(config)

    if settings.type == FOLLOWUP_SCRIPT:
        script = str(section.get(CONF_SCRIPT) or "").strip()
        if not script:
            _LOGGER.warning("followup is a script but no script is configured")
            return []
        return [("script", "turn_on", {"entity_id": script})]

    if settings.type == FOLLOWUP_MUSIC_ASSISTANT:
        media_id = str(section.get(CONF_MEDIA_ID) or "").strip()
        if not settings.player or not media_id:
            _LOGGER.warning(
                "followup is music_assistant but player/media_id is missing",
            )
            return []
        return [
            (
                "music_assistant",
                "play_media",
                {
                    "entity_id": settings.player,
                    "media_id": media_id,
                    "media_type": str(
                        section.get(CONF_MEDIA_TYPE) or MEDIA_TYPE_PLAYLIST,
                    ),
                    "enqueue": str(section.get(CONF_ENQUEUE) or ENQUEUE_REPLACE),
                },
            ),
        ]

    if settings.type == FOLLOWUP_MEDIA_PLAYER:
        content_id = str(section.get(CONF_MEDIA_CONTENT_ID) or "").strip()
        if not settings.player or not content_id:
            _LOGGER.warning(
                "followup is media_player but player/media_content_id is missing",
            )
            return []
        return [
            (
                "media_player",
                "play_media",
                {
                    "entity_id": settings.player,
                    "media_content_id": content_id,
                    "media_content_type": str(
                        section.get(CONF_MEDIA_CONTENT_TYPE) or "music",
                    ),
                },
            ),
        ]

    _LOGGER.warning("unknown followup type %r", settings.type)
    return []


async def async_run(hass: HomeAssistant, config: dict) -> bool:
    """Set the optional volume and run the configured action.

    Returns True when a service call was made. Never raises: failures are
    logged so the emission keeps its ``ok`` status.
    """
    calls = build_calls(config)
    if not calls:
        return False
    settings = resolve(config)
    if settings.volume is not None and settings.player:
        await async_set_volume(hass, settings.player, settings.volume)
    for domain, service, data in calls:
        try:
            await hass.services.async_call(domain, service, data, blocking=True)
        except Exception as err:  # noqa: BLE001 - never fail the emission
            _LOGGER.warning("followup %s.%s failed: %s", domain, service, err)
            return False
    _LOGGER.debug("followup %s.%s sent", calls[0][0], calls[0][1])
    return True
