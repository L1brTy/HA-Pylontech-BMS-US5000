"""Sensor platform for Pylontech US5000 Waveshare Edition."""
from __future__ import annotations

from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
    SensorEntityDescription,
)
from homeassistant.const import (
    UnitOfElectricPotential,
    UnitOfElectricCurrent,
    UnitOfTemperature,
    PERCENTAGE,
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN

# Mapping für alle Sensoren (mit doppelter Absicherung für die Temperatur)
SENSOR_MAPPINGS = {
    "pack_voltage": ("Pack Voltage", SensorDeviceClass.VOLTAGE, UnitOfElectricPotential.VOLT, SensorStateClass.MEASUREMENT, 3),
    "pack_current": ("Pack Current", SensorDeviceClass.CURRENT, UnitOfElectricCurrent.AMPERE, SensorStateClass.MEASUREMENT, 2),
    "state_of_charge": ("State Of Charge", SensorDeviceClass.BATTERY, PERCENTAGE, SensorStateClass.MEASUREMENT, 0),
    "power": ("Power", SensorDeviceClass.POWER, "W", SensorStateClass.MEASUREMENT, 0),
    "temp": ("Temperature", SensorDeviceClass.TEMPERATURE, UnitOfTemperature.CELSIUS, SensorStateClass.MEASUREMENT, 1),
    "temperature": ("Temperature", SensorDeviceClass.TEMPERATURE, UnitOfTemperature.CELSIUS, SensorStateClass.MEASUREMENT, 1),
    "lowest_cell_voltage": ("Lowest Cell Voltage", SensorDeviceClass.VOLTAGE, UnitOfElectricPotential.VOLT, SensorStateClass.MEASUREMENT, 3),
    "highest_cell_voltage": ("Highest Cell Voltage", SensorDeviceClass.VOLTAGE, UnitOfElectricPotential.VOLT, SensorStateClass.MEASUREMENT, 3),
    "total_capacity": ("Total Capacity", None, "Ah", SensorStateClass.MEASUREMENT, 1),
    "remaining_capacity": ("Remaining Capacity", None, "Ah", SensorStateClass.MEASUREMENT, 1),
    "barcode": ("Barcode", None, None, None, None),
    "base_state": ("Base State", None, None, None, None),
    "temperature_cells_1_4": ("Temperature Cells 1 4", SensorDeviceClass.TEMPERATURE, UnitOfTemperature.CELSIUS, SensorStateClass.MEASUREMENT, 1),
    "temperature_cells_5_8": ("Temperature Cells 5 8", SensorDeviceClass.TEMPERATURE, UnitOfTemperature.CELSIUS, SensorStateClass.MEASUREMENT, 1),
    "temperature_cells_9_12": ("Temperature Cells 9 12", SensorDeviceClass.TEMPERATURE, UnitOfTemperature.CELSIUS, SensorStateClass.MEASUREMENT, 1),
    "temperature_cells_13_16": ("Temperature Cells 13 16", SensorDeviceClass.TEMPERATURE, UnitOfTemperature.CELSIUS, SensorStateClass.MEASUREMENT, 1),
}

# Alle 16 Zellen und 16 Temp-Sensoren registrieren
for i in range(1, 17):
    SENSOR_MAPPINGS[f"cell_voltage_{i}"] = (f"Cell {i} Voltage", SensorDeviceClass.VOLTAGE, UnitOfElectricPotential.VOLT, SensorStateClass.MEASUREMENT, 3)
    SENSOR_MAPPINGS[f"temp_sensor_{i}"] = (f"Temperature Sensor {i}", SensorDeviceClass.TEMPERATURE, UnitOfTemperature.CELSIUS, SensorStateClass.MEASUREMENT, 1)


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up Pylontech sensors based on a config entry."""
    domain_data = hass.data[DOMAIN][entry.entry_id]
    
    if isinstance(domain_data, dict):
        coordinator = domain_data.get("coordinator")
    else:
        coordinator = domain_data

    entities = []
    for pid in range(1, coordinator.pack_count + 1):
        for s_key, (name, dev_class, unit, state_class, precision) in SENSOR_MAPPINGS.items():
            desc = SensorEntityDescription(
                key=s_key,
                name=name,
                device_class=dev_class,
                native_unit_of_measurement=unit,
                state_class=state_class,
                suggested_display_precision=precision,
            )
            entities.append(PylontechSensorEntity(coordinator, desc, s_key, pid))
            
    async_add_entities(entities)


class PylontechSensorEntity(CoordinatorEntity, SensorEntity):
    """Representation of a Pylontech BMS sensor."""
    def __init__(self, coordinator, description, sensor_key, pack_id):
        super().__init__(coordinator)
        self.entity_description = description
        self._sensor_key = sensor_key
        self._pack_id = pack_id
        
        # Zwingt HA die Entitäten exakt nach Dashboard-Norm zu benennen
        self.entity_id = f"sensor.pylontech_pack_{pack_id}_{sensor_key}"
        
        barcode = "unknown"
        if hasattr(coordinator, "pack_barcodes") and pack_id in coordinator.pack_barcodes:
            barcode = coordinator.pack_barcodes[pack_id]
            
        self._attr_unique_id = f"pylontech_{barcode}_{sensor_key}"
        self._attr_has_entity_name = False
        self._attr_name = f"Pylontech Pack {pack_id} {description.name}"
        
        if hasattr(coordinator, "pack_device_infos") and pack_id <= len(coordinator.pack_device_infos):
            self._attr_device_info = coordinator.pack_device_infos[pack_id - 1]

    @property
    def native_value(self):
        return self.coordinator.sensor_value(self._sensor_key, self._pack_id)

    @property
    def available(self) -> bool:
        return (
            self.coordinator.last_update_success and 
            f"pack_{self._pack_id}" in self.coordinator.data
        )
