from typing import Iterable


EVENT_FLIGHT_DELAYED = "flight_delayed"
EVENT_FLIGHT_CANCELLED = "flight_cancelled"
EVENT_NO_SHOW = "no_show"
EVENT_TRANSFER_UPDATED = "transfer_updated"
EVENT_AUDIT_ACTION = "audit_action"

ALLOWED_OPS_EVENT_TYPES = {
    EVENT_FLIGHT_DELAYED,
    EVENT_FLIGHT_CANCELLED,
    EVENT_NO_SHOW,
    EVENT_TRANSFER_UPDATED,
    EVENT_AUDIT_ACTION,
}


def detect_ops_events_from_text(raw_text: str) -> set[str]:
    text = (raw_text or "").lower()
    events: set[str] = set()

    if any(token in text for token in ["flight delayed", "delay", "delayed", "rötar", "rotar"]):
        events.add(EVENT_FLIGHT_DELAYED)

    if any(token in text for token in ["flight cancelled", "cancelled", "canceled", "cancel", "iptal"]):
        events.add(EVENT_FLIGHT_CANCELLED)

    if any(token in text for token in ["no show", "no-show", "noshow", "gelmedi"]):
        events.add(EVENT_NO_SHOW)

    if any(
        token in text
        for token in ["transfer updated", "updated", "update", "değişiklik", "degisiklik", "changed"]
    ):
        events.add(EVENT_TRANSFER_UPDATED)

    return events


def normalize_event_types(values: Iterable[str]) -> list[str]:
    normalized = [value for value in values if value in ALLOWED_OPS_EVENT_TYPES]
    return sorted(set(normalized))
