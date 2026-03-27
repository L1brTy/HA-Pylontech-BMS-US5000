"""Update coordinator for Pylontech BMS (US5000 Full-Feature Version)."""

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
        self.pack_count = 1
        self.pack_device_infos = ()
        self.available_sensors_per_pack: dict[int, dict[str, type]] = {}

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from the BMS."""
        try:
            await self.protocol.connect()
            result = {}
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
        """Mapping für US5000 - Einzelzellen, Gruppen-Temps und Card-Support."""
        result = {}

        # Basis-Werte für die Card
        if data.pack_voltage is not None: result["pack_voltage"] = data.pack_voltage
        if data.pack_current is not None: result["pack_current"] = data.pack_current
        if data.soc is not None: result["state_of_charge"] = data.soc 
        if data.power is not None: result["power"] = data.power
        
        # Kapazität & Ah Anzeige
        if data.remaining_capacity is not None: result["remaining_capacity"] = data.remaining_capacity
        result["total_capacity"] = 100.0

        # TEMPERATUREN
        p_temp = data.temperatures.get("pack")
        if p_temp is not None:
            result["pack_temperature"] = p_temp  # Wichtig für die Overview-Card
            result["temp_pack"] = p_temp

        # Extremwerte für Delta-V Anzeige
        if data.cell_volt_low is not None: result["cell_volt_low"] = data.cell_volt_low
        if data.cell_volt_high is not None: result["cell_volt_high"] = data.cell_volt_high
        if data.cell_temp_low is not None: result["cell_temp_low"] = data.cell_temp_low
        if data.cell_temp_high is not None: result["cell_temp_high"] = data.cell_temp_high

        # 1. EINZEL-TEMPERATUREN (für die Heatmap beim Klick auf "Temperature")
        # US5000 hat 15 Sensoren
        for idx, temp in enumerate(data.cell_temps):
            result[f"temp_sensor_{idx}"] = temp

        # 2. GRUPPEN-TEMPERATUREN (Durchschnittswerte für die 4 Hauptfelder)
        if len(data.cell_temps) >= 4:
            result["temperature_cells_1_4"] = round(sum(data.cell_temps[0:4]) / 4, 1)
        if len(data.cell_temps) >= 8:
            result["temperature_cells_5_8"] = round(sum(data.cell_temps[4:8]) / 4, 1)
        if len(data.cell_temps) >= 12:
            result["temperature_cells_9_12"] = round(sum(data.cell_temps[8:12]) / 4, 1)
        if len(data.cell_temps) >= 15:
            # Die letzte Gruppe hat meist nur 3 Zellen (13, 14, 15)
            result["temperature_cells_13_16"] = round(sum(data.cell_temps[12:15]) / 3, 1)

        # Einzelzellen Spannungen (Heatmap beim Klick auf "Delta V")
        for idx, voltage in enumerate(data.cell_voltages):
            result[f"cell_voltage_{idx}"] = voltage

        # Status & Fehler
        if data.base_state is not None: result["base_state"] = data.base_state
        if data.error_code is not None: result["error_code"] = data.error_code

        return result

    async def detect_sensors(self) -> None:
        """Auto-detect packs and sensors."""
        try:
            await self.protocol.connect()
            detected_packs = 0
            for pack_id in range(1, 17):
                try:
                    battery_data = await self.protocol.get_battery_data(pack_id=pack_id)
                    if battery_data.pack_voltage in (None, 0, 0.0): break
                    
                    result = self._flatten_battery_data(battery_data)
                    self.available_sensors_per_pack[pack_id] = {name: type(val) for name, val in result.items()}
                    detected_packs = pack_id
                except Exception: break

            self.pack_count = detected_packs if detected_packs > 0 else 1
            self.pack_device_infos = tuple(
                _pack_device(self.device_info_model, pid, self.device_name)
                for pid in range(1, self.pack_count + 1)
            )
        finally:
            await self.protocol.disconnect()

    def sensor_value(self, sensor: str, pack_id: int) -> Any:
        """Return value for sensor."""
        pack_key = f"pack_{pack_id}"
        return self.data.get(pack_key, {}).get(sensor)

def _pack_device(info: DeviceInfo, pack_id: int, device_name: str = "Battery") -> HADeviceInfo:
    """Helper to create device info."""
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
