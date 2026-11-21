"""Micam Web TTS: let a Xiaomi camera speak through the micam-web bridge."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .client import MicamAuthError, MicamClient, MicamError
from .const import (
    ATTR_ENTRY_ID,
    ATTR_RATE,
    ATTR_TEXT,
    ATTR_VOICE,
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_RATE,
    CONF_SSL,
    CONF_STREAM,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
    CONF_VOICE,
    DEFAULT_RATE,
    DEFAULT_VERIFY_SSL,
    DOMAIN,
    MAX_TEXT_LEN,
    SERVICE_SPEAK,
    SERVICE_STOP,
)

_LOGGER = logging.getLogger(__name__)

SPEAK_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_TEXT): vol.All(str, vol.Length(min=1, max=MAX_TEXT_LEN)),
        vol.Optional(ATTR_VOICE): str,
        vol.Optional(ATTR_RATE): str,
        vol.Optional(ATTR_ENTRY_ID): str,
    }
)

STOP_SCHEMA = vol.Schema({vol.Optional(ATTR_ENTRY_ID): str})


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Store one client per config entry and register the services once."""
    client = MicamClient(
        async_get_clientsession(hass),
        entry.data[CONF_HOST],
        entry.data[CONF_PORT],
        entry.data[CONF_SSL],
        entry.data.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL),
        entry.data[CONF_USERNAME],
        entry.data[CONF_PASSWORD],
    )
    client.stream = entry.data.get(CONF_STREAM, "cam_av")

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = client

    def _pick(call: ServiceCall) -> tuple[MicamClient, ConfigEntry]:
        wanted = call.data.get(ATTR_ENTRY_ID)
        entries: dict[str, ConfigEntry] = {
            e.entry_id: e
            for e in hass.config_entries.async_entries(DOMAIN)
            if e.entry_id in hass.data.get(DOMAIN, {})
        }
        if wanted:
            if wanted not in hass.data.get(DOMAIN, {}):
                raise HomeAssistantError(f"没有这个 entry_id: {wanted}")
            return hass.data[DOMAIN][wanted], entries[wanted]
        if not hass.data.get(DOMAIN):
            raise HomeAssistantError("还没有配置任何 micam-web 实例")
        entry_id = next(iter(hass.data[DOMAIN]))
        return hass.data[DOMAIN][entry_id], entries[entry_id]

    async def _speak(call: ServiceCall) -> None:
        client_, config_entry = _pick(call)
        voice = call.data.get(ATTR_VOICE) or config_entry.data.get(
            CONF_VOICE, "zh-CN-XiaoxiaoNeural"
        )
        rate = call.data.get(ATTR_RATE) or config_entry.data.get(CONF_RATE, DEFAULT_RATE)
        try:
            result = await client_.async_speak(call.data[ATTR_TEXT], voice, rate)
        except MicamAuthError as err:
            raise HomeAssistantError(f"鉴权失败：{err}") from err
        except MicamError as err:
            raise HomeAssistantError(f"让摄像头说话失败：{err}") from err
        if isinstance(result, dict) and result.get("error"):
            raise HomeAssistantError(f"让摄像头说话失败：{result['error']}")
        _LOGGER.debug("micam_tts spoke: %s", result)

    async def _stop(call: ServiceCall) -> None:
        client_, _entry = _pick(call)
        try:
            await client_.async_stop()
        except MicamError as err:
            raise HomeAssistantError(f"停止播报失败：{err}") from err

    if not hass.services.has_service(DOMAIN, SERVICE_SPEAK):
        hass.services.async_register(DOMAIN, SERVICE_SPEAK, _speak, schema=SPEAK_SCHEMA)
    if not hass.services.has_service(DOMAIN, SERVICE_STOP):
        hass.services.async_register(DOMAIN, SERVICE_STOP, _stop, schema=STOP_SCHEMA)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    if not hass.data.get(DOMAIN):
        for service in (SERVICE_SPEAK, SERVICE_STOP):
            if hass.services.has_service(DOMAIN, service):
                hass.services.async_remove(DOMAIN, service)
        hass.data.pop(DOMAIN, None)
    return True
