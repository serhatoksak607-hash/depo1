from app.ops_events import (
    EVENT_FLIGHT_CANCELLED,
    EVENT_FLIGHT_DELAYED,
    EVENT_NO_SHOW,
    EVENT_TRANSFER_UPDATED,
    detect_ops_events_from_text,
    normalize_event_types,
)


def test_detect_ops_events_from_text():
    text = "Flight delayed due to weather, booking updated by operations."
    events = detect_ops_events_from_text(text)
    assert EVENT_FLIGHT_DELAYED in events
    assert EVENT_TRANSFER_UPDATED in events


def test_detect_ops_events_cancelled_and_no_show():
    text = "Ucus iptal edildi. Passenger no-show oldu."
    events = detect_ops_events_from_text(text)
    assert EVENT_FLIGHT_CANCELLED in events
    assert EVENT_NO_SHOW in events


def test_normalize_event_types_filters_unknown():
    values = [
        EVENT_FLIGHT_DELAYED,
        "unknown",
        EVENT_FLIGHT_DELAYED,
        EVENT_TRANSFER_UPDATED,
    ]
    normalized = normalize_event_types(values)
    assert normalized == [EVENT_FLIGHT_DELAYED, EVENT_TRANSFER_UPDATED]
