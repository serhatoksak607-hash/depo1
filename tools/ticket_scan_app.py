from __future__ import annotations

import argparse
import csv
import json
import io
import sys
from dataclasses import dataclass
from pathlib import Path
from tkinter import Tk, filedialog

from pypdf import PdfReader
import shutil

import fitz
import pytesseract
from PIL import Image


REQUIRED_FIELDS = ["passenger_name", "pnr", "flight_no", "date", "from", "to"]
THY_TEXT_SIGNALS = ("TURKISH AIRLINES", "TURK HAVA YOLLARI", "THY")
ISTANBUL_PAIR = {"IST", "SAW"}


def _configure_tesseract() -> None:
    if shutil.which("tesseract"):
        return
    candidates = [
        Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe"),
        Path(r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"),
    ]
    for candidate in candidates:
        if candidate.exists():
            pytesseract.pytesseract.tesseract_cmd = str(candidate)
            return


def _ocr_image(image_bytes: bytes) -> str:
    image = Image.open(io.BytesIO(image_bytes))
    return (pytesseract.image_to_string(image, lang="eng") or "").strip()


def _ocr_pdf(path: Path) -> str:
    _configure_tesseract()
    doc = fitz.open(str(path))
    texts: list[str] = []
    try:
        for page in doc:
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            texts.append(_ocr_image(pix.tobytes("png")))
    finally:
        doc.close()
    return "\n".join(filter(None, texts)).strip()


@dataclass
class ScanResult:
    file_name: str
    airline_detected: str
    thy_candidate: str
    text_len: int
    passenger_name: str
    pnr: str
    flight_no: str
    date: str
    from_airport: str
    to_airport: str
    trip_type: str
    trip_scope: str
    has_transfer_segments: str
    target_airports: str
    segment_count: str
    missing_fields: str
    error: str

    def as_dict(self) -> dict[str, str | int]:
        return {
            "file_name": self.file_name,
            "airline_detected": self.airline_detected,
            "thy_candidate": self.thy_candidate,
            "text_len": self.text_len,
            "passenger_name": self.passenger_name,
            "pnr": self.pnr,
            "flight_no": self.flight_no,
            "date": self.date,
            "from": self.from_airport,
            "to": self.to_airport,
            "trip_type": self.trip_type,
            "trip_scope": self.trip_scope,
            "has_transfer_segments": self.has_transfer_segments,
            "target_airports": self.target_airports,
            "segment_count": self.segment_count,
            "missing_fields": self.missing_fields,
            "error": self.error,
        }


def _load_parser(repo_root: Path):
    backend_dir = repo_root / "backend"
    sys.path.insert(0, str(backend_dir))
    from app.parser import parse_ticket_text  # pylint: disable=import-outside-toplevel

    return parse_ticket_text


def _extract_pdf_text(path: Path) -> str:
    reader = PdfReader(str(path))
    text = "\n".join((page.extract_text() or "") for page in reader.pages).strip()
    if len(text) >= 30:
        return text
    try:
        return _ocr_pdf(path)
    except Exception:
        return text


def _is_thy(parsed: dict, text: str) -> bool:
    airline = (parsed.get("airline") or "").lower()
    flight_no = (parsed.get("flight_no") or "").upper().replace(" ", "")
    upper = text.upper()
    return (
        airline == "thy"
        or flight_no.startswith("TK")
        or any(sig in upper for sig in THY_TEXT_SIGNALS)
    )


def _choose_best_center_airport(texts: list[str], parse_ticket_text) -> list[str]:
    departure_counts: dict[str, int] = {}
    arrival_counts: dict[str, int] = {}

    def _inc(counter: dict[str, int], code: str | None) -> None:
        if not code:
            return
        code = code.strip().upper()
        if len(code) != 3 or not code.isalpha():
            return
        counter[code] = counter.get(code, 0) + 1

    for text in texts:
        if not text:
            continue
        try:
            parsed = (parse_ticket_text(text).get("parsed") or {})
        except Exception:
            continue
        segments = parsed.get("segments") or []
        if segments:
            for seg in segments:
                _inc(departure_counts, seg.get("from"))
                _inc(arrival_counts, seg.get("to"))
        else:
            _inc(departure_counts, parsed.get("from"))
            _inc(arrival_counts, parsed.get("to"))

    candidates = set(departure_counts) | set(arrival_counts)
    if not candidates:
        return []

    both_direction = [c for c in candidates if departure_counts.get(c, 0) > 0 and arrival_counts.get(c, 0) > 0]
    pool = both_direction or list(candidates)
    best = max(
        pool,
        key=lambda c: (
            min(departure_counts.get(c, 0), arrival_counts.get(c, 0)),
            departure_counts.get(c, 0) + arrival_counts.get(c, 0),
            arrival_counts.get(c, 0),
            departure_counts.get(c, 0),
        ),
    )
    if best in ISTANBUL_PAIR:
        return ["IST", "SAW"]
    return [best]


def scan_tickets(
    pdf_paths: list[Path],
    output_dir: Path,
    parse_ticket_text,
    target_airports: list[str] | None = None,
) -> tuple[list[dict], dict]:
    output_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []
    documents: list[dict] = []

    for pdf in sorted(pdf_paths):
        error = ""
        text = ""
        try:
            text = _extract_pdf_text(pdf)
        except Exception as exc:  # pragma: no cover
            error = f"pdf_read_error:{exc}"
        documents.append({"pdf": pdf, "text": text, "error": error})

    target_airports = [a.strip().upper() for a in (target_airports or []) if a.strip()]
    auto_target_mode = False
    if not target_airports:
        target_airports = _choose_best_center_airport(
            [doc["text"] for doc in documents if doc.get("text")],
            parse_ticket_text=parse_ticket_text,
        )
        auto_target_mode = bool(target_airports)

    for doc in documents:
        pdf = doc["pdf"]
        error = doc["error"] or ""
        parsed = {}
        text = doc["text"] or ""

        if text:
            try:
                parsed_res = parse_ticket_text(text, target_airports=target_airports)
                parsed = parsed_res.get("parsed") or {}
            except Exception as exc:  # pragma: no cover
                error = f"{error}|parse_error:{exc}" if error else f"parse_error:{exc}"

        missing = [field for field in REQUIRED_FIELDS if not parsed.get(field)]
        result = ScanResult(
            file_name=pdf.name,
            airline_detected=(parsed.get("airline") or "unknown").lower(),
            thy_candidate="yes" if _is_thy(parsed, text) else "no",
            text_len=len(text),
            passenger_name=parsed.get("passenger_name") or "",
            pnr=parsed.get("pnr") or "",
            flight_no=parsed.get("flight_no") or "",
            date=parsed.get("date") or "",
            from_airport=parsed.get("from") or "",
            to_airport=parsed.get("to") or "",
            trip_type=parsed.get("trip_type") or "",
            trip_scope=parsed.get("trip_scope") or "",
            has_transfer_segments="yes" if parsed.get("has_transfer_segments") else "no",
            target_airports=",".join(parsed.get("target_airports") or target_airports or []),
            segment_count=str(parsed.get("segment_count") or ""),
            missing_fields=",".join(missing),
            error=error,
        )
        rows.append(result.as_dict())

    full_report = output_dir / "ticket_scan_full_report.csv"
    thy_report = output_dir / "ticket_scan_thy_only.csv"
    missing_report = output_dir / "ticket_scan_thy_missing_summary.csv"
    summary_json = output_dir / "ticket_scan_summary.json"

    _write_csv(full_report, rows)
    thy_rows = [row for row in rows if row["thy_candidate"] == "yes"]
    _write_csv(thy_report, thy_rows, fallback_fields=(list(rows[0].keys()) if rows else ["file_name"]))
    _write_missing_summary(missing_report, thy_rows)

    summary = {
        "total_files": len(rows),
        "thy_candidates": len(thy_rows),
        "non_thy_files": len(rows) - len(thy_rows),
        "files_with_no_text": sum(1 for row in rows if int(row.get("text_len", 0)) == 0),
        "files_with_errors": sum(1 for row in rows if row.get("error")),
        "target_airports_used": target_airports,
        "target_airports_mode": "auto" if auto_target_mode else ("provided" if target_airports else "none"),
        "reports": {
            "full_report": str(full_report),
            "thy_report": str(thy_report),
            "missing_summary": str(missing_report),
        },
    }
    summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return rows, summary


def export_reports_to_xlsx(output_dir: Path) -> list[str]:
    exported: list[str] = []
    csv_files = [
        "ticket_scan_full_report.csv",
        "ticket_scan_thy_only.csv",
        "ticket_scan_thy_missing_summary.csv",
    ]
    try:
        from openpyxl import Workbook  # pylint: disable=import-outside-toplevel

        for csv_name in csv_files:
            csv_path = output_dir / csv_name
            if not csv_path.exists():
                continue
            xlsx_path = output_dir / csv_name.replace(".csv", ".xlsx")
            wb = Workbook()
            ws = wb.active
            ws.title = "report"
            with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
                reader = csv.reader(f)
                for row in reader:
                    ws.append(row)
            wb.save(xlsx_path)
            exported.append(str(xlsx_path))
        return exported
    except Exception:
        # Fallback for environments without internet/package install.
        for csv_name in csv_files:
            csv_path = output_dir / csv_name
            if not csv_path.exists():
                continue
            xls_path = output_dir / csv_name.replace(".csv", ".xls")
            with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
                reader = csv.reader(f)
                rows = list(reader)
            if not rows:
                continue
            col_count = len(rows[0])
            colgroup = "<colgroup>" + "".join("<col/>" for _ in range(col_count)) + "</colgroup>"
            html_rows = []
            for i, row in enumerate(rows):
                tag = "th" if i == 0 else "td"
                html_rows.append("<tr>" + "".join(f"<{tag}>{cell}</{tag}>" for cell in row) + "</tr>")
            html = "\n".join(
                [
                    '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"  "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">',
                    '<html xmlns="http://www.w3.org/1999/xhtml">',
                    '<head><meta charset="UTF-8"><title>Ticket Scan Report</title></head>',
                    "<body><table>",
                    colgroup,
                    *html_rows,
                    "</table></body></html>",
                ]
            )
            xls_path.write_text(html, encoding="utf-8")
            exported.append(str(xls_path))
        return exported


def _write_csv(path: Path, rows: list[dict], fallback_fields: list[str] | None = None) -> None:
    if rows:
        fieldnames = list(rows[0].keys())
    else:
        fieldnames = fallback_fields or ["file_name"]
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        if rows:
            writer.writerows(rows)


def _write_missing_summary(path: Path, thy_rows: list[dict]) -> None:
    missing_counter: dict[str, int] = {}
    for row in thy_rows:
        for missing in [x for x in (row.get("missing_fields") or "").split(",") if x]:
            missing_counter[missing] = missing_counter.get(missing, 0) + 1

    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["field", "missing_count_in_thy"])
        for field, count in sorted(missing_counter.items(), key=lambda kv: (-kv[1], kv[0])):
            writer.writerow([field, count])


def _find_repo_root() -> Path:
    here = Path(__file__).resolve()
    if (here.parent.parent / "backend" / "app" / "parser.py").exists():
        return here.parent.parent
    raise FileNotFoundError("Repo root not found next to tools/ directory.")


def _pick_pdf_paths() -> list[Path]:
    root = Tk()
    root.withdraw()
    root.update()

    file_paths = filedialog.askopenfilenames(
        title="Bilet PDF dosyalarini sec",
        filetypes=[("PDF files", "*.pdf")],
    )
    if file_paths:
        root.destroy()
        return [Path(p) for p in file_paths]

    dir_path = filedialog.askdirectory(title="PDF klasorunu sec")
    root.destroy()
    if not dir_path:
        return []
    return sorted(Path(dir_path).glob("*.pdf"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan ticket PDFs and list THY candidates with missing fields.")
    parser.add_argument("--source-dir", required=False, help="Directory containing PDF tickets")
    parser.add_argument("--files", nargs="*", help="One or more PDF files")
    parser.add_argument("--picker", action="store_true", help="Open file/folder picker UI")
    parser.add_argument("--xlsx", action="store_true", help="Also create XLSX versions of CSV reports")
    parser.add_argument(
        "--target-airports",
        default="",
        help="Hedef havalimanlari (ornek: AYT veya IST,SAW). Gidis/Donus/Aktarma siniflandirmasi icin kullanilir.",
    )
    parser.add_argument(
        "--output-dir",
        default="exports",
        help="Output directory for CSV/JSON reports (default: repo/exports)",
    )
    args = parser.parse_args()

    repo_root = _find_repo_root()
    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = repo_root / output_dir

    pdf_paths: list[Path] = []
    if args.files:
        pdf_paths = [Path(p) for p in args.files if Path(p).suffix.lower() == ".pdf"]
    elif args.source_dir:
        source_dir = Path(args.source_dir)
        if not source_dir.exists():
            print(f"SOURCE_NOT_FOUND: {source_dir}")
            return 2
        pdf_paths = sorted(source_dir.glob("*.pdf"))
    else:
        pdf_paths = _pick_pdf_paths() if args.picker or not args.source_dir else []

    if not pdf_paths:
        print("NO_PDF_SELECTED")
        return 3

    parse_ticket_text = _load_parser(repo_root)
    target_airports = [x.strip().upper() for x in args.target_airports.replace(";", ",").split(",") if x.strip()]
    _, summary = scan_tickets(
        pdf_paths=pdf_paths,
        output_dir=output_dir,
        parse_ticket_text=parse_ticket_text,
        target_airports=target_airports,
    )
    if args.xlsx:
        xlsx_files = export_reports_to_xlsx(output_dir)
        summary["reports"]["xlsx"] = xlsx_files

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
