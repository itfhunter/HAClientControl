"""Config Flow fuer HAClientControl."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

from .const import (
    CONF_DEVICE_NAME,
    CONF_TOPIC_BASE,
    DEFAULT_DEVICE_NAME,
    DEFAULT_TOPIC_BASE,
    DOMAIN,
)


def valid_topic_base(value: str) -> bool:
    """Ablehnen: leer, Wildcards, fuehrendes/abschliessendes '/', Steuerzeichen."""
    if not value or not value.strip():
        return False
    if "+" in value or "#" in value:
        return False
    if value.startswith("/") or value.endswith("/"):
        return False
    if any(ord(c) < 32 or ord(c) == 127 for c in value):
        return False
    return len(value.encode("utf-8")) <= 200


class HaccConfigFlow(ConfigFlow, domain=DOMAIN):
    """Einrichtung eines Windows-PCs."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            topic_base = user_input[CONF_TOPIC_BASE]
            name = user_input[CONF_DEVICE_NAME].strip()
            if not valid_topic_base(topic_base):
                errors[CONF_TOPIC_BASE] = "invalid_topic_base"
            elif not name:
                errors[CONF_DEVICE_NAME] = "invalid_name"
            else:
                await self.async_set_unique_id(topic_base)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=name,
                    data={CONF_TOPIC_BASE: topic_base, CONF_DEVICE_NAME: name},
                )
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_TOPIC_BASE,
                        default=(user_input or {}).get(
                            CONF_TOPIC_BASE, DEFAULT_TOPIC_BASE
                        ),
                    ): str,
                    vol.Required(
                        CONF_DEVICE_NAME,
                        default=(user_input or {}).get(
                            CONF_DEVICE_NAME, DEFAULT_DEVICE_NAME
                        ),
                    ): str,
                }
            ),
            errors=errors,
        )
