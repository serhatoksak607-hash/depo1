import re
from datetime import datetime
from typing import Any


MONTH_MAP = {
    "JAN": 1,
    "FEB": 2,
    "MAR": 3,
    "APR": 4,
    "MAY": 5,
    "JUN": 6,
    "JUL": 7,
    "AUG": 8,
    "SEP": 9,
    "OCT": 10,
    "NOV": 11,
    "DEC": 12,
}

AIRLINE_CODE_PATTERNS = {
    "ajet": r"\bVF\s?\d{2,4}\b",
    "sunexpress": r"\bXQ\s?\d{2,4}\b",
    "pegasus": r"\bPC\s?\d{2,4}\b",
    "thy": r"\bTK\s?\d{2,4}\b",
}

MALE_TITLES = {"MR", "MISTER", "BAY", "ERKEK"}
FEMALE_TITLES = {"MS", "MRS", "MISS", "MIZ", "MRS.", "MS.", "BAYAN", "KADIN"}
GENERIC_NAME_TOKENS = {
    "PASSENGER NAME",
    "YOLCU ISMI",
    "YOLCU ISMI PASSENGER NAME",
    "ISMI PASSENGER NAME",
    "COMPANY NAME",
}
INVALID_AIRPORT_CODES = {"DAY", "MON", "NVB", "NVA", "CLS", "BAG", "CPN", "TKT"}


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _normalize_name(text: str | None) -> str | None:
    if not text:
        return None
    clean = re.sub(r"[^A-Z\s]", "", text.upper())
    clean = _normalize(clean)
    return clean or None


def _strip_name_titles(name_value: str | None) -> str | None:
    if not name_value:
        return None
    parts = [p for p in name_value.split(" ") if p]
    while parts and parts[-1] in MALE_TITLES.union(FEMALE_TITLES):
        parts.pop()
    return " ".join(parts) if parts else None


def _detect_gender_from_name_line(name_line: str | None) -> str | None:
    if not name_line:
        return None
    upper = name_line.upper()
    tokens = set(re.findall(r"[A-Z]+", upper))
    if tokens & MALE_TITLES:
        return "male"
    if tokens & FEMALE_TITLES:
        return "female"
    return None


def _normalize_date(date_text: str | None) -> str | None:
    if not date_text:
        return None

    value = date_text.strip().upper()

    numeric_match = re.search(r"(\d{1,2})[./-](\d{1,2})[./-](\d{2,4})", value)
    if numeric_match:
        day = int(numeric_match.group(1))
        month = int(numeric_match.group(2))
        year = int(numeric_match.group(3))
        if year < 100:
            year += 2000
        try:
            return datetime(year, month, day).strftime("%Y-%m-%d")
        except ValueError:
            return None

    text_match = re.search(r"(\d{1,2})\s*([A-Z]{3})(?:\s*(\d{4}))?", value)
    if text_match:
        day = int(text_match.group(1))
        month = MONTH_MAP.get(text_match.group(2))
        year = int(text_match.group(3)) if text_match.group(3) else datetime.utcnow().year
        if not month:
            return None
        try:
            return datetime(year, month, day).strftime("%Y-%m-%d")
        except ValueError:
            return None

    return None


def _normalize_time(time_text: str | None) -> str | None:
    if not time_text:
        return None
    match = re.search(r"([01]\d|2[0-3])[:.]([0-5]\d)", time_text)
    if not match:
        return None
    return f"{match.group(1)}:{match.group(2)}"


def _first_match(patterns: list[str], text: str) -> str | None:
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return match.group(1) if match.lastindex else match.group(0)
    return None


def _to_amount(value: str | None) -> float | None:
    if not value:
        return None
    normalized = value.strip()
    if "," in normalized and "." in normalized:
        if normalized.rfind(",") > normalized.rfind("."):
            normalized = normalized.replace(".", "").replace(",", ".")
        else:
            normalized = normalized.replace(",", "")
    elif "," in normalized:
        normalized = normalized.replace(",", ".")
    try:
        return round(float(normalized), 2)
    except ValueError:
        return None


def _extract_pricing_fields(raw_text: str) -> dict[str, Any]:
    upper = (raw_text or "").upper()

    payment_type = _first_match(
        [r"(?:PAYMENT|ODEME|ÖDEME)\s*[:]\s*([A-Z]+)"],
        upper,
    )

    base_fare_match = re.search(
        r"(?:BASE FARE|ESAS UCRET|ESAS ÜCRET)\s*[:]\s*([A-Z]{3})?\s*([0-9]+[.,][0-9]{2})",
        upper,
    )
    total_match = re.search(
        r"(?:TOTAL|TOPLAM)\s*[:]\s*([A-Z]{3})?\s*([0-9]+[.,][0-9]{2})",
        upper,
    )
    tax_line = _first_match([r"(?:TAX|VERGI|VERGİ)\s*[:]\s*([^\n\r]+)"], upper)

    currency = None
    if total_match and total_match.group(1):
        currency = total_match.group(1)
    elif base_fare_match and base_fare_match.group(1):
        currency = base_fare_match.group(1)

    base_fare = _to_amount(base_fare_match.group(2) if base_fare_match else None)
    total_amount = _to_amount(total_match.group(2) if total_match else None)

    tax_breakdown: dict[str, float] = {}
    tax_total = None
    if tax_line:
        pairs = re.findall(r"([0-9]+[.,][0-9]{2})\s*([A-Z]{2})", tax_line)
        for amount_raw, code in pairs:
            amount = _to_amount(amount_raw)
            if amount is not None:
                tax_breakdown[code] = amount
        if tax_breakdown:
            tax_total = round(sum(tax_breakdown.values()), 2)

    return {
        "payment_type": payment_type,
        "currency": currency,
        "total_amount": total_amount,
        "base_fare": base_fare,
        "tax_total": tax_total,
        "tax_breakdown": tax_breakdown or None,
    }


def detect_airline(raw_text: str) -> str:
    upper = (raw_text or "").upper()

    # THY e-ticket format often includes ANADOLUJET legs with TK flight numbers.
    if any(
        token in upper
        for token in [
            "TURKISH AIRLINES",
            "TURK HAVA YOLLARI",
            "THY GENEL MUDURLUGU",
            "THY GENEL MÜDÜRLÜĞÜ",
            "ELECTRONIC TICKET PASSENGER ITINERARY",
            "ELEKTRONIK BILET YOLCU SEYAHAT BELGESI",
            "ELEKTRONİK BİLET YOLCU SEYAHAT BELGESİ",
        ]
    ):
        return "thy"
    if "ANADOLUJET" in upper:
        # Legacy THY-issued AnadoluJet tickets are usually TK-coded.
        if re.search(r"\bTK\s?\d{2,4}\b", upper):
            return "thy"
        return "ajet"
    if any(token in upper for token in ["AJET", "A JET"]):
        return "ajet"
    if "SUNEXPRESS" in upper:
        return "sunexpress"
    if "PEGASUS" in upper:
        return "pegasus"

    first_hit = None
    for airline, pattern in AIRLINE_CODE_PATTERNS.items():
        match = re.search(pattern, upper)
        if not match:
            continue
        if first_hit is None or match.start() < first_hit[1]:
            first_hit = (airline, match.start())
    return first_hit[0] if first_hit else "unknown"


def _extract_common_fields(raw_text: str) -> dict[str, str | None]:
    upper = (raw_text or "").upper()
    lines = [line.strip().upper() for line in (raw_text or "").splitlines() if line.strip()]

    passenger_name = None
    passenger_gender = None
    for i, line in enumerate(lines):
        if not re.search(r"(PASSENGER NAME|YOLCU ISMI|YOLCU ADI|NAME)", line):
            continue

        candidates = []
        same_line = _first_match([r"(?:PASSENGER(?: NAME)?|NAME|YOLCU(?: ISMI| ADI)?)[:\s]+(.+)$"], line)
        if same_line:
            candidates.append(same_line)

        for step in (1, 2):
            if i + step >= len(lines):
                continue
            lookahead = lines[i + step].strip(": ").strip()
            if lookahead:
                candidates.append(lookahead)

        for candidate in candidates:
            clean_upper = _normalize(re.sub(r"[^A-Z\s]", " ", candidate))
            if not clean_upper:
                continue
            if clean_upper in GENERIC_NAME_TOKENS:
                continue
            passenger_name = _strip_name_titles(clean_upper)
            passenger_gender = _detect_gender_from_name_line(candidate)
            if passenger_name:
                break
        if passenger_name:
            break

    pnr = _first_match(
        [
            r"(?:PNR|RESERVATION CODE|BOOKING CODE|BOOKING REF|REZERVASYON NO)[:\s]+([A-Z0-9]{5,8})",
            r"\bPNR[:\s]*([A-Z0-9]{5,8})\b",
        ],
        upper,
    )

    flight_no = _first_match(
        [
            r"\b((?:VF|XQ|PC|TK)\s?\d{2,4})\b",
            r"(?:FLIGHT|SEFER(?:\s*NO)?|UCUS)[:\s]+((?:VF|XQ|PC|TK)\s?\d{2,4})",
        ],
        upper,
    )
    if flight_no:
        flight_no = re.sub(r"\s+", "", flight_no)

    route_match = re.search(r"\b([A-Z]{3})\s*[-/]\s*([A-Z]{3})\b", upper)
    from_airport = route_match.group(1) if route_match else None
    to_airport = route_match.group(2) if route_match else None
    if from_airport in INVALID_AIRPORT_CODES or to_airport in INVALID_AIRPORT_CODES:
        from_airport, to_airport = None, None
    if not from_airport or not to_airport:
        code_line_match = re.search(
            r"[A-ZÇĞİÖŞÜ]{2,}/([A-Z]{3}).{0,20}[A-ZÇĞİÖŞÜ]{2,}/([A-Z]{3})",
            upper,
            flags=re.DOTALL,
        )
        if code_line_match:
            from_airport = code_line_match.group(1)
            to_airport = code_line_match.group(2)
    if not route_match:
        from_airport = _first_match([r"\bFROM[:\s]+([A-Z]{3})\b", r"\bKALKIS[:\s]+([A-Z]{3})\b"], upper)
        to_airport = _first_match([r"\bTO[:\s]+([A-Z]{3})\b", r"\bVARIS[:\s]+([A-Z]{3})\b"], upper)

    date_raw = _first_match(
        [
            r"\b(\d{1,2}[./-]\d{1,2}[./-]\d{2,4})\b",
            r"\b(\d{1,2}\s*[A-Z]{3}(?:\s*\d{4})?)\b",
        ],
        upper,
    )
    time_raw = _first_match(
        [
            r"(?:TIME|SAAT)[:\s]+(([01]\d|2[0-3])[:.][0-5]\d)\b",
            r"\b(([01]\d|2[0-3]):[0-5]\d)\b",
            r"\b(([01]\d|2[0-3])\.[0-5]\d)\b(?!\.\d{2,4})",
        ],
        upper,
    )

    return {
        "passenger_name": passenger_name,
        "gender": passenger_gender,
        "pnr": pnr,
        "flight_no": flight_no,
        "date": _normalize_date(date_raw),
        "time": _normalize_time(time_raw),
        "from": from_airport,
        "to": to_airport,
    }


def _extract_ajet_fields(raw_text: str, parsed: dict[str, str | None]) -> dict[str, str | None]:
    upper = raw_text.upper()
    if not parsed["flight_no"]:
        match = re.search(r"\b(VF\s?\d{2,4})\b", upper)
        if match:
            parsed["flight_no"] = match.group(1).replace(" ", "")
    return parsed


def _extract_sunexpress_fields(raw_text: str, parsed: dict[str, str | None]) -> dict[str, str | None]:
    upper = raw_text.upper()
    if not parsed["flight_no"]:
        match = re.search(r"\b(XQ\s?\d{2,4})\b", upper)
        if match:
            parsed["flight_no"] = match.group(1).replace(" ", "")
    return parsed


def _extract_pegasus_fields(raw_text: str, parsed: dict[str, str | None]) -> dict[str, str | None]:
    upper = raw_text.upper()
    if not parsed["flight_no"]:
        match = re.search(r"\b(PC\s?\d{2,4})\b", upper)
        if match:
            parsed["flight_no"] = match.group(1).replace(" ", "")
    return parsed


def _extract_thy_fields(raw_text: str, parsed: dict[str, str | None]) -> dict[str, str | None]:
    upper = raw_text.upper()
    if not parsed["flight_no"]:
        match = re.search(r"\b(TK\s?\d{2,4})\b", upper)
        if match:
            parsed["flight_no"] = match.group(1).replace(" ", "")
    return parsed


def parse_ticket_text(raw_text: str) -> dict[str, Any]:
    airline = detect_airline(raw_text)
    parsed = _extract_common_fields(raw_text)

    if airline == "ajet":
        parsed = _extract_ajet_fields(raw_text, parsed)
    elif airline == "sunexpress":
        parsed = _extract_sunexpress_fields(raw_text, parsed)
    elif airline == "pegasus":
        parsed = _extract_pegasus_fields(raw_text, parsed)
    elif airline == "thy":
        parsed = _extract_thy_fields(raw_text, parsed)

    normalized = {
        "airline": airline,
        "passenger_name": parsed.get("passenger_name"),
        "gender": parsed.get("gender") or "unknown",
        "pnr": parsed.get("pnr"),
        "flight_no": parsed.get("flight_no"),
        "date": parsed.get("date"),
        "time": parsed.get("time"),
        "from": parsed.get("from"),
        "to": parsed.get("to"),
    }
    normalized.update(_extract_pricing_fields(raw_text))

    scored_fields = ["passenger_name", "pnr", "flight_no", "date", "time", "from", "to"]
    found_count = sum(1 for field in scored_fields if normalized.get(field))
    confidence = round(found_count / len(scored_fields), 2)

    critical_fields = ["flight_no", "date", "from", "to"]
    missing_critical = any(not normalized.get(field) for field in critical_fields)
    needs_review = missing_critical or confidence < 0.75

    return {
        "parsed": normalized,
        "confidence": confidence,
        "needs_review": needs_review,
    }
