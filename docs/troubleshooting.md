# Troubleshooting

## `last_status` starts with `error: script generation failed`

The LLM step failed. Check, in order:

- **Conversation agent mode** — the selected agent still exists and responds in
  Developer Tools → Actions → `conversation.process`.
- **OpenAI-compatible mode** — `base_url` answers `GET /models` and
  `POST /chat/completions`; the model name matches what the endpoint serves.
- **API key** — cloud providers reject expired or missing keys. Home Assistant
  opens a reauthentication flow when it detects this; otherwise run
  **Reconfigure** from the integration card.
- **Prompt size** — if the script keeps running long, lower **Maximum script
  length** in **Configure → Script and voice**. The integration retries once to
  shorten it, then gives up.

## `last_status` starts with `error: script playback failed`

The script was generated but TTS or the media player failed.

- Confirm the **TTS entity** is a `tts.*` entity and the **media player** is
  available (not `unavailable` / `off` for long periods).
- Check that the player accepts the configured **Language**. Some engines only
  advertise a subset of voices.
- Try a manual `tts.speak` call from Developer Tools with the same entity and
  message to isolate the integration from the player.
- A failed **preload** is logged and ignored; the alarm-time playback still
  runs normally, so `preload_minutes` is not the cause.

## The alarm never fires

- The **Enabled** switch is off. Turn it back on; a missed morning is not
  replayed.
- `sensor.buenos_dias_next_alarm` says `not_scheduled` — every day in the
  scheduler's lookahead window is skipped. Check **Skip weekdays**, the manual
  **Holidays** list, and the **Holiday calendar**.
- A time entity is set and currently reports an invalid or past time. With a
  **Time entity**, the fixed **Alarm time** is ignored and the alarm re-arms
  whenever the sensor changes.
- **Skip if already emitted** is on and the alarm already ran today. A failed
  run also marks the day, so use `buenosdias.emit` to retry manually after
  fixing the cause. Only the scheduled run changes the emission date.
- Times are local. `next_alarm` is stored in UTC, so the dashboard value may
  look offset compared with the configured local time.

## The follow-up action never runs

- The follow-up is only saved after the type form (script, playlist, media) is
  submitted. Check that **Enable the follow-up** is on and the action is not
  `No follow-up`.
- With **After** and *Wait for the announcement to end* on, the action waits for
  the player to leave `playing`. A player that never reports `playing` delays it
  by about 20 seconds; one that stays `playing` (already playing something else)
  waits for **Maximum wait**, 180 seconds by default. Lower it, or switch the
  follow-up to **Before**.
- The Music Assistant form needs both a player and a media URI. Copy the URI
  from the Music Assistant UI (three dots → *Copy URI*); `library://playlist/3`
  and `spotify://playlist/…` both work.
- Errors from the action are logged as warnings and do **not** change
  `last_status`: the greeting already played. Look for `followup … failed` in
  Settings → System → Logs.

## Music starts while the greeting is still playing

That is **Before** working as designed. Switch to **After** if you want them in
sequence. The reverse case — music never starting because the announcement wait
never ends — is described above.

## Music stops after "Before" with a non-Music-Assistant player

Ducking is a Music Assistant feature: the greeting is sent as a Music Assistant
announcement, so Music Assistant mixes it over its queue. Other players replace
what they are playing. Home Assistant logs a warning when this happens. Use
**After** for those players, or move the greeting to a Music Assistant player
entity (and set it under **TTS and player**).

## The announcement volume does nothing

**Announcement volume** only applies with **Before**, with a Music Assistant
player as the **TTS and player** media player, and when Music Assistant's
`play_announcement` action is available. Otherwise the greeting is played with
`tts.speak` and the field is ignored.

## No audio, but `last_status` is `ok`

- Volume is `0`, or **Restore previous volume** put the player back to a muted
  level while playback was still starting.
- The media player was idle and did not wake for TTS. Check the player's own
  logs and wake-on-play behavior.
- The TTS engine cached the voice but the player is a different speaker than
  expected; verify **Media player** in **Configure → TTS and player**.

## Reauthentication or `invalid_auth`

OpenRouter, Groq, and other cloud endpoints can revoke a key. Finish the
reauth flow with a new key. When reconfiguring, leaving the API key empty keeps
the stored one.

## The YAML block is ignored

Since v0.2.0 configuration lives in a config entry. A `buenosdias:` block in
`configuration.yaml` runs a one-time import at startup; once the entry exists
the block is ignored and Home Assistant logs a deprecation warning. Remove the
block and manage everything in the UI. See
[`config.example.yaml`](../config.example.yaml) for the old shape.

## Still stuck?

Open an issue at
[github.com/frabarz/buenosdias/issues](https://github.com/frabarz/buenosdias/issues)
with the integration version, your Home Assistant version, `last_status`, and
the relevant lines from Settings → System → Logs.
