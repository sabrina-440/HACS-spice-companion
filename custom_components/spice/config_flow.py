"""Config and options flow for spice2x Arcade."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PASSWORD, CONF_PORT
from homeassistant.core import callback
from homeassistant.helpers import selector

from .client import SpiceAuthError, SpiceClient, SpiceConnectionError
from .const import (
    CONF_CARD_NAME,
    CONF_CARD_NUMBER,
    CONF_CARD_PIN,
    CONF_CARDS,
    CONF_DOUBLE_STAGGER,
    CONF_PIN_DELAY,
    CONF_SCREEN_DIVIDE,
    CONF_SCREEN_QUALITY,
    DEFAULT_DOUBLE_STAGGER,
    DEFAULT_NAME,
    DEFAULT_PIN_DELAY,
    DEFAULT_PORT,
    DEFAULT_SCREEN_DIVIDE,
    DEFAULT_SCREEN_QUALITY,
    DOMAIN,
)


async def _validate(hass, host: str, port: int, password: str) -> None:
    """Try to connect to the host; raise on failure."""
    client = SpiceClient(hass, host, port, password)
    try:
        await client.async_test()
    finally:
        await client.async_close()


class SpiceConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the config flow for a spice2x host."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step (add a host)."""
        errors: dict[str, str] = {}
        if user_input is not None:
            host = user_input[CONF_HOST]
            port = user_input[CONF_PORT]
            await self.async_set_unique_id(f"{host}:{port}")
            self._abort_if_unique_id_configured()

            error = await self._async_try(host, port, user_input.get(CONF_PASSWORD, ""))
            if error:
                errors["base"] = error
            else:
                return self.async_create_entry(
                    title=user_input.get(CONF_NAME) or host,
                    data={
                        CONF_HOST: host,
                        CONF_PORT: port,
                        CONF_PASSWORD: user_input.get(CONF_PASSWORD, ""),
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST): str,
                    vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
                    vol.Optional(CONF_PASSWORD, default=""): str,
                    vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
                }
            ),
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Allow editing host / port / password of an existing entry."""
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            host = user_input[CONF_HOST]
            port = user_input[CONF_PORT]

            error = await self._async_try(host, port, user_input.get(CONF_PASSWORD, ""))
            if error:
                errors["base"] = error
            else:
                return self.async_update_reload_and_abort(
                    entry,
                    unique_id=f"{host}:{port}",
                    data={
                        CONF_HOST: host,
                        CONF_PORT: port,
                        CONF_PASSWORD: user_input.get(CONF_PASSWORD, ""),
                    },
                )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST, default=entry.data[CONF_HOST]): str,
                    vol.Required(CONF_PORT, default=entry.data[CONF_PORT]): int,
                    vol.Optional(
                        CONF_PASSWORD, default=entry.data.get(CONF_PASSWORD, "")
                    ): str,
                }
            ),
            errors=errors,
        )

    async def _async_try(self, host: str, port: int, password: str) -> str | None:
        """Return an error key if the connection fails, else None."""
        try:
            await _validate(self.hass, host, port, password)
        except SpiceAuthError:
            return "invalid_auth"
        except SpiceConnectionError:
            return "cannot_connect"
        except Exception:  # noqa: BLE001
            return "unknown"
        return None

    @staticmethod
    @callback
    def async_get_options_flow(config_entry) -> SpiceOptionsFlow:
        """Return the options flow handler."""
        return SpiceOptionsFlow()


class SpiceOptionsFlow(OptionsFlow):
    """Manage cards and behaviour tuning."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show the top-level options menu."""
        return self.async_show_menu(
            step_id="init",
            menu_options=["add_card", "remove_card", "settings"],
        )

    async def async_step_add_card(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Add a new card."""
        if user_input is not None:
            cards = list(self.config_entry.options.get(CONF_CARDS, []))
            cards.append(
                {
                    CONF_CARD_NAME: user_input[CONF_CARD_NAME],
                    CONF_CARD_NUMBER: user_input[CONF_CARD_NUMBER],
                    CONF_CARD_PIN: user_input[CONF_CARD_PIN],
                }
            )
            return self._save({CONF_CARDS: cards})

        return self.async_show_form(
            step_id="add_card",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_CARD_NAME): str,
                    vol.Required(CONF_CARD_NUMBER): str,
                    vol.Required(CONF_CARD_PIN): str,
                }
            ),
        )

    async def async_step_remove_card(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Remove one or more cards."""
        cards = list(self.config_entry.options.get(CONF_CARDS, []))
        names = [c[CONF_CARD_NAME] for c in cards]
        if not names:
            return self.async_abort(reason="no_cards")

        if user_input is not None:
            remove = set(user_input[CONF_CARDS])
            kept = [c for c in cards if c[CONF_CARD_NAME] not in remove]
            return self._save({CONF_CARDS: kept})

        return self.async_show_form(
            step_id="remove_card",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_CARDS): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=names,
                            multiple=True,
                            mode=selector.SelectSelectorMode.LIST,
                        )
                    )
                }
            ),
        )

    async def async_step_settings(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Edit behaviour tuning."""
        options = self.config_entry.options
        if user_input is not None:
            return self._save(user_input)

        return self.async_show_form(
            step_id="settings",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_PIN_DELAY,
                        default=options.get(CONF_PIN_DELAY, DEFAULT_PIN_DELAY),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=0, max=30, step=1, unit_of_measurement="s"
                        )
                    ),
                    vol.Required(
                        CONF_DOUBLE_STAGGER,
                        default=options.get(
                            CONF_DOUBLE_STAGGER, DEFAULT_DOUBLE_STAGGER
                        ),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=0, max=10, step=1, unit_of_measurement="s"
                        )
                    ),
                    vol.Required(
                        CONF_SCREEN_QUALITY,
                        default=options.get(
                            CONF_SCREEN_QUALITY, DEFAULT_SCREEN_QUALITY
                        ),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(min=1, max=100, step=1)
                    ),
                    vol.Required(
                        CONF_SCREEN_DIVIDE,
                        default=options.get(
                            CONF_SCREEN_DIVIDE, DEFAULT_SCREEN_DIVIDE
                        ),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(min=1, max=16, step=1)
                    ),
                }
            ),
        )

    @callback
    def _save(self, updates: dict[str, Any]) -> ConfigFlowResult:
        """Merge updates into the current options and persist them."""
        options = {**self.config_entry.options, **updates}
        return self.async_create_entry(title="", data=options)
