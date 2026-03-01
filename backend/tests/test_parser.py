from app.parser import parse_ticket_text


def test_parse_ticket_text_extracts_thy_fields():
    raw_text = """
    THY BOARDING PASS
    PASSENGER: A*** B***
    FLIGHT TK2410
    ROUTE IST-ADB
    DATE 12 APR
    TIME 14:35
    PNR AB12CD
    """

    result = parse_ticket_text(raw_text)

    assert result["parsed"]["passenger_name"] == "A B"
    assert result["parsed"]["flight_no"] == "TK2410"
    assert result["parsed"]["from"] == "IST"
    assert result["parsed"]["to"] == "ADB"
    assert result["parsed"]["date"] == "12 APR"
    assert result["parsed"]["time"] == "14:35"
    assert result["parsed"]["pnr"] == "AB12CD"
    assert result["confidence"] >= 0.9
    assert result["needs_review"] is False


def test_parse_ticket_text_handles_ocr_noise():
    raw_text = """
    THY
    PASSENGER A*** B***
    TK 0907
    FROM IST TO AYT
    13/05/2026 07.20
    """

    result = parse_ticket_text(raw_text)

    assert result["parsed"]["flight_no"] == "TK0907"
    assert result["parsed"]["from"] == "IST"
    assert result["parsed"]["to"] == "AYT"
    assert result["parsed"]["date"] == "13/05/2026"
    assert result["parsed"]["time"] == "07:20"
    assert result["confidence"] >= 0.75
