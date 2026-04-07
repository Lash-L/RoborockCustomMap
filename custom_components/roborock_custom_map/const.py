"""Constants for Roborock Custom Map integration."""

from vacuum_map_parser_base.config.drawable import Drawable

DOMAIN = "roborock_custom_map"

CONF_MAP_ROTATION = "map_rotation"
DEFAULT_MAP_ROTATION = 0
MAP_ROTATION_OPTIONS = (0, 90, 180, 270)

SIGNAL_ROTATION_CHANGED = "roborock_custom_map_rotation_changed"

CONF_SHOW_BACKGROUND = "show_background"
CONF_SHOW_WALLS = "show_walls"
CONF_SHOW_ROOMS = "show_rooms"
CONF_SHOW_FLOOR = "show_floor"
DRAWABLES = "drawables"

DEFAULT_DRAWABLES = {
    Drawable.CHARGER: True,
    Drawable.CLEANED_AREA: False,
    Drawable.GOTO_PATH: False,
    Drawable.IGNORED_OBSTACLES: False,
    Drawable.IGNORED_OBSTACLES_WITH_PHOTO: False,
    Drawable.MOP_PATH: False,
    Drawable.NO_CARPET_AREAS: False,
    Drawable.NO_GO_AREAS: False,
    Drawable.NO_MOPPING_AREAS: False,
    Drawable.OBSTACLES: False,
    Drawable.OBSTACLES_WITH_PHOTO: False,
    Drawable.PATH: True,
    Drawable.PREDICTED_PATH: False,
    Drawable.VACUUM_POSITION: True,
    Drawable.VIRTUAL_WALLS: False,
    Drawable.ZONES: False,
}
