"""Package for reading data from Pylontech US5000 BMS."""
from __future__ import annotations
import logging
from typing import Any

_LOGGER = logging.getLogger(__name__)

class Sensor:
    def __init__(self, name: str, unit: str, value: Any):
        self.name, self.unit, self.value = name, unit, value
class Text(Sensor):
    def __init__(self, name: str): super().__init__(name, "", None)
    def set(self, val: str): self.value = val; return self
class Integer(Sensor):
    def __init__(self, name: str): super().__init__(name, "", None)
    def set(self, val: str): self.value = int(val) if val.isdigit() else 0; return self
class Percent(Sensor):
    def __init__(self, name: str): super().__init__(name, "%", None)
    def set(self, val: str): 
        v = val.replace("%","").strip()
        self.value = int(v) if v.isdigit() else 0; return self
class Current(Sensor):
    def __init__(self, name: str): super().__init__(name, "A", None)
    def set(self, val: str): self.value = int(val)/1000 if val.replace("-","").isdigit() else 0.0; return self
class Voltage(Sensor):
    def __init__(self, name: str): super().__init__(name, "V", None)
    def set(self, val: str): self.value = int(val)/1000 if val.isdigit() else 0.0; return self
class Temp(Sensor):
    def __init__(self, name: str): super().__init__(name, "C", None)
    def set(self, val: str): self.value = int(val)/1000 if val.replace("-","").isdigit() else 0.0; return self

class PwrCommand:
    def __init__(self, lines: tuple[str], pack_id: int = 1):
        self.volt, self.curr, self.soc = Voltage("Volt"), Current("Curr"), Percent("SOC")
        self.temp, self.cell_temp_low, self.cell_temp_high = Temp("T"), Temp("TL"), Temp("TH")
        self.cell_volt_low, self.cell_bolt_high = Voltage("VL"), Voltage("VH")
        self.base_state, self.error_code = Text("State"), Text("Err")
        prefix = str(pack_id)
        for line in lines:
            chunks = line.split()
            if chunks and chunks[0] == prefix and len(chunks) >= 13:
                self.volt.set(chunks[1]); self.curr.set(chunks[2])
                self.temp.set(chunks[3]); self.cell_temp_low.set(chunks[4])
                self.cell_temp_high.set(chunks[5]); self.cell_volt_low.set(chunks[6])
                self.cell_bolt_high.set(chunks[7]); self.base_state.set(chunks[8])
                self.soc.set(chunks[12]); self.error_code.set(chunks[27] if len(chunks)>27 else "0")

class BatValues:
    def __init__(self, line: str):
        chunks = line.split()
        if len(chunks) < 11 or not chunks[0].isdigit(): return
        self.bat, self.volt = chunks[0], int(chunks[1])/1000
        self.curr, self.tempr = int(chunks[2])/1000, int(chunks[3])/1000

class BatCommand:
    def __init__(self, lines: tuple[str]):
        self.values = []
        for line in lines:
            v = BatValues(line)
            if hasattr(v, 'bat'): self.values.append(v)

class InfoCommand:
    def __init__(self, lines: tuple[str]):
        self.module_barcode = Text("Barcode")
        self.device_name = Text("Name")
        self.main_sw_version = Text("SW")
        self.hard_version = Text("HW")
        self.cell_number = Integer("Cells")
        for line in lines:
            if ":" in line:
                k, v = line.split(":", 1)
                k, v = k.strip(), v.strip()
                if "Module Barcode" in k or "Barcode" in k: self.module_barcode.set(v)
                elif "Device name" in k: self.device_name.set(v)
                elif "Main Soft" in k: self.main_sw_version.set(v)
                elif "Hard" in k: self.hard_version.set(v)
                elif "Cell Number" in k: self.cell_number.set(v)

class UnitCommand:
    def __init__(self, lines: tuple[str]): self.values = []
