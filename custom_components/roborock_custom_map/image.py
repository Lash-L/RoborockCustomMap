"""Support for Roborock image."""

from __future__ import annotations

from datetime import datetime
import io
import logging

from PIL import Image, UnidentifiedImageError
from roborock.devices.traits.v1.home import HomeTrait
from roborock.devices.traits.v1.map_content import MapContent

from homeassistant.components.image import ImageEntity
from homeassistant.components.roborock.coordinator import RoborockDataUpdateCoordinator
from homeassistant.components.roborock.entity import RoborockCoordinatedEntityV1
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import (
    CONF_MAP_ROTATION,
    DEFAULT_MAP_ROTATION,
    DOMAIN,
    MAP_ROTATION_OPTIONS,
    SIGNAL_ROTATION_CHANGED,
)

_LOGGER = logging.getLogger(__name__)

PARALLEL_UPDATES = 0


def _png_dimensions(data: bytes) -> tuple[int, int] | None:
    """Return PNG (width, height) from raw bytes, or None if not a PNG."""
    if len(data) < 24:
        return None
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    width = int.from_bytes(data[16:20], "big")
    height = int.from_bytes(data[20:24], "big")
    if width <= 0 or height <= 0:
        return None
    return (width, height)


def _rotate_point_map_xy(
    x: float, y: float, w: int, h: int, rotation: int
) -> tuple[float, float]:
    """Rotate a point in map pixel space around the image bounds.

    rotation is counter-clockwise (PIL Image.rotate does CCW).
    Uses continuous coordinates (w - x / h - y) to avoid off-by-one issues.
    """
    if rotation == 0:
        return (x, y)
    if rotation == 90:
        # CCW 90: new size (h, w)
        return (y, w - x)
    if rotation == 180:
        return (w - x, h - y)
    if rotation == 270:
        # CCW 270 == CW 90: new size (h, w)
        return (h - y, x)
    return (x, y)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Roborock image platform."""
    async_add_entities(
        RoborockMap(
            config_entry,
            f"{coord.duid_slug}_custom_map_{map_info.name or f'Map {map_info.map_flag}'}",
            coord,
            coord.properties_api.home,
            map_info.map_flag,
            map_info.name,
        )
        for coord in config_entry.runtime_data
        if coord.properties_api.home is not None
        for map_info in (coord.properties_api.home.home_map_info or {}).values()
    )


class RoborockMap(RoborockCoordinatedEntityV1, ImageEntity):
    """A class to let you visualize the map."""

    _attr_has_entity_name = True
    image_last_updated: datetime
    _attr_name: str

    def __init__(
        self,
        config_entry: ConfigEntry,
        unique_id: str,
        coordinator: RoborockDataUpdateCoordinator,
        home_trait: HomeTrait,
        map_flag: int,
        map_name: str,
    ) -> None:
        """Initialize a Roborock map."""
        RoborockCoordinatedEntityV1.__init__(self, unique_id, coordinator)
        ImageEntity.__init__(self, coordinator.hass)

        self.config_entry = config_entry
        self.map_flag = map_flag
        self._home_trait = home_trait

        if not map_name:
            map_name = f"Map {map_flag}"
        self._attr_name = f"{map_name}_custom"

        self.cached_map = b""
        self._raw_image_size: tuple[int, int] | None = None

        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def is_selected(self) -> bool:
        """Return if this map is the currently selected map."""
        return self.map_flag == self.coordinator.properties_api.maps.current_map

    @property
    def _map_content(self) -> MapContent | None:
        if self._home_trait.home_map_content and (
            map_content := self._home_trait.home_map_content.get(self.map_flag)
        ):
            return map_content
        return None

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass load any previously cached maps from disk."""
        await super().async_added_to_hass()

        self._attr_image_last_updated = self.coordinator.last_home_update

        # Listen for rotation changes from the Select entity
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{SIGNAL_ROTATION_CHANGED}_{self.config_entry.entry_id}_{self.map_flag}",
                self._handle_rotation_changed,
            )
        )

        self.async_write_ha_state()

    def _handle_rotation_changed(self) -> None:
        """Rotation changed; bump last_updated to bust the image cache."""
        self._attr_image_last_updated = dt_util.utcnow()
        self.async_write_ha_state()

    def _handle_coordinator_update(self) -> None:
        """Handle coordinator update."""
        if (map_content := self._map_content) is None:
            return

        if self.cached_map != map_content.image_content:
            self.cached_map = map_content.image_content
            self._raw_image_size = _png_dimensions(self.cached_map)
            self._attr_image_last_updated = self.coordinator.last_home_update

        super()._handle_coordinator_update()

    def _rotate_image(self, raw: bytes, rotation: int) -> bytes:
        """Rotate image in executor thread."""
        img = Image.open(io.BytesIO(raw))
        img = img.rotate(rotation, expand=True)

        out = io.BytesIO()
        img.save(out, format="PNG")
        return out.getvalue()

    def _get_rotation(self) -> int:
        """Get configured rotation for this map from hass.data (set by select entity)."""
        rotation = (
            self.hass.data.get(DOMAIN, {})
            .get(self.config_entry.entry_id, {})
            .get(CONF_MAP_ROTATION, {})
            .get(self.map_flag, DEFAULT_MAP_ROTATION)
        )

        if rotation not in MAP_ROTATION_OPTIONS:
            _LOGGER.debug(
                "Unsupported map rotation %s, allowed values: %s, falling back to %s",
                rotation,
                MAP_ROTATION_OPTIONS,
                DEFAULT_MAP_ROTATION,
            )
            return DEFAULT_MAP_ROTATION

        return rotation

    async def async_image(self) -> bytes | None:
        """Get the image (with optional rotation)."""
        if (map_content := self._map_content) is None:
            raise HomeAssistantError("Map flag not found in coordinator maps")

        raw = map_content.image_content
        rotation = self._get_rotation()

        if rotation == DEFAULT_MAP_ROTATION:
            return raw

        try:
            return await self.hass.async_add_executor_job(
                self._rotate_image, raw, rotation
            )
        except (OSError, UnidentifiedImageError) as err:
            _LOGGER.debug(
                "Failed to rotate Roborock map image: %s, returning original image",
                err,
            )
            return raw

    @property
    def extra_state_attributes(self):
        """Return extra attributes for map card usage (rotation-aware calibration)."""
        if (map_content := self._map_content) is None:
            raise HomeAssistantError("Map flag not found in coordinator maps")

        map_data = map_content.map_data
        if map_data is None:
            return {}

        # Attach room names (same behavior as before)
        if map_data.rooms is not None:
            for room in map_data.rooms.values():
                name = self._home_trait._rooms_trait.room_map.get(room.number)
                room.name = name.name if name else "Unknown"

        calibration = map_data.calibration()

        # Rotate ONLY the "map" (pixel-space) side of calibration points.
        # Rooms/zones are in vacuum coordinate space and are mapped via calibration.
        rotation = self._get_rotation()
        size = self._raw_image_size
        if rotation != DEFAULT_MAP_ROTATION and size is not None:
            w, h = size
            rotated_calibration = []
            for pt in calibration:
                mp = pt.get("map") or {}
                x = mp.get("x")
                y = mp.get("y")

                # If missing/invalid, keep point as-is
                if x is None or y is None:
                    rotated_calibration.append(pt)
                    continue

                nx, ny = _rotate_point_map_xy(float(x), float(y), w, h, rotation)

                new_pt = dict(pt)
                new_map = dict(mp)
                new_map["x"] = nx
                new_map["y"] = ny
                new_pt["map"] = new_map
                rotated_calibration.append(new_pt)

            calibration = rotated_calibration

        return {
            "calibration_points": calibration,
            "rooms": map_data.rooms,
            "zones": map_data.zones,
        }
