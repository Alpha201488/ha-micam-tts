"""Config flow / options flow for Micam Web TTS."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .client import MicamAuthError, MicamClient, MicamError
from .const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_RATE,
    CONF_SSL,
    CONF_STREAM,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
    CONF_VOICE,
    DEFAULT_PORT,
    DEFAULT_RATE,
    DEFAULT_SSL,
    DEFAULT_VOICE,
    DEFAULT_VERIFY_SSL,
    DOMAIN,
    RATE_OPTIONS,
)

_LOGGER = logging.getLogger(__name__)


def _conn_schema(defaults: dict[str, Any] | None = None) -> vol.Schema:
    d = defaults or {}
    return vol.Schema(
        {
            vol.Required(CONF_HOST, default=d.get(CONF_HOST, "")): str,
            vol.Required(CONF_PORT, default=d.get(CONF_PORT, DEFAULT_PORT)): int,
            vol.Required(CONF_SSL, default=d.get(CONF_SSL, DEFAULT_SSL)): bool,
            vol.Required(
                CONF_VERIFY_SSL,
                default=d.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL),
            ): bool,
            vol.Required(CONF_USERNAME, default=d.get(CONF_USERNAME, "")): str,
            vol.Required(CONF_PASSWORD, default=d.get(CONF_PASSWORD, "")): str,
        }
    )


def _speech_schema(
    voices: list[dict[str, str]], defaults: dict[str, Any] | None = None
) -> vol.Schema:
    d = defaults or {}
    options = [
        SelectOptionDict(value=v["id"], label=f"{v.get('name', v['id'])}") for v in voices
    ]
    if not options:
        options = [SelectOptionDict(value=DEFAULT_VOICE, label="晓晓 · 女声（自然）")]
    return vol.Schema(
        {
            vol.Required(
                CONF_VOICE, default=d.get(CONF_VOICE, DEFAULT_VOICE)
            ): SelectSelector(
                SelectSelectorConfig(options=options, mode=SelectSelectorMode.DROPDOWN)
            ),
            vol.Required(CONF_RATE, default=d.get(CONF_RATE, DEFAULT_RATE)): SelectSelector(
                SelectSelectorConfig(options=RATE_OPTIONS, mode=SelectSelectorMode.DROPDOWN)
            ),
        }
    )


class MicamTtsConfigFlow(ConfigFlow, domain=DOMAIN):
    """Wizard: host/port/credentials, then voice and speed."""

    VERSION = 1

    def __init__(self) -> None:
        self._pending: dict[str, Any] = {}
        self._voices: list[dict[str, str]] = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        errors: dict[str, str] = {}
        if user_input is not None:
            client = MicamClient(
                async_get_clientsession(self.hass),
                user_input[CONF_HOST],
                user_input[CONF_PORT],
                user_input[CONF_SSL],
                user_input[CONF_VERIFY_SSL],
                user_input[CONF_USERNAME],
                user_input[CONF_PASSWORD],
            )
            try:
                info = await client.async_validate()
                self._voices = await client.async_voices()
            except MicamAuthError:
                errors["base"] = "invalid_auth"
            except MicamError as err:
                _LOGGER.warning("micam_tts validate failed: %s", err)
                errors["base"] = "cannot_connect"
            else:
                self._pending = dict(user_input)
                self._pending[CONF_STREAM] = info.get("stream", "cam_av")

                await self.async_set_unique_id(
                    f"{user_input[CONF_HOST]}:{user_input[CONF_PORT]}"
                )
                self._abort_if_unique_id_configured()

                if self._voices:
                    return await self.async_step_voice()
                return self._create_entry()

        return self.async_show_form(
            step_id="user",
            data_schema=_conn_schema(user_input),
            errors=errors,
        )

    async def async_step_voice(
        self, user_input: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        if user_input is not None:
            self._pending.update(user_input)
            return self._create_entry()
        return self.async_show_form(
            step_id="voice",
            data_schema=_speech_schema(self._voices),
        )

    def _create_entry(self) -> dict[str, Any]:
        data = dict(self._pending)
        data.setdefault(CONF_VOICE, DEFAULT_VOICE)
        data.setdefault(CONF_RATE, DEFAULT_RATE)
        title = f"Micam TTS ({data[CONF_HOST]}:{data[CONF_PORT]})"
        return self.async_create_entry(title=title, data=data)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return MicamTtsOptionsFlow()


class MicamTtsOptionsFlow(OptionsFlow):
    """Change the default voice / speed."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        entry = self.config_entry
        client = MicamClient(
            async_get_clientsession(self.hass),
            entry.data[CONF_HOST],
            entry.data[CONF_PORT],
            entry.data[CONF_SSL],
            entry.data.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL),
            entry.data[CONF_USERNAME],
            entry.data[CONF_PASSWORD],
        )
        voices: list[dict[str, str]] = []
        try:
            voices = await client.async_voices()
        except MicamError as err:
            _LOGGER.debug("options flow could not fetch voices: %s", err)

        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=_speech_schema(voices, {**entry.data, **entry.options}),
        )
