class PylontechSensorEntity(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, description, sensor_key, pack_id):
        super().__init__(coordinator)
        self.entity_description = description
        self._sensor_key, self._pack_id = sensor_key, pack_id
        # ERZWINGT DEN NAMEN sensor.pylontech_pack_X_metric
        self._attr_has_entity_name = True
        self._attr_unique_id = f"pylontech_pack_{pack_id}_{sensor_key}"
        self._attr_suggested_object_id = f"pylontech_pack_{pack_id}_{sensor_key}"
        self._attr_device_info = coordinator.pack_device_infos[pack_id - 1]

    @property
    def native_value(self):
        return self.coordinator.sensor_value(self._sensor_key, self._pack_id)

    @property
    def available(self) -> bool:
        return f"pack_{self._pack_id}" in self.coordinator.data
