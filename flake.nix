# flake.nix — package, devShell, and checks.
# Layout: custom_components/buenosdias is the HA integration, tests/ is the
# pytest suite, pkgs/buenosdias-ha packages it, config.example.yaml is the
# deprecated YAML import reference.
{
  description = "buenosdias: a personalized morning radio for Home Assistant with LLM";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  };

  outputs =
    {
      self,
      nixpkgs,
    }:
    let
      system = "x86_64-linux";
      pkgs = import nixpkgs { inherit system; };

      # Nix store source for the component derivation: only the integration,
      # tests, and packaging metadata.
      componentSrc = pkgs.lib.fileset.toSource {
        root = ./.;
        fileset = pkgs.lib.fileset.unions [
          ./custom_components
          ./tests
          ./pyproject.toml
        ];
      };

      component = pkgs.home-assistant.python3Packages.callPackage ./pkgs/buenosdias-ha/package.nix {
        src = componentSrc;
        inherit (pkgs) home-assistant;
      };

      home-assistant = pkgs.home-assistant;
    in
    {
      packages.${system} = {
        inherit component;
        default = component;
      };

      devShells.${system}.default = pkgs.mkShell {
        packages = [
          (home-assistant.python3Packages.python.buildEnv.override {
            extraLibs =
              (with home-assistant.python3Packages; [
                pytest
                pytest-homeassistant-custom-component
                feedparser
              ])
              ++ (home-assistant.getPackages "switch" home-assistant.python3Packages)
              ++ (home-assistant.getPackages "sensor" home-assistant.python3Packages);
          })
        ];
        shellHook = ''
          echo "buenosdias dev shell (Python 3.14 + Home Assistant). Run: pytest -q"
        '';
      };

      checks.${system} = {
        build = component;
      };
    };
}
