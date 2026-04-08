from __future__ import annotations

from datetime import datetime
from typing import Any

MONEY_FIELDS = {"ucret_toplam", "ucret_matrah", "vergi_alan", "vergi_kdv_vq", "vergi_toplam"}
EXPORT_COLUMNS = [
    "first_name",
    "last_name",
    "segment_type",
    "source_file",
    "pnr",
    "flight_no",
    "from",
    "to",
    "departure_date",
    "departure_time",
    "arrival_date",
    "arrival_time",
    "status",
    "payment_type",
    "issue_date",
    "ucret_toplam",
    "ucret_matrah",
    "vergi_alan",
    "vergi_kdv_vq",
    "vergi_toplam",
]


def _split_name(passenger_name: str | None) -> tuple[str, str]:
    if not passenger_name:
        return "", ""
    clean = " ".join((passenger_name or "").strip().split())
    parts = clean.split(" ")
    if len(parts) == 1:
        return parts[0].title(), ""
    # THY OCR samples are often "SOYAD AD"; keep this default.
    return " ".join(parts[1:]).title(), parts[0].title()


def _format_date(value: str | None) -> str:
    if not value:
        return ""
    txt = value.strip()
    for fmt in ("%Y-%m-%d", "%d.%m.%Y"):
        try:
            dt = datetime.strptime(txt, fmt)
            return dt.strftime("%d.%m.%Y")
        except ValueError:
            continue
    return txt


def _format_amount(value: Any) -> str:
    if value is None or value == "":
        return ""
    try:
        amount = float(value)
    except (TypeError, ValueError):
        return str(value)
    return f"{amount:.2f}".replace(".", ",")


def _segment_type(index: int, segment_count: int, role: str | None = None) -> str:
    if role == "gidis":
        return "outbound"
    if role == "donus":
        return "return"
    if role == "aktarma":
        return "transfer"
    if index == 0:
        return "outbound"
    if index == 1:
        return "return"
    return f"segment_{index + 1}"


def _extract_segments(transfer: Any) -> list[dict[str, str]]:
    raw_parse = transfer.raw_parse or {}
    raw_segments = raw_parse.get("segments") or []
    segments: list[dict[str, str]] = []
    for seg in raw_segments:
        segments.append(
            {
                "from": (seg.get("from") or ""),
                "to": (seg.get("to") or ""),
                "flight_no": (seg.get("flight_no") or ""),
                "departure_date": _format_date(seg.get("departure_date")),
                "departure_time": seg.get("departure_time") or "",
                "arrival_date": _format_date(seg.get("arrival_date")),
                "arrival_time": seg.get("arrival_time") or "",
                "segment_role": seg.get("segment_role") or "",
            }
        )
    if segments:
        return segments
    return [
        {
            "from": transfer.pickup_location or "",
            "to": transfer.dropoff_location or "",
            "flight_no": transfer.flight_no or "",
            "departure_date": _format_date(transfer.flight_date),
            "departure_time": transfer.flight_time or "",
            "arrival_date": "",
            "arrival_time": "",
        }
    ]


def build_transfer_export_rows(transfer: Any, source_file: str) -> list[dict[str, str]]:
    first_name, last_name = _split_name(transfer.passenger_name)
    segments = _extract_segments(transfer)
    row_count = len(segments) if segments else 1
    total_each = (transfer.total_amount / row_count) if transfer.total_amount is not None else None
    base_each = (transfer.base_fare / row_count) if transfer.base_fare is not None else None

    tax_breakdown = transfer.tax_breakdown or {}
    tax_yr_each = (tax_breakdown.get("YR") / row_count) if tax_breakdown.get("YR") is not None else None
    tax_vq_each = (tax_breakdown.get("VQ") / row_count) if tax_breakdown.get("VQ") is not None else None
    tax_total_each = (transfer.tax_total / row_count) if transfer.tax_total is not None else None

    rows: list[dict[str, str]] = []
    iter_segments = segments if segments else segments[:1]
    for idx, seg in enumerate(iter_segments):
        rows.append(
            {
                "first_name": first_name,
                "last_name": last_name,
                "segment_type": _segment_type(idx, len(iter_segments), seg.get("segment_role")),
                "source_file": source_file,
                "pnr": transfer.pnr or "",
                "flight_no": seg.get("flight_no") or transfer.flight_no or "",
                "from": seg.get("from") or transfer.pickup_location or "",
                "to": seg.get("to") or transfer.dropoff_location or "",
                "departure_date": seg.get("departure_date") or _format_date(transfer.flight_date),
                "departure_time": seg.get("departure_time") or transfer.flight_time or "",
                "arrival_date": seg.get("arrival_date") or "",
                "arrival_time": seg.get("arrival_time") or "",
                "status": transfer.status or "unassigned",
                "payment_type": transfer.payment_type or "",
                "issue_date": _format_date(transfer.issue_date),
                "ucret_toplam": _format_amount(total_each),
                "ucret_matrah": _format_amount(base_each),
                "vergi_alan": _format_amount(tax_yr_each),
                "vergi_kdv_vq": _format_amount(tax_vq_each),
                "vergi_toplam": _format_amount(tax_total_each),
            }
        )
    return rows


def rows_to_csv(rows: list[dict[str, str]]) -> str:
    lines = [";".join(EXPORT_COLUMNS)]
    for row in rows:
        lines.append(";".join((row.get(col) or "") for col in EXPORT_COLUMNS))
    return "\n".join(lines) + "\n"


def rows_to_xls_html(rows: list[dict[str, str]]) -> str:
    colgroup = "<colgroup>" + "".join("<col/>" for _ in EXPORT_COLUMNS) + "</colgroup>"
    header = "<tr>" + "".join(f"<th>{col}</th>" for col in EXPORT_COLUMNS) + "</tr>"
    body_rows = []
    for row in rows:
        tds = []
        for col in EXPORT_COLUMNS:
            value = row.get(col) or ""
            if col in MONEY_FIELDS:
                tds.append(f'<td style="mso-number-format:\\\"\\#\\,\\#\\#0\\.00\\\">{value}</td>')
            else:
                tds.append(f"<td>{value}</td>")
        body_rows.append("<tr>" + "".join(tds) + "</tr>")

    html_lines = [
        '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"  "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">',
        '<html xmlns="http://www.w3.org/1999/xhtml">',
        '<head><meta charset="UTF-8"><title>Transfer Export</title></head>',
        "<body><table>",
        colgroup,
        header,
        *body_rows,
        "</table></body></html>",
    ]
    return "\n".join(html_lines)
