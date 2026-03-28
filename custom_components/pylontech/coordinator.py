from __future__ import annotations
import logging
from typing import Any
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from .const import DOMAIN, SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)

class PylontechUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    def __init__(self, hass, entry, protocol, device_info, device_name="US5000"):
        super().__init__(hass, _LOGGER, name=entry.title, update_interval=SCAN_INTERVAL)
        self.protocol, self.pack_count, self.pack_barcodes, self.pack_device_infos = protocol, 1, {}, ()

    async def _async_update_data(self):
        try:
            await self.protocol.connect()
            res = {}
            for pid in range(1, self.pack_count + 1):
                data = await self.protocol.get_battery_data(pid)
                res[f"pack_{pid}"] = self._flatten(data, pid)
            return res
        except Exception as e: raise UpdateFailed(e)
        finally: await self.protocol.disconnect()

    def _flatten(self, d, pid):
        res = {
            "pack_voltage": d.pack_voltage, "pack_current": d.pack_current, "state_of_charge": d.soc,
            "power": d.power, "lowest_cell_voltage": d.cell_volt_low, "highest_cell_voltage": d.cell_volt_high,
            "base_state": d.base_state, "cycle_count": d.cycle_count, "barcode": self.pack_barcodes.get(pid, f"SN_{pid}")
        }
        for i in range(15):
            res[f"cell_{i}_voltage"] = d.cell_voltages[i] if i < len(d.cell_voltages) else 0.0
            res[f"cell_{i}_soc"] = d.cell_socs[i] if i < len(d.cell_socs) else 0
            res[f"cell_{i}_balancing"] = "Balancing" if i < len(d.cell_balances) and d.cell_balances[i] == "Y" else "Idle"
        
        for i, key in enumerate(["temperature_cells_1_4", "temperature_cells_5_8", "temperature_cells_9_12", "temperature_cells_13_16"]):
            res[key] = d.cell_temps[i] if i < len(d.cell_temps) else 0.0
        return res

    async def detect_sensors(self):
        try:
            await self.protocol.connect()
            p_raw = await self.protocol.pwr()
            self.pack_count = len([line for line in p_raw if line and line.split()[0].isdigit() and "Absent" not in line])
            for pid in range(1, self.pack_count + 1):
                try: 
                    info = await self.protocol.info(pid)
                    self.pack_barcodes[pid] = info.module_barcode.value
                except: self.pack_barcodes[pid] = f"US5000_P{pid}"
            
            from homeassistant.helpers.entity import DeviceInfo as HADeviceInfo
            self.pack_device_infos = tuple(HADeviceInfo(
                identifiers={(DOMAIN, self.pack_barcodes[p])}, 
                name=f"Pylontech Pack {p}", 
                model="US5000", 
                manufacturer="Pylontech"
            ) for p in range(1, self.pack_count + 1))
        finally: await self.protocol.disconnect()

    def sensor_value(self, sensor, pid): return self.data.get(f"pack_{pid}", {}).get(sensor)
