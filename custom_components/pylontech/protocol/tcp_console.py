"""TCP Console Protocol implementation for Pylontech BMS.

This module implements the text-based console protocol over TCP.
Commands: pwr, unit, bat, info
Response format: ASCII text with 'pylon>' prompt
"""

from __future__ import annotations

import asyncio
from asyncio import StreamReader, StreamWriter
import logging
from typing import Any

from .base import ProtocolBase
from ..const import BatteryVariant, ConnectionType
from ..models import BatteryData, BMUData, DeviceInfo

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from pylontech import (
    BatCommand,
    InfoCommand,
    PwrCommand,
    UnitCommand,
    Sensor,
)

_LOGGER = logging.getLogger(__name__)

class TCPConsoleProtocol(ProtocolBase):
    """Pylontech BMS TCP console protocol implementation."""

    _END_PROMPTS = ("Command completed successfully", "$$")

    def __init__(self, host: str, port: int) -> None:
        self.host = host
        self.port = port
        self.reader: StreamReader | None = None
        self.writer: StreamWriter | None = None

    async def connect(self) -> None:
        self.reader, self.writer = await asyncio.wait_for(
            asyncio.open_connection(self.host, self.port), 5
        )
        _LOGGER.debug("Connected to %s:%s", self.host, self.port)

    async def disconnect(self) -> None:
        if self.writer is not None:
            self.writer.close()
            await self.writer.wait_closed()
            self.reader = None
            self.writer = None
            _LOGGER.debug("Disconnected from %s:%s", self.host, self.port)

    async def _exec_cmd(self, cmd: str) -> tuple[str]:
        self.writer.write((cmd + "\r").encode("ascii"))
        await asyncio.wait_for(self.writer.drain(), 2)
        lines = []
        linebytes = bytearray()
        while linebytes != b"pylon>":
            data = await asyncio.wait_for(self.reader.read(120), 2)
            for i in data:
                if i not in (13, 10):
                    linebytes.append(i)
                elif len(linebytes) > 0:
                    line = linebytes.decode("ascii")
                    if line not in self._END_PROMPTS:
                        lines.append(line)
                    linebytes = bytearray()
        if lines.pop(0) != cmd:
            raise ValueError("Command echo mismatch")
        if lines.pop(0) != "@":
            raise ValueError("Missing @ separator")
        return tuple(lines)

    async def bat(self) -> BatCommand:
        return BatCommand(await self._exec_cmd("bat"))

    async def info(self) -> InfoCommand:
        return InfoCommand(await self._exec_cmd("info"))

    # FIX 1: pwr nimmt jetzt pack_id an
    async def pwr(self, pack_id: int = 1) -> PwrCommand:
        cmd = f"pwr {pack_id}" if pack_id > 1 else "pwr"
        return PwrCommand(await self._exec_cmd(cmd), pack_id)

    async def unit(self) -> UnitCommand:
        return UnitCommand(await self._exec_cmd("unit"))

    async def get_device_info(self) -> DeviceInfo:
        info = await self.info()
        return DeviceInfo(
            manufacturer=info.manufacturer.value if info.manufacturer.value else "Pylontech",
            model=info.device_name.value if info.device_name.value else "Unknown",
            barcode=info.module_barcode.value if info.module_barcode.value else "Unknown",
            firmware_version=info.main_sw_version.value if info.main_sw_version.value else "Unknown",
            connection_type=ConnectionType.TCP_CONSOLE,
            variant=BatteryVariant.PYLONTECH_STANDARD,
            device_name=info.device_name.value,
            hardware_version=info.hard_version.value,
            device_address=info.device_address.value,
            cell_count=info.cell_number.value,
            max_charge_current=info.max_charge_current.value,
            max_discharge_current=info.max_discharge_current.value,
            bmu_modules=list(info.bmu_modules),
            bmu_pcbas=list(info.bmu_pcbas),
        )

    # FIX 2: get_battery_data nimmt pack_id und holt Werte absturzsicher ab
    async def get_battery_data(self, pack_id: int = 1) -> BatteryData:
        pwr = await self.pwr(pack_id)
        unit = await self.unit()

        # Hilfsfunktion, um Werte sicher zu lesen
        def get_val(obj, attr):
            return getattr(obj, attr).value if hasattr(obj, attr) else None

        temperatures = {
            "average": get_val(pwr, "avg_temp"),
            "pack": get_val(pwr, "temp"),
            "cell_low": get_val(pwr, "cell_temp_low"),
            "cell_high": get_val(pwr, "cell_temp_high"),
            "unit_low": get_val(pwr, "unit_temp_low"),
            "unit_high": get_val(pwr, "unit_temp_high"),
        }

        cell_voltages = []
        cell_temps = []
        if hasattr(unit, 'values'):
            for unit_val in unit.values:
                if get_val(unit_val, 'cell_volt_low'): cell_voltages.append(get_val(unit_val, 'cell_volt_low'))
                if get_val(unit_val, 'cell_bolt_high'): cell_voltages.append(get_val(unit_val, 'cell_bolt_high'))
                if get_val(unit_val, 'cell_temp_low'): cell_temps.append(get_val(unit_val, 'cell_temp_low'))
                if get_val(unit_val, 'cell_temp_high'): cell_temps.append(get_val(unit_val, 'cell_temp_high'))

        volt = get_val(pwr, "volt")
        curr = get_val(pwr, "curr")
        power = volt * curr if volt is not None and curr is not None else None
        
        soc = get_val(pwr, "soc")
        if soc is None:
            soc = get_val(pwr, "charge_ah_perc")

        return BatteryData(
            pack_voltage=volt,
            pack_current=curr,
            soc=soc,
            remaining_capacity=get_val(pwr, "charge_ah"),
            total_capacity=None,
            power=power,
            temperatures=temperatures,
            avg_temperature=get_val(pwr, "avg_temp"),
            cell_voltages=cell_voltages,
            cell_temps=cell_temps,
            base_state=get_val(pwr, "base_state"),
            volt_state=get_val(pwr, "volt_state"),
            curr_state=get_val(pwr, "curr_state"),
            temp_state=get_val(pwr, "temp_state"),
            cell_volt_state=get_val(pwr, "cell_volt_state"),
            cell_temp_state=get_val(pwr, "cell_temp_state"),
            unit_volt_state=get_val(pwr, "unit_volt_state"),
            unit_temp_state=get_val(pwr, "unit_temp_state"),
            charge_ah=get_val(pwr, "charge_ah"),
            charge_ah_perc=get_val(pwr, "charge_ah_perc"),
            charge_wh=get_val(pwr, "charge_wh_wh"),
            charge_wh_perc=get_val(pwr, "charge_wh_perc"),
            cell_volt_low=get_val(pwr, "cell_volt_low"),
            cell_volt_high=get_val(pwr, "cell_bolt_high"),
            unit_volt_low=get_val(pwr, "unit_volt_low"),
            unit_volt_high=get_val(pwr, "unit_volt_high"),
            dc_voltage=get_val(pwr, "dc_voltage"),
            bat_voltage=get_val(pwr, "bat_voltage"),
            error_code=get_val(pwr, "error_code"),
            alarms={},
            cycle_count=None,
        )

    def __repr__(self) -> str:
        return f"<TCPConsoleProtocol host={self.host} port={self.port}>"
