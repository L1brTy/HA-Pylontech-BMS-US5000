"""Update coordinator for Pylontech US5000 (Waveshare Edition)."""
from __future__ import annotations
import logging
from typing import Any
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from .const import DOMAIN, SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)

class PylontechUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    def __init__(self, hass, entry, protocol, device_info, device_name="US5000"):
        super().__init__(hass, _LOGGER, name=entry.title, update_interval=SCAN_INTERVAL)
        self.protocol = protocol
        self.pack_count = 1
        self.pack_barcodes = {}
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
        # Grundwerte sicherstellen
        res = {
            "pack_voltage": getattr(d, 'pack_voltage', 0.0),
            "pack_current": getattr(d, 'pack_current', 0.0),
            "state_of_charge": getattr(d, 'soc', 0),
            "power": getattr(d, 'power', 0),
            "average_temperature": sum(d.cell_temps) / len(d.cell_temps) if hasattr(d, 'cell_temps') and d.cell_temps else 0.0,
            "lowest_cell_voltage": getattr(d, 'cell_volt_low', 0.0),
            "highest_cell_voltage": getattr(d, 'cell_volt_high', 0.0),
            "base_state": getattr(d, 'base_state', "Unknown"),
            "total_capacity": 100.0,
            "remaining_capacity": getattr(d, 'remain_cap', 0.0),
            "barcode": self.pack_barcodes.get(pid, "Unknown"),
            "system_status": getattr(d, 'system_status', "Normal"),
            "protect_status": getattr(d, 'protect_status', "Normal"),
            "fault_status": getattr(d, 'fault_status', "Normal"),
            "alarm_status": getattr(d, 'alarm_status', "Normal"),
            "cycle_count": getattr(d, 'cycle_count', 0)
        }
        
        # Details für jede der 15 Zellen (0-14)
        for i in range(15):
            # 1. Spannung (Volt)
            voltages = getattr(d, 'cell_voltages', [])
            res[f"cell_{i}_voltage"] = voltages[i] if i < len(voltages) else 0.0
            
            # 2. SOC pro Zelle
            socs = getattr(d, 'cell_socs', [])
            res[f"cell_{i}_soc"] = socs[i] if i < len(socs) else None
            
            # 3. Balancing Status
            balances = getattr(d, 'cell_balances', [])
            if i < len(balances):
                res[f"cell_{i}_balancing"] = "Balancing" if balances[i] in ["Y", "y", True] else "Idle"
            else:
                res[f"cell_{i}_balancing"] = "Idle"
            
        # Temperaturen (Zuweisung auf die 4 Zonen-Sensoren)
        temps = getattr(d, 'cell_temps', [])
        res["temperature_cells_1_4"] = temps[0] if len(temps) > 0 else 0.0
        res["temperature_cells_5_8"] = temps[1] if len(temps) > 1 else 0.0
        res["temperature_cells_9_12"] = temps[2] if len(temps) > 2 else 0.0
        res["temperature_cells_13_16"] = temps[3] if len(temps) > 3 else 0.0
        
        return res

    async def detect_sensors(self):
        try:
            await self.protocol.connect()
            det = 0
            for pid in range(1, 17):
                try:
                    info = await self.protocol.info(pid)
                    barcode = info.module_barcode.value if hasattr(info.module_barcode, 'value') else str(info.module_barcode)
                    if not barcode or barcode == "Unknown":
                        if pid == 1: barcode = "Master_Pack"
                        else: break
                    self.pack_barcodes[pid] = barcode
                    det = pid
                except: break
            
            self.pack_count = det if det > 0 else 1
            from homeassistant.helpers.entity import DeviceInfo as HADeviceInfo
            self.pack_device_infos = tuple(HADeviceInfo(
                identifiers={(DOMAIN, f"pylon_us5000_{self.pack_barcodes[p]}")},
                name=f"Pylontech US5000 Pack {p}",
                model="US5000", manufacturer="Pylontech"
            ) for p in range(1, self.pack_count + 1))
        finally:
            await self.protocol.disconnect()

    def sensor_value(self, sensor, pid):
        if not self.data: return None
        return self.data.get(f"pack_{pid}", {}).get(sensor)
