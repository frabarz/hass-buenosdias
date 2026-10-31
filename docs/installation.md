# Installation

## HACS (recommended)

1. HACS → Integrations → ⋮ → Custom repositories → add this repository URL
   with category *Integration*.
2. Find “Buenos Días” in HACS and install it.
3. Restart Home Assistant.
4. Settings → Devices & Services → Add Integration → Buenos Días.

The first step asks how the script is generated: Home Assistant's conversation
agent or an OpenAI-compatible endpoint. Everything else (TTS, sources, RSS,
schedule) is configured in the integration options. See
[Configuration](configuration.md).

## Manual install

Copy `custom_components/buenosdias/` into your Home Assistant
`config/custom_components/` directory and restart. Home Assistant installs the
manifest requirements (`feedparser`, `httpx`). Requires Home Assistant 2025.2+
(Python ≥ 3.13).

## Via the NixOS flake

The flake exposes the component as `packages.<system>.default`:

```nix
{
  inputs.hass-buenosdias = {
    url = "github:frabarz/buenosdias";
    inputs.nixpkgs.follows = "nixpkgs";
  };

  # In your NixOS configuration (`inputs` is available via specialArgs):
  services.home-assistant = {
    enable = true;
    customComponents = [
      inputs.hass-buenosdias.packages.${pkgs.stdenv.hostPlatform.system}.default
    ];
  };
}
```

Keep `inputs.nixpkgs.follows = "nixpkgs"` so the component is built against the
same Home Assistant version you run. Configuration stays in the Home Assistant
UI (there is no declarative YAML for this integration).

Or build the component derivation directly:

```bash
nix build .#default
# result/custom_components/buenosdias/
```

## Requirements

- Home Assistant 2025.2 or newer.
- An LLM: a Home Assistant conversation agent, or an OpenAI-compatible endpoint
  that serves `/chat/completions` (Ollama, OpenRouter, Groq, LM Studio, …).
- A TTS engine (e.g. Piper) and a media player for the morning playback.

Next: [Configuration](configuration.md).
