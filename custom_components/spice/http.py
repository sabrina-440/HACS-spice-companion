"""HTTP frame endpoint, websocket touch command, and frontend registration."""

from __future__ import annotations

import logging
import os

import voluptuous as vol
from aiohttp import web

from homeassistant.components import websocket_api
from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import HomeAssistantView, StaticPathConfig
from homeassistant.core import HomeAssistant, callback

from .client import SpiceConnectionError
from .const import (
    CONF_SCREEN_DIVIDE,
    CONF_SCREEN_QUALITY,
    DEFAULT_SCREEN_DIVIDE,
    DEFAULT_SCREEN_QUALITY,
    DOMAIN,
    FRONTEND_CARD_FILENAME,
    FRONTEND_CARD_URL,
    WS_TYPE_TOUCH,
)

_LOGGER = logging.getLogger(__name__)

_REGISTERED = f"{DOMAIN}_frontend_registered"


def _client(hass: HomeAssistant, entry_id: str):
    """Return the SpiceClient for an entry_id, or None."""
    return hass.data.get(DOMAIN, {}).get(entry_id)


class SpiceFrameView(HomeAssistantView):
    """Serve a single fresh JPEG frame from a machine's screen."""

    url = "/api/spice/{entry_id}/frame"
    name = "api:spice:frame"
    requires_auth = True

    async def get(self, request: web.Request, entry_id: str) -> web.Response:
        """Return one JPEG frame with width/height headers."""
        hass: HomeAssistant = request.app["hass"]
        client = _client(hass, entry_id)
        if client is None:
            return web.Response(status=404)

        entry = hass.config_entries.async_get_entry(entry_id)
        options = entry.options if entry else {}
        quality = int(
            request.query.get(
                "quality", options.get(CONF_SCREEN_QUALITY, DEFAULT_SCREEN_QUALITY)
            )
        )
        divide = int(
            request.query.get(
                "divide", options.get(CONF_SCREEN_DIVIDE, DEFAULT_SCREEN_DIVIDE)
            )
        )
        screen = int(request.query.get("screen", 0))

        try:
            frame = await client.async_capture_jpg(screen, quality, divide)
        except SpiceConnectionError as err:
            _LOGGER.debug("Frame capture failed: %s", err)
            return web.Response(status=502)
        if frame is None:
            return web.Response(status=502)

        return web.Response(
            body=frame["jpeg"],
            content_type="image/jpeg",
            headers={
                "X-Spice-Width": str(frame["width"]),
                "X-Spice-Height": str(frame["height"]),
                "Cache-Control": "no-store",
            },
        )


@websocket_api.websocket_command(
    {
        vol.Required("type"): WS_TYPE_TOUCH,
        vol.Required("entry_id"): str,
        vol.Required("action"): vol.In(["down", "move", "up"]),
        vol.Required("id"): int,
        vol.Optional("x"): int,
        vol.Optional("y"): int,
    }
)
@websocket_api.async_response
async def _ws_touch(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict
) -> None:
    """Forward a touch event from the Lovelace card to the machine."""
    client = _client(hass, msg["entry_id"])
    if client is None:
        connection.send_error(msg["id"], "not_found", "Unknown machine")
        return
    try:
        if msg["action"] == "up":
            await client.async_touch_reset([msg["id"]])
        else:
            await client.async_touch_write([[msg["id"], msg["x"], msg["y"]]])
    except SpiceConnectionError as err:
        connection.send_error(msg["id"], "spice_error", str(err))
        return
    connection.send_result(msg["id"], {"ok": True})


async def async_register_frontend(hass: HomeAssistant) -> None:
    """Register the frame view, touch command, and Lovelace card (once)."""
    if hass.data.get(_REGISTERED):
        return
    hass.data[_REGISTERED] = True

    hass.http.register_view(SpiceFrameView())
    websocket_api.async_register_command(hass, _ws_touch)

    card_path = os.path.join(
        os.path.dirname(__file__), "frontend", FRONTEND_CARD_FILENAME
    )
    await hass.http.async_register_static_paths(
        [StaticPathConfig(FRONTEND_CARD_URL, card_path, cache_headers=False)]
    )
    add_extra_js_url(hass, FRONTEND_CARD_URL)


@callback
def async_unregister_frontend(hass: HomeAssistant) -> None:
    """No-op: HTTP/websocket/frontend registrations live for the session."""
    return
