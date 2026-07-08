"""Async wrapper around the blocking spiceapi library.

The vendored ``spiceapi`` library uses blocking sockets and a stateful RC4
cipher, so a single :class:`Connection` is *not* safe for concurrent requests.
``SpiceClient`` owns one lazily-created connection per host and:

* serialises every request behind an :class:`asyncio.Lock` (cipher safety),
* runs every blocking call in the executor (never on the event loop),
* keeps multi-step login flows atomic behind a coarser flow lock,
* reconnects once on a dropped/expired connection before giving up.

The 7 second card warm-up and 1 second PIN stagger are awaited with
``asyncio.sleep`` *between* locked steps so executor threads are never held for
seconds at a time.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable

from homeassistant.core import HomeAssistant

from . import spiceapi
from .spiceapi.exceptions import APIError
from .const import (
    DEFAULT_DOUBLE_STAGGER,
    DEFAULT_PIN_DELAY,
    SCREENSHOT_KEYPAD_VALUE,
    SIDE_P1,
    SIDE_P2,
)

_LOGGER = logging.getLogger(__name__)


class SpiceConnectionError(Exception):
    """Raised when the spice host cannot be reached or returns an error."""


class SpiceAuthError(SpiceConnectionError):
    """Raised when the host rejects the request (e.g. wrong password)."""


def _other_side(side: int) -> int:
    """Return the opposite player side."""
    return SIDE_P2 if side == SIDE_P1 else SIDE_P1


class SpiceClient:
    """Manage a single connection to a spice2x host."""

    def __init__(
        self, hass: HomeAssistant, host: str, port: int, password: str
    ) -> None:
        """Initialise the client (does not connect yet)."""
        self._hass = hass
        self._host = host
        self._port = port
        self._password = password or ""
        self._con: spiceapi.Connection | None = None
        self._lock = asyncio.Lock()  # cipher/socket safety
        self._flow_lock = asyncio.Lock()  # whole-flow atomicity

        # currently selected player side, driven by the "Card side" select entity
        self.selected_side: int = SIDE_P1

    # -- connection management ------------------------------------------------

    def _connect(self) -> spiceapi.Connection:
        """Blocking: open a fresh connection. Runs in the executor."""
        return spiceapi.Connection(self._host, self._port, self._password)

    def _safe_close(self) -> None:
        """Blocking: close the connection, ignoring errors."""
        if self._con is not None:
            try:
                self._con.close()
            except Exception:  # noqa: BLE001 - best effort
                pass
            self._con = None

    async def _ensure_connected(self) -> None:
        """Open the connection if it isn't already established."""
        if self._con is not None:
            return
        try:
            self._con = await self._hass.async_add_executor_job(self._connect)
        except APIError as err:
            self._con = None
            raise SpiceAuthError(str(err)) from err
        except (OSError, RuntimeError) as err:
            self._con = None
            raise SpiceConnectionError(str(err)) from err

    async def _run(self, func: Callable[..., Any], *args: Any) -> Any:
        """Run a blocking spiceapi function with lock + one reconnect retry.

        ``func`` is called as ``func(connection, *args)`` in the executor.
        """
        async with self._lock:
            await self._ensure_connected()
            try:
                return await self._hass.async_add_executor_job(
                    func, self._con, *args
                )
            except APIError as err:
                raise SpiceAuthError(str(err)) from err
            except (OSError, RuntimeError) as err:
                # socket died / session expired - drop it and retry once
                _LOGGER.debug("spice request failed (%s); reconnecting", err)
                await self._hass.async_add_executor_job(self._safe_close)
                await self._ensure_connected()
                try:
                    return await self._hass.async_add_executor_job(
                        func, self._con, *args
                    )
                except APIError as err2:
                    raise SpiceAuthError(str(err2)) from err2
                except (OSError, RuntimeError) as err2:
                    await self._hass.async_add_executor_job(self._safe_close)
                    raise SpiceConnectionError(str(err2)) from err2

    async def async_close(self) -> None:
        """Close the connection."""
        async with self._lock:
            await self._hass.async_add_executor_job(self._safe_close)

    async def async_test(self) -> Any:
        """Validate the connection by fetching AVS info."""
        return await self._run(spiceapi.info_avs)

    # -- high level login flows ----------------------------------------------

    async def async_card_insert(self, side: int, card_number: str) -> None:
        """Insert a single card on the given side."""
        await self._run(spiceapi.card_insert, side, card_number)

    async def async_keypad_write(self, side: int, values: str) -> None:
        """Write keypad input (PIN / button presses) to a side."""
        await self._run(spiceapi.keypads_write, side, values)

    async def async_insert_single(
        self, side: int, card_number: str, pin: str, pin_delay: int = DEFAULT_PIN_DELAY
    ) -> None:
        """Insert one card and enter its PIN after the warm-up delay."""
        async with self._flow_lock:
            await self.async_card_insert(side, card_number)
            await asyncio.sleep(pin_delay)
            await self.async_keypad_write(side, pin)

    async def async_insert_double(
        self,
        side: int,
        card_number: str,
        pin: str,
        card_number2: str,
        pin2: str,
        pin_delay: int = DEFAULT_PIN_DELAY,
        stagger: int = DEFAULT_DOUBLE_STAGGER,
    ) -> None:
        """Insert two cards (both sides) and enter both PINs."""
        other = _other_side(side)
        async with self._flow_lock:
            await self.async_card_insert(side, card_number)
            await self.async_card_insert(other, card_number2)
            await asyncio.sleep(pin_delay)
            await self.async_keypad_write(other, pin2)
            await asyncio.sleep(stagger)
            await self.async_keypad_write(side, pin)

    async def async_screenshot(self, side: int) -> None:
        """Trigger a screenshot on the host for the given side."""
        await self.async_keypad_write(side, SCREENSHOT_KEYPAD_VALUE)

    # -- screen capture -------------------------------------------------------

    async def async_capture_screens(self) -> list:
        """Return the list of available screen IDs."""
        return await self._run(spiceapi.capture_get_screens)

    async def async_capture_jpg(
        self, screen: int = 0, quality: int = 60, divide: int = 1
    ) -> dict | None:
        """Grab a single JPEG frame from the given screen."""
        return await self._run(
            spiceapi.capture_get_jpg, screen, quality, divide
        )

    # -- touch ----------------------------------------------------------------

    async def async_touch_write(self, points: list) -> None:
        """Write touch points ``[[id, x, y], ...]``."""
        await self._run(spiceapi.touch_write, points)

    async def async_touch_reset(self, ids: list) -> None:
        """Lift the given touch IDs."""
        await self._run(spiceapi.touch_write_reset, ids)

    # -- full API passthroughs ------------------------------------------------

    async def async_buttons_write(self, states: list) -> None:
        """Write button states ``[[name, value], ...]``."""
        await self._run(spiceapi.buttons_write, states)

    async def async_lights_write(self, states: list) -> None:
        """Write light states ``[[name, value], ...]``."""
        await self._run(spiceapi.lights_write, states)

    async def async_coin_insert(self, amount: int = 1) -> None:
        """Insert coins."""
        await self._run(spiceapi.coin_insert, amount)

    async def async_iidx_ticker_set(self, text: str) -> None:
        """Set the IIDX ticker text."""
        await self._run(spiceapi.iidx_ticker_set, text)

    async def async_control(self, action: str) -> None:
        """Run a control action: restart / exit / shutdown / reboot."""
        func = {
            "restart": spiceapi.control_restart,
            "exit": spiceapi.control_exit,
            "shutdown": spiceapi.control_shutdown,
            "reboot": spiceapi.control_reboot,
        }[action]
        await self._run(func)
