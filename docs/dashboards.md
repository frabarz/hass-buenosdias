# Dashboards

Entity ids below assume the default device name; yours follow the same pattern.
See [Entities](entities.md) for the attribute reference.

## Status at a glance

```yaml
type: entities
title: Buenos Días
entities:
  - entity: switch.buenos_dias_enabled
  - entity: sensor.buenos_dias_last_status
  - entity: sensor.buenos_dias_next_alarm
```

## Last script (Markdown)

```yaml
type: markdown
content: >-
  **{{ states('sensor.buenos_dias_last_status') }}** ·
  {{ state_attr('sensor.buenos_dias_last_status', 'last_emission_date') or 'sin emisión' }}

  {{ state_attr('sensor.buenos_dias_last_status', 'last_script') or '' }}
```

## Play now

```yaml
type: button
name: Buenos Días ahora
icon: mdi:radio
tap_action:
  action: perform-action
  perform_action: buenosdias.emit
```

## Failure notification

Fires when the scheduled run records an error:

```yaml
automation:
  - alias: "Aviso fallo Buenos Días"
    triggers:
      - trigger: state
        entity_id: sensor.buenos_dias_last_status
    conditions:
      - condition: template
        value_template: >-
          {{ states('sensor.buenos_dias_last_status').startswith('error') }}
    actions:
      - action: notify.mobile_app_tu_telefono
        data:
          title: "Buenos Días falló"
          message: "{{ states('sensor.buenos_dias_last_status') }}"
```

Next: [Troubleshooting](troubleshooting.md).
