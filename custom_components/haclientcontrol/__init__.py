"""HAClientControl: Windows-Anmeldung/Entsperrung ueber den MQTT-Vertrag des Dienstes."""
from __future__ import annotations

import json
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from homeassistant.components import mqtt
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo

import re

from .const import CONF_DEVICE_NAME, CONF_TOPIC_BASE, DOMAIN, RESULT_ACTIONS, RESULT_STATUSES

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["button", "sensor"]


@dataclass
class HaccState:
    """Gemeinsamer Zustand eines Windows-PCs (nur im Speicher)."""

    topic_base: str
    device_name: str
    online: bool = False
    result: dict[str, Any] | None = None
    last_sent_request_id: str | None = None
    listeners: list[Callable[[], None]] = field(default_factory=list)
    unsubscribe: list[Callable[[], None]] = field(default_factory=list)

    @property
    def request_topic(self) -> str:
        return f"{self.topic_base}/logon/request"

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self.topic_base)},
            name=self.device_name,
            manufacturer="HAClientControl",
            model="Windows-Anmeldung",
        )

    @callback
    def notify(self) -> None:
        for listener in list(self.listeners):
            listener()

    @callback
    def add_listener(self, listener: Callable[[], None]) -> Callable[[], None]:
        self.listeners.append(listener)

        @callback
        def remove() -> None:
            if listener in self.listeners:
                self.listeners.remove(listener)

        return remove


def parse_result(payload: str) -> dict[str, Any] | None:
    """Nur gueltiges Ergebnis-JSON (version 1, bekannter status) uebernehmen."""
    try:
        data = json.loads(payload)
    except (TypeError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    version = data.get("version")
    if isinstance(version, bool) or version != 1:
        return None
    status = data.get("status")
    if not isinstance(status, str) or status not in RESULT_STATUSES:
        return None
    request_id = data.get("request_id")
    finished_at = data.get("finished_at")
    action = data.get("action")
    app_id = data.get("app_id")
    return {
        "status": status,
        "action": action if action in RESULT_ACTIONS else None,
        "app_id": app_id if isinstance(app_id, str) and re.fullmatch(r"[0-9a-f]{16}", app_id) else None,
        "request_id": request_id if isinstance(request_id, str) else None,
        "finished_at": finished_at if isinstance(finished_at, str) else None,
    }


def _text(payload: Any) -> str:
    if isinstance(payload, (bytes, bytearray)):
        return bytes(payload).decode("utf-8", "replace")
    return str(payload)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Richtet die Integration ein; veroeffentlicht dabei nie etwas."""
    await mqtt.async_wait_for_mqtt_client(hass)

    state = HaccState(
        topic_base=entry.data[CONF_TOPIC_BASE],
        device_name=entry.data[CONF_DEVICE_NAME],
    )

    @callback
    def availability_received(msg: mqtt.ReceiveMessage) -> None:
        online = _text(msg.payload) == "online"
        if online != state.online:
            state.online = online
            state.notify()

    @callback
    def result_received(msg: mqtt.ReceiveMessage) -> None:
        result = parse_result(_text(msg.payload))
        if result is None:
            _LOGGER.debug("Ungueltiges Ergebnis auf %s ignoriert", msg.topic)
            return
        state.result = result
        state.notify()

    state.unsubscribe.append(
        await mqtt.async_subscribe(
            hass, f"{state.topic_base}/availability", availability_received, qos=1
        )
    )
    state.unsubscribe.append(
        await mqtt.async_subscribe(
            hass, f"{state.topic_base}/logon/result", result_received, qos=1
        )
    )

    entry.runtime_data = state
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Entlaedt die Plattformen und beendet die Abos."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        state: HaccState = entry.runtime_data
        for unsub in state.unsubscribe:
            unsub()
        state.unsubscribe.clear()
        state.listeners.clear()
    return unloaded
