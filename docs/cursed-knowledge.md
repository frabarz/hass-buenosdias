# Cursed Knowledge

Cursed knowledge we have learned building buenosdias that we wish we never knew.

## 11/13/2026

- **A new module plus `nix build` produces a fake "circular import"**

  Adding `followup.py` and importing it from `coordinator.py` as
  `from . import followup` made `nix build .#default` fail in *every* test
  module with:

  ```text
  ImportError: cannot import name 'followup' from partially initialized
  module 'custom_components.buenosdias' (most likely due to a circular
  import)
  ```

  while `pytest` from `nix develop` passed. There was no circular import. Two
  traps stacked:

  1. The flake source is filtered by git, so **untracked files do not exist**
     for `nix build` (`git add` the new module first — the error never says
     the file is missing).
  2. Python's `from . import x` swallows the `ModuleNotFoundError` and reports
     the confusing "partially initialized module" message instead
     (`importlib._bootstrap._handle_fromlist` ignores a missing submodule).

  Tell-tale sign: the failure hits *all* test modules at collection, not just
  the ones touching the new module. Check `git status` before debugging
  imports.

## 8/15/2026

- **`ConfigEntry.add_update_listener` is cursed**

  Home Assistant's `ConfigEntry.add_update_listener` does **not** deduplicate:
  it blindly appends to `entry.update_listeners`
  (`homeassistant/config_entries.py`, `ConfigEntry.add_update_listener`).
  We called it inside `async_setup_entry`, so every reload added another copy.
  The first time a user saved a preference through the options flow
  (`config_flow.py` → `_replace_options` → `async_create_entry`), HA's
  `OptionsFlowManager.async_finish_flow` called `async_update_entry`, which
  fired *every* accumulated listener. Each one ran
  `_async_update_listener` → `async_reload`, and each reload re-added another
  duplicate — an exponential reload cascade. The event loop flooded with
  `Setup of buenosdias.sensor/switch` cycles until the websocket hit
  `Client unable to keep up with pending messages. Reached 4096 pending
  messages` and HA hard-froze while the "entry updated" events queued up.

  The rule: **always keep the unlisten callback returned by
  `add_update_listener` and call it in `async_unload_entry`**
  (see `__init__.py:async_setup_entry` / `async_unload_entry`).
  It is the same lifecycle discipline as `event.async_track_*` and
  `async_track_time_change`.

  Tell-tale symptom in the log: a single config-entry `modified_at` timestamp,
  then a wall of repeating `Setting up <platform>` lines, and a websocket
  connection dropping with 4096 pending `entry updated` messages.