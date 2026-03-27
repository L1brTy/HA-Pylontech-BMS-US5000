"""The Pylontech US5000 (Waveshare Edition) integration."""
from __future__ import annotations
import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from .const import DOMAIN, PLATFORMS, ConnectionType
from .coordinator import PylontechUpdateCoordinator
from .models import DeviceInfo
from .protocol.tcp_console import TCPConsoleProtocol

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Pylontech from a config entry."""
    host = entry.data["host"]
    port = entry.data["port"]
    
    # Protokoll initialisieren
    protocol = TCPConsoleProtocol(host, port)
    
    # Dummy Device Info für den Start
    device_info = DeviceInfo(
        manufacturer="Pylontech",
        model="US5000",
        barcode=entry.data.get("barcode", "Unknown"),
        firmware_version="Unknown",
        connection_type=ConnectionType.TCP_CONSOLE,
        variant="Standard"
    )

    coordinator = PylontechUpdateCoordinator(hass, entry, protocol, device_info)
    
    # WICHTIG: Erst Sensoren suchen, dann starten
    await coordinator.detect_sensors()
    await coordinator.async_config_entry_first_refresh()

    # Den Koordinator richtig speichern (nicht als dict!)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
