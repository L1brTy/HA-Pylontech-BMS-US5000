def _flatten_battery_data(self, data: BatteryData) -> dict[str, Any]:
        """Mapping für US5000 - Einzelzellen und Gruppen-Temperaturen."""
        result = {}

        # Basis-Werte
        if data.pack_voltage is not None: result["pack_voltage"] = data.pack_voltage
        if data.pack_current is not None: result["pack_current"] = data.pack_current
        if data.soc is not None: result["state_of_charge"] = data.soc 
        if data.power is not None: result["power"] = data.power
        result["total_capacity"] = 100.0

        # Die Haupt-Temperatur für die Karte
        p_temp = data.temperatures.get("pack")
        if p_temp is not None:
            result["pack_temperature"] = p_temp
            result["temp_pack"] = p_temp

        # Delta-V und Extremwerte (für die Anzeige rechts oben in der Card)
        if data.cell_volt_low is not None: result["cell_volt_low"] = data.cell_volt_low
        if data.cell_volt_high is not None: result["cell_volt_high"] = data.cell_volt_high
        if data.cell_temp_low is not None: result["cell_temp_low"] = data.cell_temp_low
        if data.cell_temp_high is not None: result["cell_temp_high"] = data.cell_temp_high

        # 1. EINZEL-TEMPERATUREN (für die Heatmap beim Klick)
        # Die Karte sucht nach 'temp_sensor_0' bis 'temp_sensor_14'
        for idx, temp in enumerate(data.cell_temps):
            result[f"temp_sensor_{idx}"] = temp

        # 2. GRUPPEN-TEMPERATUREN (für die 4 Felder in der Karten-Übersicht)
        # Wir berechnen den Durchschnitt für jede 4er-Gruppe
        if len(data.cell_temps) >= 4:
            result["temperature_cells_1_4"] = round(sum(data.cell_temps[0:4]) / 4, 1)
        if len(data.cell_temps) >= 8:
            result["temperature_cells_5_8"] = round(sum(data.cell_temps[4:8]) / 4, 1)
        if len(data.cell_temps) >= 12:
            result["temperature_cells_9_12"] = round(sum(data.cell_temps[8:12]) / 4, 1)
        if len(data.cell_temps) >= 15:
            # Die letzte Gruppe hat beim US5000 nur 3 Zellen (13, 14, 15)
            result["temperature_cells_13_16"] = round(sum(data.cell_temps[12:15]) / 3, 1)

        # Einzelzellen Spannungen (Heatmap)
        for idx, voltage in enumerate(data.cell_voltages):
            result[f"cell_voltage_{idx}"] = voltage

        # Status
        if data.base_state is not None: result["base_state"] = data.base_state

        return result
