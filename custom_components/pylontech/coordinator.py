"""Update coordinator for Pylontech US5000."""
from __future__ import annotations
import logging
from typing import Any
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from .const import DOMAIN, SCAN_INTERVAL
from .protocol import ProtocolBase

_LOGGER = logging.getLogger(__name__)

class PylontechUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    def __init__(self, hass, entry, protocol, device_info, device_name="US5000"):
        super().__init__(hass, _LOGGER, name=entry.title, update_interval=SCAN_INTERVAL)
        self.protocol, self.pack_count = protocol, 1
        self.pack_barcodes, self.available_sensors_per_pack = {}, {}
        self.pack_device_infos = ()

    async def _async_update_data(self):
        try:
            await self.protocol.connect(); res = {}
            for pid in range(1, self.pack_count + 1):
                data = await self.protocol.get_battery_data(pid)
                res[f"pack_{pid}"] = self._flatten(data, pid)
            return res
        except Exception as e: raise UpdateFailed(e)
        finally: await self.protocol.disconnect()

    def _flatten(self, d, pid):
        # EXAKTES MAPPING FÜR DIE OVERVIEW CARD
        res = {
            "pack_voltage": d.pack_voltage, "pack_current": d.pack_current,
            "state_of_charge": d.soc, "power": d.power,
            "pack_temperature": d.temperatures.get("pack", 0.0),
            "cell_volt_low": d.cell_volt_low, "cell_volt_high": d.cell_volt_high,
            "base_state": d.base_state, "total_capacity": 100.0,
            "barcode": self.pack_barcodes.get(pid, "SN_Pending")
        }
        for i, v in enumerate(d.cell_voltages): res[f"cell_voltage_{i}"] = v
        for i, t in enumerate(d.cell_temps): res[f"temp_sensor_{i}"] = t
        if len(d.cell_temps) >= 15:
            res["temperature_cells_1_4"] = round(sum(d.cell_temps[0:4])/4, 1)
            res["temperature_cells_5_8"] = round(sum(d.cell_temps[4:8])/4, 1)
            res["temperature_cells_9_12"] = round(sum(d.cell_temps[8:12])/4, 1)
            res["temperature_cells_13_16"] = round(sum(d.cell_temps[12:15])/3, 1)
        return res

    async def detect_sensors(self):
        try:
            await self.protocol.connect(); det = 0
            for pid in range(1, 17):
                try:
                    info = await self.protocol.info(pid)
                    if not info.module_barcode.value: break
                    self.pack_barcodes[pid] = info.module_barcode.value
                    data = await self.protocol.get_battery_data(pid)
                    self.available_sensors_per_pack[pid] = {n: type(v) for n, v in self._flatten(data, pid).items()}
                    det = pid
                except: break
            self.pack_count = det if det > 0 else 1
            from homeassistant.helpers.entity import DeviceInfo as HADeviceInfo
            self.pack_device_infos = tuple(HADeviceInfo(
                identifiers={(DOMAIN, f"pylon_us5000_{self.pack_barcodes[p]}")},
                name=f"Pylontech US5000 Pack {p} ({self.pack_barcodes[p]})",
                model="US5000", manufacturer="Pylontech", serial_number=self.pack_barcodes[p]
            ) for p in range(1, self.pack_count + 1))
        finally: await self.protocol.disconnect()

    def sensor_value(self, sensor, pid): return self.data.get(f"pack_{pid}", {}).get(sensor)
