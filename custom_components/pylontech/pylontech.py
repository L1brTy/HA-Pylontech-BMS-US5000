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
            # Suche nach der Zeile des aktuellen Packs
            if chunks and chunks[0] == target_prefix and len(chunks) >= 13:
                self.volt.set(chunks[1])
                self.curr.set(chunks[2])
                self.temp.set(chunks[3])
                self.cell_temp_low.set(chunks[4])
                self.cell_temp_high.set(chunks[5])
                self.cell_volt_low.set(chunks[6])
                self.cell_bolt_high.set(chunks[7])
                self.base_state.set(chunks[8])
                # SOC Fix: Die Prozentzahl steht in Spalte 13 (Index 12)!
                self.soc.set(chunks[12] if len(chunks) > 12 else "0")
                self.error_code.set(chunks[27] if len(chunks) > 27 else "0")
                break

class BatValues:
    def __init__(self, line: str) -> None:
        chunks = line.split()
        # Header ausblenden, nur echte Zellzeilen (0-14) zulassen
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
