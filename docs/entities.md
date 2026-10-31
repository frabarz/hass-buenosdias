# Entities

One device, **Buenos Días** (manufacturer `Buenos Días`, model `Morning
radio`), carries the switch and the two status sensors. Unique ids are stable
(`buenosdias_*`), so renames never duplicate entities.

## `switch.buenos_dias_enabled` — Enabled

Pauses or resumes the daily alarm. When off, the scheduler still computes the
next alarm but does not fire. Turning it back on does not replay a missed
morning.

## `sensor.buenos_dias_last_status` — Last status

Result of the last scheduled emission:

| State | Meaning |
|---|---|
| `never` | No emission has run yet |
| `ok` | The last emission generated the script and started playback |
| `error: …` | The pipeline failed; the text after the colon is the reason |

Attributes:

- `last_script` — full generated script (attributes are not limited to 255
  characters, so the whole text is available).
- `last_emission_date` — local date of the last scheduled alarm run
  (`YYYY-MM-DD`), or `null`. It is recorded even when that run failed, because
  `skip_if_emitted` prevents a second attempt the same day.
- `next_alarm` — next firing time in ISO-8601 UTC, or `null`.

## `sensor.buenos_dias_next_alarm` — Next alarm

Next scheduled firing time as an ISO-8601 UTC timestamp, or `not_scheduled`
when no valid day is left in the scheduler's lookahead window (for example,
every day is skipped or blocked by holidays).

The value is computed in local time and stored in UTC. Use it in automations
with `as_datetime()` or compare against `now()`.

Next: [Services](services.md).
