import re
from datetime import datetime
from typing import Any

from .iata_tr import IATA_EQUIVALENT_GROUPS, TURKEY_IATA_CODES


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
    "OCA": 1,
    "SUB": 2,
    "MAR": 3,
    "NIS": 4,
    "MAY": 5,
    "HAZ": 6,
    "TEM": 7,
    "AGU": 8,
    "EYL": 9,
    "EKI": 10,
    "KAS": 11,
    "ARA": 12,
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
TR_UPPER_MAP = str.maketrans({"Ç": "C", "Ğ": "G", "İ": "I", "Ö": "O", "Ş": "S", "Ü": "U"})


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _normalize_name(text: str | None) -> str | None:
    if not text:
        return None
    clean = re.sub(r"[^A-Z\s]", "", text.upper())
    clean = re.sub(r"\b(PASSENGER|NAME|YOLCU|ISMI|ADI)\b", " ", clean)
    clean = _normalize(clean)
    return clean or None


def _strip_name_titles(name_value: str | None) -> str | None:
    if not name_value:
        return None
    parts = [p for p in name_value.split(" ") if p]
    while parts and parts[-1] in MALE_TITLES.union(FEMALE_TITLES):
        parts.pop()
    return " ".join(parts) if parts else None


def _normalize_passenger_name_order(name_value: str | None, airline: str | None) -> str | None:
    if not name_value:
        return None
    parts = [p for p in str(name_value).split(" ") if p]
    if (airline or "").lower() == "thy" and len(parts) >= 2:
        surname = parts[0]
        given_names = parts[1:]
        return " ".join(given_names + [surname]).strip()
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


def _gender_label_tr(gender: str | None) -> str:
    value = (gender or "").lower()
    if value == "male":
        return "Erkek"
    if value == "female":
        return "Kadın"
    return "UNKNOW"


def _normalize_date(date_text: str | None) -> str | None:
    if not date_text:
        return None

    value = date_text.strip().upper().replace(",", " ")

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

    short_numeric = re.search(r"^(\d{1,2})[./-](\d{1,2})$", value)
    if short_numeric:
        day = int(short_numeric.group(1))
        month = int(short_numeric.group(2))
        year = datetime.utcnow().year
        try:
            return datetime(year, month, day).strftime("%Y-%m-%d")
        except ValueError:
            return None

    text_match = re.search(r"(\d{1,2})\s*([A-ZÃ‡ÄÄ°Ã–ÅÃœ]{3,9})(?:\s*(\d{2,4}))?", value)
    if text_match:
        day = int(text_match.group(1))
        month_token = text_match.group(2).translate(TR_UPPER_MAP)[:3]
        month = MONTH_MAP.get(month_token)
        year = int(text_match.group(3)) if text_match.group(3) else datetime.utcnow().year
        if year < 100:
            year += 2000
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


def _normalize_hhmm(value: str | None) -> str | None:
    if not value:
        return None
    digits = re.sub(r"[^0-9]", "", value)
    if len(digits) != 4:
        return None
    hh, mm = digits[:2], digits[2:]
    if int(hh) > 23 or int(mm) > 59:
        return None
    return f"{hh}:{mm}"


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


def _to_labeled_amount(value: str | None, *, allow_leading_index: bool = False) -> float | None:
    if not value:
        return None
    candidate = str(value).strip()
    if allow_leading_index:
        indexed = re.match(r"^\s*\d{1,2}\s+([0-9]+(?:[.,][0-9]{2}))\s*$", candidate)
        if indexed:
            candidate = indexed.group(1)
    return _to_amount(candidate)


def _extract_thy_accounting_fields(
    raw_text: str,
    *,
    base_fare: float | None = None,
    total_amount: float | None = None,
    tax_breakdown: dict[str, float] | None = None,
    is_domestic: bool = False,
) -> dict[str, float | None]:
    upper = (raw_text or "").upper()
    compact_upper = re.sub(r"\s+", "", upper)

    restriction_block = ""
    restriction_match = re.search(
        r"(?:KISITLAMA|ENDORSMEN|RESTR)[^\n\r]*[:]\s*(.*?)(?=(?:ODEME|PAYMENT|ESAS UCRET|ESAS ÜCRET|BASE FARE|VERGI|VERGİ|TAX|TOPLAM|TOTAL)\b)",
        upper,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if restriction_match:
        restriction_block = str(restriction_match.group(1) or "").strip()
    compact_restriction_block = re.sub(r"\s+", "", restriction_block.upper()) if restriction_block else ""

    def _pick(patterns: list[tuple[str, bool]]) -> float | None:
        for pattern, allow_leading_index in patterns:
            for haystack in [restriction_block, upper, compact_restriction_block, compact_upper]:
                if not haystack:
                    continue
                match = re.search(pattern, haystack, flags=re.IGNORECASE)
                if not match:
                    continue
                value = _to_labeled_amount(match.group(1), allow_leading_index=allow_leading_index)
                if value is not None:
                    return value
        return None

    tkm_amount = _pick([
        (r"\bTKM\b\s*[:]\s*([0-9][0-9\s.,]*[.,][0-9]{2})", False),
        (r"\bTKM\b[^0-9]{0,8}([0-9][0-9\s.,]*[.,][0-9]{2})", False),
        (r"TKM[:]?([0-9]+[.,][0-9]{2})TRY", False),
    ])
    tbu_amount = _pick([
        (r"\bTBU\b\s*[:]\s*([0-9][0-9\s.,]*[.,][0-9]{2})", False),
        (r"\bTBU\b[^0-9]{0,8}([0-9][0-9\s.,]*[.,][0-9]{2})", False),
        (r"TBU[:]?([0-9]+[.,][0-9]{2})TRY", False),
    ])
    explicit_total = _pick([
        (r"\b(?:TOPLAM|TOTAL)\b[^\n\r]{0,40}?([0-9][0-9\s.,]*[.,][0-9]{2})", False),
    ])

    tax_map = dict(tax_breakdown or {})
    vq_amount = tax_map.get("VQ")
    yr_amount = tax_map.get("YR")

    toplam_tutar = tbu_amount if tbu_amount is not None else explicit_total if explicit_total is not None else total_amount

    matrah = None
    if base_fare is not None:
        matrah_calc = float(base_fare) / 1.2 if is_domestic else float(base_fare)
        if vq_amount is not None:
            matrah_calc += float(vq_amount)
        if yr_amount is not None:
            matrah_calc += float(yr_amount) / 1.2
        if tkm_amount is not None:
            matrah_calc += float(tkm_amount) / 1.2
        matrah = round(matrah_calc, 2)

    kdv = None
    if toplam_tutar is not None and matrah is not None:
        kdv = round(float(toplam_tutar) - float(matrah), 2)

    return {
        "matrah": matrah,
        "kdv": kdv,
        "toplam_tutar": toplam_tutar,
    }


def _has_invalid_thy_accounting(parsed: dict[str, Any]) -> bool:
    if (parsed.get("airline") or "").lower() != "thy":
        return False
    base_fare = parsed.get("base_fare")
    toplam_tutar = parsed.get("toplam_tutar")
    if base_fare is None or toplam_tutar is None:
        return False
    try:
        return float(toplam_tutar) < float(base_fare)
    except (TypeError, ValueError):
        return False


def _clear_thy_accounting_fields(parsed: dict[str, Any]) -> None:
    parsed["matrah"] = None
    parsed["kdv"] = None
    parsed["toplam_tutar"] = None


def _extract_pricing_fields(raw_text: str, airline: str | None = None) -> dict[str, Any]:
    upper = (raw_text or "").upper()

    payment_type = _first_match(
        [r"(?:PAYMENT|ODEME|Ã–DEME)\s*[:]\s*([A-Z]+)"],
        upper,
    )

    base_fare_match = re.search(
        r"(?:BASE FARE|ESAS UCRET|ESAS ÃœCRET)\s*[:]\s*([A-Z]{3})?\s*([0-9]+[.,][0-9]{2})",
        upper,
    )
    total_match = re.search(
        r"(?:TOTAL|TOPLAM)\s*[:]\s*([A-Z]{3})?\s*([0-9]+[.,][0-9]{2})",
        upper,
    )
    tax_line = _first_match([r"(?:TAX|VERGI|VERGÄ°)\s*[:]\s*([^\n\r]+)"], upper)

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

    extracted = {
        "payment_type": payment_type,
        "currency": currency,
        "total_amount": total_amount,
        "base_fare": base_fare,
        "tax_total": tax_total,
        "tax_breakdown": tax_breakdown or None,
    }
    extracted.update({"matrah": None, "kdv": None, "toplam_tutar": None})
    return extracted


def _is_domestic_ticket(parsed: dict[str, Any]) -> bool:
    segments = parsed.get("segments") or []
    if isinstance(segments, list) and segments:
        codes: list[str] = []
        for seg in segments:
            if not isinstance(seg, dict):
                continue
            codes.extend([str(seg.get("from") or "").upper(), str(seg.get("to") or "").upper()])
        codes = [c for c in codes if c]
        if codes:
            return all(code in TURKEY_IATA_CODES for code in codes)
    from_code = str(parsed.get("from") or "").upper()
    to_code = str(parsed.get("to") or "").upper()
    if from_code and to_code:
        return from_code in TURKEY_IATA_CODES and to_code in TURKEY_IATA_CODES
    return False


def _extract_issue_date(raw_text: str) -> str | None:
    upper = (raw_text or "").upper()
    candidates: list[str] = []

    issue_line = _first_match(
        [r"(?:ISSUE DATE|DUZENLENDIGI TARIH|DÃœZENLENDIÄI TARIH)\s*[:]\s*([^\n\r]+)"],
        upper,
    )
    if issue_line:
        candidates.append(issue_line)
    candidates.append(upper)

    token_pattern = re.compile(
        r"(\d{1,2}[./-]\d{1,2}[./-]\d{2,4}|\d{1,2}\s*[A-ZÃ‡ÄÄ°Ã–ÅÃœ]{3,9}\s*\d{2,4})"
    )
    for text in candidates:
        for match in token_pattern.findall(text):
            normalized = _normalize_date(match)
            if normalized:
                return normalized
    return None


def detect_airline(raw_text: str) -> str:
    upper = (raw_text or "").upper()

    # THY e-ticket format often includes ANADOLUJET legs with TK flight numbers.
    if any(
        token in upper
        for token in [
            "TURKISH AIRLINES",
            "TURK HAVA YOLLARI",
            "THY GENEL MUDURLUGU",
            "THY GENEL MÃœDÃœRLÃœÄÃœ",
            "ELECTRONIC TICKET PASSENGER ITINERARY",
            "ELEKTRONIK BILET YOLCU SEYAHAT BELGESI",
            "ELEKTRONÄ°K BÄ°LET YOLCU SEYAHAT BELGESÄ°",
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
        if not re.search(r"(PASSENGER NAME|PASSENGER|YOLCU ISMI|YOLCU ADI|NAME)", line):
            continue

        candidates = []
        if ":" in line:
            candidates.append(line.split(":", 1)[1])

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

    if not passenger_name:
        direct_name = _first_match(
            [
                r"(?:PASSENGER(?: NAME)?|YOLCU(?: ISMI| ADI)?)\s*[:]\s*([A-Z\*\s]{2,})",
            ],
            upper,
        )
        if direct_name:
            passenger_name = _strip_name_titles(_normalize_name(direct_name))
            passenger_gender = _detect_gender_from_name_line(direct_name)

    if passenger_name:
        passenger_name = re.sub(
            r"^(?:PASSENGER NAME|PASSENGER|NAME|YOLCU ISMI|YOLCU ADI)\s+",
            "",
            passenger_name,
        ).strip()

    pnr = _first_match(
        [
            r"(?:PNR|RESERVATION CODE|BOOKING CODE|BOOKING REF|REZERVASYON NO)[:\s]+([A-Z0-9]{5,8})",
            r"(?:REZERVASYON NUMARASI|REZERVASYON NUMARASI)[:\s]+([A-Z0-9]{5,8})",
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
            r"[A-ZÃ‡ÄÄ°Ã–ÅÃœ]{2,}/([A-Z]{3}).{0,20}[A-ZÃ‡ÄÄ°Ã–ÅÃœ]{2,}/([A-Z]{3})",
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
    segments = _extract_prefixed_segments(raw_text, ("VF",))
    if segments:
        _apply_segment_summary(parsed, segments)
    return parsed


def _extract_sunexpress_fields(raw_text: str, parsed: dict[str, str | None]) -> dict[str, str | None]:
    upper = raw_text.upper()
    if not parsed.get("passenger_name"):
        pax_match = re.search(r"YOLCU\s+([A-ZÇĞİÖŞÜ\s]+?)\s+DO[ĞG]UM", upper, flags=re.DOTALL)
        if pax_match:
            parsed["passenger_name"] = _normalize_name(pax_match.group(1))
    if not parsed["flight_no"]:
        match = re.search(r"\b(XQ\s?\d{2,4})\b", upper)
        if match:
            parsed["flight_no"] = match.group(1).replace(" ", "")
    segments = _extract_prefixed_segments(raw_text, ("XQ",))
    if not segments:
        segments = _extract_sunexpress_turkish_segments(raw_text)
    if not segments:
        segments = _extract_sunexpress_ocr_segments(raw_text)
    if not parsed.get("passenger_name"):
        parsed["passenger_name"] = _extract_sunexpress_ocr_name(raw_text)
    if not parsed.get("pnr"):
        pnr = _extract_sunexpress_ocr_pnr(raw_text)
        if pnr:
            parsed["pnr"] = pnr
    if segments:
        _apply_segment_summary(parsed, segments)
    return parsed


def _extract_pegasus_fields(raw_text: str, parsed: dict[str, str | None]) -> dict[str, str | None]:
    upper = raw_text.upper()
    if not parsed.get("passenger_name"):
        pax_match = re.search(
            r"U[ÇC]U[ŞS]\s+B[İI]LG[İI]LER[İI]N[İI]Z\s+([A-ZÇĞİÖŞÜ\s]+?)\s+REZERVASYON",
            upper,
            flags=re.DOTALL,
        )
        if pax_match:
            parsed["passenger_name"] = _strip_name_titles(_normalize_name(pax_match.group(1)))
    if not parsed["flight_no"]:
        match = re.search(r"\b(PC\s?\d{2,4})\b", upper)
        if match:
            parsed["flight_no"] = match.group(1).replace(" ", "")
    segments = _extract_prefixed_segments(raw_text, ("PC",))
    if not segments:
        segments = _extract_pegasus_tabular_segments(raw_text)
    if segments:
        _apply_segment_summary(parsed, segments)
    return parsed


def _extract_thy_fields(raw_text: str, parsed: dict[str, str | None]) -> dict[str, str | None]:
    upper = raw_text.upper()
    if not parsed["flight_no"]:
        match = re.search(r"\b(TK\s?\d{2,4})\b", upper)
        if match:
            parsed["flight_no"] = match.group(1).replace(" ", "")
    segments = _extract_prefixed_segments(raw_text, ("TK",))
    if segments:
        _apply_segment_summary(parsed, segments)
    return parsed


def _normalize_airport_targets(target_airports: str | list[str] | tuple[str, ...] | None) -> list[str]:
    if not target_airports:
        return []
    if isinstance(target_airports, str):
        raw_items = re.split(r"[,;\s]+", target_airports.strip().upper())
    else:
        raw_items = [str(item).strip().upper() for item in target_airports]

    codes = [code for code in raw_items if re.fullmatch(r"[A-Z]{3}", code)]
    expanded: list[str] = []
    for code in codes:
        if code in IATA_EQUIVALENT_GROUPS:
            expanded.extend(sorted(IATA_EQUIVALENT_GROUPS[code]))
            continue
        # Keep Turkish IATA list as first-class and allow non-TR fallback codes.
        if code in TURKEY_IATA_CODES:
            expanded.append(code)
        else:
            expanded.append(code)

    seen = set()
    ordered: list[str] = []
    for code in expanded:
        if code in seen:
            continue
        seen.add(code)
        ordered.append(code)
    return ordered


def _classify_segments_by_targets(
    segments: list[dict[str, str | None]], target_airports: list[str]
) -> dict[str, Any]:
    if not segments:
        return {
            "segments": [],
            "outbound_segment": None,
            "return_segment": None,
            "trip_scope": "unknown",
            "has_transfer_segments": False,
        }

    targets = set(target_airports or [])
    classified: list[dict[str, str | None]] = []
    outbound = None
    inbound = None
    has_transfer = False

    for seg in segments:
        from_code = seg.get("from")
        to_code = seg.get("to")
        if targets and to_code in targets and from_code not in targets:
            role = "gidis"
            outbound = outbound or seg
        elif targets and from_code in targets and to_code not in targets:
            role = "donus"
            inbound = inbound or seg
        elif targets:
            role = "aktarma"
            has_transfer = True
        else:
            role = "belirsiz"

        tagged = dict(seg)
        tagged["segment_role"] = role
        classified.append(tagged)

    if targets and not outbound and not inbound:
        trip_scope = "transfer_only"
    elif targets:
        trip_scope = "target_related"
    else:
        trip_scope = "unclassified"

    return {
        "segments": classified,
        "outbound_segment": outbound,
        "return_segment": inbound,
        "trip_scope": trip_scope,
        "has_transfer_segments": has_transfer,
    }


def _extract_prefixed_segments(raw_text: str, prefixes: tuple[str, ...]) -> list[dict[str, str | None]]:
    if not prefixes:
        return []
    upper = raw_text.upper()
    prefix_pattern = "|".join(prefixes)
    pattern = re.compile(
        r"[A-ZÃ‡ÄÄ°Ã–ÅÃœ]{2,}/([A-Z]{3})\s+"
        r"[A-ZÃ‡ÄÄ°Ã–ÅÃœ]{2,}/([A-Z]{3})"
        r".{0,120}?\b(" + prefix_pattern + r")\s*([0-9]{2,4})\b"
        r".{0,80}?(\d{2}-\d{2})"
        r".{0,40}?(\d{2}-\d{2})"
        r".{0,80}?(\d{4})\s+(\d{4})",
        re.DOTALL,
    )
    segments: list[dict[str, str | None]] = []
    seen = set()
    for m in pattern.finditer(upper):
        from_code, to_code, code_prefix, flt_no, dep_ddmm, arr_ddmm, dep_hhmm, arr_hhmm = m.groups()
        dep_time = _normalize_hhmm(dep_hhmm)
        arr_time = _normalize_hhmm(arr_hhmm)
        dep_date = _normalize_date(dep_ddmm)
        arr_date = _normalize_date(arr_ddmm)
        key = (from_code, to_code, code_prefix, flt_no, dep_ddmm, arr_ddmm, dep_time, arr_time)
        if key in seen:
            continue
        seen.add(key)
        segments.append(
            {
                "from": from_code,
                "to": to_code,
                "flight_no": f"{code_prefix}{flt_no}",
                "departure_date": dep_date,
                "arrival_date": arr_date,
                "departure_time": dep_time,
                "arrival_time": arr_time,
            }
        )
    return segments


def _apply_segment_summary(parsed: dict[str, str | None], segments: list[dict[str, str | None]]) -> None:
    first = segments[0]
    parsed["from"] = parsed.get("from") or first["from"]
    parsed["to"] = parsed.get("to") or first["to"]
    parsed["flight_no"] = parsed.get("flight_no") or first["flight_no"]
    parsed["date"] = parsed.get("date") or first["departure_date"]
    parsed["time"] = parsed.get("time") or first["departure_time"]
    parsed["segments"] = segments

    reverse = next(
        (
            seg
            for seg in segments[1:]
            if seg["from"] == first["to"] and seg["to"] == first["from"]
        ),
        None,
    )
    parsed["outbound_departure_date"] = first["departure_date"]
    parsed["outbound_departure_time"] = first["departure_time"]
    parsed["outbound_arrival_date"] = first["arrival_date"]
    parsed["outbound_arrival_time"] = first["arrival_time"]
    if reverse:
        parsed["trip_type"] = "round_trip"
        parsed["outbound_date"] = first["departure_date"]
        parsed["return_date"] = reverse["departure_date"]
        parsed["return_departure_date"] = reverse["departure_date"]
        parsed["return_departure_time"] = reverse["departure_time"]
        parsed["return_arrival_date"] = reverse["arrival_date"]
        parsed["return_arrival_time"] = reverse["arrival_time"]
    elif len(segments) > 1:
        parsed["trip_type"] = "connection"
        parsed["outbound_date"] = first["departure_date"]
        parsed["return_date"] = None
    else:
        parsed["trip_type"] = "one_way"
        parsed["outbound_date"] = first["departure_date"]
        parsed["return_date"] = None
    parsed["segment_count"] = len(segments)


def _extract_pegasus_tabular_segments(raw_text: str) -> list[dict[str, str | None]]:
    upper = (raw_text or "").upper()
    pattern = re.compile(
        r"\(([A-Z]{3})\)\s*"
        r".{0,180}?\(([A-Z]{3})\)\s*"
        r"PC\s*-\s*([0-9]{2,4})\s*"
        r"(\d{2}/\d{2}/\d{4})\s*"
        r"([0-2]\d:[0-5]\d)\s*"
        r"([0-2]\d:[0-5]\d)",
        re.DOTALL,
    )
    segments: list[dict[str, str | None]] = []
    seen = set()
    for m in pattern.finditer(upper):
        from_code, to_code, flt_no, dep_date_raw, dep_time_raw, arr_time_raw = m.groups()
        dep_date = _normalize_date(dep_date_raw)
        dep_time = _normalize_time(dep_time_raw)
        arr_time = _normalize_time(arr_time_raw)
        key = (from_code, to_code, flt_no, dep_date, dep_time, arr_time)
        if key in seen:
            continue
        seen.add(key)
        segments.append(
            {
                "from": from_code,
                "to": to_code,
                "flight_no": f"PC{flt_no}",
                "departure_date": dep_date,
                "arrival_date": dep_date,
                "departure_time": dep_time,
                "arrival_time": arr_time,
            }
        )
    return segments


def _extract_sunexpress_turkish_segments(raw_text: str) -> list[dict[str, str | None]]:
    upper = (raw_text or "").upper()
    clean = upper.replace(",", " ")
    pattern = re.compile(
        r"(GIDI[ŞS]\s+U[ÇC]U[ŞS]U|D[ÖO]N[ÜU][ŞS]\s+U[ÇC]U[ŞS]U)"
        r"\s+(?:[A-ZÇĞİÖŞÜ]+\s+)?"
        r"(\d{1,2}\s+[A-ZÇĞİÖŞÜ]{3,9}\s+\d{4}|\d{1,2}[./-]\d{1,2}[./-]\d{4})"
        r".{0,120}?"
        r"([0-2]\d:[0-5]\d)\s+[^\n\r()]*\(([A-Z]{3})\)"
        r".{0,80}?"
        r"([0-2]\d:[0-5]\d)\s+[^\n\r()]*\(([A-Z]{3})\)"
        r".{0,120}?(?:SUNEXPRESS\s+)?\bXQ\s*([0-9]{2,4})\b",
        re.DOTALL,
    )
    segments: list[dict[str, str | None]] = []
    seen = set()
    for m in pattern.finditer(clean):
        _, dep_date_raw, dep_time_raw, from_code, arr_time_raw, to_code, flt_no = m.groups()
        dep_date = _normalize_date(dep_date_raw)
        dep_time = _normalize_time(dep_time_raw)
        arr_time = _normalize_time(arr_time_raw)
        key = (from_code, to_code, flt_no, dep_date, dep_time, arr_time)
        if key in seen:
            continue
        seen.add(key)
        segments.append(
            {
                "from": from_code,
                "to": to_code,
                "flight_no": f"XQ{flt_no}",
                "departure_date": dep_date,
                "arrival_date": dep_date,
                "departure_time": dep_time,
                "arrival_time": arr_time,
            }
        )
    return segments


def _extract_sunexpress_ocr_name(raw_text: str) -> str | None:
    upper = (raw_text or "").upper()
    # OCR'de "DOGUM TARI" bozulabildiği için sadece "DOGUM" arıyoruz.
    m = re.search(r"\bYOLCU\b.{0,120}?([A-ZÇĞİÖŞÜ]{2,}(?:\s+[A-ZÇĞİÖŞÜ]{2,}){1,3})\s+D[O0][ĞG]UM", upper, re.DOTALL)
    if not m:
        return None
    candidate = _normalize_name(m.group(1))
    if not candidate:
        return None
    bad = {"SUNEXPRESS", "MY", "EY", "UCUS", "BILET"}
    tokens = [t for t in candidate.split() if t not in bad]
    return " ".join(tokens) if tokens else None


def _extract_sunexpress_ocr_pnr(raw_text: str) -> str | None:
    upper = (raw_text or "").upper()
    m = re.search(r"REZERVASYON\s+NUMAR[AI][S5I]?\s*[:\-]?\s*([A-Z0-9]{5,8})", upper)
    if m:
        return m.group(1)
    return None


def _extract_sunexpress_ocr_segments(raw_text: str) -> list[dict[str, str | None]]:
    upper = (raw_text or "").upper().replace("@", "G")
    iata_pairs = re.findall(r"\(([A-Z]{3})\)", upper)
    if len(iata_pairs) < 2:
        return []
    from_code, to_code = iata_pairs[0], iata_pairs[1]

    flight_match = re.search(r"\bXQ\s*([0-9]{2,4})\b", upper)
    date_match = re.search(r"(\d{1,2}[./-]\d{1,2}[./-]\d{4}|\d{1,2}\s+[A-ZÇĞİÖŞÜ]{3,9}\s+\d{4})", upper)
    times = re.findall(r"\b([0-2]\d:[0-5]\d)\b", upper)
    if not flight_match or not date_match or len(times) < 2:
        return []

    dep_date = _normalize_date(date_match.group(1))
    dep_time = _normalize_time(times[0])
    arr_time = _normalize_time(times[1])
    if not dep_date or not dep_time or not arr_time:
        return []
    return [
        {
            "from": from_code,
            "to": to_code,
            "flight_no": f"XQ{flight_match.group(1)}",
            "departure_date": dep_date,
            "arrival_date": dep_date,
            "departure_time": dep_time,
            "arrival_time": arr_time,
        }
    ]


def parse_ticket_text(
    raw_text: str,
    target_airports: str | list[str] | tuple[str, ...] | None = None,
    pricing_scan_enabled: bool = False,
) -> dict[str, Any]:
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

    normalized_targets = _normalize_airport_targets(target_airports)
    if parsed.get("segments"):
        classified = _classify_segments_by_targets(parsed.get("segments") or [], normalized_targets)
        parsed["segments"] = classified["segments"]
        parsed["trip_scope"] = classified["trip_scope"]
        parsed["has_transfer_segments"] = classified["has_transfer_segments"]
        parsed["target_airports"] = normalized_targets or None

        outbound = classified["outbound_segment"]
        inbound = classified["return_segment"]
        if outbound:
            parsed["outbound_departure_date"] = outbound.get("departure_date")
            parsed["outbound_departure_time"] = outbound.get("departure_time")
            parsed["outbound_arrival_date"] = outbound.get("arrival_date")
            parsed["outbound_arrival_time"] = outbound.get("arrival_time")
            parsed["from"] = outbound.get("from") or parsed.get("from")
            parsed["to"] = outbound.get("to") or parsed.get("to")
            parsed["flight_no"] = outbound.get("flight_no") or parsed.get("flight_no")
            parsed["date"] = outbound.get("departure_date") or parsed.get("date")
            parsed["time"] = outbound.get("departure_time") or parsed.get("time")
            parsed["outbound_date"] = outbound.get("departure_date") or parsed.get("outbound_date")
        if inbound:
            parsed["return_departure_date"] = inbound.get("departure_date")
            parsed["return_departure_time"] = inbound.get("departure_time")
            parsed["return_arrival_date"] = inbound.get("arrival_date")
            parsed["return_arrival_time"] = inbound.get("arrival_time")
            parsed["return_date"] = inbound.get("departure_date")
        if outbound and inbound:
            parsed["trip_type"] = "round_trip"
        elif outbound:
            parsed["trip_type"] = "one_way"
        elif inbound:
            parsed["trip_type"] = "return_only"
        elif normalized_targets:
            parsed["trip_type"] = "connection"

    normalized = {
        "airline": airline,
        "passenger_name": _normalize_passenger_name_order(parsed.get("passenger_name"), airline),
        "gender": parsed.get("gender") or "unknown",
        "cinsiyet": _gender_label_tr(parsed.get("gender")),
        "pnr": parsed.get("pnr"),
        "flight_no": parsed.get("flight_no"),
        "date": parsed.get("date"),
        "time": parsed.get("time"),
        "trip_type": parsed.get("trip_type"),
        "outbound_date": parsed.get("outbound_date"),
        "return_date": parsed.get("return_date"),
        "segment_count": parsed.get("segment_count"),
        "outbound_departure_date": parsed.get("outbound_departure_date"),
        "outbound_departure_time": parsed.get("outbound_departure_time"),
        "outbound_arrival_date": parsed.get("outbound_arrival_date"),
        "outbound_arrival_time": parsed.get("outbound_arrival_time"),
        "return_departure_date": parsed.get("return_departure_date"),
        "return_departure_time": parsed.get("return_departure_time"),
        "return_arrival_date": parsed.get("return_arrival_date"),
        "return_arrival_time": parsed.get("return_arrival_time"),
        "segments": parsed.get("segments"),
        "target_airports": parsed.get("target_airports"),
        "trip_scope": parsed.get("trip_scope"),
        "has_transfer_segments": parsed.get("has_transfer_segments"),
        "from": parsed.get("from"),
        "to": parsed.get("to"),
        "issue_date": _extract_issue_date(raw_text),
    }
    normalized.update(_extract_pricing_fields(raw_text, airline))
    if airline == "thy" and pricing_scan_enabled:
        normalized.update(
            _extract_thy_accounting_fields(
                raw_text,
                base_fare=normalized.get("base_fare"),
                total_amount=normalized.get("total_amount"),
                tax_breakdown=normalized.get("tax_breakdown"),
                is_domestic=_is_domestic_ticket(parsed),
            )
        )

    scored_fields = ["passenger_name", "pnr", "flight_no", "date", "time", "from", "to"]
    found_count = sum(1 for field in scored_fields if normalized.get(field))
    confidence = round(found_count / len(scored_fields), 2)

    critical_fields = ["flight_no", "date", "from", "to"]
    missing_critical = any(not normalized.get(field) for field in critical_fields)
    invalid_thy_accounting = pricing_scan_enabled and _has_invalid_thy_accounting(normalized)
    if invalid_thy_accounting:
        _clear_thy_accounting_fields(normalized)
    needs_review = missing_critical or confidence < 0.75 or invalid_thy_accounting

    return {
        "parsed": normalized,
        "confidence": confidence,
        "needs_review": needs_review,
    }
