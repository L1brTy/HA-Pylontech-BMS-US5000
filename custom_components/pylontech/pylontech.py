"""Package for reading data from Pylontech (US5000 Fix) BMS."""

from __future__ import annotations

import asyncio
from asyncio import StreamReader, StreamWriter
from dataclasses import dataclass, field
import logging
from typing import Any

_LOGGER = logging.getLogger(__name__)

@dataclass
class Sensor:
    name: str
    unit: str
    value: Any
    def __str__(self): return f"{self.name}: {self.value} {self.unit}"

class Text(Sensor):
    def set(self, source: str) -> Text:
        self.value = source
        return self

class Integer(Sensor):
    def set(self, source: str) -> Integer:
        self.value = int(source) if source != "-" else 0
        return self

class Percent(Sensor):
    def set(self, source: str) -> Percent:
        self.value = int(source.replace("%", "")) if "%" in source else 0
        return self

class Current(Sensor):
    def set(self, source: str, divider: int = 1000) -> Current:
        try:
            self.value = int(source) / divider
        except ValueError:
            self.value = int(source.replace("mA", "")) / divider if "mA" in source else 0
        return self

class Voltage(Sensor):
    def set(self, source: str, divider: int = 1000) -> Voltage:
        self.value = int(source) / divider if source != "-" else 0
        return self

class Temp(Sensor):
    def set(self, source: str) -> Temp:
        self.value = int(source) / 1000 if source != "-" else 0
        return self

# --- US5000 PARSER LOGIK ---

class BatValues:
    """Repräsentiert die Zell-Daten einer US5000 (bat Befehl)."""
    def __init__(self, line: str) -> None:
        chunks = line.split()
        if len(chunks) < 10: return
        self.bat = chunks[0]
        self.volt = int(chunks[1]) / 1000
        self.curr = int(chunks[2]) / 1000
        self.tempr = int(chunks[3]) / 1000
        self.v_state = chunks[5] # US5000 Index Fix
        self.t_state = chunks[7] # US5000 Index Fix
        soc_raw = chunks[8].replace("%", "")
        self.charge_ah_perc = int(soc_raw) if soc_raw.isdigit() else 0
        self.charge_ah = chunks[9]
        self.bal = chunks[11] if len(chunks) > 11 else "N"

class PwrCommand:
    """Verarbeitet die 'pwr' Antwort für ein spezifisches Pack (US5000)."""
    def __init__(self, lines: list[str], pack_id: int = 1) -> None:
        self.volt = Voltage("Voltage")
        self.curr = Current("Current")
        self.temp = Temp("Temperature")
        self.soc = Percent("SOC")
        self.delta_v = Integer("Delta V")
        
        # Suche die Zeile, die mit der Pack-ID beginnt (1, 2, etc.)
        target_prefix = str(pack_id)
        for line in lines:
            chunks = line.split()
            if chunks and chunks[0] == target_prefix:
                self.volt.set(chunks[1])
                self.curr.set(chunks[2])
                self.temp.set(chunks[3])
                self.soc.set(chunks[11]) # SOC ist bei US5000 an Position 11
                # Delta V berechnen aus Vhigh (7) - Vlow (6)
                vlow = int(chunks[6])
                vhigh = int(chunks[7])
                self.delta_v.value = vhigh - vlow
                break

class PylontechBMS:
    """Pylontech BMS Verbindungsklasse (TCP/Waveshare)."""
    _END_PROMPTS = ("Command completed successfully", "$$", "pylon>")

    def __init__(self, host: str, port: int) -> None:
        self.host = host
        self.port = port
        self.reader = None
        self.writer = None

    async def _exec_cmd(self, cmd: str) -> list[str]:
        if not self.writer: await self.connect()
        self.writer.write((cmd + "\r").encode("ascii"))
        await asyncio.wait_for(self.writer.drain(), 2)
        
        lines = []
        try:
            while True:
                data = await asyncio.wait_for(self.reader.readuntil(b"pylon>"), 5)
                decoded = data.decode("ascii", errors="ignore")
                for line in decoded.splitlines():
                    clean = line.strip()
                    if clean and clean not in self._END_PROMPTS and clean != cmd and clean != "@":
                        lines.append(clean)
                break
        except Exception as e:
            _LOGGER.error("Fehler beim Lesen vom BMS: %s", e)
        return lines

    async def connect(self) -> None:
        self.reader, self.writer = await asyncio.open_connection(self.host, self.port)

    async def disconnect(self) -> None:
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()

    async def get_battery_data(self, pack_id: int = 1) -> Any:
        """Dies ist die Brücke zum Coordinator."""
        lines = await self._exec_cmd("pwr")
        return PwrCommand(lines, pack_id)
