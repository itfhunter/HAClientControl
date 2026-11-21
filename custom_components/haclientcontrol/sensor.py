"""Sensor mit dem letzten vom PC gemeldeten Ergebnis."""
from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from . import HaccState
from .const import RESULT_STATUSES


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities([HaccLastResultSensor(entry.runtime_data)])


class HaccLastResultSensor(SensorEntity, RestoreEntity):
    """Zeigt den letzten gueltigen Status (auch accepted)."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_translation_key = "last_result"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = RESULT_STATUSES

    def __init__(self, state: HaccState) -> None:
        self._state = state
        self._attr_unique_id = f"{state.topic_base}_last_result"
        self._attr_device_info = state.device_info
        self._restored: dict[str, Any] | None = None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_state()
        if last is not None and last.state in RESULT_STATUSES:
            self._restored = {
                "status": last.state,
                "request_id": last.attributes.get("request_id"),
                "finished_at": last.attributes.get("finished_at"),
                "action": last.attributes.get("action"),
                "app_id": last.attributes.get("app_id"),
            }
        self.async_on_remove(self._state.add_listener(self._changed))

    @callback
    def _changed(self) -> None:
        self.async_write_ha_state()

    @property
    def _current(self) -> dict[str, Any] | None:
        return self._state.result or self._restored

    @property
    def available(self) -> bool:
        return self._state.online

    @property
    def native_value(self) -> str | None:
        cur = self._current
        return cur["status"] if cur else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        cur = self._current
        if not cur:
            return {}
        rid = cur.get("request_id")
        return {
            "request_id": rid,
            "finished_at": cur.get("finished_at"),
            "action": cur.get("action"),
            "app_id": cur.get("app_id"),
            "eigener_auftrag": bool(rid) and rid == self._state.last_sent_request_id,
        }
