"""Support for Roborock map rotation select entities."""

from __future__ import annotations

import logging

from homeassistant.components.roborock.coordinator import RoborockDataUpdateCoordinator
from homeassistant.components.roborock.entity import RoborockCoordinatedEntityV1
from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import (
    CONF_MAP_ROTATION,
    DEFAULT_MAP_ROTATION,
    DOMAIN,
    MAP_ROTATION_OPTIONS,
    SIGNAL_ROTATION_CHANGED,
)

_LOGGER = logging.getLogger(__name__)

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up rotation Select entities (one per map)."""
    async_add_entities(
        RoborockMapRotationSelect(
            config_entry=config_entry,
            unique_id=f"{coord.duid_slug}_map_rotation_{map_info.map_flag}",
            coordinator=coord,
            map_flag=map_info.map_flag,
            map_name=map_info.name,
        )
        for coord in config_entry.runtime_data
        if coord.properties_api.home is not None
        for map_info in (coord.properties_api.home.home_map_info or {}).values()
    )


class RoborockMapRotationSelect(RoborockCoordinatedEntityV1, RestoreEntity, SelectEntity):
    """Select entity to control map rotation."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self,
        config_entry: ConfigEntry,
        unique_id: str,
        coordinator: RoborockDataUpdateCoordinator,
        map_flag: int,
        map_name: str,
    ) -> None:
        """Initialize rotation select."""
        RoborockCoordinatedEntityV1.__init__(self, unique_id, coordinator)

        self.config_entry = config_entry
        self.map_flag = map_flag

        if not map_name:
            map_name = f"Map {map_flag}"

        self._attr_name = f"{map_name} rotation"
        self._attr_options = [str(v) for v in MAP_ROTATION_OPTIONS]
        self._attr_current_option = str(DEFAULT_MAP_ROTATION)
        self._attr_translation_key = "rotation"

    async def async_added_to_hass(self) -> None:
        """Restore previous rotation setting and store in hass.data."""
        await super().async_added_to_hass()

        if (last := await self.async_get_last_state()) is not None:
            if last.state in self._attr_options:
                self._attr_current_option = last.state

        # Persist selection for the image entity to read
        self.hass.data[DOMAIN][self.config_entry.entry_id][CONF_MAP_ROTATION][
            self.map_flag
        ] = int(self._attr_current_option)

        self.async_write_ha_state()

    async def async_select_option(self, option: str) -> None:
        """Handle user selecting a rotation option."""
        if option not in self._attr_options:
            return

        self._attr_current_option = option

        self.hass.data[DOMAIN][self.config_entry.entry_id][CONF_MAP_ROTATION][
            self.map_flag
        ] = int(option)

        # Notify the image entity to bust the cache via image_last_updated bump
        async_dispatcher_send(
            self.hass,
            f"{SIGNAL_ROTATION_CHANGED}_{self.config_entry.entry_id}_{self.map_flag}",
        )

        self.async_write_ha_state()
