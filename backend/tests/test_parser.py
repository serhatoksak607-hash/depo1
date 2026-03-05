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
    ANKARA/ESB ANTALYA/AYT TK 7022 T 23-03 23-03 0800 0905
    ANTALYA/AYT ANKARA/ESB TK 7023 B 27-03 27-03 0920 1025
    """
    result = parse_ticket_text(raw_text)

    parsed = result["parsed"]
    assert parsed["airline"] == "thy"
    assert parsed["flight_no"] == "TK7022"
    assert parsed["passenger_name"] == "SIMSEK ABDURRAHMAN"
    assert parsed["gender"] == "male"
    assert parsed["pnr"] == "S6UWP8"
    assert parsed["trip_type"] == "round_trip"
    assert parsed["segment_count"] == 2
    assert parsed["outbound_date"] is not None
    assert parsed["return_date"] is not None
    assert parsed["segments"][0]["from"] == "ESB"
    assert parsed["segments"][0]["to"] == "AYT"


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


def test_target_airport_classification_marks_outbound_and_return():
    raw_text = """
    TURKISH AIRLINES
    Yolcu ismi / Passenger Name : SIMSEK ABDURRAHMAN MR
    Rezervasyon No / Booking Ref : S6UWP8
    ANKARA/ESB ANTALYA/AYT TK 7022 T 23-03 23-03 0800 0905
    ANTALYA/AYT ANKARA/ESB TK 7023 B 27-03 27-03 0920 1025
    """
    result = parse_ticket_text(raw_text, target_airports="AYT")
    parsed = result["parsed"]

    assert parsed["target_airports"] == ["AYT"]
    assert parsed["trip_scope"] == "target_related"
    assert parsed["trip_type"] == "round_trip"
    assert parsed["from"] == "ESB"
    assert parsed["to"] == "AYT"
    assert parsed["segments"][0]["segment_role"] == "gidis"
    assert parsed["segments"][1]["segment_role"] == "donus"


def test_target_airport_classification_marks_transfer_when_target_not_in_route():
    raw_text = """
    TURKISH AIRLINES
    Yolcu ismi / Passenger Name : KUTLU BURAK MR
    Rezervasyon No / Booking Ref : UMTZ4G
    ANTALYA/AYT ANKARA/ESB TK 7035 B 26-03 26-03 2205 2310
    """
    result = parse_ticket_text(raw_text, target_airports="IST")
    parsed = result["parsed"]

    assert parsed["target_airports"] == ["IST", "SAW"]
    assert parsed["trip_scope"] == "transfer_only"
    assert parsed["has_transfer_segments"] is True
    assert parsed["trip_type"] == "connection"
    assert parsed["segments"][0]["segment_role"] == "aktarma"


def test_target_airport_classification_supports_return_only():
    raw_text = """
    TURKISH AIRLINES
    Yolcu ismi / Passenger Name : KUTLU BURAK MR
    Rezervasyon No / Booking Ref : UMTZ4G
    ANTALYA/AYT ANKARA/ESB TK 7035 B 26-03 26-03 2205 2310
    """
    result = parse_ticket_text(raw_text, target_airports="AYT")
    parsed = result["parsed"]

    assert parsed["trip_scope"] == "target_related"
    assert parsed["trip_type"] == "return_only"
    assert parsed["segments"][0]["segment_role"] == "donus"


def test_no_target_means_unclassified_segments():
    raw_text = """
    TURKISH AIRLINES
    Yolcu ismi / Passenger Name : SIMSEK ABDURRAHMAN MR
    Rezervasyon No / Booking Ref : S6UWP8
    ANKARA/ESB ANTALYA/AYT TK 7022 T 23-03 23-03 0800 0905
    ANTALYA/AYT ANKARA/ESB TK 7023 B 27-03 27-03 0920 1025
    """
    result = parse_ticket_text(raw_text)
    parsed = result["parsed"]

    assert parsed["target_airports"] is None
    assert parsed["trip_scope"] == "unclassified"
    assert parsed["segments"][0]["segment_role"] == "belirsiz"
    assert parsed["segments"][1]["segment_role"] == "belirsiz"


def test_pegasus_multisegment_target_classification():
    raw_text = """
    PEGASUS E-TICKET
    PASSENGER NAME: DEMO USER
    PNR AB12CD
    ISTANBUL/SAW ANTALYA/AYT PC 2210 B 23-03 23-03 0930 1040
    ANTALYA/AYT ISTANBUL/SAW PC 2211 B 27-03 27-03 1200 1310
    """
    result = parse_ticket_text(raw_text, target_airports="AYT")
    parsed = result["parsed"]

    assert parsed["airline"] == "pegasus"
    assert parsed["trip_type"] == "round_trip"
    assert parsed["segments"][0]["flight_no"] == "PC2210"
    assert parsed["segments"][0]["segment_role"] == "gidis"
    assert parsed["segments"][1]["flight_no"] == "PC2211"
    assert parsed["segments"][1]["segment_role"] == "donus"
