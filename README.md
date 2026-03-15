# Sunpura Cloud Control (Home Assistant Integration)

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
[![Last Commit](https://img.shields.io/github/last-commit/michaelbudisch/sunpura-cloud-control)](https://github.com/michaelbudisch/sunpura-cloud-control/commits/main)
[![License](https://img.shields.io/github/license/michaelbudisch/sunpura-cloud-control)](https://github.com/michaelbudisch/sunpura-cloud-control/blob/main/LICENSE)

Repository: `https://github.com/michaelbudisch/sunpura-cloud-control`  
Upstream: `https://github.com/smartenergycontrol-be/sunpura-cloud-control`

---

## Deutsch

### Überblick

Diese Integration verbindet Home Assistant mit der Sunpura Cloud, um Batterie- und Energiedaten zu lesen und Steuerbefehle zu senden.

Schwerpunkte dieses Forks:

- stabileres Login-Verhalten gegen die aktuelle Sunpura API
- kompatiblere Request-Header/Payloads (inkl. iOS-naher Varianten)
- optionales Feld `base_url` in der Einrichtung

### Funktionen

- Echtzeit-Sensoren für Batterie, Leistung und Energie
- Schalten von Betriebsoptionen
- Zahlenwerte für Lade-/Entladeleistung und Grenzwerte
- Auswahllisten für Modi und Prioritäten
- Geräte-Erkennung über den Cloud-Account

### Voraussetzungen

- Home Assistant `2023.1.0+`
- gültiger Sunpura-Cloud-Account
- online erreichbare Sunpura-Geräte

### Installation über HACS (empfohlen)

1. In Home Assistant `HACS -> Integrationen` öffnen.
2. Menü (`...`) -> `Custom repositories`.
3. URL eintragen: `https://github.com/michaelbudisch/sunpura-cloud-control`
4. Kategorie: `Integration`.
5. `Sunpura Battery Control` installieren.
6. Home Assistant neu starten.

### Manuelle Installation

```bash
cd /config
git clone https://github.com/michaelbudisch/sunpura-cloud-control.git
mkdir -p /config/custom_components
cp -r /config/sunpura-cloud-control/custom_components/sunpura_battery /config/custom_components/
```

Danach Home Assistant neu starten.

### Einrichtung in Home Assistant

Pfad: `Einstellungen -> Geräte und Dienste -> Integration hinzufügen -> Sunpura Battery Control`

| Feld | Pflicht | Hinweis |
|---|---|---|
| `username` | Ja | meist die E-Mail aus der Sunpura App |
| `password` | Ja | gleiches Passwort wie in der Sunpura App |
| `base_url` | Nein | optionaler API-Endpunkt |

Empfohlene `base_url` bei Login-Problemen:

`https://server-nj.ai-ec.cloud:8443`

### Fehlerbehebung

#### `invalid_auth`

- Zugangsdaten zuerst in der Sunpura App prüfen.
- In der Integration `base_url` auf `https://server-nj.ai-ec.cloud:8443` setzen.
- Integration ggf. löschen und neu einrichten.

#### Keine Geräte gefunden

- Prüfen, ob Geräte in der Sunpura App sichtbar und online sind.
- Einige Minuten warten und Integration neu laden.

#### Werte aktualisieren nicht

- Integration neu laden.
- Home Assistant neu starten.
- Debug-Logging aktivieren.

Debug-Logging in `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.sunpura_battery: debug
```

### Projektstruktur

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

### Mitwirken

Issues und PRs sind willkommen:  
`https://github.com/michaelbudisch/sunpura-cloud-control/issues`

Wenn ein Fix auch ins Originalprojekt soll, danach zusätzlich bei Upstream einreichen:
`https://github.com/smartenergycontrol-be/sunpura-cloud-control`

### Lizenz und Hinweis

MIT-Lizenz, siehe [LICENSE](LICENSE).  
Kein offizielles Sunpura-Produkt. Nutzung auf eigenes Risiko.

---

## English

### Overview

This integration connects Home Assistant to the Sunpura cloud to read battery/energy data and send control commands.

Focus of this fork:

- more robust login handling against current Sunpura API behavior
- more compatible request headers/payloads (including iOS-like variants)
- optional `base_url` field during setup

### Features

- real-time sensors for battery, power and energy
- switches for operation options
- number entities for charge/discharge power and limits
- select entities for modes and priorities
- cloud account based device discovery

### Requirements

- Home Assistant `2023.1.0+`
- valid Sunpura cloud account
- online Sunpura devices

### Installation via HACS (recommended)

1. In Home Assistant open `HACS -> Integrations`.
2. Open menu (`...`) -> `Custom repositories`.
3. Add URL: `https://github.com/michaelbudisch/sunpura-cloud-control`
4. Category: `Integration`.
5. Install `Sunpura Battery Control`.
6. Restart Home Assistant.

### Manual Installation

```bash
cd /config
git clone https://github.com/michaelbudisch/sunpura-cloud-control.git
mkdir -p /config/custom_components
cp -r /config/sunpura-cloud-control/custom_components/sunpura_battery /config/custom_components/
```

Then restart Home Assistant.

### Setup in Home Assistant

Path: `Settings -> Devices & Services -> Add Integration -> Sunpura Battery Control`

| Field | Required | Notes |
|---|---|---|
| `username` | Yes | usually the email used in Sunpura app |
| `password` | Yes | same password as in Sunpura app |
| `base_url` | No | optional API endpoint override |

Recommended `base_url` if login fails:

`https://server-nj.ai-ec.cloud:8443`

### Troubleshooting

#### `invalid_auth`

- Verify credentials in the Sunpura mobile app first.
- Set `base_url` to `https://server-nj.ai-ec.cloud:8443`.
- Recreate the integration if needed.

#### No devices found

- Confirm devices are visible and online in the Sunpura app.
- Wait a few minutes and reload the integration.

#### Values are not updating

- Reload integration.
- Restart Home Assistant.
- Enable debug logging.

Debug logging in `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.sunpura_battery: debug
```

### Project Layout

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

### Contributing

Issues and PRs are welcome:  
`https://github.com/michaelbudisch/sunpura-cloud-control/issues`

If a fix should also be included upstream, open it there afterwards:
`https://github.com/smartenergycontrol-be/sunpura-cloud-control`

### License and Disclaimer

MIT license, see [LICENSE](LICENSE).  
This is not an official Sunpura product. Use at your own risk.
