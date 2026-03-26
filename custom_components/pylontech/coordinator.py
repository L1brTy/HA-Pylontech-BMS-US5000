def _flatten_battery_data(self, data: BatteryData) -> dict[str, Any]:
        """Optimiertes Mapping für US5000 und die Overview-Card."""
        result = {}

        # Basis-Werte
        if data.pack_voltage is not None: result["pack_voltage"] = data.pack_voltage
        if data.pack_current is not None: result["pack_current"] = data.pack_current
        if data.soc is not None: result["state_of_charge"] = data.soc 
        if data.power is not None: result["power"] = data.power
        
        # Kapazität
        if data.remaining_capacity is not None: result["remaining_capacity"] = data.remaining_capacity
        result["total_capacity"] = 100.0

        # TEMPERATUREN - Hier haben wir beide Namen drin (für HA und für die Karte)
        p_temp = data.temperatures.get("pack")
        if p_temp is not None:
            result["pack_temperature"] = p_temp  # Wichtig für die Karte
            result["temp_pack"] = p_temp         # Standard-Name

        # Extremwerte für Delta-V
        if data.cell_volt_low is not None: result["cell_volt_low"] = data.cell_volt_low
        if data.cell_volt_high is not None: result["cell_volt_high"] = data.cell_volt_high
        
        # Temperatur-Extremwerte (Wichtig für Heatmap)
        if data.cell_temp_low is not None: result["cell_temp_low"] = data.cell_temp_low
        if data.cell_temp_high is not None: result["cell_temp_high"] = data.cell_temp_high

        # Status & Fehler
        if data.base_state is not None: result["base_state"] = data.base_state
        if data.error_code is not None: result["error_code"] = data.error_code

        # Einzelzellen (Heatmap)
        for idx, voltage in enumerate(data.cell_voltages):
            result[f"cell_voltage_{idx}"] = voltage

        # Einzelne Zell-Temperaturen (falls vorhanden)
        for idx, temp in enumerate(data.cell_temps):
            result[f"temp_sensor_{idx}"] = temp

        return result
