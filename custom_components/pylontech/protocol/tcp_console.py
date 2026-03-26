"""TCP Console Protocol implementation for Pylontech BMS."""

from __future__ import annotations

import asyncio
from asyncio import StreamReader, StreamWriter
import logging
from typing import Any

from .base import ProtocolBase
from ..const import BatteryVariant, ConnectionType
from ..models import BatteryData, DeviceInfo

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

    _END_PROMPTS = ("Command completed successfully", "$$", "pylon>")

    def __init__(self, host: str, port: int) -> None:
        self.host = host
        self.port = port
        self.reader: StreamReader | None = None
        self.writer: StreamWriter | None = None

    async def connect(self) -> None:
        self.reader, self.writer = await asyncio.wait_for(
            asyncio.open_connection(self.host, self.port), 5
        )

    async def disconnect(self) -> None:
        if self.writer is not None:
            self.writer.close()
            await self.writer.wait_closed()
            self.reader = None
            self.writer = None

    async def _exec_cmd(self, cmd: str) -> tuple[str]:
        # HIER WIRD DER BEFEHL PHYSISCH GESENDET
        self.writer.write((cmd + "\r").encode("ascii"))
        await asyncio.wait_for(self.writer.drain(), 2)
        lines = []
        try:
            data = await asyncio.wait_for(self.reader.readuntil(b"pylon>"), 5)
            decoded = data.decode("ascii", errors="ignore")
            for line in decoded.splitlines():
                clean = line.strip()
                if clean and clean not in self._END_PROMPTS and clean != cmd and clean != "@":
                    lines.append(clean)
        except Exception as e:
            _LOGGER.error(f"Error executing {cmd}: {e}")
        return tuple(lines)

    async def bat(self, pack_id: int = 1) -> BatCommand:
        # Zwingt ihn, "bat 1" oder "bat 2" zu senden
        cmd = f"bat {pack_id}"
        return BatCommand(await self._exec_cmd(cmd))

    async def info(self) -> InfoCommand:
        return InfoCommand(await self._exec_cmd("info"))

    async def pwr(self, pack_id: int = 1) -> PwrCommand:
        cmd = f"pwr {pack_id}"
        return PwrCommand(await self._exec_cmd(cmd), pack_id)

    async def unit(self) -> UnitCommand:
        return UnitCommand(await self._exec_cmd("unit"))

    async def get_device_info(self) -> DeviceInfo:
        info = await self.info()
        return DeviceInfo(
            manufacturer=info.manufacturer.value if info.manufacturer.value else "Pylontech",
            model=info.device_name.value if info.device_name.value else "US5000",
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

    async def get_battery_data(self, pack_id: int = 1) -> BatteryData:
        # HIER rufen wir jetzt explizit PWR und BAT ab
        pwr = await self.pwr(pack_id)
        bat_data = await self.bat(pack_id)

        def get_val(obj, attr):
            return getattr(obj, attr).value if hasattr(obj, attr) else None

        temperatures = {
            "average": get_val(pwr, "avg_temp"),
            "pack": get_val(pwr, "temp"),
            "cell_low": get_val(pwr, "cell_temp_low"),
            "cell_high": get_val(pwr, "cell_temp_high"),
        }

        # Auslesen der Zellspannungen aus der Bat-Antwort
        cell_voltages = []
        cell_temps = []
        if hasattr(bat_data, 'values'):
            for cell in bat_data.values:
                if hasattr(cell, 'volt') and cell.volt:
                    cell_voltages.append(cell.volt)
                if hasattr(cell, 'tempr') and cell.tempr:
                    cell_temps.append(cell.tempr)

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
            charge_ah=get_val(pwr, "charge_ah"),
            charge_ah_perc=get_val(pwr, "charge_ah_perc"),
            charge_wh=get_val(pwr, "charge_wh_wh"),
            charge_wh_perc=get_val(pwr, "charge_wh_perc"),
            cell_volt_low=get_val(pwr, "cell_volt_low"),
            cell_volt_high=get_val(pwr, "cell_bolt_high"),
            dc_voltage=get_val(pwr, "dc_voltage"),
            bat_voltage=get_val(pwr, "bat_voltage"),
            error_code=get_val(pwr, "error_code"),
        )
