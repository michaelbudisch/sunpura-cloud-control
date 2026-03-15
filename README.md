# Sunpura Cloud Control (Home Assistant Integration)

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
[![Last Commit](https://img.shields.io/github/last-commit/michaelbudisch/sunpura-cloud-control)](https://github.com/michaelbudisch/sunpura-cloud-control/commits/main)
[![License](https://img.shields.io/github/license/michaelbudisch/sunpura-cloud-control)](https://github.com/michaelbudisch/sunpura-cloud-control/blob/main/LICENSE)

Community-maintained Home Assistant integration for Sunpura cloud-connected battery systems.

This fork focuses on API reliability, especially around current Sunpura cloud login behavior.

## Quick Links

- Fork repo (recommended for HACS): `https://github.com/michaelbudisch/sunpura-cloud-control`
- Upstream project: `https://github.com/smartenergycontrol-be/sunpura-cloud-control`
- Issues for this fork: `https://github.com/michaelbudisch/sunpura-cloud-control/issues`

## Deutsche Anleitung (Schnellstart)

### Installation ueber HACS

1. In Home Assistant `HACS -> Integrationen` oeffnen.
2. Oben rechts auf das Menue (`...`) klicken und `Custom repositories` waehlen.
3. Diese URL eintragen: `https://github.com/michaelbudisch/sunpura-cloud-control`
4. Kategorie `Integration` waehlen und speichern.
5. `Sunpura Battery Control` installieren.
6. Home Assistant neu starten.

### Einrichtung in Home Assistant

1. Gehe zu `Einstellungen -> Geraete und Dienste -> Integration hinzufuegen`.
2. Waehle `Sunpura Battery Control`.
3. Trage deine Sunpura App-Daten ein:
   - `username` (meist E-Mail aus der App)
   - `password` (gleiches Passwort wie in der App)
   - `base_url` optional

Falls Login-Fehler auftreten (`invalid_auth`), setze:

`base_url = https://server-nj.ai-ec.cloud:8443`

### Haeufige Probleme

- `invalid_auth`: Zugangsdaten in der Sunpura App testen und Integration danach neu konfigurieren.
- Keine Geraete gefunden: In der App pruefen, ob die Anlage online ist, dann Integration neu laden.
- Keine Datenupdates: Integration neu laden, Home Assistant neu starten, Debug-Logs aktivieren.

## What Is Different In This Fork

- Updated and hardened cloud login flow for recent Sunpura API behavior.
- iOS-style request headers and payload variants for better auth compatibility.
- Optional `API Base URL` field in the config flow.
- More defensive request/response handling in the cloud hub.

## Features

- Real-time battery and inverter monitoring
- Daily, monthly, yearly and total energy metrics
- Charge/discharge power control
- Switches, numbers and selects for operational settings
- Multi-device discovery through the cloud account

## Supported Environment

- Home Assistant `2023.1.0+`
- Sunpura cloud account
- Cloud-reachable Sunpura devices (S2400 class and compatible systems)

## Installation

### Option A: HACS (recommended)

1. Open HACS -> Integrations -> menu (3 dots) -> Custom repositories.
2. Add `https://github.com/michaelbudisch/sunpura-cloud-control`.
3. Category: `Integration`.
4. Install `Sunpura Battery Control`.
5. Restart Home Assistant.

### Option B: Manual

```bash
cd /config
git clone https://github.com/michaelbudisch/sunpura-cloud-control.git
mkdir -p /config/custom_components
cp -r /config/sunpura-cloud-control/custom_components/sunpura_battery /config/custom_components/
```

Restart Home Assistant after copying files.

## Setup In Home Assistant

Go to `Settings -> Devices & Services -> Add Integration -> Sunpura Battery Control`.

Required fields:

| Field | Required | Notes |
|---|---|---|
| `username` | Yes | Usually your Sunpura app email/username |
| `password` | Yes | Same password as mobile app |
| `base_url` | No | Use when your account needs a specific endpoint |

Recommended `base_url` if login fails:

`https://server-nj.ai-ec.cloud:8443`

## Login Notes

Sunpura login behavior can differ by app version and region.  
This fork attempts multiple compatible login payloads and headers automatically, including iOS-style fields (`phoneOs`, `phoneModel`, `appVersion`).

You only enter your normal app credentials in Home Assistant.

## Entities Created

- `sensor`: SOC, battery values, power flow, energy counters
- `number`: battery power setpoint, limits and thresholds
- `switch`: operation toggles and control flags
- `select`: operation/priority modes and schedules

## Troubleshooting

### `invalid_auth`

- Confirm the same credentials work in the Sunpura mobile app.
- In the integration options, set `base_url` to:
  - `https://server-nj.ai-ec.cloud:8443`
- Reconfigure the integration from scratch if needed.

### Devices not found

- Check device visibility in the mobile app first.
- Wait a few minutes after first successful login.
- Reload the integration.

### Data not updating

- Reload the integration.
- Restart Home Assistant.
- Enable debug logs and check API responses.

Enable debug logging in `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.sunpura_battery: debug
```

## Repository Layout

```text
custom_components/sunpura_battery/
  __init__.py
  config_flow.py
  hub.py
  sensor.py
  switch.py
  number.py
  select.py
```

## Contributing

- PRs and issues are welcome in this fork.
- If a fix should also go upstream, open the PR here first and then share it with:
  `https://github.com/smartenergycontrol-be/sunpura-cloud-control`

## License

MIT. See [LICENSE](LICENSE).

## Disclaimer

Not affiliated with or officially supported by Sunpura.  
Use at your own risk.
