"""Connectivity binary sensor for spice2x Arcade."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import SpiceConfigEntry
from .entity import SpiceCoordinatorEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SpiceConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the connectivity sensor."""
    runtime_data = entry.runtime_data
    async_add_entities(
        [
            SpiceConnectivitySensor(
                entry, runtime_data.client, runtime_data.coordinator
            )
        ]
    )


class SpiceConnectivitySensor(SpiceCoordinatorEntity, BinarySensorEntity):
    """Reports whether the spice2x host is reachable."""

    _attr_translation_key = "connectivity"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    def __init__(self, entry, client, coordinator) -> None:
        """Initialise the connectivity sensor."""
        super().__init__(entry, client, coordinator)
        self._attr_unique_id = f"{entry.entry_id}_connectivity"

    @property
    def is_on(self) -> bool:
        """Return True if the last poll reached the host."""
        return bool(self.coordinator.data)

