"""Buttons zum Anmelden/Entsperren und zum Sperren des PCs."""
from __future__ import annotations

import json
import uuid

from homeassistant.components import mqtt
from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from . import HaccState
from .const import REQUEST_TTL_SECONDS


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities(
        [
            HaccLogonButton(entry.runtime_data, "logon", "login_or_unlock"),
            HaccLogonButton(entry.runtime_data, "lock", "lock"),
        ]
    )


class HaccLogonButton(ButtonEntity):
    """Veroeffentlicht nur in async_press einen Auftrag (login_or_unlock oder lock)."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, state: HaccState, key: str, action: str) -> None:
        self._state = state
        self._action = action
        self._attr_translation_key = key
        self._attr_unique_id = f"{state.topic_base}_{key}"
        self._attr_device_info = state.device_info

    @property
    def available(self) -> bool:
        return self._state.online

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(self._state.add_listener(self._changed))

    @callback
    def _changed(self) -> None:
        self.async_write_ha_state()

    async def async_press(self) -> None:
        request_id = str(uuid.uuid4()).lower()
        payload = json.dumps(
            {
                "version": 1,
                "request_id": request_id,
                "action": self._action,
                "issued_at": dt_util.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                "ttl_seconds": REQUEST_TTL_SECONDS,
            },
            separators=(",", ":"),
        )
        self._state.last_sent_request_id = request_id
        await mqtt.async_publish(
            self.hass, self._state.request_topic, payload, qos=1, retain=False
        )
        self._state.notify()
