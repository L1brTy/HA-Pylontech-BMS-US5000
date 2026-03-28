"""TCP Console Protocol for Pylontech US5000 (Waveshare Edition)."""
from __future__ import annotations
import asyncio
from .base import ProtocolBase
from ..const import BatteryVariant, ConnectionType
from ..models import BatteryData, DeviceInfo
from ..pylontech import BatCommand, InfoCommand, PwrCommand, StatCommand

class TCPConsoleProtocol(ProtocolBase):
    def __init__(self, host: str, port: int):
        self.host, self.port = host, port
        self.reader, self.writer = None, None

    async def connect(self):
        self.reader, self.writer = await asyncio.wait_for(asyncio.open_connection(self.host, self.port), 5)

    async def disconnect(self):
        if self.writer: 
            try:
                self.writer.close()
                await self.writer.wait_closed()
            except: pass
            self.reader = self.writer = None

    async def _exec_cmd(self, cmd: str) -> tuple[str]:
        if not self.writer: await self.connect()
        self.writer.write((cmd + "\r").encode("ascii"))
        await asyncio.wait_for(self.writer.drain(), 2)
        data = await asyncio.wait_for(self.reader.readuntil(b"pylon>"), 5)
        return tuple(line.strip() for line in data.decode("ascii", errors="ignore").splitlines() if line.strip())

    # Diese Methode MUSS vorhanden sein, damit der Config-Flow nicht abstürzt
    async def get_device_info(self) -> DeviceInfo:
        raw = await self._exec_cmd("info 1")
        i = InfoCommand(raw)
        return DeviceInfo(
            manufacturer="Pylontech",
            model="US5000",
            barcode=i.module_barcode.value,
            firmware_version=i.soft_version.value,
            connection_type=ConnectionType.TCP_CONSOLE,
            variant=BatteryVariant.PYLONTECH_STANDARD
        )

    async def get_battery_data(self, pack_id: int = 1) -> BatteryData:
        p_raw = await self._exec_cmd("pwr")
        b_raw = await self._exec_cmd(f"bat {pack_id}")
        s_raw = await self._exec_cmd(f"stat {pack_id}")
        
        p = PwrCommand(p_raw, pack_id)
        b = BatCommand(b_raw)
        s = StatCommand(s_raw)
        
        return BatteryData(
            pack_voltage=p.volt.value,
            pack_current=p.curr.value,
            soc=p.soc.value,
            power=round(p.volt.value * p.curr.value, 0),
            remaining_capacity=0.0,
            total_capacity=100.0,
            temperatures={"pack": p.temp.value, "cell_low": p.cell_temp_low.value, "cell_high": p.cell_temp_high.value},
            cell_voltages=[v.volt for v in b.values],
            cell_temps=[v.tempr for v in b.values],
            cell_socs=[v.soc for v in b.values],
            cell_balances=[v.balance for v in b.values],
            cell_volt_low=p.cell_volt_low.value,
            cell_volt_high=p.cell_volt_high.value,
            base_state=p.base_state.value,
            error_code=0,
            cycle_count=s.cycle_count
        )

    # Hilfsmethoden, die oft von der Basis-Klasse erwartet werden
    async def pwr(self): return await self._exec_cmd("pwr")
    async def info(self, pack_id: int = 1): return InfoCommand(await self._exec_cmd(f"info {pack_id}"))
    async def bat(self, pack_id: int = 1): return BatCommand(await self._exec_cmd(f"bat {pack_id}"))
