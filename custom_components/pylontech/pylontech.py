"""Package for reading data from Pylontech (US5000 Bulletproof & Complete) BMS."""

from __future__ import annotations
import asyncio
import logging
from typing import Any

_LOGGER = logging.getLogger(__name__)

# --- SENSOR GRUNDKLASSEN ---

class Sensor:
    def __init__(self, name: str, unit: str, value: Any):
        self.name = name
        self.unit = unit
        self.value = value
    def __str__(self):
        return f"{self.name}: {self.value} {self.unit}"

class Text(Sensor):
    def __init__(self, name: str) -> None:
        super().__init__(name, " ", None)
    def set(self, source: str) -> Text:
        self.value = source
        return self

class Integer(Sensor):
    def __init__(self, name: str) -> None:
        super().__init__(name, "", None)
    def set(self, source: str) -> Integer:
        self.value = int(source) if source != "-" and source.isdigit() else 0
        return self

class Percent(Sensor):
    def __init__(self, name: str) -> None:
        super().__init__(name, "%", None)
    def set(self, source: str) -> Percent:
        val = source.replace("%", "").strip()
        self.value = int(val) if val.isdigit() else 0
        return self

class Current(Sensor):
    def __init__(self, name: str) -> None:
        super().__init__(name, "A", None)
    def set(self, source: str, divider: int = 1000) -> Current:
        try:
            self.value = int(source) / divider
        except ValueError:
            self.value = int(source.replace("mA", "").strip()) / divider if "mA" in source else 0
        return self

class Voltage(Sensor):
    def __init__(self, name: str) -> None:
        super().__init__(name, "V", None)
    def set(self, source: str, divider: int = 1000) -> Voltage:
        self.value = int(source) / divider if source != "-" and source.lstrip('-').isdigit() else 0
        return self

class ChargeAh(Sensor):
    def __init__(self, name: str) -> None:
        super().__init__(name, "Ah", None)
    def set(self, source: str, divider: int = 1000) -> ChargeAh:
        self.value = int(source) / divider if source != "-" and source.isdigit() else 0
        return self

class ChargeWh(Sensor):
    def __init__(self, name: str) -> None:
        super().__init__(name, "Wh", None)
    def set(self, source: str, divider: int = 1) -> ChargeWh:
        self.value = int(source) / divider if source != "-" and source.isdigit() else 0
        return self

class Temp(Sensor):
    def __init__(self, name: str) -> None:
        super().__init__(name, "C", None)
    def set(self, source: str) -> Temp:
        self.value = int(source) / 1000 if source != "-" and source.lstrip('-').isdigit() else 0
        return self

# --- PARSER KLASSEN ---

class UnitValues:
    def __init__(self, line: str) -> None:
        pass

class UnitCommand:
    def __init__(self, lines: tuple[str]) -> None:
        self.values = []

class PwrCommand:
    """US5000 Optimized PWR Parser."""
    def __init__(self, lines: tuple[str], pack_id: int = 1) -> None:
        self.avg_temp = Temp("Average temperature").set("0")
        self.dc_voltage = Voltage("DC Voltage").set("0")
        self.bat_voltage = Voltage("Bat Voltage").set("0")
        self.volt = Voltage("Voltage")
        self.curr = Current("Current")
        self.temp = Temp("Temperature")
        self.cell_temp_low = Temp("Lowest cell temperature")
        self.cell_temp_high = Temp("Highest cell temperature")
        self.cell_volt_low = Voltage("Lowest cell voltage")
        self.cell_bolt_high = Voltage("Highest cell voltage")
        self.base_state = Text("Basic state")
        self.soc = Percent("SOC")
        self.error_code = Text("Error code")
        
        target_prefix = str(pack_id)
        for line in lines:
            chunks = line.split()
            if chunks and chunks[0] == target_prefix and len(chunks) >= 13:
                self.volt.set(chunks[1])
                self.curr.set(chunks[2])
                self.temp.set(chunks[3])
                self.cell_temp_low.set(chunks[4])
                self.cell_temp_high.set(chunks[5])
                self.cell_volt_low.set(chunks[6])
                self.cell_bolt_high.set(chunks[7])
                self.base_state.set(chunks[8])
                self.soc.set(chunks[12] if len(chunks) > 12 else "0")
                self.error_code.set(chunks[27] if len(chunks) > 27 else "0")
                break

class BatValues:
    def __init__(self, line: str) -> None:
        chunks = line.split()
        if len(chunks) < 11 or not chunks[0].isdigit():
            return
        self.bat = chunks[0]
        self.volt = int(chunks[1]) / 1000 if chunks[1].isdigit() else 0.0
        self.curr = int(chunks[2]) / 1000 if chunks[2].lstrip('-').isdigit() else 0.0
        self.tempr = int(chunks[3]) / 1000 if chunks[3].lstrip('-').isdigit() else 0.0
        self.v_state = chunks[5] if len(chunks) > 5 else "Unknown"
        self.bal = chunks[-1] if chunks else "N"

class BatCommand:
    def __init__(self, lines: tuple[str]) -> None:
        self.values = []
        for line in lines:
            val = BatValues(line)
            if hasattr(val, 'bat'):
                self.values.append(val)

class InfoCommand:
    """Pylontech BMS console command 'info'."""
    def __init__(self, lines: tuple[str]) -> None:
        self.device_address = Integer("Device address")
        self.manufacturer = Text("Manufacturer")
        self.device_name = Text("Device name")
        self.board_version = Text("Board version")
        self.hard_version = Text("Hard version")
        self.main_sw_version = Text("Main Soft version")
        self.sw_version = Text("Soft version")
        self.boot_version = Text("Boot version")
        self.comm_version = Text("Comm version")
        self.release_date = Text("Release Date")
        self.barcode = Text("Barcode")
        self.pcba_barcode = Text("PCBA Barcode")
        self.module_barcode = Text("Module Barcode")
        self.pwr_supply_barcode = Text("PowerSupply Barcode")
        self.device_test_time = Text("Device Test Time")
        self.specification = Text("Specification")
        self.cell_number = Integer("Cell Number")
        self.max_discharge_current = Current("Max Discharge Curr")
        self.max_charge_current = Current("Max Charge Curr")
        self.shut_circuit = Text("Shut Circuit")
        self.relay_feedback = Text("Relay Feedback")
        self.new_board = Text("New Board")
        self.bmu_modules = []
        self.bmu_pcbas = []

        for line in lines:
            try:
                if ":" in line:
                    key, val = line.split(":", 1)
                    key = key.strip()
                    val = val.strip()
                    if "Device address" in key: self.device_address.set(val)
                    elif "Manufacturer" in key: self.manufacturer.set(val)
                    elif "Device name" in key: self.device_name.set(val)
                    elif "Board version" in key: self.board_version.set(val)
                    elif "Hard" in key and "version" in key: self.hard_version.set(val)
                    elif "Main Soft version" in key: self.main_sw_version.set(val)
                    elif "Soft" in key and "version" in key and "Main" not in key: self.sw_version.set(val)
                    elif "Boot" in key and "version" in key: self.boot_version.set(val)
                    elif "Comm" in key and "version" in key: self.comm_version.set(val)
                    elif "Release Date" in key: self.release_date.set(val)
                    elif "Barcode" in key and "Module" not in key and "PCBA" not in key and "PowerSupply" not in key: self.barcode.set(val)
                    elif "Module Barcode" in key: self.module_barcode.set(val)
                    elif "PCBA Barcode" in key: self.pcba_barcode.set(val)
                    elif "PowerSupply Barcode" in key: self.pwr_supply_barcode.set(val)
                    elif "Cell Number" in key: self.cell_number.set(val)
                    elif "Max Disch" in key: self.max_discharge_current.set(val)
                    elif "Max Charge" in key: self.max_charge_current.set(val)
                elif line.startswith("Module"):
                    self.bmu_modules.insert(0, line.split()[2] if len(line.split()) > 2 else "")
                elif line.startswith("PCBA"):
                    self.bmu_pcbas.insert(0, line.split()[2] if len(line.split()) > 2 else "")
            except Exception:
                pass

        if not self.module_barcode.value:
            self.module_barcode.value = self.barcode.value if self.barcode.value else "Unknown_US5000"

    def __str__(self) -> str:
        return f"Device: {self.device_name.value}, SN: {self.barcode.value}"

# Placeholder for compatibility if anyone imports it
class PylontechBMS:
    def __init__(self, host: str, port: int) -> None:
        pass
