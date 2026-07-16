"""Buttons for spice2x Arcade: per-card insert and screenshot."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import slugify

from . import SpiceConfigEntry
from .client import SpiceConnectionError
from .const import (
    CONF_CARD_NAME,
    CONF_CARD_NUMBER,
    CONF_CARD_PIN,
    CONF_CARDS,
    CONF_PIN_DELAY,
    DEFAULT_PIN_DELAY,
)
from .entity import SpiceEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SpiceConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the insert buttons (one per configured card) and screenshot."""
    client = entry.runtime_data.client
    entities: list[ButtonEntity] = [SpiceScreenshotButton(entry, client)]
    for card in entry.options.get(CONF_CARDS, []):
        entities.append(SpiceCardButton(entry, client, card))
    async_add_entities(entities)


class SpiceCardButton(SpiceEntity, ButtonEntity):
    """Insert a configured card on the currently selected side."""

    _attr_icon = "mdi:card-account-details"

    def __init__(self, entry: SpiceConfigEntry, client, card: dict) -> None:
        """Initialise the card button."""
        super().__init__(entry, client)
        self._card = card
        name = card[CONF_CARD_NAME]
        self._attr_name = f"Insert {name}"
        self._attr_unique_id = f"{entry.entry_id}_card_{slugify(name)}"

    async def async_press(self) -> None:
        """Insert the card and enter its PIN on the selected side."""
        pin_delay = int(
            self._entry.options.get(CONF_PIN_DELAY, DEFAULT_PIN_DELAY)
        )
        try:
            await self._client.async_insert_single(
                self._client.selected_side,
                self._card[CONF_CARD_NUMBER],
                self._card[CONF_CARD_PIN],
                pin_delay,
            )
        except SpiceConnectionError as err:
            raise HomeAssistantError(f"Failed to insert card: {err}") from err


class SpiceScreenshotButton(SpiceEntity, ButtonEntity):
    """Trigger a screenshot on the currently selected side."""

    _attr_translation_key = "screenshot"
    _attr_icon = "mdi:camera"

    def __init__(self, entry: SpiceConfigEntry, client) -> None:
        """Initialise the screenshot button."""
        super().__init__(entry, client)
        self._attr_unique_id = f"{entry.entry_id}_screenshot"

    async def async_press(self) -> None:
        """Trigger the screenshot."""
        try:
            await self._client.async_screenshot(self._client.selected_side)
        except SpiceConnectionError as err:
            raise HomeAssistantError(f"Failed to take screenshot: {err}") from err
