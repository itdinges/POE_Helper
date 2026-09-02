from __future__ import annotations

import json
import logging
import os
import random
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote

import requests

from app.market import MarketClient


POE_OAUTH_TOKEN_URL = "https://www.pathofexile.com/oauth/token"
POE_CX_API_BASE_URL = "https://api.pathofexile.com/currency-exchange"
SETTINGS_PATH = Path("config/settings.json")
log = logging.getLogger("poe-helper.oauth")


@dataclass
class OAuthToken:
    access_token: str
    expires_at_epoch: float | None


class OAuthTokenProvider:
    def __init__(
        self,
        *,
        client_id: str,
        client_secret: str,
        token_url: str = POE_OAUTH_TOKEN_URL,
        scope: str = "service:cxapi",
        timeout_seconds: int = 20,
        user_agent: str | None = None,
    ) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.token_url = token_url
        self.scope = scope
        self.timeout_seconds = timeout_seconds
        self.user_agent = user_agent
        self._cached_token: OAuthToken | None = None

    def get_access_token(self) -> str:
        now = time.time()
        if self._cached_token is not None:
            expires_at = self._cached_token.expires_at_epoch
            if expires_at is None or now < expires_at - 60:
                return self._cached_token.access_token

        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        if self.user_agent:
            headers["User-Agent"] = self.user_agent

        response = requests.post(
            self.token_url,
            data={
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "scope": self.scope,
            },
            headers=headers,
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("Unexpected OAuth token response format")

        access_token = payload.get("access_token")
        if not isinstance(access_token, str) or not access_token.strip():
            raise ValueError("OAuth token response missing access_token")

        expires_in_raw = payload.get("expires_in")
        expires_in = _to_float(expires_in_raw)
        expires_at_epoch = None if expires_in is None else (now + float(expires_in))
        self._cached_token = OAuthToken(access_token=access_token, expires_at_epoch=expires_at_epoch)
        return access_token


class OAuthCurrencyExchangeClient(MarketClient):
    def __init__(
        self,
        *,
        token_provider: OAuthTokenProvider,
        api_base_url: str = POE_CX_API_BASE_URL,
        realm: str = "poe2",
        timeout_seconds: int = 20,
        max_retries: int = 3,
        retry_base_seconds: float = 1.0,
        user_agent: str | None = None,
    ) -> None:
        super().__init__(base_url=api_base_url, timeout_seconds=timeout_seconds)
        self.token_provider = token_provider
        self.realm = realm
        self.max_retries = max(0, max_retries)
        self.retry_base_seconds = max(0.1, retry_base_seconds)
        self.user_agent = user_agent

    @classmethod
    def from_environment(cls) -> "OAuthCurrencyExchangeClient":
        settings = _load_oauth_settings()
        client_id = _setting_or_env("POE_CX_CLIENT_ID", settings.get("client_id", "")).strip()
        client_secret = _setting_or_env("POE_CX_CLIENT_SECRET", settings.get("client_secret", "")).strip()
        contact = _setting_or_env("POE_CX_USER_AGENT_CONTACT", settings.get("contact", "local-dev")).strip()
        app_id = _setting_or_env("POE_CX_APP_ID", settings.get("app_id", "poe-helper")).strip()
        app_version = _setting_or_env("POE_CX_APP_VERSION", settings.get("app_version", "0.1.0")).strip()
        token_url = _setting_or_env("POE_CX_TOKEN_URL", settings.get("token_url", POE_OAUTH_TOKEN_URL)).strip()
        api_base_url = _setting_or_env("POE_CX_API_BASE_URL", settings.get("api_base_url", POE_CX_API_BASE_URL)).strip()
        realm = _setting_or_env("POE_CX_REALM", settings.get("realm", "poe2")).strip()
        timeout = _parse_int_setting(_setting_or_env("POE_CX_TIMEOUT_SECONDS", settings.get("timeout_seconds", "20")), default=20)
        max_retries = _parse_int_setting(_setting_or_env("POE_CX_MAX_RETRIES", settings.get("max_retries", "3")), default=3)
        retry_base = _parse_float_setting(_setting_or_env("POE_CX_RETRY_BASE_SECONDS", settings.get("retry_base_seconds", "1.0")), default=1.0)
        user_agent = f"OAuth {app_id}/{app_version} (contact: {contact})"

        if not client_id or not client_secret:
            raise ValueError(
                "OAuth currency source requires confidential-client credentials. "
                "Set POE_CX_CLIENT_ID and POE_CX_CLIENT_SECRET (env or config/settings.json). "
                "Note: service:cxapi is intended for confidential-client token flow (/oauth/token client_credentials), "
                "not public-client authorization-only flows."
            )

        token_provider = OAuthTokenProvider(
            client_id=client_id,
            client_secret=client_secret,
            token_url=token_url,
            timeout_seconds=timeout,
            user_agent=user_agent,
        )
        return cls(
            token_provider=token_provider,
            api_base_url=api_base_url,
            realm=realm,
            timeout_seconds=timeout,
            max_retries=max_retries,
            retry_base_seconds=retry_base,
            user_agent=user_agent,
        )

    def fetch_overview(self, league: str, market_type: str) -> dict[str, Any]:
        if market_type.strip().lower() != "currency":
            raise ValueError("OAuth Currency Exchange source currently supports market type 'Currency' only")

        token = self.token_provider.get_access_token()
        endpoint = f"{self.base_url.rstrip('/')}/{self.realm}/{quote(league, safe='')}"
        headers = {"Authorization": f"Bearer {token}"}
        if self.user_agent:
            headers["User-Agent"] = self.user_agent

        return _request_json_with_retries(
            endpoint,
            headers=headers,
            timeout_seconds=self.timeout_seconds,
            max_retries=self.max_retries,
            retry_base_seconds=self.retry_base_seconds,
        )


def _request_json_with_retries(
    url: str,
    *,
    headers: dict[str, str] | None,
    timeout_seconds: int,
    max_retries: int,
    retry_base_seconds: float,
) -> dict[str, Any]:
    retry_statuses = {429, 500, 502, 503, 504}
    attempt = 0
    while True:
        response = requests.get(url, headers=headers, timeout=timeout_seconds)
        if response.status_code == 401:
            raise PermissionError("OAuth request unauthorized (401). Check token scope and credentials.")
        if response.status_code == 403:
            raise PermissionError("OAuth request forbidden (403). Check service:cxapi scope and account access.")

        if response.status_code in retry_statuses and attempt < max_retries:
            retry_after = _retry_after_seconds(response)
            backoff = retry_after if retry_after is not None else retry_base_seconds * (2**attempt)
            backoff += random.uniform(0.0, 0.25)
            log.warning(
                "Retrying OAuth Currency Exchange request",
                extra={
                    "url": url,
                    "attempt": attempt + 1,
                    "status_code": response.status_code,
                    "backoff_seconds": backoff,
                },
            )
            time.sleep(max(0.0, backoff))
            attempt += 1
            continue

        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("Unexpected market payload format: expected JSON object")
        return payload


def _retry_after_seconds(response: requests.Response) -> float | None:
    raw = response.headers.get("Retry-After")
    if not raw:
        return None

    numeric = _to_float(raw)
    if numeric is not None:
        return max(0.0, numeric)

    try:
        retry_time = parsedate_to_datetime(raw)
    except (TypeError, ValueError):
        return None
    delta = (retry_time - datetime.now(UTC)).total_seconds()
    return max(0.0, delta)


def _load_oauth_settings() -> dict[str, Any]:
    try:
        payload = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return {}
    if not isinstance(payload, dict):
        return {}

    oauth = payload.get("oauth")
    if not isinstance(oauth, dict):
        return {}
    return oauth


def _setting_or_env(env_key: str, fallback: Any) -> str:
    env_value = os.getenv(env_key)
    if isinstance(env_value, str) and env_value.strip():
        return env_value
    if fallback is None:
        return ""
    if isinstance(fallback, (int, float)):
        return str(fallback)
    if isinstance(fallback, str):
        return fallback
    return ""


def _parse_int_setting(value: str, *, default: int) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


def _parse_float_setting(value: str, *, default: float) -> float:
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return default


def _to_float(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        try:
            return float(stripped)
        except ValueError:
            return None
    return None
