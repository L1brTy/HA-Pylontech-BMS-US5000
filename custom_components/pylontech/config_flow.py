"""Config flow for Pylontech US5000 (Waveshare Edition)."""
from __future__ import annotations
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from .const import DOMAIN
from .protocol.tcp_console import TCPConsoleProtocol

class PylontechConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        
        # Sobald der User im ersten Fenster auf "Senden" klickt:
        if user_input is not None:
            host = user_input["host"]
            port = user_input["port"]
            
            # Verbindung sofort im Hintergrund testen
            protocol = TCPConsoleProtocol(host, port)
            try:
                await protocol.connect()
                info = await protocol.get_device_info()
                await protocol.disconnect()
                
                # Wenn erfolgreich: Integration sofort erstellen (kein 2. Fenster!)
                return self.async_create_entry(
                    title=f"US5000 Pack ({info.barcode})",
                    data={
                        "host": host,
                        "port": port,
                        "barcode": info.barcode
                    }
                )
            except Exception:
                # Nur wenn es fehlschlägt, bleiben wir im gleichen Fenster und zeigen einen Fehler
                errors["base"] = "cannot_connect"

        # Das ist das einzige Fenster, das der User jemals sieht:
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("host", default="10.10.10.200"): str,
                vol.Required("port", default=4196): int,
            }),
            errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return PylontechOptionsFlowHandler(config_entry)


class PylontechOptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional("device_name", default="US5000"): str,
            })
        )
