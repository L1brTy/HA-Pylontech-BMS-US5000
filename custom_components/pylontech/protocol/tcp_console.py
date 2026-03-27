"""TCP Console Protocol for Pylontech US5000."""
from __future__ import annotations
import asyncio
from asyncio import StreamReader, StreamWriter
from .base import ProtocolBase
from ..models import BatteryData, DeviceInfo
from ..pylontech import BatCommand, InfoCommand, PwrCommand, UnitCommand

class TCPConsoleProtocol(ProtocolBase):
    def __init__(self, host: str, port: int):
        self.host, self.port = host, port
        self.reader, self.writer = None, None

    async def connect(self):
        self.reader, self.writer = await asyncio.wait_for(asyncio.open_connection(self.host, self.port), 5)

    async def disconnect(self):
        if self.writer: self.writer.close(); await self.writer.wait_closed()

    async def _exec_cmd(self, cmd: str) -> tuple[str]:
        self.writer.write((cmd + "\r").encode("ascii"))
        await asyncio.wait_for(self.writer.drain(), 2)
        lines = []
        data = await asyncio.wait_for(self.reader.readuntil(b"pylon>"), 5)
        for line in data.decode("ascii", errors="ignore").splitlines():
            c = line.strip()
            if c and c not in ("Command completed successfully", "$$", "pylon>", cmd, "@"): lines.append(c)
        return tuple(lines)

    async def bat(self, pack_id: int = 1): return BatCommand(await self._exec_cmd(f"bat {pack_id}"))
    async def pwr(self): return PwrCommand(await self._exec_cmd("pwr"))
    async def info(self, pack_id: int = 1): return InfoCommand(await self._exec_cmd(f"info {pack_id}"))

    async def get_battery_data(self, pack_id: int = 1) -> BatteryData:
        p, b = await self.pwr(), await self.bat(pack_id)
        p_p = PwrCommand(p.lines if hasattr(p,'lines') else [], pack_id) # Hilfs-Fix falls pwr global
        return BatteryData(
            pack_voltage=p.volt.value, pack_current=p.curr.value, soc=p.soc.value,
            power=p.volt.value * p.curr.value if p.volt.value else 0,
            remaining_capacity=None, total_capacity=100.0,
            temperatures={"pack": p.temp.value, "cell_low": p.cell_temp_low.value, "cell_high": p.cell_temp_high.value},
            cell_voltages=[v.volt for v in b.values], cell_temps=[v.tempr for v in b.values],
            cell_volt_low=p.cell_volt_low.value, cell_volt_high=p.cell_bolt_high.value,
            base_state=p.base_state.value, error_code=p.error_code.value
        )

    async def get_device_info(self) -> DeviceInfo:
        i = await self.info(1)
        return DeviceInfo(manufacturer="Pylontech", model="US5000", barcode=i.module_barcode.value, firmware_version=i.main_sw_version.value)
