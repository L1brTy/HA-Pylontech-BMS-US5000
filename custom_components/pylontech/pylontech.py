class InfoCommand:
    """Pylontech BMS console command 'info' (US5000 Extended)."""

    def __init__(self, lines: tuple[str]) -> None:
        """Initialize the info command."""
        source = list(lines)
        # Wir legen alle Felder an, die die Integration erwartet, 
        # damit es keinen AttributeError gibt.
        self.device_address = Integer("Device address").fetch(source)
        self.manufacturer = Text("Manufacturer").fetch(source)
        self.device_name = Text("Device name").fetch(source)
        self.board_version = Text("Board version").fetch(source)
        self.sw_version = Text("Soft version").fetch(source, "Soft  version")
        self.main_sw_version = Text("Main Soft version").fetch(source)
        self.barcode = Text("Barcode").fetch(source)
        self.module_barcode = Text("Module Barcode").fetch(source)
        self.cell_number = Integer("Cell Number").fetch(source)
        
        # Falls module_barcode leer blieb, füllen wir es mit dem normalen Barcode
        if self.module_barcode.value is None or self.module_barcode.value == " ":
            self.module_barcode.value = self.barcode.value

    def __str__(self) -> str:
        """Return string representation of info command."""
        return f"Device: {self.device_name.value}, SN: {self.barcode.value}"
