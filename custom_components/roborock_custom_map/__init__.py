"""Roborock Custom Map integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntryState
from homeassistant.exceptions import ConfigEntryNotReady

PLATFORMS = [Platform.IMAGE]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Roborock Custom map from a config entry."""
    roborock_entries = hass.config_entries.async_entries("roborock")
    coordinators = []

    async def unload_this_entry():
        await hass.config_entries.async_reload(entry.entry_id)

    for r_entry in roborock_entries:
        if r_entry.state == ConfigEntryState.LOADED:
            if hasattr(r_entry.runtime_data, "v1"):
                # Support for older versions of Roborock integration
                coordinators.extend(r_entry.runtime_data.v1)
            elif isinstance(r_entry.runtime_data, dict):
                # Support for newer versions where runtime_data is a dict of coordinators
                coordinators.extend(r_entry.runtime_data.values())
            else:
                # Fallback if runtime_data is the coordinator itself or something else
                # This depends on exact structure, but assuming dict or object
                # If it's a list (unlikely for typed runtime_data but possible)
                if isinstance(r_entry.runtime_data, list):
                    coordinators.extend(r_entry.runtime_data)
                # If it's something else, we can't safely extract coordinators.

            # If any unload, then we should reload as well in case there are major changes.
            r_entry.async_on_unload(unload_this_entry)
    if len(coordinators) == 0:
        raise ConfigEntryNotReady("No Roborock entries loaded. Cannot start.")
    entry.runtime_data = coordinators
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
