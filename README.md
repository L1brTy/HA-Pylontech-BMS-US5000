# Pylontech BMS US5000 (Waveshare Edition)

Dieser Home Assistant Custom Component ist ein spezialisierter **Fork** von [jtubb/HA-Pylontech-BMS](https://github.com/jtubb/HA-Pylontech-BMS). 

Er wurde grundlegend umgebaut und optimiert, um die Kommunikation mit **Pylontech US5000** Batterien über einen **Waveshare RS232-to-Ethernet Konverter** (Anschluss am Console-Port der Batterie) zu ermöglichen.

> [!WARNING]  
> Diese Integration wurde **ausschließlich mit Pylontech US5000** Modellen getestet. Die Kompatibilität mit älteren Modellen (US2000/US3000) ist aufgrund der Protokoll-Anpassungen nicht garantiert.

## 🚀 Key Features & Verbesserungen

* **Entwickelt von Gemini (AI):** Dieser Fork wurde mit intensiver Unterstützung von Google Gemini erstellt und für die spezifischen Eigenheiten des US5000 Konsolen-Protokolls optimiert.
* **Individuelle Pack-Identität:** Jedes Batterie-Pack wird automatisch mit seinem echten **Barcode (Seriennummer)** im Namen registriert (z.B. `Pylontech US5000 Pack 1 (P225...)`). Dies ermöglicht eine eindeutige Zuordnung im Rack.
* **15-Zellen Support:** Korrektes Auslesen aller 15 Einzelspannungen des US5000.
* **SOC & Power Fix:** Korrigierter Parser für die Konsolenausgabe des US5000, um falsche 0% SOC-Werte und falsche Spaltenzuordnungen zu vermeiden.
* **ISA-101 Dashboard Ready:** Die Sensor-Entitäten werden automatisch so benannt (`sensor.pylontech_pack_X_...`), dass sie nativ mit der [Pylontech Battery Overview Card](https://github.com/jtubb/Pylontech-Battery-Card) funktionieren.
* **Detailliertes Monitoring:** * Einzelzell-Spannungen (Zelle 0-14).
    * Einzelzell-Temperaturen (Heatmap-Support).
    * Durchschnittliche Gruppen-Temperaturen für die schnelle Übersicht.

## 🛠 Hardware-Konfiguration

Getestet mit:
* **Batterie:** Pylontech US5000.
* **Adapter:** Waveshare RS232/485 TO ETH (B) konfiguriert als TCP-Server.
* **Anschluss:** RS232 Kabel am Console-Port (RJ11/RJ12) der Pylontech.
* **Standard-Port:** `4196` (Telnet-Protokoll).

## 📦 Installation

### Manuell
1. Lade dieses Repository herunter.
2. Kopiere den Ordner `custom_components/pylontech` in deinen Home Assistant `config/custom_components/` Ordner.
3. Starte Home Assistant neu.
4. Füge die Integration unter **Einstellungen -> Geräte & Dienste** hinzu (IP des Waveshare-Adapters und Port angeben).

## 📊 Dashboard Visualisierung

Für die beste Darstellung (inkl. Heatmaps für Zellen und Temperaturen) empfehlen wir die [Pylontech-Battery-Card](https://github.com/jtubb/Pylontech-Battery-Card). Beispiel-Konfiguration:

```yaml
type: custom:pylontech-battery-overview
entity_prefix: sensor.pylontech
pack_count: 2  # Anzahl deiner installierten Packs
title: "US5000 Speicher-System"
soc_warning: 20
soc_alarm: 10
