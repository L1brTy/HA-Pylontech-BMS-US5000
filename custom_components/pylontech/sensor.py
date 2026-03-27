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

# Mapping aller Sensoren für die Pylontech Overview Card
SENSOR_MAPPINGS = {
    "pack_voltage": ("Pack Voltage", SensorDeviceClass.VOLTAGE, UnitOfElectricPotential.VOLT, SensorStateClass.MEASUREMENT),
    "pack_current": ("Pack Current", SensorDeviceClass.CURRENT, UnitOfElectricCurrent.AMPERE, SensorStateClass.MEASUREMENT),
    "state_of_charge": ("State Of Charge", SensorDeviceClass.BATTERY, PERCENTAGE, SensorStateClass.MEASUREMENT),
    "power": ("Power", SensorDeviceClass.POWER, "W", SensorStateClass.MEASUREMENT),
    "pack_temperature": ("Pack Temperature", SensorDeviceClass.TEMPERATURE, UnitOfTemperature.CELSIUS, SensorStateClass.MEASUREMENT),
    "cell_volt_low": ("Lowest Cell Voltage", SensorDeviceClass.VOLTAGE, UnitOfElectricPotential.VOLT, SensorStateClass.MEASUREMENT),
    "cell_volt_high": ("Highest Cell Voltage", SensorDeviceClass.VOLTAGE, UnitOfElectricPotential.VOLT, SensorStateClass.MEASUREMENT),
    "barcode": ("Barcode", None, None, None),
    "base_state": ("Base State", None, None, None),
    "temperature_cells_1_4": ("Temperature Cells 1 4", SensorDeviceClass.TEMPERATURE, UnitOfTemperature.CELSIUS, SensorStateClass.MEASUREMENT),
    "temperature_cells_5_8": ("Temperature Cells 5 8", SensorDeviceClass.TEMPERATURE, UnitOfTemperature.CELSIUS, SensorStateClass.MEASUREMENT),
    "temperature_cells_9_12": ("Temperature Cells 9 12", SensorDeviceClass.TEMPERATURE, UnitOfTemperature.CELSIUS, SensorStateClass.MEASUREMENT),
    "temperature_cells_13_16": ("Temperature Cells 13 16", SensorDeviceClass.TEMPERATURE, UnitOfTemperature.CELSIUS, SensorStateClass.MEASUREMENT),
}

# Dynamische Ergänzung für die 15 Einzelzellen des US5000
for i in range(15):
    SENSOR_MAPPINGS[f"cell_voltage_{i}"] = (f"Cell {i} Voltage", SensorDeviceClass.VOLTAGE, UnitOfElectricPotential.VOLT, SensorStateClass.MEASUREMENT)
    SENSOR_MAPPINGS[f"temp_sensor_{i}"] = (f"Temperature Sensor {i}", SensorDeviceClass.TEMPERATURE, UnitOfTemperature.CELSIUS, SensorStateClass.MEASUREMENT)


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up Pylontech sensors based on a config entry."""
    
    # BULLETPROOF-WEICHE: Prüft, ob die Daten direkt oder als Dictionary (Box) kommen
    domain_data = hass.data[DOMAIN][entry.entry_id]
    
    if isinstance(domain_data, dict):
        coordinator = domain_data.get("coordinator")
    else:
        coordinator = domain_data

    # Jetzt haben wir sicher den Koordinator und können den pack_count abfragen
    entities = []
    for pid in range(1, coordinator.pack_count + 1):
        for s_key, (name, dev_class, unit, state_class) in SENSOR_MAPPINGS.items():
            desc = SensorEntityDescription(
                key=s_key,
                name=name,
                device_class=dev_class,
                native_unit_of_measurement=unit,
                state_class=state_class,
            )
            entities.append(PylontechSensorEntity(coordinator, desc, s_key, pid))
            
    async_add_entities(entities)


class PylontechSensorEntity(CoordinatorEntity, SensorEntity):
    """Representation of a Pylontech BMS sensor."""

    def __init__(self, coordinator, description, sensor_key, pack_id):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._sensor_key = sensor_key
        self._pack_id = pack_id
        
        # WICHTIG: Erzeugt die exakte Entity-ID für die Dashboard-Karte (ISA-101 Standard)
        self._attr_has_entity_name = True
        self._attr_unique_id = f"pylontech_pack_{pack_id}_{sensor_key}"
        self._attr_suggested_object_id = f"pylontech_pack_{pack_id}_{sensor_key}"
        
        if pack_id <= len(coordinator.pack_device_infos):
            self._attr_device_info = coordinator.pack_device_infos[pack_id - 1]

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self.coordinator.sensor_value(self._sensor_key, self._pack_id)

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return (
            self.coordinator.last_update_success and 
            f"pack_{self._pack_id}" in self.coordinator.data
        )
