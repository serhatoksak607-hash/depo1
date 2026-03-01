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


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _normalize_name(text: str | None) -> str | None:
    if not text:
        return None
    clean = re.sub(r"[^A-Z\s]", "", text.upper())
    clean = _normalize(clean)
    return clean or None


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


def detect_airline(raw_text: str) -> str:
    upper = (raw_text or "").upper()

    if any(token in upper for token in ["AJET", "A JET", "ANADOLUJET"]):
        return "ajet"
    if "SUNEXPRESS" in upper:
        return "sunexpress"
    if "PEGASUS" in upper:
        return "pegasus"
    if any(token in upper for token in ["TURKISH AIRLINES", "TURK HAVA YOLLARI", " THY "]):
        return "thy"

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
    for line in lines:
        name_match = re.search(r"(?:PASSENGER|NAME|YOLCU(?: ADI)?)[:\s]+(.+)$", line)
        if name_match:
            passenger_name = _normalize_name(name_match.group(1))
            if passenger_name:
                break

    pnr = _first_match(
        [
            r"(?:PNR|RESERVATION CODE|BOOKING CODE)[:\s]+([A-Z0-9]{5,8})",
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
        flight_no = flight_no.replace(" ", "")

    route_match = re.search(r"\b([A-Z]{3})\s*[-/]\s*([A-Z]{3})\b", upper)
    from_airport = route_match.group(1) if route_match else None
    to_airport = route_match.group(2) if route_match else None
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
        "pnr": parsed.get("pnr"),
        "flight_no": parsed.get("flight_no"),
        "date": parsed.get("date"),
        "time": parsed.get("time"),
        "from": parsed.get("from"),
        "to": parsed.get("to"),
    }

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
