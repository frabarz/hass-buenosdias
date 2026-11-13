# Configuration

Everything happens in the UI — there is no YAML setup. The integration allows a
single config entry, and that entry owns the alarm, the entities, and the
services.

## Adding the integration

1. Settings → Devices & Services → Add Integration → Buenos Días.
2. Pick the **LLM mode**:
   - **Home Assistant conversation agent** — pick the agent entity that writes
     the script (e.g. `conversation.assist`).
   - **OpenAI-compatible endpoint** — set `base_url`, `model`, and (optionally)
     `api_key`. The connection is probed with `GET /models` before saving.
3. Finish the entry, then open **Configure** to set TTS, sources, RSS, and the
   schedule.

## LLM connection

The connection is edited from the integration card → ⋮ → **Reconfigure**. Mode
and endpoint can change; leaving the API key empty keeps the stored one.

- **Conversation agent mode** uses `conversation.async_converse` with an extra
  system prompt. It needs Home Assistant 2025.2 or newer.
- **OpenAI-compatible mode** posts to `{base_url}/chat/completions`. Any
  endpoint that serves `/models` and `/chat/completions` works (Ollama,
  OpenRouter, Groq, LM Studio, …). API key is optional for local endpoints.

If the stored key stops working, Home Assistant opens a reauthentication flow
asking for a new key.

## Options

Open the integration card → **Configure**. The menu has six sections.

### Script and voice

| Option | Meaning | Default |
|---|---|---|
| Maximum script length | Characters allowed in the spoken script (100–20000) | 2000 |
| Persona | Free text that controls language, tone, and style | empty |

The persona is the only place that decides the spoken language. Write it in the
language you want to hear.

Persona examples:

```text
Eres el locutor de una radio matutina. Habla en español neutral, con tono
cercano y natural. Puedes incluir un toque de humor pero sé informativo.
```

```text
You are a friendly morning radio host. Speak in clear, warm English. Keep it
brief and upbeat. Highlight what matters today.
```

### TTS and player

| Option | Meaning | Default |
|---|---|---|
| TTS entity | Text-to-speech engine, e.g. `tts.piper` | — |
| Media player | Speaker that plays the script | — |
| Language | Language passed to `tts.speak` | `es-ES` |
| Volume | Playback volume (0.0–1.0) | 0.6 |
| Restore previous volume | Put the player's old volume back after playback | on |

### Sources

Multi-select the weather, calendar, and sensor entities included in the morning
context. Nothing is sent anywhere except the chosen LLM endpoint.

Weather entities can also carry a forecast. The integration calls
`weather.get_forecasts`, so the script can talk about the hours ahead instead
of only the current conditions (Home Assistant no longer exposes forecasts as
entity attributes).

| Option | Meaning | Default |
|---|---|---|
| Forecast | `Current conditions only`, `Hourly forecast`, or `Daily forecast` | Current conditions only |
| Forecast entries | Maximum entries sent to the LLM (hours for hourly, days for daily) | 12 |

The forecast is attached to each weather entity in the context as a `forecast`
list. Empty fields are dropped to keep the prompt small, and a failing forecast
call is logged and ignored — the rest of the context is still generated. Not
every weather integration supports both types: Tomorrow.io, for example,
provides 24 hourly and 14 daily entries.

### RSS feeds

Add, edit, or remove feeds inline. Each feed has:

| Option | Meaning | Default |
|---|---|---|
| URL | Feed URL | — |
| Kind | `News` or `Events` | News |
| Max age | Drop entries older than this many hours | 72 |
| Max items | Cap entries kept from this feed | 5 |
| Tags | Optional keywords that describe the feed | — |
| Excluded keywords | Skip entries whose title or summary contains any keyword | — |

Exclusions are a comma- or newline-separated list of plain substrings, not a
regex. Matching ignores case and accents, so `futbol` also skips `fútbol`.
Removal is done from the edit screen (tick **Remove this feed** and save).

### Schedule

| Option | Meaning | Default |
|---|---|---|
| Alarm time | Fixed local time (`HH:MM`); seconds are ignored | `07:00` |
| Time entity | Sensor that supplies the alarm time dynamically | — |
| Skip weekdays | Days on which the alarm never fires | none |
| Holidays | One ISO date (`YYYY-MM-DD`) per line | none |
| Holiday calendar | Calendar whose all-day events count as holidays | — |
| Skip if already emitted | Do not fire twice on the same day | on |
| Preload minutes | Generate and warm the TTS cache this many minutes early (0–60) | 0 |

When a time entity is set it takes precedence over the fixed time, and the
alarm is re-armed whenever the sensor changes (useful for a phone's next-alarm
sensor). `preload_minutes` is disabled at `0`; `2`–`3` is the recommended range
so the cached voice plays instantly at alarm time.

### Follow-up action

Optional. Runs something around the announcement: start a playlist once the
greeting ends, or put music underneath it. Disabled by default.

| Option | Meaning | Default |
|---|---|---|
| Enable the follow-up | Master switch for the action | off |
| When | `After the announcement` or `Before the announcement` | After |
| Action | `Run a script`, `Play a Music Assistant playlist`, or `Play media on a media player` | No follow-up |
| Wait for the announcement to end | Only for *After*: wait until the player stops before running the action | on |
| Maximum wait | Give up waiting after this many seconds (5–1800) | 180 |

The action type only decides which extra form appears next; the three are:

- **Script** — a `script.*` entity is turned on. This is the escape hatch: the
  script can start music from any integration, switch lights, open blinds, send
  a notification, or call anything else.
- **Music Assistant** — `music_assistant.play_media` on the chosen player with
  a media URI (`library://playlist/3`, `spotify://playlist/…`), a media type
  (playlist, album, track, artist, radio, audiobook, podcast) and the queue
  behaviour (`play`, `replace`, `next`, `add`). Copy the URI from the Music
  Assistant UI (three dots → *Copy URI*).
- **Media player** — generic `media_player.play_media`: pick any player plus the
  media content id and type it accepts (a radio stream URL, for instance).

Both music types take an optional **volume**, applied before the media starts.
Leaving it empty keeps the player's volume.

#### After vs before

**After** plays the greeting, waits for the announcement to finish, and only
then runs the action. This is the useful one for any speaker: the greeting is
never cut off by the music.

The wait watches the configured media player: it looks for the state to reach
`playing` and to leave it again. If the player never reports `playing` (some
players do not), the action starts after about 20 seconds. If the player is
still `playing` when **Maximum wait** runs out, the action runs anyway. Two
consequences worth knowing:

- A player that stays `playing` forever (because something else is already
  playing on it) burns the whole timeout.
- Turning *Wait for the announcement to end* off starts the action as soon as
  the TTS service call returns.

**Before** runs the action first and then plays the greeting *on top of it*.
With a Music Assistant player this is exactly the "radio with the host talking
over it" effect: `tts.speak` sends `announce=True`, so Music Assistant ducks the
queue for the greeting and resumes it afterwards. Nothing else is involved —
Music Assistant does the mixing.

Two caveats for **Before**:

- The media must be playing on the same player the greeting uses, and that
  player must be a Music Assistant player entity. With any other player the
  greeting simply replaces the media.
- The TTS volume option still applies, so the greeting may play at a different
  level than the music.

Next: [Entities](entities.md).
