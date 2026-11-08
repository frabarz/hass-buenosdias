"""Tests of context collection from HA state."""

import asyncio
import json
from types import SimpleNamespace

from custom_components.buenosdias import sources
from custom_components.buenosdias.const import (
    CONF_CALENDAR,
    CONF_FORECAST_LIMIT,
    CONF_FORECAST_TYPE,
    CONF_SENSORS,
    CONF_SOURCES,
    CONF_WEATHER,
    KIND_EVENTS,
    KIND_NEWS,
)


class FakeState:
    def __init__(self, state, attributes=None, last_updated=None):
        self.state = state
        self.attributes = attributes or {}
        self.last_updated = last_updated


def make_hass(states):
    return SimpleNamespace(states=SimpleNamespace(get=lambda eid: states.get(eid)))


def make_forecast_hass(states, response=None, error=None, error_entities=None):
    """Return a hass stub whose weather.get_forecasts returns ``response``."""
    calls = []

    async def async_call(
        domain,
        service,
        data=None,
        target=None,
        blocking=False,
        return_response=False,
    ):
        calls.append(
            {
                "domain": domain,
                "service": service,
                "data": data,
                "target": target,
                "blocking": blocking,
                "return_response": return_response,
            }
        )
        if error is not None and (
            error_entities is None or target["entity_id"] in error_entities
        ):
            raise error
        return response

    hass = SimpleNamespace(
        states=SimpleNamespace(get=lambda eid: states.get(eid)),
        services=SimpleNamespace(async_call=async_call),
    )
    hass.forecast_calls = calls
    return hass


def test_entity_brief_serializable():
    brief = sources.entity_brief(
        "weather.casa",
        FakeState("sunny", {"temperature": 21.5}, last_updated=None),
    )
    assert brief["entity_id"] == "weather.casa"
    assert brief["state"] == "sunny"
    assert brief["attributes"] == {"temperature": 21.5}
    assert brief["last_updated"] is None
    json.dumps(brief)  # must be serializable


def test_gather_ha_entities_returns_briefs():
    hass = make_hass({"weather.casa": FakeState("sunny", {"temperature": 21.5})})
    result = sources.gather_ha_entities(hass, ["weather.casa"])
    assert result["weather.casa"]["state"] == "sunny"


def test_gather_ha_entities_missing_entity():
    hass = make_hass({})
    result = sources.gather_ha_entities(hass, ["sensor.ghost"])
    assert result["sensor.ghost"] == {"error": "entity not found"}


def test_async_gather_context_structure():
    hass = make_hass(
        {
            "weather.casa": FakeState("rainy", {"temperature": 12.0}),
            "calendar.familia": FakeState(
                "on", {"message": "doctor's appointment 10:00"}
            ),
        }
    )
    config = {
        CONF_SOURCES: {
            CONF_WEATHER: ["weather.casa"],
            CONF_CALENDAR: ["calendar.familia"],
            CONF_SENSORS: [],
        }
    }

    context = asyncio.run(sources.async_gather_context(hass, config))
    assert "timestamp" in context
    assert context[CONF_WEATHER]["weather.casa"]["state"] == "rainy"
    assert (
        context[CONF_CALENDAR]["calendar.familia"]["attributes"]["message"]
        == "doctor's appointment 10:00"
    )
    assert context[CONF_SENSORS] == {}
    assert context[KIND_NEWS] == []
    assert context[KIND_EVENTS] == []
    json.dumps(context)  # must be serializable


def _forecast_config(forecast_type, limit):
    return {
        CONF_SOURCES: {
            CONF_WEATHER: ["weather.casa"],
            CONF_FORECAST_TYPE: forecast_type,
            CONF_FORECAST_LIMIT: limit,
        }
    }


def test_forecast_is_attached_and_limited():
    hass = make_forecast_hass(
        {"weather.casa": FakeState("sunny", {"temperature": 21.5})},
        response={
            "weather.casa": {
                "forecast": [
                    {
                        "datetime": "2026-11-08T08:00:00+00:00",
                        "condition": "rainy",
                        "temperature": 12.0,
                        "precipitation_probability": None,
                    },
                    {
                        "datetime": "2026-11-08T09:00:00+00:00",
                        "condition": "cloudy",
                        "temperature": 13.0,
                    },
                ]
            }
        },
    )

    context = asyncio.run(
        sources.async_gather_context(hass, _forecast_config("hourly", 1))
    )

    forecast = context[CONF_WEATHER]["weather.casa"]["forecast"]
    assert len(forecast) == 1
    assert forecast[0] == {
        "datetime": "2026-11-08T08:00:00+00:00",
        "condition": "rainy",
        "temperature": 12.0,
    }
    call = hass.forecast_calls[0]
    assert call["domain"] == "weather"
    assert call["service"] == "get_forecasts"
    assert call["data"] == {"type": "hourly"}
    assert call["target"] == {"entity_id": "weather.casa"}
    assert call["blocking"] is True
    assert call["return_response"] is True
    json.dumps(context)


def test_no_forecast_type_skips_the_service():
    hass = make_forecast_hass(
        {"weather.casa": FakeState("sunny")},
        response={"weather.casa": {"forecast": []}},
    )

    context = asyncio.run(
        sources.async_gather_context(hass, _forecast_config("none", 12))
    )

    assert "forecast" not in context[CONF_WEATHER]["weather.casa"]
    assert hass.forecast_calls == []


def test_forecast_service_failure_keeps_current_conditions():
    hass = make_forecast_hass(
        {"weather.casa": FakeState("sunny")},
        error=RuntimeError("boom"),
    )

    context = asyncio.run(
        sources.async_gather_context(hass, _forecast_config("daily", 3))
    )

    assert context[CONF_WEATHER]["weather.casa"]["state"] == "sunny"
    assert "forecast" not in context[CONF_WEATHER]["weather.casa"]


def test_forecast_not_attached_to_missing_entity():
    hass = make_forecast_hass(
        {},
        response={"weather.casa": {"forecast": [{"temperature": 10.0}]}},
    )

    context = asyncio.run(
        sources.async_gather_context(hass, _forecast_config("hourly", 12))
    )

    assert context[CONF_WEATHER]["weather.casa"] == {"error": "entity not found"}


def test_forecast_failure_for_one_entity_does_not_block_the_others():
    hass = make_forecast_hass(
        {
            "weather.casa": FakeState("sunny"),
            "weather.office": FakeState("cloudy"),
        },
        response={"weather.office": {"forecast": [{"temperature": 9.0}]}},
        error=RuntimeError("unsupported forecast"),
        error_entities={"weather.casa"},
    )
    config = {
        CONF_SOURCES: {
            CONF_WEATHER: ["weather.casa", "weather.office"],
            CONF_FORECAST_TYPE: "hourly",
            CONF_FORECAST_LIMIT: 12,
        }
    }

    context = asyncio.run(sources.async_gather_context(hass, config))

    assert "forecast" not in context[CONF_WEATHER]["weather.casa"]
    assert context[CONF_WEATHER]["weather.office"]["forecast"] == [{"temperature": 9.0}]
    assert len(hass.forecast_calls) == 2


def test_forecast_limit_is_clamped_to_a_minimum_of_one():
    hass = make_forecast_hass(
        {"weather.casa": FakeState("sunny")},
        response={"weather.casa": {"forecast": [{"temperature": 10.0}]}},
    )

    context = asyncio.run(
        sources.async_gather_context(hass, _forecast_config("hourly", 0))
    )

    assert len(context[CONF_WEATHER]["weather.casa"]["forecast"]) == 1


def test_invalid_forecast_limit_falls_back_to_the_default():
    hass = make_forecast_hass(
        {"weather.casa": FakeState("sunny")},
        response={
            "weather.casa": {"forecast": [{"temperature": float(i)} for i in range(20)]}
        },
    )

    context = asyncio.run(
        sources.async_gather_context(hass, _forecast_config("hourly", "not-a-number"))
    )

    assert len(context[CONF_WEATHER]["weather.casa"]["forecast"]) == 12
