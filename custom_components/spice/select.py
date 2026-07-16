"""Player-side selector for spice2x Arcade."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from . import SpiceConfigEntry
from .const import SIDE_LABELS, SIDE_P1, SIDES
from .entity import SpiceEntity

_LABEL_TO_SIDE = {label: side for side, label in SIDE_LABELS.items()}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SpiceConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the card-side selector."""
    async_add_entities([SpiceCardSideSelect(entry, entry.runtime_data.client)])


class SpiceCardSideSelect(SpiceEntity, SelectEntity, RestoreEntity):
    """Selects which player side card inserts and screenshots target."""

    _attr_translation_key = "card_side"
    _attr_icon = "mdi:account-switch"
    _attr_options = [SIDE_LABELS[side] for side in SIDES]

    def __init__(self, entry: SpiceConfigEntry, client) -> None:
        """Initialise the selector."""
        super().__init__(entry, client)
        self._attr_unique_id = f"{entry.entry_id}_side"
        self._attr_current_option = SIDE_LABELS[SIDE_P1]

    async def async_added_to_hass(self) -> None:
        """Restore the previously selected side."""
        await super().async_added_to_hass()
        last = await self.async_get_last_state()
        if last is not None and last.state in _LABEL_TO_SIDE:
            self._attr_current_option = last.state
            self._client.selected_side = _LABEL_TO_SIDE[last.state]

    async def async_select_option(self, option: str) -> None:
        """Change the selected side."""
        self._attr_current_option = option
        self._client.selected_side = _LABEL_TO_SIDE[option]
        self.async_write_ha_state()
