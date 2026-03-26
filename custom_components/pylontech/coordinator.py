def _flatten_battery_data(self, data: BatteryData) -> dict[str, Any]:
        """Flatten BatteryData model to match the Pylontech-Overview-Card perfectly."""
        result = {}

        # Basis-Werte
        if data.pack_voltage is not None: result["pack_voltage"] = data.pack_voltage
        if data.pack_current is not None: result["pack_current"] = data.pack_current
        if data.soc is not None: result["state_of_charge"] = data.soc # Wichtig für die Karte!
        if data.power is not None: result["power"] = data.power
        
        # Kapazität (für die Anzeige ganz unten in der Karte)
        if data.remaining_capacity is not None: result["remaining_capacity"] = data.remaining_capacity
        result["total_capacity"] = 100.0 # US5000 hat 100Ah

        # Temperaturen (Die Karte sucht nach 'pack_temperature')
        result["pack_temperature"] = data.temperatures.get("pack", 0.0)
        
        # Extremwerte für Delta-V (WICHTIG: exakte Namen für die Karte!)
        if data.cell_volt_low is not None: result["cell_volt_low"] = data.cell_volt_low
        if data.cell_volt_high is not None: result["cell_volt_high"] = data.cell_volt_high
        if data.cell_temp_low is not None: result["cell_temp_low"] = data.cell_temp_low
        if data.cell_temp_high is not None: result["cell_temp_high"] = data.cell_temp_high

        # Status
        if data.base_state is not None: result["base_state"] = data.base_state

        # Einzelzellen (Heatmap funktioniert ja schon, wir lassen die Namen so)
        for idx, voltage in enumerate(data.cell_voltages):
            result[f"cell_voltage_{idx}"] = voltage

        return result
