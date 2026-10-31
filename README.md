# Buenos Días — Home Assistant integration

A morning radio for Home Assistant: it gathers weather, calendar, sensors and
RSS, asks an LLM for a short spoken script, and plays it on your speakers
through `tts.speak`. It runs as a `custom_component`, so there is no extra
container or add-on.

## What it does

Set up once, get a device with:

- **Enabled switch** — pause or resume the daily alarm.
- **Last status** — `ok`, `error: …`, or `never`, with the full script and the
  last emission date as attributes.
- **Next alarm** — the next firing time in ISO-8601 UTC, or `not_scheduled`.
- **Actions** — `buenosdias.context`, `buenosdias.generate`, and
  `buenosdias.emit` for previews and manual playback.

The script can come from Home Assistant's own conversation agent or any
OpenAI-compatible endpoint (Ollama, OpenRouter, Groq, LM Studio, …). The UI is
translated into English, Spanish, German, and French. Requires Home Assistant
2025.2 or newer.

## Install

Via HACS (recommended):

1. HACS → Integrations → ⋮ → Custom repositories → add this repo URL
   (category *Integration*).
2. Install “Buenos Días”, restart Home Assistant.
3. Settings → Devices & Services → Add Integration → Buenos Días, then pick the
   LLM connection.

Details and alternatives (manual install, NixOS flake):
[docs/installation.md](docs/installation.md).

## Documentation

- [Configuration](docs/configuration.md) — LLM, TTS, sources, RSS, schedule.
- [Entities](docs/entities.md) — switch, status sensors, attributes.
- [Services](docs/services.md) — `context`, `generate`, `emit`.
- [Dashboards](docs/dashboards.md) — cards, buttons, failure notifications.
- [Troubleshooting](docs/troubleshooting.md) — LLM, TTS, alarms, migration.

## Development

```bash
nix develop            # HA + Python 3.13+ + pytest + ruff
pytest tests/
ruff check . && ruff format --check .
nix build .#default    # runs the suite with --asyncio-mode=auto
nix flake check
```

The integration lives in `custom_components/buenosdias/`. Tests use a small
`fake_hass` for unit tests and the real `hass` fixture from
`pytest-homeassistant-custom-component` for config-flow tests.

Implementation notes live in [AGENTS.md](AGENTS.md); traps we hit are in
[docs/cursed-knowledge.md](docs/cursed-knowledge.md).

## License

Apache-2.0, see [LICENSE](LICENSE).
