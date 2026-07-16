"""Base entity for the spice2x Arcade integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .client import SpiceClient
from .const import CONF_HOST, DOMAIN
from .coordinator import SpiceConnectivityCoordinator


class SpiceEntity(Entity):
    """Base class holding the shared device info for one spice host."""

    _attr_has_entity_name = True

    def __init__(self, entry: ConfigEntry, client: SpiceClient) -> None:
        """Initialise the entity for a config entry."""
        self._entry = entry
        self._client = client
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="spice2x",
            model="Arcade Machine",
            configuration_url=f"http://{entry.data[CONF_HOST]}",
        )


class SpiceCoordinatorEntity(CoordinatorEntity[SpiceConnectivityCoordinator], SpiceEntity):
    """Base class for entities backed by the connectivity coordinator."""

    def __init__(
        self,
        entry: ConfigEntry,
        client: SpiceClient,
        coordinator: SpiceConnectivityCoordinator,
    ) -> None:
        """Initialise both the coordinator and device-info mixins."""
        CoordinatorEntity.__init__(self, coordinator)
        SpiceEntity.__init__(self, entry, client)

