"""Update coordinator for Pylontech BMS."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo as HADeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, SCAN_INTERVAL
from .models import BatteryData, DeviceInfo
from .protocol import ProtocolBase

_LOGGER = logging.getLogger(__name__)


class PylontechUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Gather data for the energy device."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        protocol: ProtocolBase,
        device_info: DeviceInfo,
        device_name: str = "Battery",
    ) -> None:
        """Initialize update coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=entry.title,
            update_interval=SCAN_INTERVAL,
            update_method=self._async_update_data,
        )
        self.protocol = protocol
        self.device_info_model = device_info
        self.serial_nr = device_info.barcode if device_info.barcode else "unknown_serial"
        self.device_name = device_name
        
        # Startwert (wird in detect_sensors gleich automatisch korrigiert)
        self.pack_count = 1
        
        # Create device info for each pack
        self.pack_device_infos = tuple(
            _pack_device(device_info, pack_id, device_name)
            for pack_id in range(1, self.pack_count + 1)
        )
        # Store available sensors per pack: {pack_id: {sensor_name: type}}
        self.available_sensors_per_pack: dict[int, dict[str, type]] = {}

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from the BMS."""
        try:
            await self.protocol.connect()
            result = {}

            # Query each pack separately using the detected pack_count
            for pack_id in range(1, self.pack_count + 1):
                try:
                    battery_data = await self.protocol.get_battery_data(pack_id=pack_id)
                    pack_data = self._flatten_battery_data(battery_data)
                    result[f"pack_{pack_id}"] = pack_data
                except Exception as err:
                    _LOGGER.warning("Failed to fetch data for pack %d: %s", pack_id, err)

            return result
        except Exception as ex:
            raise UpdateFailed(ex) from ex
        finally:
            await self.protocol.disconnect()

    def _flatten_battery_data(self, data: BatteryData) -> dict[str, Any]:
        """Flatten BatteryData model to dictionary format."""
        result = {}

        if data.pack_voltage is not None: result["pack_voltage"] = data.pack_voltage
        if data.pack_current is not None: result["pack_current"] = data.pack_current
        if data.soc is not None: result["soc"] = data.soc
        if data.power is not None: result["power"] = data.power
        if data.remaining_capacity is not None: result["remaining_capacity"] = data.remaining_capacity
        if data.total_capacity is not None: result["total_capacity"] = data.total_capacity
        if data.avg_temperature is not None: result["avg_temperature"] = data.avg_temperature
        
        for temp_name, temp_value in data.temperatures.items():
            result[f"temp_{temp_name}"] = temp_value

        if data.base_state is not None: result["base_state"] = data.base_state
        if data.volt_state is not None: result["volt_state"] = data.volt_state
        if data.curr_state is not None: result["curr_state"] = data.curr_state
        if data.temp_state is not None: result["temp_state"] = data.temp_state
        
        # Cycle count und Zellspannungen (US5000 Support)
        if data.cycle_count is not None: result["cycle_count"] = data.cycle_count
        for idx, voltage in enumerate(data.cell_voltages):
            result[f"cell_voltage_{idx}"] = voltage

        temp_names = ["temp_cells_1_4", "temp_cells_5_8", "temp_cells_9_12", "temp_cells_13_16", "temp_mos", "temp_env"]
        for idx, temp in enumerate(data.cell_temps):
            if idx < len(temp_names):
                result[temp_names[idx]] = temp
            else:
                result[f"temp_sensor_{idx}"] = temp

        return result

    async def detect_sensors(self) -> None:
        """Retrieve all supported sensor names and AUTO-DETECT packs."""
        try:
            await self.protocol.connect()
            
            detected_packs = 0
            _LOGGER.info("Starte automatische Erkennung der Pylontech Packs...")
            
            # Wir fragen nacheinander die Packs ab (Pylontech unterstützt max. 16 am RS485 Bus)
            for pack_id in range(1, 17):
                try:
                    battery_data = await self.protocol.get_battery_data(pack_id=pack_id)
                    
                    # Wenn keine Spannung zurückkommt, existiert das Pack sehr wahrscheinlich nicht
                    if battery_data.pack_voltage in (None, 0, 0.0):
                        break
                        
                    result = self._flatten_battery_data(battery_data)
                    pack_sensors = {name: type(val) for name, val in result.items()}
                    self.available_sensors_per_pack[pack_id] = pack_sensors
                    detected_packs = pack_id
                    
                except Exception:
                    # Sobald ein Fehler fliegt (z.B. Pack existiert nicht), brechen wir ab
                    break

            # Nach der Suchschleife wissen wir genau, wie viele Packs es gibt
            if detected_packs > 0:
                self.pack_count = detected_packs
                _LOGGER.info("Erfolgreich %d Pylontech Packs erkannt!", self.pack_count)
                
                # Gerätedaten für Home Assistant mit der korrekten Anzahl neu aufbauen
                self.pack_device_infos = tuple(
                    _pack_device(self.device_info_model, pid, self.device_name)
                    for pid in range(1, self.pack_count + 1)
                )
            else:
                _LOGGER.warning("Konnte keine Packs erkennen. Falle auf 1 Pack zurück.")
                self.pack_count = 1

        finally:
            await self.protocol.disconnect()

    def sensor_value(self, sensor: str, pack_id: int) -> Any:
        """Answer current value of the sensor for a specific pack."""
        pack_key = f"pack_{pack_id}"
        if pack_key not in self.data:
            return None
        return self.data[pack_key].get(sensor)


def _pack_device(info: DeviceInfo, pack_id: int, device_name: str = "Battery") -> HADeviceInfo:
    """Create device info for individual battery pack."""
    serial = info.barcode if info.barcode else "unknown"
    pack_serial = f"{serial}_pack{pack_id}"
    return HADeviceInfo(
        identifiers={(DOMAIN, pack_serial)},
        name=f"{info.manufacturer} {device_name} Pack {pack_id}",
        model=info.model if info.model else "US5000",
        manufacturer=info.manufacturer if info.manufacturer else "Pylontech",
        sw_version=info.firmware_version,
        serial_number=pack_serial,
    )
