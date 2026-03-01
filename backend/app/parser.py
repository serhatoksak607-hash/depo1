import re
from typing import Any


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def parse_ticket_text(raw_text: str) -> dict[str, Any]:
    text = _normalize(raw_text)
    upper = text.upper()
    lines = [line.strip().upper() for line in (raw_text or "").splitlines() if line.strip()]

    parsed: dict[str, str] = {}

    flight_match = re.search(r"\b(?:TK|PC)\s?\d{2,4}\b", upper)
    if flight_match:
        parsed["flight_no"] = flight_match.group(0).replace(" ", "")

    pnr_match = re.search(r"(?:PNR|RESERVATION CODE)[:\s]+([A-Z0-9]{6})", upper)
    if pnr_match:
        parsed["pnr"] = pnr_match.group(1)

    for line in lines:
        name_match = re.search(r"(?:PASSENGER|NAME)[:\s]+(.+)$", line)
        if not name_match:
            continue
        clean_name = re.sub(r"[^A-Z\s]", "", name_match.group(1))
        clean_name = _normalize(clean_name)
        if clean_name:
            parsed["passenger_name"] = clean_name
            break

    route_match = re.search(r"\b([A-Z]{3})\s*[-/]\s*([A-Z]{3})\b", upper)
    if route_match:
        parsed["from"] = route_match.group(1)
        parsed["to"] = route_match.group(2)
    else:
        from_to_match = re.search(r"FROM[:\s]+([A-Z]{3}).*TO[:\s]+([A-Z]{3})", upper)
        if from_to_match:
            parsed["from"] = from_to_match.group(1)
            parsed["to"] = from_to_match.group(2)

    date_match = re.search(
        r"\b(\d{1,2}[./-]\d{1,2}[./-]\d{2,4}|\d{1,2}\s?[A-Z]{3})\b", upper
    )
    if date_match:
        parsed["date"] = date_match.group(1)

    time_match = re.search(r"\b([01]\d|2[0-3])[:.][0-5]\d\b", upper)
    if time_match:
        parsed["time"] = time_match.group(0).replace(".", ":")

    target_fields = ["passenger_name", "flight_no", "date", "time", "from", "to"]
    filled_count = sum(1 for key in target_fields if key in parsed)
    confidence = round(min(1.0, filled_count / len(target_fields)), 2)
    if "pnr" in parsed and confidence < 1.0:
        confidence = round(min(1.0, confidence + 0.1), 2)

    needs_review = confidence < 0.75

    return {
        "parsed": parsed,
        "confidence": confidence,
        "needs_review": needs_review,
    }
