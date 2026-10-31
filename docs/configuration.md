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

Open the integration card → **Configure**. The menu has five sections.

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

Next: [Entities](entities.md).
