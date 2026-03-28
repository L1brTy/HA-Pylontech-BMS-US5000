"""Sensor platform for Pylontech US5000 Waveshare Edition."""
from __future__ import annotations
from homeassistant.components.sensor import (
    SensorEntity, SensorDeviceClass, SensorStateClass, SensorEntityDescription,
)
from homeassistant.const import (
    UnitOfElectricPotential, UnitOfElectricCurrent, UnitOfTemperature, PERCENTAGE,
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN

SENSOR_MAPPINGS = {
    "pack_voltage": ("Pack Voltage", SensorDeviceClass.VOLTAGE, UnitOfElectricPotential.VOLT, SensorStateClass.MEASUREMENT, 3),
    "pack_current": ("Pack Current", SensorDeviceClass.CURRENT, UnitOfElectricCurrent.AMPERE, SensorStateClass.MEASUREMENT, 2),
    "state_of_charge": ("State Of Charge", SensorDeviceClass.BATTERY, PERCENTAGE, SensorStateClass.MEASUREMENT, 0),
    "power": ("Power", SensorDeviceClass.POWER, "W", SensorStateClass.MEASUREMENT, 0),
    "average_temperature": ("Average Temperature", SensorDeviceClass.TEMPERATURE, UnitOfTemperature.CELSIUS, SensorStateClass.MEASUREMENT, 1),
    "lowest_cell_voltage": ("Lowest Cell Voltage", SensorDeviceClass.VOLTAGE, UnitOfElectricPotential.VOLT, SensorStateClass.MEASUREMENT, 3),
    "highest_cell_voltage": ("Highest Cell Voltage", SensorDeviceClass.VOLTAGE, UnitOfElectricPotential.VOLT, SensorStateClass.MEASUREMENT, 3),
    "total_capacity": ("Total Capacity", None, "Ah", SensorStateClass.MEASUREMENT, 1),
    "remaining_capacity": ("Remaining Capacity", None, "Ah", SensorStateClass.MEASUREMENT, 1),
    "cycle_count": ("Cycle Count", None, None, SensorStateClass.TOTAL_INCREASING, 0),
    "base_state": ("Base State", None, None, None, None),
    "system_status": ("System Status", None, None, None, None),
    "protect_status": ("Protection Status", None, None, None, None),
    "fault_status": ("Fault Status", None, None, None, None),
    "alarm_status": ("Alarm Status", None, None, None, None),
    "temperature_cells_1_4": ("Temperature Zone 1", SensorDeviceClass.TEMPERATURE, UnitOfTemperature.CELSIUS, SensorStateClass.MEASUREMENT, 1),
    "temperature_cells_5_8": ("Temperature Zone 2", SensorDeviceClass.TEMPERATURE, UnitOfTemperature.CELSIUS, SensorStateClass.MEASUREMENT, 1),
    "temperature_cells_9_12": ("Temperature Zone 3", SensorDeviceClass.TEMPERATURE, UnitOfTemperature.CELSIUS, SensorStateClass.MEASUREMENT, 1),
    "temperature_cells_13_16": ("Temperature Zone 4", SensorDeviceClass.TEMPERATURE, UnitOfTemperature.CELSIUS, SensorStateClass.MEASUREMENT, 1),
}

# 15 Zellen registrieren
for i in range(15):
    SENSOR_MAPPINGS[f"cell_{i}_voltage"] = (f"Cell {i} Voltage", SensorDeviceClass.VOLTAGE, UnitOfElectricPotential.VOLT, SensorStateClass.MEASUREMENT, 3)
    SENSOR_MAPPINGS[f"cell_{i}_soc"] = (f"Cell {i} State of Charge", SensorDeviceClass.BATTERY, PERCENTAGE, SensorStateClass.MEASUREMENT, 0)
    SENSOR_MAPPINGS[f"cell_{i}_balancing"] = (f"Cell {i} Balancing Status", None, None, None, None)

async def async_setup_entry(hass, entry, async_add_entities):
    domain_data = hass.data[DOMAIN][entry.entry_id]
    coordinator = domain_data if not isinstance(domain_data, dict) else domain_data.get("coordinator")
    
    entities = []
    for pid in range(1, coordinator.pack_count + 1):
        for s_key, (name, dev_class, unit, state_class, precision) in SENSOR_MAPPINGS.items():
            desc = SensorEntityDescription(
                key=s_key, name=name, device_class=dev_class,
                native_unit_of_measurement=unit, state_class=state_class,
                suggested_display_precision=precision,
            )
            entities.append(PylontechSensorEntity(coordinator, desc, s_key, pid))
    async_add_entities(entities)

class PylontechSensorEntity(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, description, sensor_key, pack_id):
        super().__init__(coordinator)
        self.entity_description = description
        self._sensor_key = sensor_key
        self._pack_id = pack_id
        self.entity_id = f"sensor.pylontech_pack_{pack_id}_{sensor_key}"
        barcode = coordinator.pack_barcodes.get(pack_id, f"pack_{pack_id}")
        self._attr_unique_id = f"pylon_{barcode}_{sensor_key}"
        self._attr_has_entity_name = False
        self._attr_name = f"Pylontech Pack {pack_id} {description.name}"
        self._attr_device_info = coordinator.pack_device_infos[pack_id - 1]

    @property
    def native_value(self):
        return self.coordinator.sensor_value(self._sensor_key, self._pack_id)
