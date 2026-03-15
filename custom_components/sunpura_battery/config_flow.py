"""Config flow for Sunpura Battery Control integration."""
from __future__ import annotations

import hashlib
import json
import logging
from urllib.parse import urlparse

from aiohttp import ClientError, ContentTypeError
from homeassistant import config_entries, exceptions
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import voluptuous as vol

from .const import (
    BASE_URL,
    CONF_POLL_INTERVAL_SECONDS,
    DEFAULT_POLL_INTERVAL_SECONDS,
    DOMAIN,
    MAX_POLL_INTERVAL_SECONDS,
    MIN_POLL_INTERVAL_SECONDS,
)

_LOGGER = logging.getLogger(__name__)
IOS_APP_VERSION = "1.260204.2"
IOS_USER_AGENT = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 18_7 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 "
    "Html5Plus/1.0 (Immersed/20) uni-app"
)
SUNPURA_PROJECT_TYPE = "14"
SUNPURA_INTERFACE_TYPE = "2"


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Sunpura Battery Control."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    def __init__(self):
        self.data = {}
        self.family = {}

    @staticmethod
    def async_get_options_flow(config_entry):
        return SunpuraOptionsFlow(config_entry)

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            try:
                username = user_input["username"].strip()
                password = user_input["password"]
                base_url = self._normalize_base_url(user_input.get("base_url", BASE_URL))
                poll_interval_seconds = int(
                    user_input.get(
                        CONF_POLL_INTERVAL_SECONDS,
                        DEFAULT_POLL_INTERVAL_SECONDS,
                    )
                )
                await self._login(username, password, base_url)
                self.data.update(
                    {
                        "username": username,
                        "password": password,
                        "base_url": base_url,
                        CONF_POLL_INTERVAL_SECONDS: poll_interval_seconds,
                    }
                )
                return await self.async_step_select_device()
            except InvalidAuth as err:
                _LOGGER.warning(f"Invalid authentication: {err}")
                errors["base"] = "invalid_auth"
            except CannotConnect as err:
                _LOGGER.error(f"Connection error: {err}")
                errors["base"] = "cannot_connect"
            except InvalidHost as err:
                _LOGGER.error(f"Invalid host: {err}")
                errors["base"] = "cannot_connect"
            except Exception as err:
                _LOGGER.exception(f"Unexpected login error: {err}")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required("username"): str,
                    vol.Required("password"): str,
                    vol.Optional("base_url", default=BASE_URL): str,
                    vol.Optional(
                        CONF_POLL_INTERVAL_SECONDS,
                        default=DEFAULT_POLL_INTERVAL_SECONDS,
                    ): vol.All(
                        vol.Coerce(int),
                        vol.Range(
                            min=MIN_POLL_INTERVAL_SECONDS,
                            max=MAX_POLL_INTERVAL_SECONDS,
                        ),
                    ),
                }
            ),
            errors=errors,
        )

    async def async_step_select_device(self, user_input=None):
        if user_input is not None:
            selected_device_id = user_input["family"]
            selected_device_name = self.family[selected_device_id]
            self.data.update(
                {
                    "selected_device_id": selected_device_id,
                    "selected_device_name": selected_device_name,
                }
            )
            return self.async_create_entry(
                title=f"Integration - {selected_device_name}",
                data=self.data,
            )

        try:
            self.family = await self._fetch_devices(self.data["base_url"])
        except CannotConnect as err:
            _LOGGER.error(f"Device fetch connection error: {err}")
            return self.async_abort(reason="cannot_connect")
        except Exception as err:
            _LOGGER.exception(f"Device fetch error: {err}")
            return self.async_abort(reason="unknown")

        return self.async_show_form(
            step_id="select_device",
            data_schema=vol.Schema(
                {
                    vol.Required("family"): vol.In(self.family),
                }
            ),
        )

    def md5_hash(self, password: str) -> str:
        """Return an MD5 hash for the given password."""
        hasher = hashlib.md5()
        hasher.update(password.encode("utf-8"))
        return hasher.hexdigest()

    @staticmethod
    def _login_field_variants() -> tuple[str, ...]:
        return ("email", "username", "userName", "account", "phone")

    @staticmethod
    def _normalize_base_url(value: str) -> str:
        base_url = (value or "").strip()
        if not base_url:
            return BASE_URL
        if "://" not in base_url:
            base_url = f"https://{base_url}"
        base_url = base_url.rstrip("/")
        parsed = urlparse(base_url)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise InvalidHost(f"Invalid API base URL: {value}")
        return base_url

    def _build_login_payloads(self, username: str, password: str) -> list[tuple[str, dict]]:
        hashed_password = self.md5_hash(password)
        client_variants = (
            {"phoneOs": "2", "phoneModel": "apple", "appVersion": IOS_APP_VERSION},
            {"phoneOs": 2, "phoneModel": "iPhone", "appVersion": "V1.1"},
            {"phoneOs": 1, "phoneModel": "1.1", "appVersion": "V1.1"},
        )
        payloads: list[tuple[str, dict]] = []
        seen_payloads: set[str] = set()
        for client in client_variants:
            phone_os = client["phoneOs"]
            for field_name in self._login_field_variants():
                for password_mode, password_value in (("md5", hashed_password), ("plain", password)):
                    payload = {field_name: username, "password": password_value, **client}
                    payload_key = json.dumps(payload, sort_keys=True)
                    if payload_key in seen_payloads:
                        continue
                    seen_payloads.add(payload_key)
                    payloads.append((f"os{phone_os}/{field_name}/{password_mode}", payload))
        return payloads

    def _build_common_headers(self) -> dict:
        language = "en-US"
        try:
            if hasattr(self.hass, "config") and hasattr(self.hass.config, "language"):
                lang = str(self.hass.config.language).lower()
                language = {
                    "de": "de-DE",
                    "en": "en-US",
                    "fr": "fr-FR",
                    "es": "es-ES",
                    "it": "it-IT",
                    "nl": "nl-NL",
                }.get(lang, "en-US")
        except Exception:
            pass

        return {
            "Accept": "*/*",
            "Accept-Language": language,
            "User-Agent": IOS_USER_AGENT,
            "interfacetype": SUNPURA_INTERFACE_TYPE,
            "appversion": IOS_APP_VERSION,
            "projecttype": SUNPURA_PROJECT_TYPE,
            "token": "<null>",
        }

    @staticmethod
    def _looks_like_connectivity_error(message: str) -> bool:
        if not message:
            return False
        lowered = message.lower()
        markers = (
            "timeout",
            "timed out",
            "network",
            "server",
            "gateway",
            "service",
            "connection",
            "connect",
            "系统",
            "服务",
            "连接",
        )
        return any(marker in lowered for marker in markers)

    async def _login(self, username: str, password: str, base_url: str) -> bool:
        url = f"{base_url}/user/login"
        session = async_get_clientsession(self.hass)
        headers = {
            **self._build_common_headers(),
            "Content-Type": "application/json;charset=UTF-8",
        }
        last_message = "Login failed"

        # Prime a session cookie (JSESSIONID) like the app does before POST login.
        try:
            async with session.get(url, headers=self._build_common_headers()) as resp:
                session.cookie_jar.update_cookies(resp.cookies)
        except ClientError:
            pass

        for variant_name, login_payload in self._build_login_payloads(username, password):
            payload = {}
            try:
                async with session.post(url, headers=headers, data=json.dumps(login_payload)) as resp:
                    if resp.status != 200:
                        raise CannotConnect(f"Login failed (HTTP {resp.status})")
                    session.cookie_jar.update_cookies(resp.cookies)
                    try:
                        payload = await resp.json()
                    except (json.JSONDecodeError, ContentTypeError) as err:
                        response_text = await resp.text()
                        raise CannotConnect(
                            f"Unexpected login response: {response_text[:120]}"
                        ) from err
            except ClientError as err:
                raise CannotConnect(f"HTTP error during login: {err}") from err

            if not isinstance(payload, dict):
                raise CannotConnect(f"Invalid login response format: {payload}")

            if payload.get("result") == 1:
                _LOGGER.info(f"Login succeeded with variant: {variant_name}")
                return True

            message = str(payload.get("msg", "Login failed"))
            result = payload.get("result")
            _LOGGER.debug(
                "Login attempt failed for variant %s (result=%s, msg=%s)",
                variant_name,
                result,
                message,
            )
            last_message = message
            if self._looks_like_connectivity_error(message):
                raise CannotConnect(message)

        raise InvalidAuth(last_message)

    async def _fetch_devices(self, base_url: str) -> dict:
        url = f"{base_url}/plant/getPlantVos"
        session = async_get_clientsession(self.hass)
        devices = {}

        try:
            async with session.get(url, headers=self._build_common_headers()) as resp:
                if resp.status != 200:
                    raise CannotConnect(f"Failed to fetch devices (HTTP {resp.status})")
                session.cookie_jar.update_cookies(resp.cookies)
                try:
                    devices = await resp.json()
                except (json.JSONDecodeError, ContentTypeError) as err:
                    response_text = await resp.text()
                    raise CannotConnect(
                        f"Unexpected device response: {response_text[:120]}"
                    ) from err
        except ClientError as err:
            raise CannotConnect(f"HTTP error while fetching devices: {err}") from err

        if not isinstance(devices, dict) or not isinstance(devices.get("obj"), list):
            raise CannotConnect(f"Invalid device response format: {devices}")

        return {
            str(item["id"]): item.get("plantName", str(item["id"]))
            for item in devices["obj"]
            if isinstance(item, dict) and "id" in item
        }


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(exceptions.HomeAssistantError):
    """Error to indicate there is invalid auth."""


class InvalidHost(exceptions.HomeAssistantError):
    """Error to indicate there is an invalid hostname."""


class SunpuraOptionsFlow(config_entries.OptionsFlow):
    """Handle options for Sunpura Battery Control."""

    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            poll_interval_seconds = int(
                user_input.get(
                    CONF_POLL_INTERVAL_SECONDS,
                    DEFAULT_POLL_INTERVAL_SECONDS,
                )
            )
            return self.async_create_entry(
                title="",
                data={CONF_POLL_INTERVAL_SECONDS: poll_interval_seconds},
            )

        current_poll_interval = int(
            self.config_entry.options.get(
                CONF_POLL_INTERVAL_SECONDS,
                self.config_entry.data.get(
                    CONF_POLL_INTERVAL_SECONDS,
                    DEFAULT_POLL_INTERVAL_SECONDS,
                ),
            )
        )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_POLL_INTERVAL_SECONDS,
                        default=current_poll_interval,
                    ): vol.All(
                        vol.Coerce(int),
                        vol.Range(
                            min=MIN_POLL_INTERVAL_SECONDS,
                            max=MAX_POLL_INTERVAL_SECONDS,
                        ),
                    ),
                }
            ),
        )
