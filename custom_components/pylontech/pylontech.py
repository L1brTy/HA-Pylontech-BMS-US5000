"""Parser for Pylontech US5000 Console Output."""
from __future__ import annotations

class BatValue:
    def __init__(self, line: str):
        p = line.split()
        if len(p) < 11: raise ValueError("Line too short")
        self.cell_id = int(p[0])
        self.volt = int(p[1]) / 1000.0
        self.curr = int(p[2]) / 1000.0
        self.tempr = int(p[3]) / 1000.0
        self.base_state = p[4]
        # In der 'bat' Tabelle steht SOC an Index 8
        self.soc = int(p[8].replace('%', '')) if '%' in p[8] else 0
        self.balance = p[-1] # BAL ist die letzte Spalte

class BatCommand:
    def __init__(self, lines: tuple[str]):
        self.values = []
        for line in lines:
            if line and line[0].isdigit() and len(line.split()) > 10:
                try: self.values.append(BatValue(line))
                except: continue

class PwrCommand:
    def __init__(self, lines: tuple[str], pack_id: int = 1):
        self.volt = type('V', (), {'value': 0.0})
        self.curr = type('C', (), {'value': 0.0})
        self.soc = type('S', (), {'value': 0})
        self.temp = type('T', (), {'value': 0.0})
        self.cell_volt_low = type('VL', (), {'value': 0.0})
        self.cell_volt_high = type('VH', (), {'value': 0.0})
        self.cell_temp_low = type('TL', (), {'value': 0.0})
        self.cell_temp_high = type('TH', (), {'value': 0.0})
        self.base_state = type('B', (), {'value': "Idle"})

        target = str(pack_id)
        for line in lines:
            p = line.split()
            # Deine US5000: Index 1 & 2. Volt=Index 1, SOC=Index 12
            if len(p) > 12 and p[0] == target and p[8] != "Absent":
                try:
                    self.volt.value = int(p[1]) / 1000.0
                    self.curr.value = int(p[2]) / 1000.0
                    self.temp.value = int(p[3]) / 1000.0
                    self.cell_temp_low.value = int(p[4]) / 1000.0
                    self.cell_temp_high.value = int(p[5]) / 1000.0
                    self.cell_volt_low.value = int(p[6]) / 1000.0
                    self.cell_volt_high.value = int(p[7]) / 1000.0
                    self.base_state.value = p[8]
                    # SOC steht in der 'pwr' Zeile an Index 12
                    self.soc.value = int(p[12].replace('%', '')) if '%' in p[12] else 0
                except: pass
                break

class StatCommand:
    def __init__(self, lines: tuple[str]):
        self.cycle_count = 0
        for line in lines:
            if "CYCLE Times" in line:
                try:
                    self.cycle_count = int(line.split(":")[-1].strip())
                except: pass

class InfoCommand:
    def __init__(self, lines: tuple[str]):
        self.module_barcode = type('B', (), {'value': "Unknown"})
        self.soft_version = type('V', (), {'value': "Unknown"})
        for line in lines:
            if "Barcode" in line: self.module_barcode.value = line.split(":")[-1].strip()
            if "Main Soft version" in line: self.soft_version.value = line.split(":")[-1].strip()
