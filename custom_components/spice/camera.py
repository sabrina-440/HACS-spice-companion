"""Screen-mirror camera for spice2x Arcade."""

from __future__ import annotations

import logging

from homeassistant.components.camera import Camera
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import SpiceConfigEntry
from .client import SpiceConnectionError
from .const import (
    CONF_SCREEN_DIVIDE,
    CONF_SCREEN_QUALITY,
    DEFAULT_SCREEN_DIVIDE,
    DEFAULT_SCREEN_QUALITY,
    DOMAIN,
)
from .entity import SpiceEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SpiceConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up one camera per available screen."""
    client = entry.runtime_data
    try:
        screens = await client.async_capture_screens()
    except SpiceConnectionError as err:
        # host may be offline at setup; fall back to a single screen
        _LOGGER.debug("Could not query screens (%s); defaulting to screen 0", err)
        screens = [0]
    if not screens:
        screens = [0]

    async_add_entities(
        SpiceScreenCamera(entry, client, int(screen), len(screens) > 1)
        for screen in screens
    )


class SpiceScreenCamera(SpiceEntity, Camera):
    """Live JPEG mirror of a spice2x screen."""

    _attr_icon = "mdi:monitor-screenshot"

    def __init__(
        self, entry: SpiceConfigEntry, client, screen: int, multi: bool
    ) -> None:
        """Initialise the camera for a screen."""
        SpiceEntity.__init__(self, entry, client)
        Camera.__init__(self)
        self._screen = screen
        self._attr_unique_id = f"{entry.entry_id}_screen_{screen}"
        self._attr_name = f"Screen {screen}" if multi else "Screen"

    @property
    def _quality(self) -> int:
        return int(self._entry.options.get(CONF_SCREEN_QUALITY, DEFAULT_SCREEN_QUALITY))

    @property
    def _divide(self) -> int:
        return int(self._entry.options.get(CONF_SCREEN_DIVIDE, DEFAULT_SCREEN_DIVIDE))

    async def async_camera_image(
        self, width: int | None = None, height: int | None = None
    ) -> bytes | None:
        """Return a single JPEG frame from the screen."""
        try:
            frame = await self._client.async_capture_jpg(
                self._screen, self._quality, self._divide
            )
        except SpiceConnectionError as err:
            _LOGGER.debug("Screen capture failed: %s", err)
            return None
        if frame is None:
            return None
        return frame["jpeg"]
