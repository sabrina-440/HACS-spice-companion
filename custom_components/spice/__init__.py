"""The spice2x Arcade integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .client import SpiceClient
from .const import CONF_HOST, CONF_PASSWORD, CONF_PORT, DOMAIN
from .http import async_register_frontend, async_unregister_frontend
from .services import async_setup_services, async_unload_services

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.BUTTON, Platform.CAMERA, Platform.SELECT]

type SpiceConfigEntry = ConfigEntry[SpiceClient]


async def async_setup_entry(hass: HomeAssistant, entry: SpiceConfigEntry) -> bool:
    """Set up spice2x Arcade from a config entry."""
    client = SpiceClient(
        hass,
        entry.data[CONF_HOST],
        entry.data[CONF_PORT],
        entry.data.get(CONF_PASSWORD, ""),
    )
    entry.runtime_data = client

    # per-entry client registry for service / websocket / http lookup by entry_id
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = client

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # reload the entry when options (cards / tuning) change
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))

    # domain-wide, register only once
    async_setup_services(hass)
    await async_register_frontend(hass)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: SpiceConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        await entry.runtime_data.async_close()
        hass.data[DOMAIN].pop(entry.entry_id, None)
        if not hass.data[DOMAIN]:
            async_unload_services(hass)
            async_unregister_frontend(hass)
    return unloaded


async def _async_reload_entry(hass: HomeAssistant, entry: SpiceConfigEntry) -> None:
    """Reload the config entry when its options change."""
    await hass.config_entries.async_reload(entry.entry_id)
