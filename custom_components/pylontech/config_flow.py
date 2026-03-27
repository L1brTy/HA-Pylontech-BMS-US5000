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
        if user_input is not None:
            self.host = user_input["host"]
            self.port = user_input["port"]
            return await self.async_step_connection()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("host", default="10.10.10.200"): str,
                vol.Required("port", default=4196): int,
            })
        )

    async def async_step_connection(self, user_input=None):
        errors = {}
        if user_input is not None:
            protocol = TCPConsoleProtocol(self.host, self.port)
            try:
                await protocol.connect()
                info = await protocol.get_device_info()
                await protocol.disconnect()
                
                return self.async_create_entry(
                    title=f"US5000 Pack ({info.barcode})",
                    data={
                        "host": self.host,
                        "port": self.port,
                        "barcode": info.barcode
                    }
                )
            except Exception:
                errors["base"] = "cannot_connect"

        return self.async_show_form(step_id="connection", errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return PylontechOptionsFlowHandler(config_entry)

class PylontechOptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        # FIX: Home Assistant >= 2024.x erwartet das hier so:
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
