# Pylontech BMS US5000 (Waveshare Edition)

[![HACS Add Repository](https://img.shields.io/badge/HACS-Add%20Repository-orange.svg?style=for-the-badge&logo=homeassistant)](https://my.home-assistant.io/redirect/hacs_repository/?category=integration&repository=L1brTy/HA-Pylontech-BMS-US5000)



Dieser Home Assistant Custom Component ist ein spezialisierter **Fork** von [jtubb/HA-Pylontech-BMS](https://github.com/jtubb/HA-Pylontech-BMS). 

Er wurde grundlegend optimiert, um die Kommunikation mit **Pylontech US5000** Batterien über einen **Waveshare RS232-to-Ethernet Konverter** (direkt am Console-Port der Master-Batterie) zu ermöglichen.

> [!IMPORTANT]  
> **Kompatibilität:** Diese Integration wurde ausschließlich mit **Pylontech US5000** Modellen via Waveshare-Gateway entwickelt und getestet. Aufgrund spezifischer Protokoll-Anpassungen (15 Zellen, Konsolen-Spalten-Mapping) ist sie für ältere Modelle wie US2000 oder US3000 nur bedingt geeignet.

## 🚀 Key Features & Verbesserungen

* **AI-Optimiert:** Dieser Fork wurde mit intensiver Unterstützung von **Google Gemini** entwickelt, um den Parser für das US5000 Konsolen-Protokoll zu perfektionieren.
* **Eindeutige Pack-Identifikation:** Jedes Batterie-Pack wird automatisch mit seinem echten **Barcode (Seriennummer)** im Namen registriert (z.B. `Pylontech US5000 Pack 1 (P2250...)`). Ideal für Rack-Systeme zur Fehlerlokalisierung.
* **Dashboard-Zwang (ISA-101):** Die Sensor-Entitäten werden strikt auf das Format `sensor.pylontech_pack_X_...` gemappt. Dies garantiert die sofortige Funktion der [Pylontech Battery Overview Card](https://github.com/jtubb/Pylontech-Battery-Card) ohne manuelles Umbenennen.
* **Vollständiges Monitoring:**
    * **Spannungen:** Alle 15 Einzelzellen (Zelle 0 bis 14) pro Pack.
    * **Temperaturen:** Alle 15 Einzelsensoren (Heatmap-Support) sowie automatisierte Gruppen-Durchschnitte (Cells 1-4, 5-8, etc.) für die Hauptübersicht.
    * **SOC-Fix:** Korrektes Auslesen der US5000-Konsolenausgabe zur Vermeidung von 0% SOC-Anzeigen.
    * **Delta-V:** Echtzeit-Berechnung des Zellspannungs-Unterschieds.

## 🛠 Hardware-Setup

* **Batterie:** Pylontech US5000 (Master-Pack am Console-Port verbunden).
* **Konverter:** Waveshare RS232 TO ETH (B) oder ähnliche Gateways.
* **Einstellungen:**
    * Protokoll: **TCP Server**
    * Port: **4196** (Standard für Telnet/Console)
    * Baudrate: **1200** (Standard Console-Port Pylontech)

## 📦 Installation

### 1. Über den Button (Empfohlen)
Klicke auf den "HACS Add Repository" Button oben. Falls dein Browser den Dienst `my.homeassistant.io` blockiert, nutze die manuelle Installation.

### 2. Manuelle Installation via HACS
1. Öffne HACS in deiner Home Assistant Instanz.
2. Klicke auf die drei Punkte oben rechts -> **Benutzerdefinierte Repositories**.
3. Füge die URL `https://github.com/L1brTy/HA-Pylontech-BMS-US5000` hinzu.
4. Wähle als Kategorie **Integration**.
5. Suche nach "Pylontech US5000 (Waveshare Edition)" und klicke auf Herunterladen.
6. Starte Home Assistant neu.

## 📊 Dashboard Visualisierung

Für eine perfekte Visualisierung empfehlen wir die Nutzung der `custom:pylontech-battery-overview` Karte:

```yaml
type: custom:pylontech-battery-overview
entity_prefix: sensor.pylontech
pack_count: 2  # Anzahl deiner Packs im System
title: "Batteriespeicher US5000"
soc_warning: 25
soc_alarm: 15
delta_v_warning: 30
delta_v_alarm: 60
