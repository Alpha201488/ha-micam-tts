"""Tiny async client for the micam-web HTTP API."""

from __future__ import annotations

import asyncio
from typing import Any

import aiohttp

TIMEOUT = aiohttp.ClientTimeout(total=30)


class MicamError(Exception):
    """Raised when micam-web answers with an error."""


class MicamAuthError(MicamError):
    """Raised when credentials are rejected."""


class MicamClient:
    """Client for one micam-web instance."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        host: str,
        port: int,
        use_ssl: bool,
        verify_ssl: bool,
        username: str,
        password: str,
    ) -> None:
        self._session = session
        self._auth = aiohttp.BasicAuth(username, password)
        scheme = "https" if use_ssl else "http"
        self.base_url = f"{scheme}://{host}:{port}"
        self._ssl: bool | None = None if verify_ssl else False
        self.stream: str | None = None

    async def _request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        try:
            async with self._session.request(
                method,
                url,
                json=payload,
                auth=self._auth,
                timeout=TIMEOUT,
                ssl=self._ssl,
            ) as resp:
                if resp.status in (401, 403):
                    raise MicamAuthError("用户名或密码不对")
                text = await resp.text()
                if resp.status >= 400:
                    raise MicamError(f"HTTP {resp.status}: {text[:200]}")
                try:
                    return await resp.json(content_type=None)
                except ValueError:
                    return {"raw": text[:200]}
        except aiohttp.ClientError as err:
            raise MicamError(f"连不上 {self.base_url}: {err}") from err
        except asyncio.TimeoutError as err:
            raise MicamError(f"请求超时: {self.base_url}") from err

    async def async_validate(self) -> dict[str, Any]:
        """Cheap authenticated call used to verify host/port/credentials."""
        data = await self._request("GET", "/config")
        if "go2rtc" not in data and "stream" not in data:
            raise MicamError("这个地址不像 micam-web（/config 返回不对）")
        if isinstance(data.get("stream"), str):
            self.stream = data["stream"]
        return data

    async def async_voices(self) -> list[dict[str, str]]:
        """Return the voice shortlist exposed by the server."""
        data = await self._request("GET", "/tts/voices")
        if isinstance(data, list):
            return [v for v in data if isinstance(v, dict) and "id" in v]
        return []

    async def async_speak(self, text: str, voice: str, rate: str) -> dict[str, Any]:
        return await self._request(
            "POST", "/tts", {"text": text, "voice": voice, "rate": rate}
        )

    async def async_stop(self) -> None:
        """Ask the camera to end the current speaker session (0x108)."""
        from urllib.parse import quote

        stream = self.stream or "cam_av"
        await self._request(
            "GET",
            f"/g2r/api/xiaomi/command?src={quote(stream)}&cmd=0x108",
            None,
        )
