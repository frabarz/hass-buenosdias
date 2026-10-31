# AGENTS.md

## Project Overview

Personalized morning radio for Home Assistant: it gathers context (weather,
calendar, sensors, RSS), asks an LLM for a spoken script, and plays it through
TTS. HACS-installable repo **and** Nix flake (`packages`, `devShells`,
`checks`) for NixOS deployment.

- Integration code: `custom_components/buenosdias/` (domain `buenosdias`,
  config-flow-only, `single_config_entry`, runtime `requirements`:
  `feedparser`; `httpx` comes bundled with Home Assistant and is used through
  `homeassistant.helpers.httpx_client`).
- Nix package: `pkgs/buenosdias-ha/package.nix` (via
  `buildHomeAssistantComponent`), exposed as `packages.<system>.default`.
- Config flow: LLM connection only (HA conversation agent or OpenAI-compatible,
  probed with `GET /models`); everything else lives in the options flow.
- Options: script/persona, TTS, sources, RSS feeds, schedule.
- Packaging versions must match in `const.py`, `manifest.json`,
  `pyproject.toml`, and `pkgs/buenosdias-ha/package.nix` (currently `0.3.2`).
- Toolchain: Nix flake, Python 3.13+ (dev shell 3.14), HA 2025.2+ runtime,
  `pytest` + `pytest-homeassistant-custom-component`, ruff with `select = ["ALL"]`.

## Setup Commands

- Enter dev env: `nix develop`
- Run tests: `pytest tests/ -q`
- Lint and format check: `ruff check . && ruff format --check .`
- Build package: `nix build .#default`
- Check everything: `nix flake check`

## Development Workflow

- Pipeline: `sources.py` (HA entities + RSS) → `script.py`/`prompts.py` →
  `llm.py` → `speak.py`, orchestrated by `coordinator.py`.
- LLM clients in `llm.py`: `HAConversationLLM` (`conversation.async_converse`),
  `OpenAICompatLLM` (`/chat/completions`), `FallbackLLM`.
- Scheduling in `scheduler.py` (`time` / `time_entity`, `skip_days`,
  `feriados`, `holiday_calendar`, `skip_if_emitted`, `preload_minutes`).
  Persisted state lives in `state.py`; entities in `switch.py` / `sensor.py`.
- Services (`context`, `generate`, `emit`) are registered in `__init__.py`;
  descriptions live in `services.yaml`.
- Config and options in `config_flow.py`; validation/defaults in
  `config_schema.py` / `config_utils.py`. The YAML block is import-only since
  v0.2.0.
- NixOS consumer wiring:
  ```nix
  services.home-assistant = {
    enable = true;
    customComponents = [
      inputs.hass-buenosdias.packages.${pkgs.stdenv.hostPlatform.system}.default
    ];
  };
  ```
  Keep `inputs.nixpkgs.follows = "nixpkgs"` in the flake input. Configuration
  stays in the HA UI (no declarative YAML).
- Version bumps: update `const.py`, `manifest.json`, `pyproject.toml`, and
  `pkgs/buenosdias-ha/package.nix`, then run the full gate.

## Testing Instructions

- Run all tests: `pytest tests/ -q` (from repo root, inside `nix develop`).
- Two harnesses: a small `fake_hass` for unit tests and the real `hass` fixture
  from `pytest-homeassistant-custom-component` for config/options flows. Split
  in `tests/conftest.py`.
- Suites: `test_sources`, `test_rss`, `test_llm`, `test_script`,
  `test_speak`, `test_scheduler`, `test_state`, `test_entities`,
  `test_coordinator`, `test_init`, `test_setup`, `test_config_flow`,
  `test_options_flow`, `test_config_schema`, `test_config_utils`.
- `nix build .#default` runs the suite with `--asyncio-mode=auto`.
- CI: hassfest (`hassfest.yaml`) and HACS validation (`validate.yaml`). Run
  `pytest` and `ruff` locally; they are not wired into CI.

## Code Style

- `ruff check .` and `ruff format --check .` must pass (`select = ["ALL"]`,
  with the documented ignores in `pyproject.toml`).
- Fully typed, async-only code. All HA access goes through the injected `hass`
  object; never block the event loop.
- Service and entity names in English; UI strings and translations can be any
  language.

## Build and Deployment

- `nix build .#default` → component derivation (`result/custom_components/buenosdias/`).
- HACS install: keep `custom_components/buenosdias/` at the repo root,
  `hacs.json` (`homeassistant: 2025.2`), `README.md`, and `docs/`.
- Bump `manifest.json → version` on every release (HACS compares it).

## Additional Notes

- `docs/cursed-knowledge.md` collects traps; start with the
  `ConfigEntry.add_update_listener` unsubscribe rule.
- `.design/` is local-only (gitignored) and holds plans/specs.
