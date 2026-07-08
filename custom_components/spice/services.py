"""Full-API services for spice2x Arcade."""

from __future__ import annotations

import voluptuous as vol

from homeassistant.const import ATTR_DEVICE_ID
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv, device_registry as dr

from .client import SpiceClient, SpiceConnectionError
from .const import (
    ATTR_ACTION,
    ATTR_AMOUNT,
    ATTR_BUTTONS,
    ATTR_CARD_NUMBER,
    ATTR_CARD_NUMBER2,
    ATTR_IDS,
    ATTR_LIGHTS,
    ATTR_PIN,
    ATTR_PIN2,
    ATTR_PIN_DELAY,
    ATTR_POINTS,
    ATTR_SIDE,
    ATTR_STAGGER,
    ATTR_TEXT,
    ATTR_VALUES,
    CONTROL_ACTIONS,
    DEFAULT_DOUBLE_STAGGER,
    DEFAULT_PIN_DELAY,
    DOMAIN,
    SERVICE_BUTTON_PRESS,
    SERVICE_COIN_INSERT,
    SERVICE_CONTROL,
    SERVICE_IIDX_TICKER,
    SERVICE_INSERT_CARD,
    SERVICE_INSERT_DOUBLE,
    SERVICE_KEYPAD_WRITE,
    SERVICE_LIGHTS_WRITE,
    SERVICE_SCREENSHOT,
    SERVICE_TOUCH,
    SERVICE_TOUCH_RESET,
    SIDES,
)

_TARGET = {vol.Required(ATTR_DEVICE_ID): vol.All(cv.ensure_list, [cv.string])}
_SIDE = vol.All(vol.Coerce(int), vol.In(SIDES))

_SCHEMAS = {
    SERVICE_INSERT_CARD: vol.Schema(
        {
            **_TARGET,
            vol.Required(ATTR_CARD_NUMBER): cv.string,
            vol.Required(ATTR_PIN): cv.string,
            vol.Required(ATTR_SIDE): _SIDE,
            vol.Optional(ATTR_PIN_DELAY, default=DEFAULT_PIN_DELAY): vol.Coerce(int),
        }
    ),
    SERVICE_INSERT_DOUBLE: vol.Schema(
        {
            **_TARGET,
            vol.Required(ATTR_CARD_NUMBER): cv.string,
            vol.Required(ATTR_PIN): cv.string,
            vol.Required(ATTR_CARD_NUMBER2): cv.string,
            vol.Required(ATTR_PIN2): cv.string,
            vol.Required(ATTR_SIDE): _SIDE,
            vol.Optional(ATTR_PIN_DELAY, default=DEFAULT_PIN_DELAY): vol.Coerce(int),
            vol.Optional(ATTR_STAGGER, default=DEFAULT_DOUBLE_STAGGER): vol.Coerce(int),
        }
    ),
    SERVICE_KEYPAD_WRITE: vol.Schema(
        {**_TARGET, vol.Required(ATTR_SIDE): _SIDE, vol.Required(ATTR_VALUES): cv.string}
    ),
    SERVICE_SCREENSHOT: vol.Schema({**_TARGET, vol.Required(ATTR_SIDE): _SIDE}),
    SERVICE_BUTTON_PRESS: vol.Schema(
        {**_TARGET, vol.Required(ATTR_BUTTONS): list}
    ),
    SERVICE_LIGHTS_WRITE: vol.Schema({**_TARGET, vol.Required(ATTR_LIGHTS): list}),
    SERVICE_COIN_INSERT: vol.Schema(
        {**_TARGET, vol.Optional(ATTR_AMOUNT, default=1): vol.Coerce(int)}
    ),
    SERVICE_TOUCH: vol.Schema({**_TARGET, vol.Required(ATTR_POINTS): list}),
    SERVICE_TOUCH_RESET: vol.Schema({**_TARGET, vol.Required(ATTR_IDS): list}),
    SERVICE_CONTROL: vol.Schema(
        {**_TARGET, vol.Required(ATTR_ACTION): vol.In(CONTROL_ACTIONS)}
    ),
    SERVICE_IIDX_TICKER: vol.Schema({**_TARGET, vol.Required(ATTR_TEXT): cv.string}),
}


def _clients(hass: HomeAssistant, call: ServiceCall) -> list[SpiceClient]:
    """Resolve targeted devices to their SpiceClient instances."""
    dev_reg = dr.async_get(hass)
    entries = hass.data.get(DOMAIN, {})
    found: list[SpiceClient] = []
    for device_id in call.data.get(ATTR_DEVICE_ID, []):
        device = dev_reg.async_get(device_id)
        if device is None:
            continue
        for entry_id in device.config_entries:
            if entry_id in entries and entries[entry_id] not in found:
                found.append(entries[entry_id])
    if not found:
        raise HomeAssistantError("No spice2x machine was targeted.")
    return found


async def _dispatch(hass: HomeAssistant, call: ServiceCall) -> None:
    """Run the service against every targeted client."""
    data = call.data
    for client in _clients(hass, call):
        try:
            await _run_one(client, call.service, data)
        except SpiceConnectionError as err:
            raise HomeAssistantError(f"spice2x request failed: {err}") from err


async def _run_one(client: SpiceClient, service: str, data: dict) -> None:
    """Execute a single service call on one client."""
    if service == SERVICE_INSERT_CARD:
        await client.async_insert_single(
            data[ATTR_SIDE], data[ATTR_CARD_NUMBER], data[ATTR_PIN], data[ATTR_PIN_DELAY]
        )
    elif service == SERVICE_INSERT_DOUBLE:
        await client.async_insert_double(
            data[ATTR_SIDE],
            data[ATTR_CARD_NUMBER],
            data[ATTR_PIN],
            data[ATTR_CARD_NUMBER2],
            data[ATTR_PIN2],
            data[ATTR_PIN_DELAY],
            data[ATTR_STAGGER],
        )
    elif service == SERVICE_KEYPAD_WRITE:
        await client.async_keypad_write(data[ATTR_SIDE], data[ATTR_VALUES])
    elif service == SERVICE_SCREENSHOT:
        await client.async_screenshot(data[ATTR_SIDE])
    elif service == SERVICE_BUTTON_PRESS:
        await client.async_buttons_write(data[ATTR_BUTTONS])
    elif service == SERVICE_LIGHTS_WRITE:
        await client.async_lights_write(data[ATTR_LIGHTS])
    elif service == SERVICE_COIN_INSERT:
        await client.async_coin_insert(data[ATTR_AMOUNT])
    elif service == SERVICE_TOUCH:
        await client.async_touch_write(data[ATTR_POINTS])
    elif service == SERVICE_TOUCH_RESET:
        await client.async_touch_reset(data[ATTR_IDS])
    elif service == SERVICE_CONTROL:
        await client.async_control(data[ATTR_ACTION])
    elif service == SERVICE_IIDX_TICKER:
        await client.async_iidx_ticker_set(data[ATTR_TEXT])


@callback
def async_setup_services(hass: HomeAssistant) -> None:
    """Register all services once."""

    async def handler(call: ServiceCall) -> None:
        await _dispatch(hass, call)

    for service, schema in _SCHEMAS.items():
        if not hass.services.has_service(DOMAIN, service):
            hass.services.async_register(DOMAIN, service, handler, schema=schema)


@callback
def async_unload_services(hass: HomeAssistant) -> None:
    """Remove all services."""
    for service in _SCHEMAS:
        hass.services.async_remove(DOMAIN, service)
