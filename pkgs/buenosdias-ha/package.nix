# Arguments are resolved from home-assistant.python3Packages scope.
# IMPORTANT: call via pkgs.home-assistant.python3Packages.callPackage, NOT
# pkgs.callPackage, so buildHomeAssistantComponent and any future Python
# deps come from HA's pinned interpreter set.
{
  lib,
  buildHomeAssistantComponent,
  feedparser,
  pytestCheckHook,
  pytest-homeassistant-custom-component,
  home-assistant,
  src,
}:

buildHomeAssistantComponent rec {
  owner = "buenosdias";
  domain = "buenosdias";
  version = "0.3.2";

  inherit src;

  dependencies = [
    feedparser
  ];

  nativeCheckInputs = [
    pytestCheckHook
    pytest-homeassistant-custom-component
  ]
  ++ (home-assistant.getPackages "switch" home-assistant.python3Packages)
  ++ (home-assistant.getPackages "sensor" home-assistant.python3Packages);

  # The HA harness registers autouse async fixtures; this component's tests
  # are synchronous and use asyncio.run(), so pytest-asyncio's auto mode is
  # required.
  pytestFlags = [ "--asyncio-mode=auto" ];

  meta = {
    description = "A personalized morning radio for Home Assistant";
    homepage = "https://github.com/frabarz/buenosdias";
    license = lib.licenses.asl20;
    maintainers = [ ];
  };
}
