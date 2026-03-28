from __future__ import annotations
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass, SensorEntityDescription
from homeassistant.const import UnitOfElectricPotential, UnitOfElectricCurrent, UnitOfTemperature, PERCENTAGE
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN

SENSOR_MAPPINGS = {
    "pack_voltage": ("Pack Voltage", SensorDeviceClass.VOLTAGE, UnitOfElectricPotential.VOLT, SensorStateClass.MEASUREMENT, 3),
    "pack_current": ("Pack Current", SensorDeviceClass.CURRENT, UnitOfElectricCurrent.AMPERE, SensorStateClass.MEASUREMENT, 2),
    "state_of_charge": ("State Of Charge", SensorDeviceClass.BATTERY, PERCENTAGE, SensorStateClass.MEASUREMENT, 0),
    "power": ("Power", SensorDeviceClass.POWER, "W", SensorStateClass.MEASUREMENT, 0),
    "cycle_count": ("Cycle Count", None, None, SensorStateClass.TOTAL_INCREASING, 0),
    "base_state": ("Base State", None, None, None, None),
    "temperature_cells_1_4": ("Temp Zone 1", SensorDeviceClass.TEMPERATURE, UnitOfTemperature.CELSIUS, SensorStateClass.MEASUREMENT, 1),
    "temperature_cells_5_8": ("Temp Zone 2", SensorDeviceClass.TEMPERATURE, UnitOfTemperature.CELSIUS, SensorStateClass.MEASUREMENT, 1),
    "temperature_cells_9_12": ("Temp Zone 3", SensorDeviceClass.TEMPERATURE, UnitOfTemperature.CELSIUS, SensorStateClass.MEASUREMENT, 1),
    "temperature_cells_13_16": ("Temp Zone 4", SensorDeviceClass.TEMPERATURE, UnitOfTemperature.CELSIUS, SensorStateClass.MEASUREMENT, 1),
}

for i in range(15):
    SENSOR_MAPPINGS[f"cell_{i}_voltage"] = (f"Cell {i} Voltage", SensorDeviceClass.VOLTAGE, UnitOfElectricPotential.VOLT, SensorStateClass.MEASUREMENT, 3)
    SENSOR_MAPPINGS[f"cell_{i}_soc"] = (f"Cell {i} SOC", SensorDeviceClass.BATTERY, PERCENTAGE, SensorStateClass.MEASUREMENT, 0)
    SENSOR_MAPPINGS[f"cell_{i}_balancing"] = (f"Cell {i} Balancing", None, None, None, None)

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = []
    for pid in range(1, coordinator.pack_count + 1):
        for s_key, (name, dev_class, unit, state_class, prec) in SENSOR_MAPPINGS.items():
            desc = SensorEntityDescription(key=s_key, name=name, device_class=dev_class, native_unit_of_measurement=unit, state_class=state_class, suggested_display_precision=prec)
            entities.append(PylontechSensorEntity(coordinator, desc, s_key, pid))
    async_add_entities(entities)

class PylontechSensorEntity(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, description, sensor_key, pack_id):
        super().__init__(coordinator)
        self.entity_description, self._sensor_key, self._pack_id = description, sensor_key, pack_id
        self.entity_id = f"sensor.pylontech_p{pack_id}_{sensor_key}"
        self._attr_unique_id = f"pylon_{coordinator.pack_barcodes.get(pack_id, pack_id)}_{sensor_key}"
        self._attr_device_info = coordinator.pack_device_infos[pack_id - 1]
        self._attr_name = f"Pylontech Pack {pack_id} {description.name}"

    @property
    def native_value(self): return self.coordinator.sensor_value(self._sensor_key, self._pack_id)
