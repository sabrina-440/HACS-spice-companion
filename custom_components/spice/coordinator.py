"""Connectivity polling for spice2x Arcade."""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .client import SpiceClient, SpiceConnectionError
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class SpiceConnectivityCoordinator(DataUpdateCoordinator[bool]):
    """Polls the spice2x host and reports whether it is reachable."""

    def __init__(self, hass: HomeAssistant, client: SpiceClient, name: str) -> None:
        """Initialise the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{name}_connectivity",
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self._client = client

    async def _async_update_data(self) -> bool:
        """Return True if the host answered, False otherwise (never raises)."""
        try:
            await self._client.async_test()
        except SpiceConnectionError:
            return False
        return True

