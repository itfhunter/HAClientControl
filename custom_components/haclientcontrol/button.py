"""Buttons zum Anmelden/Entsperren und zum Sperren des PCs."""
from __future__ import annotations

import asyncio
import json
import logging
import uuid

from homeassistant.components import mqtt
from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from . import HaccState, _text, parse_discovery_apps
from .const import REQUEST_TTL_SECONDS

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    state: HaccState = entry.runtime_data
    async_add_entities(
        [
            HaccLogonButton(state, "logon", "login_or_unlock"),
            HaccLogonButton(state, "lock", "lock"),
        ]
    )
    await _async_setup_app_buttons(hass, entry, state, async_add_entities)


async def _async_setup_app_buttons(
    hass: HomeAssistant,
    entry: ConfigEntry,
    state: HaccState,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Legt je freigegebener Anwendung einen Button an (Liste aus der MQTT-Discovery des Dienstes).

    Leere oder ungueltige Payload wird ignoriert (Abschalten der Discovery leert nichts). Ein Tombstone
    oder das Fehlen einer App in einer gueltigen Payload entfernt Entitaet und Registry-Eintrag.
    """
    buttons: dict[str, HaccAppButton] = {}
    lock = asyncio.Lock()
    prefix = f"{state.topic_base}_app_"

    async def discovery_received(msg: mqtt.ReceiveMessage) -> None:
        parsed = parse_discovery_apps(_text(msg.payload))
        if parsed is None:
            _LOGGER.debug("Leere oder ungueltige Discovery auf %s ignoriert", msg.topic)
            return
        apps, unclear = parsed
        async with lock:
            new: list[HaccAppButton] = []
            for app_id, name in apps.items():
                existing = buttons.get(app_id)
                if existing is not None:
                    existing.set_app_name(name)
                else:
                    button = HaccAppButton(state, app_id, name)
                    buttons[app_id] = button
                    new.append(button)
            if new:
                async_add_entities(new)
            # Entfernte Apps: laufende Entitaeten und (nach HA-Neustart) nur noch registrierte Eintraege.
            registry = er.async_get(hass)
            for app_id in [i for i in buttons if i not in apps and i not in unclear]:
                button = buttons.pop(app_id)
                if button.hass is not None:
                    await button.async_remove()
            for reg in er.async_entries_for_config_entry(registry, entry.entry_id):
                if reg.domain != "button" or not (reg.unique_id or "").startswith(prefix):
                    continue
                app_id = reg.unique_id[len(prefix):]
                if app_id in apps or app_id in unclear or app_id in buttons:
                    continue
                registry.async_remove(reg.entity_id)

    entry.async_on_unload(
        await mqtt.async_subscribe(hass, state.discovery_topic, discovery_received, qos=1)
    )


class HaccLogonButton(ButtonEntity):
    """Veroeffentlicht nur in async_press einen Auftrag (login_or_unlock oder lock)."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    _app_id: str | None = None

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
        body: dict[str, object] = {
            "version": 1,
            "request_id": request_id,
            "action": self._action,
        }
        if self._app_id is not None:
            body["app_id"] = self._app_id
        body["issued_at"] = dt_util.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        body["ttl_seconds"] = REQUEST_TTL_SECONDS
        payload = json.dumps(body, separators=(",", ":"))
        self._state.last_sent_request_id = request_id
        await mqtt.async_publish(
            self.hass, self._state.request_topic, payload, qos=1, retain=False
        )
        self._state.notify()


class HaccAppButton(HaccLogonButton):
    """Startet eine am PC freigegebene Anwendung (launch_app); nur in async_press wird veroeffentlicht."""

    _attr_translation_key = None

    def __init__(self, state: HaccState, app_id: str, name: str) -> None:
        super().__init__(state, f"app_{app_id}", "launch_app")
        self._attr_translation_key = None
        self._app_id = app_id
        self._attr_name = name

    @callback
    def set_app_name(self, name: str) -> None:
        """Umbenennen: unique_id und entity_id bleiben, nur der Anzeigename aendert sich."""
        if name == self._attr_name:
            return
        self._attr_name = name
        if self.hass is not None:
            self.async_write_ha_state()
