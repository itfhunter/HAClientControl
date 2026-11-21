"""Konstanten der Integration HAClientControl."""

DOMAIN = "haclientcontrol"

CONF_TOPIC_BASE = "topic_base"
CONF_DEVICE_NAME = "device_name"

DEFAULT_TOPIC_BASE = "windows/buero"
DEFAULT_DEVICE_NAME = "Windows-PC"

# Status laut docs/MQTT.md Abschnitt 1 (Ergebnis PC -> HA).
RESULT_STATUSES = [
    "accepted",
    "logged_in",
    "unlocked",
    "already_unlocked",
    "other_user_active",
    "authentication_failed",
    "interaction_required",
    "session_state_unknown",
    "not_enabled",
    "not_configured",
    "locked",
    "already_locked",
    "no_session",
    "app_started",
    "session_locked",
    "app_not_found",
    "app_start_failed",
    "busy",
    "outcome_unknown",
]

REQUEST_TTL_SECONDS = 15

RESULT_ACTIONS = ["login_or_unlock", "lock", "launch_app"]
