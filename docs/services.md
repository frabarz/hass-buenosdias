# Services

Call these from Developer Tools → Actions or your automations. All three accept
an optional response: enable **Return response** in Developer Tools, or use
`response_variable` in YAML.

## `buenosdias.context`

Collect the morning context without calling the LLM. Useful for debugging what
the script will see.

```yaml
action: buenosdias.context
response_variable: context
```

The response contains `timestamp`, `weather`, `calendar`, `sensors`, `news`,
and `events`.

## `buenosdias.generate`

Run context → LLM and return the script without playing audio (dry-run). The
result is also stored in `sensor.buenos_dias_last_status.last_script`.

```yaml
action: buenosdias.generate
response_variable: result
```

The response is `{"script": "…"}`.

## `buenosdias.emit`

Run the full pipeline: collect context, generate the script, and play it through
`tts.speak` on the configured media player. Also stores the script in
`last_script`.

```yaml
action: buenosdias.emit
response_variable: result
```

The response is `{"script": "…"}`. This is the action to call from a dashboard
button or a "play now" automation; the daily alarm calls the same pipeline on
its own and records `last_emission_date` and `last_status`.

Next: [Dashboards](dashboards.md).
