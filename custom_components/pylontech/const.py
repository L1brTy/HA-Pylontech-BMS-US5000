"""Constants for Pylontech US5000 (Waveshare Edition)."""
from __future__ import annotations
from datetime import timedelta
from enum import StrEnum

DOMAIN = "pylontech"
SCAN_INTERVAL = timedelta(seconds=30)
PLATFORMS = ["sensor"]

# Legacy Constants from original repo
VARIANT_PYLONTECH = "Pylontech"
VARIANT_SOK = "SOK"
VARIANT_STANDARD = "Standard"

class ConnectionType(StrEnum):
    TCP_CONSOLE = "TCP Console"
    BINARY = "Binary"

class BatteryVariant(StrEnum):
    PYLONTECH_STANDARD = "Pylontech Standard"
    US5000 = "US5000"
    SOK = "SOK"
