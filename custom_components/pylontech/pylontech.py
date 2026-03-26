"""Package for reading data from Pylontech (US5000 Bulletproof) BMS."""

from __future__ import annotations

import asyncio
from asyncio import StreamReader, StreamWriter
from dataclasses import dataclass
import logging
from typing import Any

_LOGGER = logging.getLogger(__name__)

# --- SENSOR GRUNDKLASSEN ---

@dataclass
class Sensor:
    """Definition of inverter sensor and its attributes."""
    name: str
    unit: str
    value: Any
    def __str__(self):
        return f"{self.name}: {self.value} {self.unit}"

class Text(Sensor):
    def __init__(self, name: str) -> None:
        super().__init__(name, " ", None)
    def set(self, source: str) -> Text:
        self.value = source
        return self
    def fetch(self, source: list[str], lookup: str | None = None) -> Text:
        if (lookup if lookup else self.name) in source[0]:
            self.value = source[0].split(":")[1].strip()
            source.pop(0)
        return self

class Integer(Sensor):
    def __init__(self, name: str) -> None:
        super().__init__(name, "", None)
    def set(self, source: str) -> Integer:
        self.value = int(source) if source != "-" and source.isdigit() else 0
        return self
    def fetch(self, source: list[str], lookup: str | None = None) -> Integer:
        if (lookup if lookup else self.name) in source[0]:
            val = source[0].split(":")[1].strip()
            self.value = int(val) if val.isdigit() else 0
            source.pop(0)
        return self

class Percent(Sensor):
    def __init__(self, name: str) -> None:
        super().__init__(name, "%", None)
    def set(self, source: str) -> Percent:
        val = source.replace("%", "").strip()
        self.value = int(val) if val.isdigit() else 0
        return self

class Current(Sensor):
    def __init__(self, name: str) -> None:
        super().__init__(name, "A", None)
    def set(self, source: str, divider: int = 1000) -> Current:
        try:
            self.value = int(source) / divider
        except ValueError:
            self.value = int(source.replace("mA", "").strip()) / divider if "mA" in source else 0
        return self
    def fetch(self, source: list[str], lookup: str | None = None) -> Current:
        if (lookup if lookup else self.name) in source[0]:
            val = source[0].split(":")[1].replace("mA", "").strip()
            self.value = int(val) / 1000 if val.isdigit() else 0
            source.pop(0)
        return self

class Voltage(Sensor):
    def __init__(self, name: str) -> None:
        super().__init__(name, "V", None)
    def set(self, source: str, divider: int = 1000) -> Voltage:
        self.value = int(source) / divider if source != "-" and source.lstrip('-').isdigit() else 0
        return self

class ChargeAh(Sensor):
    def __init__(self, name: str) -> None:
        super().__init__(name, "Ah", None)
    def set(self, source: str, divider: int = 1000) -> ChargeAh:
        self.value = int(source) / divider if source != "-" and source.isdigit() else 0
        return self

class ChargeWh(Sensor):
    def __init__(self, name: str) -> None:
        super().__init__(name, "Wh", None)
    def set(self, source: str, divider: int = 1) -> ChargeWh:
        self.value = int(source) / divider if source != "-" and source.isdigit() else 0
        return self

class Temp(Sensor):
    def __init__(self, name: str) -> None:
        super().__init__(name, "C", None)
    def set(self, source: str) -> Temp:
        self.value = int(source) / 1000 if source != "-" and source.lstrip('-').isdigit() else 0
        return self

# --- PARSER KLASSEN ---

class UnitValues:
    def __init__(self, line: str) -> None:
        chunks = line.split()
        if len(chunks) < 10: return
        self.index = Integer("Index").set(chunks[0])
        self.volt = Voltage("Voltage").set(chunks[1])
        self.curr = Current("Current").set(chunks[2])
        self.temp = Temp("Temperature").set(chunks[3])
        self.base_state = Text("Basic state").set(chunks[8])

class UnitCommand:
    def __init__(self, lines: tuple[str]) -> None:
        self.values = [UnitValues(line) for line in lines if line and line[0].isdigit()]

class PwrCommand:
    """US5000 Optimized PWR Parser."""
    def __init__(self, lines: tuple[str], pack_id: int = 1) -> None:
        self.avg_temp = Temp("Average temperature").set("0")
        self.dc_voltage = Voltage("DC Voltage").set("0")
        self.bat_voltage = Voltage("Bat Voltage").set("0")
        
        self.volt = Voltage("Voltage")
        self.curr = Current("Current")
        self.temp = Temp("Temperature")
        self.cell_temp_low = Temp("Lowest cell temperature")
        self.cell_temp_high = Temp("Highest cell temperature")
        self.cell_volt_low = Voltage("Lowest cell voltage")
        self.cell_bolt_high = Voltage("Highest cell voltage")
        self.base_state = Text("Basic state")
        self.soc = Percent("SOC")
        self.error_code = Text("Error code")
        
        target_prefix = str(pack_id)
        for line in lines:
            chunks = line.split()
            # Suche nach der Zeile des aktuellen Packs
            if chunks and chunks[0] == target_prefix and len(chunks) > 15:
                self.volt.set(chunks[1])
                self.curr.set(chunks[2])
                self.temp.set(chunks[3])
                self.cell_temp_low.set(chunks[4])
                self.cell_temp_high.set(chunks[5])
                self.cell_volt_low.set(chunks[6])
                self.cell_bolt_high.set(chunks[7])
                self.base_state.set(chunks[8])
                self.soc.set(chunks[11]) # US5000 SOC Position
                self.error_code.set(chunks[27] if len(chunks) > 27 else "0")
                break

class BatValues:
    def __init__(self, line: str) -> None:
        chunks = line.split()
        if len(chunks) < 5: return
        self.bat = chunks[0]
        self.volt = int(chunks[1]) / 1000 if chunks[1].isdigit() else 0
        self.curr = int(chunks[2]) / 1000 if chunks[2].lstrip('-').isdigit() else 0
        self.tempr = int(chunks[3]) / 1000 if chunks[3].lstrip('-').isdigit() else 0
        self.v_state = chunks[4]
        self.bal = chunks[10] if len(chunks) > 10 else "N"

class BatCommand:
    def __init__(self, lines: tuple[str]) -> None:
        self.values = [BatValues(line) for line in lines if line and line[0].isdigit()]

class InfoCommand:
    """Pylontech BMS console command 'info' (Bulletproof Version)."""
    def __init__(self, lines: tuple[str]) -> None:
        self.device_address = Integer("Device address")
        self.manufacturer = Text("Manufacturer")
        self.device_name = Text("Device name")
        self.board_version = Text("Board version")
        self.sw_version = Text("Soft version")
        self.main_sw_version = Text("Main Soft version")
        self.barcode = Text("Barcode")
        self.module_barcode = Text("Module Barcode")
        self.cell_number = Integer("Cell Number")

        for line in lines:
            if "Device address" in line: self.device_address.set(line.split(":")[1].strip())
            elif "Manufacturer" in line: self.manufacturer.set(line.split(":")[1].strip())
            elif "Device name" in line: self.device_name.set(line.split(":")[1].strip())
            elif "Board version" in line: self.board_version.set(line.split(":")[1].strip())
            elif "Soft  version" in line or "Soft version" in line: self.sw_version.set(line.split(":")[1].strip())
            elif "Main Soft version" in line: self.main_sw_version.set(line.split(":")[1].strip())
            elif "Barcode" in line and "Module" not in line and "PCBA" not in line: 
                self.barcode.set(line.split(":")[1].strip())
            elif "Module Barcode" in line: self.module_barcode.set(line.split(":")[1].strip())
            elif "Cell Number" in line: self.cell_number.set(line.split(":")[1].strip())

        # Sicherstellen, dass module_barcode NIEMALS leer ist (Config Flow Fix)
        if not self.module_barcode.value:
            self.module_barcode.value = self.barcode.value if self.barcode.value else "Unknown_US5000"

    def __str__(self) -> str:
        return f"Device: {self.device_name.value}, SN: {self.barcode.value}"

# --- MAIN BMS CLASS ---

class PylontechBMS:
    """Pylontech BMS connection class."""
    _END_PROMPTS = ("Command completed successfully", "$$", "pylon>")

    def __init__(self, host: str, port: int) -> None:
        self.host = host
        self.port = port
        self.reader = None
        self.writer = None

    async def _exec_cmd(self, cmd: str) -> tuple[str]:
        if not self.writer: await self.connect()
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
            _LOGGER.error("BMS Read Error: %s", e)
        return tuple(lines)

    async def connect(self) -> None:
        self.reader, self.writer = await asyncio.open_connection(self.host, self.port)

    async def disconnect(self) -> None:
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()
            self.reader = None
            self.writer = None

    async def bat(self) -> BatCommand: 
        return BatCommand(await self._exec_cmd("bat"))
    
    async def info(self) -> InfoCommand: 
        return InfoCommand(await self._exec_cmd("info"))
    
    async def pwr(self) -> PwrCommand: 
        return PwrCommand(await self._exec_cmd("pwr"))
    
    async def unit(self) -> UnitCommand: 
        return UnitCommand(await self._exec_cmd("unit"))
        
    async def get_battery_data(self, pack_id: int = 1) -> Any:
        """Spezielle Methode für den Coordinator"""
        cmd_str = f"pwr {pack_id}" if pack_id > 1 else "pwr"
        lines = await self._exec_cmd(cmd_str)
        return PwrCommand(lines, pack_id)
