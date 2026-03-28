from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
from .const import BatteryVariant, ConnectionType

@dataclass
class BatteryData:
    pack_voltage: float
    pack_current: float
    soc: int
    power: float
    remaining_capacity: float
    total_capacity: float
    temperatures: dict[str, float]
    cell_voltages: list[float]
    cell_temps: list[float]
    cell_volt_low: float
    cell_volt_high: float
    base_state: str
    error_code: int
    cell_socs: list[int] = field(default_factory=list)
    cell_balances: list[str] = field(default_factory=list)
    cycle_count: int = 0

@dataclass
class DeviceInfo:
    manufacturer: str
    model: str
    barcode: str
    firmware_version: str
    connection_type: ConnectionType
    variant: BatteryVariant
