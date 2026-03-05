from types import SimpleNamespace

from app.exporters import build_transfer_export_rows


def _base_transfer(**overrides):
    data = {
        "airline": "pegasus",
        "passenger_name": "SIMSEK ABDURRAHMAN",
        "pnr": "ABC123",
        "flight_no": "PC2012",
        "pickup_location": "ESB",
        "dropoff_location": "AYT",
        "flight_date": "2022-03-23",
        "flight_time": "08:00",
        "status": "unassigned",
        "payment_type": "CASH",
        "issue_date": "2022-02-09",
        "total_amount": 1000.0,
        "base_fare": 800.0,
        "tax_total": 200.0,
        "tax_breakdown": {"YR": 120.0, "VQ": 80.0},
        "raw_parse": {
            "segments": [
                {
                    "from": "ESB",
                    "to": "AYT",
                    "flight_no": "PC2012",
                    "departure_date": "2022-03-23",
                    "departure_time": "08:00",
                    "arrival_date": "2022-03-23",
                    "arrival_time": "09:05",
                    "segment_role": "gidis",
                },
                {
                    "from": "AYT",
                    "to": "ESB",
                    "flight_no": "PC2013",
                    "departure_date": "2022-03-27",
                    "departure_time": "09:20",
                    "arrival_date": "2022-03-27",
                    "arrival_time": "10:20",
                    "segment_role": "donus",
                },
            ]
        },
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def test_exporter_uses_all_segments_for_non_thy():
    transfer = _base_transfer()
    rows = build_transfer_export_rows(transfer, "sample.pdf")

    assert len(rows) == 2
    assert rows[0]["segment_type"] == "outbound"
    assert rows[1]["segment_type"] == "return"
    assert rows[0]["flight_no"] == "PC2012"
    assert rows[1]["flight_no"] == "PC2013"


def test_exporter_maps_transfer_role():
    transfer = _base_transfer(
        raw_parse={
            "segments": [
                {
                    "from": "AYT",
                    "to": "SAW",
                    "flight_no": "PC2017",
                    "departure_date": "2022-03-27",
                    "departure_time": "17:05",
                    "arrival_date": "2022-03-27",
                    "arrival_time": "18:20",
                    "segment_role": "donus",
                },
                {
                    "from": "SAW",
                    "to": "ECN",
                    "flight_no": "PC1924",
                    "departure_date": "2022-03-27",
                    "departure_time": "19:50",
                    "arrival_date": "2022-03-27",
                    "arrival_time": "21:20",
                    "segment_role": "aktarma",
                },
            ]
        },
    )
    rows = build_transfer_export_rows(transfer, "sample.pdf")

    assert len(rows) == 2
    assert rows[0]["segment_type"] == "return"
    assert rows[1]["segment_type"] == "transfer"
