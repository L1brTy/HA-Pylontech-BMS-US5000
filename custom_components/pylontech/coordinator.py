"""Update coordinator for Pylontech US5000 (Waveshare Edition)."""
from __future__ import annotations
import logging
from typing import Any
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from .const import DOMAIN, SCAN_INTERVAL
from .protocol.base import ProtocolBase

_LOGGER = logging.getLogger(__name__)

class PylontechUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    def __init__(self, hass, entry, protocol, device_info, device_name="US5000"):
        super().__init__(hass, _LOGGER, name=entry.title, update_interval=SCAN_INTERVAL)
        self.protocol = protocol
        self.pack_count = 1
        self.pack_barcodes = {}
        self.available_sensors_per_pack = {}
        self.pack_device_infos = ()

    async def _async_update_data(self):
        try:
            await self.protocol.connect()
            res = {}
            for pid in range(1, self.pack_count + 1):
                data = await self.protocol.get_battery_data(pid)
                res[f"pack_{pid}"] = self._flatten(data, pid)
            return res
        except Exception as e: 
            _LOGGER.error("Update failed: %s", e)
            raise UpdateFailed(e)
        finally: 
            await self.protocol.disconnect()

    def _flatten(self, d, pid):
        # EXAKTE Namen für die Dashboard-Karte (jetzt auch mit Temperatur)
        res = {
            "pack_voltage": d.pack_voltage,
            "pack_current": d.pack_current,
            "state_of_charge": d.soc,
            "power": d.power,
            "pack_temperature": d.temperatures.get("pack", 0.0),
            "lowest_cell_voltage": d.cell_volt_low,
            "highest_cell_voltage": d.cell_volt_high,
            "base_state": d.base_state,
            "total_capacity": 100.0,
            "remaining_capacity": round((d.soc / 100.0) * 100.0, 1) if d.soc else 0.0,
            "barcode": self.pack_barcodes.get(pid, "Unknown")
        }
        
        # Zellen bei 1 anfangen lassen (WICHTIG für das Popup der Karte!)
        for i, v in enumerate(d.cell_voltages, 1): res[f"cell_voltage_{i}"] = v
        for i, t in enumerate(d.cell_temps, 1): res[f"temp_sensor_{i}"] = t
        
        if len(d.cell_temps) >= 15:
            res["temperature_cells_1_4"] = round(sum(d.cell_temps[0:4])/4, 1)
            res["temperature_cells_5_8"] = round(sum(d.cell_temps[4:8])/4, 1)
            res["temperature_cells_9_12"] = round(sum(d.cell_temps[8:12])/4, 1)
            res["temperature_cells_13_16"] = round(sum(d.cell_temps[12:15])/3, 1)
        return res

    async def detect_sensors(self):
        try:
            await self.protocol.connect()
            det = 0
            for pid in range(1, 17):
                try:
                    info = await self.protocol.info(pid)
                    barcode = info.module_barcode.value
                    if not barcode or barcode == "Unknown":
                        if pid == 1: barcode = "Master_Pack"
                        else: break
                    
                    self.pack_barcodes[pid] = barcode
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
        finally: 
            await self.protocol.disconnect()

    def sensor_value(self, sensor, pid): 
        return self.data.get(f"pack_{pid}", {}).get(sensor)
