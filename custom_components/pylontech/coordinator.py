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
        # Berechnungen für die Dashboard-Karte (N/A Fix)
        avg_temp = sum(d.cell_temps) / len(d.cell_temps) if d.cell_temps else 0.0
        min_volt = min(d.cell_voltages) if d.cell_voltages else 0.0
        max_volt = max(d.cell_voltages) if d.cell_voltages else 0.0
        
        res = {
            "pack_voltage": d.pack_voltage, "pack_current": d.pack_current, "state_of_charge": d.soc,
            "power": d.power, "cycle_count": d.cycle_count, "base_state": d.base_state,
            "average_temperature": avg_temp, "lowest_cell_voltage": min_volt, "highest_cell_voltage": max_volt,
            "total_capacity": 100.0, "remaining_capacity": round((d.soc / 100.0) * 100.0, 1),
            "barcode": self.pack_barcodes.get(pid, f"SN_{pid}")
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
                try: self.pack_barcodes[pid] = (await self.protocol.info(pid)).module_barcode.value
                except: self.pack_barcodes[pid] = f"US5000_P{pid}"
            from homeassistant.helpers.entity import DeviceInfo as HADeviceInfo
            self.pack_device_infos = tuple(HADeviceInfo(identifiers={(DOMAIN, self.pack_barcodes[p])}, name=f"Pylontech Pack {p}", model="US5000", manufacturer="Pylontech") for p in range(1, self.pack_count + 1))
        finally: await self.protocol.disconnect()

    def sensor_value(self, sensor, pid): return self.data.get(f"pack_{pid}", {}).get(sensor)
