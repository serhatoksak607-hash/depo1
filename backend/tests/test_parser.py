from app.parser import parse_ticket_text


def test_parse_ajet_ticket():
    raw_text = """
    AJET
    PASSENGER: A*** B***
    PNR: VF12AB
    FLIGHT VF3012
    ROUTE ESB-ADB
    DATE 13/05/2026
    TIME 07.20
    """
    result = parse_ticket_text(raw_text)

    parsed = result["parsed"]
    assert parsed["airline"] == "ajet"
    assert parsed["passenger_name"] == "A B"
    assert parsed["pnr"] == "VF12AB"
    assert parsed["flight_no"] == "VF3012"
    assert parsed["date"] == "2026-05-13"
    assert parsed["time"] == "07:20"
    assert parsed["from"] == "ESB"
    assert parsed["to"] == "ADB"
    assert result["needs_review"] is False


def test_parse_sunexpress_ticket():
    raw_text = """
    SUNEXPRESS E-TICKET
    NAME: C*** D***
    RESERVATION CODE ZX91QW
    FLIGHT XQ9591
    FROM ADB TO AYT
    24-06-2026 21:45
    """
    result = parse_ticket_text(raw_text)

    parsed = result["parsed"]
    assert parsed["airline"] == "sunexpress"
    assert parsed["flight_no"] == "XQ9591"
    assert parsed["date"] == "2026-06-24"
    assert parsed["time"] == "21:45"
    assert parsed["from"] == "ADB"
    assert parsed["to"] == "AYT"
    assert parsed["pnr"] == "ZX91QW"
    assert result["needs_review"] is False


def test_parse_pegasus_ticket():
    raw_text = """
    PEGASUS
    PASSENGER NAME: E*** F***
    PNR AB12CD
    FLIGHT PC2210
    ROUTE SAW-AYT
    DATE 03.07.2026
    TIME 09:30
    """
    result = parse_ticket_text(raw_text)

    parsed = result["parsed"]
    assert parsed["airline"] == "pegasus"
    assert parsed["flight_no"] == "PC2210"
    assert parsed["date"] == "2026-07-03"
    assert parsed["time"] == "09:30"
    assert parsed["from"] == "SAW"
    assert parsed["to"] == "AYT"
    assert result["needs_review"] is False


def test_parse_thy_ticket():
    raw_text = """
    TURKISH AIRLINES
    PASSENGER: G*** H***
    PNR TK45LM
    FLIGHT TK2410
    ROUTE IST-ADB
    DATE 12 APR 2026
    TIME 14:35
    """
    result = parse_ticket_text(raw_text)

    parsed = result["parsed"]
    assert parsed["airline"] == "thy"
    assert parsed["flight_no"] == "TK2410"
    assert parsed["date"] == "2026-04-12"
    assert parsed["time"] == "14:35"
    assert parsed["from"] == "IST"
    assert parsed["to"] == "ADB"
    assert result["needs_review"] is False


def test_needs_review_when_critical_field_missing():
    raw_text = """
    PEGASUS
    FLIGHT PC2210
    DATE 03.07.2026
    TIME 09:30
    """
    result = parse_ticket_text(raw_text)

    parsed = result["parsed"]
    assert parsed["airline"] == "pegasus"
    assert parsed["from"] is None
    assert parsed["to"] is None
    assert result["needs_review"] is True


def test_detect_thy_when_ticket_contains_anadolujet_leg():
    raw_text = """
    TURKISH AIRLINES
    THY Genel Mudurlugu
    ELEKTRONIK BILET YOLCU SEYAHAT BELGESI
    Yolcu ismi / Passenger Name : SIMSEK ABDURRAHMAN MR
    Bilet No / Ticket Number : 2352413550750
    Rezervasyon No / Booking Ref : S6UWP8
    ANADOLUJET
    TK 7022
    ANKARA/ESB - ANTALYA/AYT
    23-03 0800
    """
    result = parse_ticket_text(raw_text)

    parsed = result["parsed"]
    assert parsed["airline"] == "thy"
    assert parsed["flight_no"] == "TK7022"
    assert parsed["passenger_name"] == "SIMSEK ABDURRAHMAN"
    assert parsed["gender"] == "male"
    assert parsed["pnr"] == "S6UWP8"


def test_parse_pricing_fields():
    raw_text = """
    ODEME / PAYMENT : CASH
    Esas Ucret / Base Fare : TRY 850.98
    Vergi / Tax : 52.00YR 74.00VQ
    Toplam / Total : TRY 976.98
    """
    result = parse_ticket_text(raw_text)
    parsed = result["parsed"]

    assert parsed["payment_type"] == "CASH"
    assert parsed["currency"] == "TRY"
    assert parsed["base_fare"] == 850.98
    assert parsed["tax_total"] == 126.0
    assert parsed["tax_breakdown"] == {"YR": 52.0, "VQ": 74.0}
    assert parsed["total_amount"] == 976.98
