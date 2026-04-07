"""Config flow for Roborock Custom Map integration."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import OptionsFlowWithReload
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import (
    CONF_SHOW_BACKGROUND,
    CONF_SHOW_FLOOR,
    CONF_SHOW_ROOMS,
    CONF_SHOW_WALLS,
    DEFAULT_DRAWABLES,
    DOMAIN,
    DRAWABLES,
)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Roborock Custom Map."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        return self.async_create_entry(title="Roborock Custom Map", data={})

    @staticmethod
    @callback
    def async_get_options_flow(config_entry) -> RoborockCustomMapOptionsFlow:
        """Create the options flow."""
        return RoborockCustomMapOptionsFlow(config_entry)


class RoborockCustomMapOptionsFlow(OptionsFlowWithReload):
    """Handle options for Roborock Custom Map."""

    def __init__(self, config_entry) -> None:
        """Initialize options flow."""
        self.options = deepcopy(dict(config_entry.options))

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            self.options[CONF_SHOW_BACKGROUND] = user_input.pop(CONF_SHOW_BACKGROUND)
            self.options[CONF_SHOW_WALLS] = user_input.pop(CONF_SHOW_WALLS)
            self.options[CONF_SHOW_ROOMS] = user_input.pop(CONF_SHOW_ROOMS)
            self.options[CONF_SHOW_FLOOR] = user_input.pop(CONF_SHOW_FLOOR)
            self.options.setdefault(DRAWABLES, {}).update(user_input)
            return self.async_create_entry(title="", data=self.options)

        data_schema: dict = {}
        for drawable, default_value in DEFAULT_DRAWABLES.items():
            data_schema[
                vol.Required(
                    drawable.value,
                    default=self.config_entry.options.get(DRAWABLES, {}).get(
                        drawable.value, default_value
                    ),
                )
            ] = bool
        data_schema[
            vol.Required(
                CONF_SHOW_BACKGROUND,
                default=self.config_entry.options.get(CONF_SHOW_BACKGROUND, True),
            )
        ] = bool
        data_schema[
            vol.Required(
                CONF_SHOW_WALLS,
                default=self.config_entry.options.get(CONF_SHOW_WALLS, True),
            )
        ] = bool
        data_schema[
            vol.Required(
                CONF_SHOW_ROOMS,
                default=self.config_entry.options.get(CONF_SHOW_ROOMS, True),
            )
        ] = bool
        data_schema[
            vol.Required(
                CONF_SHOW_FLOOR,
                default=self.config_entry.options.get(CONF_SHOW_FLOOR, True),
            )
        ] = bool

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(data_schema),
        )
