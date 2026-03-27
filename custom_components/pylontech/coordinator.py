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
        # Alle Namen exakt wie von jtubb programmiert!
        res = {
            "pack_voltage": d.pack_voltage,
            "pack_current": d.pack_current,
            "state_of_charge": d.soc,
            "power": d.power,
            "average_temperature": d.temperatures.get("pack", 0.0), # Hier sucht die Karte nach der Temperatur!
            "lowest_cell_voltage": d.cell_volt_low,
            "highest_cell_voltage": d.cell_volt_high,
            "base_state": d.base_state,
            "total_capacity": 100.0,
            "remaining_capacity": round((d.soc / 100.0) * 100.0, 1) if d.soc else 0.0,
            "barcode": self.pack_barcodes.get(pid, "Unknown"),
            "system_status": "Normal",
            "protect_status": "Normal",
            "fault_status": "Normal",
            "alarm_status": "Normal",
            "cycle_count": 0
        }
        
        # Zellen von 0 bis 15 anlegen (16 Stück). WICHTIG: Name muss 'cell_X_voltage' sein
        for i in range(16):
            res[f"cell_{i}_voltage"] = 0.0
            
        for i, v in enumerate(d.cell_voltages): 
            res[f"cell_{i}_voltage"] = v
            
        # Temperatur-Blöcke (für das Temperatur-Popup)
        res["temperature_cells_1_4"] = d.cell_temps[0] if len(d.cell_temps) > 0 else 0.0
        res["temperature_cells_5_8"] = d.cell_temps[1] if len(d.cell_temps) > 1 else 0.0
        res["temperature_cells_9_12"] = d.cell_temps[2] if len(d.cell_temps) > 2 else 0.0
        res["temperature_cells_13_16"] = d.cell_temps[3] if len(d.cell_temps) > 3 else 0.0
        
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
