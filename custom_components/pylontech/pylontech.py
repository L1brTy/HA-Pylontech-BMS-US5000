"""Parser for Pylontech US5000 Console Output."""
from __future__ import annotations

class BatValue:
    def __init__(self, line: str):
        # Index Volt Curr Temp BaseState V.State C.State T.State SOC Coulomb BAL
        # 0 3376 -396 10900 Dischg Normal Normal Normal 89% 84450 mAH N
        parts = line.split()
        self.cell_id = int(parts[0])
        self.volt = int(parts[1]) / 1000.0
        self.curr = int(parts[2]) / 1000.0
        self.tempr = int(parts[3]) / 1000.0
        self.base_state = parts[4]
        # SOC extrahieren (89% -> 89)
        self.soc = int(parts[8].replace('%', '')) if len(parts) > 8 and '%' in parts[8] else 0
        # Balancing (N oder Y)
        self.balance = parts[-1] if len(parts) > 10 else "N"

class BatCommand:
    def __init__(self, lines: tuple[str]):
        self.values = []
        for line in lines:
            if line and line[0].isdigit():
                try:
                    self.values.append(BatValue(line))
                except Exception:
                    continue

class PwrCommand:
    def __init__(self, lines: tuple[str], pack_id: int = 1):
        # Dummys initialisieren
        self.volt = type('V', (), {'value': 0.0})
        self.curr = type('C', (), {'value': 0.0})
        self.soc = type('S', (), {'value': 0})
        self.temp = type('T', (), {'value': 0.0})
        self.remain_cap = type('R', (), {'value': 0.0})
        self.base_state = type('B', (), {'value': "Idle"})
        self.cell_volt_low = type('VL', (), {'value': 0.0})
        self.cell_volt_high = type('VH', (), {'value': 0.0})
        self.cell_temp_low = type('TL', (), {'value': 0.0})
        self.cell_temp_high = type('TH', (), {'value': 0.0})
        self.error_code = type('E', (), {'value': 0})
        self.cycle_count = 0

        for line in lines:
            p = line.split()
            # Suche Zeile die mit der Pack-ID beginnt (0-basiert im Log)
            if len(p) > 9 and p[0].isdigit() and int(p[0]) == (pack_id - 1):
                self.volt.value = int(p[1]) / 1000.0
                self.curr.value = int(p[2]) / 1000.0
                self.temp.value = int(p[3]) / 1000.0
                self.base_state.value = p[4]
                self.soc.value = int(p[8].replace('%', '')) if '%' in p[8] else int(p[8])
                self.remain_cap.value = float(p[9])
                
                # Wenn das Log mehr Spalten hat, nimm Cycle Count und Min/Max
                if len(p) > 12:
                    self.cycle_count = int(p[12])

class InfoCommand:
    def __init__(self, lines: tuple[str]):
        self.module_barcode = type('B', (), {'value': "Unknown"})
        self.main_sw_version = type('V', (), {'value': "Unknown"})
        for line in lines:
            if "Module Barcode" in line: self.module_barcode.value = line.split(":")[-1].strip()
            if "Main Soft Version" in line: self.main_sw_version.value = line.split(":")[-1].strip()
