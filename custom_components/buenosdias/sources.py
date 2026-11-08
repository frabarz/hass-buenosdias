"""Context collection from Home Assistant state and RSS feeds.

``gather_ha_entities`` serialises requested ``weather``/``calendar``/``sensor``
entities via :func:`entity_brief` (state + attributes + last_updated).
``async_gather_weather`` optionally enriches weather briefs with the forecast
returned by ``weather.get_forecasts`` (``forecast_type`` is ``hourly`` or
``daily``). ``async_gather_context`` merges those with
:func:`rss.async_fetch_feeds` (news/events) and a timestamp — the dict consumed
by :mod:`prompts` and the LLM.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from . import rss
from .const import (
    CONF_CALENDAR,
    CONF_FEEDS,
    CONF_FORECAST_LIMIT,
    CONF_FORECAST_TYPE,
    CONF_RSS,
    CONF_SENSORS,
    CONF_SOURCES,
    CONF_WEATHER,
    DEFAULT_FORECAST_LIMIT,
    FORECAST_NONE,
    FORECAST_TYPES,
    KIND_EVENTS,
    KIND_NEWS,
    MAX_FORECAST_LIMIT,
)

_LOGGER = logging.getLogger(__name__)

SECTION_TIMESTAMP = "timestamp"
SECTION_FORECAST = "forecast"
WEATHER_DOMAIN = "weather"
FORECAST_SERVICE = "get_forecasts"
ATTR_FORECAST_TYPE = "type"


def entity_brief(entity_id: str, state: Any) -> dict:
    """Return a serializable dict with the essentials of a state."""
    return {
        "entity_id": entity_id,
        "state": state.state,
        "attributes": dict(state.attributes) if state.attributes else {},
        "last_updated": (
            state.last_updated.isoformat(timespec="seconds")
            if state.last_updated
            else None
        ),
    }


def gather_ha_entities(hass: Any, entity_ids: list[str]) -> dict:
    """Return a serializable brief for each requested entity_id."""
    result: dict = {}
    for entity_id in entity_ids or []:
        state = hass.states.get(entity_id)
        if state is None:
            result[entity_id] = {"error": "entity not found"}
            continue
        result[entity_id] = entity_brief(entity_id, state)
    return result


def _compact_forecast(entries: Any, limit: int) -> list[dict]:
    """Keep at most ``limit`` forecast entries, dropping unset fields."""
    compact: list[dict] = []
    for entry in entries or []:
        if not isinstance(entry, dict):
            continue
        compact.append(
            {key: value for key, value in entry.items() if value is not None},
        )
        if len(compact) >= limit:
            break
    return compact


async def async_fetch_forecast(
    hass: Any,
    entity_ids: list[str],
    forecast_type: str,
    limit: int,
) -> dict[str, list[dict]]:
    """Return the forecast of each weather entity, keyed by entity_id.

    Uses the ``weather.get_forecasts`` action, since Home Assistant no longer
    exposes forecasts as entity attributes. Failures are logged and ignored:
    a forecast is an enrichment, never a reason to skip the morning radio.
    """
    if not entity_ids or forecast_type not in FORECAST_TYPES:
        return {}
    forecasts: dict[str, list[dict]] = {}
    for entity_id in entity_ids:
        try:
            response = await hass.services.async_call(
                WEATHER_DOMAIN,
                FORECAST_SERVICE,
                {ATTR_FORECAST_TYPE: forecast_type},
                target={"entity_id": entity_id},
                blocking=True,
                return_response=True,
            )
        except Exception:
            _LOGGER.warning(
                "Could not fetch the %s weather forecast for %s; continuing without it",
                forecast_type,
                entity_id,
                exc_info=True,
            )
            continue

        payload = (response or {}).get(entity_id)
        entries = payload.get(SECTION_FORECAST) if isinstance(payload, dict) else None
        compact = _compact_forecast(entries, max(1, limit))
        if compact:
            forecasts[entity_id] = compact
    return forecasts


async def async_gather_weather(hass: Any, sources_cfg: dict) -> dict:
    """Return weather briefs, enriched with the configured forecast."""
    entity_ids = sources_cfg.get(CONF_WEATHER, [])
    weather = gather_ha_entities(hass, entity_ids)
    forecast_type = sources_cfg.get(CONF_FORECAST_TYPE, FORECAST_NONE)
    try:
        limit = int(sources_cfg.get(CONF_FORECAST_LIMIT, DEFAULT_FORECAST_LIMIT))
    except (TypeError, ValueError):
        limit = DEFAULT_FORECAST_LIMIT
    limit = min(max(1, limit), MAX_FORECAST_LIMIT)
    forecasts = await async_fetch_forecast(hass, entity_ids, forecast_type, limit)
    for entity_id, entries in forecasts.items():
        brief = weather.get(entity_id)
        if isinstance(brief, dict) and "error" not in brief:
            brief[SECTION_FORECAST] = entries
    return weather


async def async_gather_context(hass: Any, config: dict) -> dict:
    """Collect the morning context (weather, calendar, sensors and RSS)."""
    sources_cfg = config.get(CONF_SOURCES, {})
    feeds = sources_cfg.get(CONF_RSS, {}).get(CONF_FEEDS, [])
    rss_sections = await rss.async_fetch_feeds(hass, feeds)
    return {
        SECTION_TIMESTAMP: datetime.now().isoformat(timespec="seconds"),
        CONF_WEATHER: await async_gather_weather(hass, sources_cfg),
        CONF_CALENDAR: gather_ha_entities(hass, sources_cfg.get(CONF_CALENDAR, [])),
        CONF_SENSORS: gather_ha_entities(hass, sources_cfg.get(CONF_SENSORS, [])),
        KIND_NEWS: rss_sections[KIND_NEWS],
        KIND_EVENTS: rss_sections[KIND_EVENTS],
    }
