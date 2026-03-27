"""Models for Pylontech US5000 (Waveshare Edition)."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
from .const import ConnectionType, BatteryVariant

@dataclass
class DeviceInfo:
    """Device info."""
    manufacturer: str
    model: str
    barcode: str
    firmware_version: str
    connection_type: ConnectionType
    variant: BatteryVariant

@dataclass
class BatteryData:
    """Battery data."""
    pack_voltage: float | None = None
    pack_current: float | None = None
    soc: int | None = None
    power: float | None = None
    remaining_capacity: float | None = None
    total_capacity: float | None = None
    temperatures: dict[str, float] = field(default_factory=dict)
    cell_voltages: list[float] = field(default_factory=list)
    cell_temps: list[float] = field(default_factory=list)
    cell_volt_low: float | None = None
    cell_volt_high: float | None = None
    base_state: str | None = None
    error_code: str | None = None
    cell_temp_low: float | None = None
    cell_temp_high: float | None = None
