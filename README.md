# Creatro Web Platform

Bu repo mobil aplikasyon degil, Docker ile calisan bir web platformu.

Ana bilesenler:
- FastAPI backend
- PostgreSQL
- Redis
- Arka plan worker
- Ayrik domain servisleri (`platform_core`, `fleet_domain`, `agency_domain`)

Core flow:
`Upload -> Parse -> Transfer -> Operations list`

Detayli tasarim: `docs/spec.md`  
AI agent workflow: `docs/ai-agent-developer-workflow.md`  
Production deployment notes: `docs/deployment-production.md`

## GitHub ve Vercel

Bu repo GitHub'a uygundur.

Vercel'e tum sistemi koymak uygun degil:
- proje Docker tabanli
- Postgres ve Redis kullaniyor
- worker sureci var
- kalici upload storage gerekiyor

Dogru kullanim:
- kaynak kod: GitHub
- calisan ana sistem: Docker destekli sunucu veya VPS
- Vercel: ancak ileride ayri bir frontend cikarsa

## Quick Start

1. Docker Desktop acik olsun.
2. Proje kokunde calistir:

```bash
docker compose up --build -d
```

3. Health kontrolu:

```bash
curl http://localhost:3000/health
```

4. Ana arayuz:

```text
http://localhost:3000/
```

## Portlar

- `http://localhost:3000` ana sistem
- `http://localhost:3001` platform cekirdegi
- `http://localhost:3002` arac firmasi domaini
- `http://localhost:3003` acente domaini

Container ici portlar `8000/8001/8002/8003`, host tarafinda acilan portlar `3000/3001/3002/3003`.

## Publish Notlari

GitHub'a cikmadan once:
1. `.env` dosyasini commit etme.
2. Gercek sifreleri sadece sunucudaki `.env` icinde tut.
3. `APP_ADMIN_PASS` degerini degistir.
4. `PUBLIC_BASE_URL`, `CORS_ORIGINS` ve `TRUSTED_HOSTS` degerlerini ortama gore ayarla.

## Main Endpoints

- `POST /upload`
- `GET /uploads/{id}`
- `GET /transfers`
- `GET /ops-events`

## Airline Detection Order

Parser once marka adini, sonra ucus kodunu kullanir:

1. Marka sinyali:
   - `AJET/ANADOLUJET` -> `ajet`
   - `SUNEXPRESS` -> `sunexpress`
   - `PEGASUS` -> `pegasus`
   - `TURKISH AIRLINES/THY` -> `thy`
2. Ucus kodu:
   - `VF` -> `ajet`
   - `XQ` -> `sunexpress`
   - `PC` -> `pegasus`
   - `TK` -> `thy`
3. Hicbiri yoksa: `unknown`

## Samples

- `samples/ajet_ticket_masked.txt`
- `samples/sunexpress_ticket_masked.txt`
- `samples/pegasus_ticket_masked.txt`
- `samples/thy_ticket_masked.txt`
- `samples/ocr_ticket.png`

## Sprint 2 Validation (OCR + Parser)

1. Unit tests:

```bash
docker compose exec backend python -m pytest -q
```

2. Upload test:

```bash
curl -X POST "http://localhost:3000/upload" ^
  -H "accept: application/json" ^
  -H "Content-Type: multipart/form-data" ^
  -F "file=@C:/path/samples/ocr_ticket.png"
```

3. Upload sonucu:

```bash
curl http://localhost:3000/uploads/{id}
```

Beklenen:
- Ilk anda `status=pending` olabilir.
- Sonra `status=processed`.
- `parse_result` formati:
  `{"method":"pdf_text|ocr","raw_text":"...","parsed":{...},"confidence":0-1,"needs_review":true|false}`

## Sprint 3 Validation (Transfer Engine + Ops Events)

1. Upload gonder:

```bash
curl -X POST "http://localhost:3000/upload" ^
  -H "accept: application/json" ^
  -H "Content-Type: multipart/form-data" ^
  -F "file=@C:/path/samples/ocr_ticket.png"
```

2. Transfer listesi:

```bash
curl http://localhost:3000/transfers
```

3. Ops event listesi:

```bash
curl http://localhost:3000/ops-events
```

4. Filtre ornekleri:

```bash
curl "http://localhost:3000/transfers?status=unassigned"
curl "http://localhost:3000/transfers?airline=ajet"
curl "http://localhost:3000/transfers?needs_review=true"
curl "http://localhost:3000/ops-events?event_type=flight_delayed"
```

## Ticket Scan App (THY List + Missing Fields)

Klasordeki tum PDF biletleri tarar, THY adaylarini listeler ve eksik alan raporu uretir.

Calistirma:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\run_ticket_scan.ps1 `
  -SourceDir "C:\Users\SAĞLAM YAPI\OneDrive\SERHAT\,\Yeni klasör\GEÇİCİ MASAÜSTÜ -2\Yeni klasör\GÖNDERİLMİŞ OLANLAR" `
  -OutputDir "exports"
```

Uygulama icinden dosya/klasor secmek icin:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\run_ticket_scan.ps1
```

Opsiyonel XLSX cikti icin:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\run_ticket_scan.ps1 -Xlsx
```

Uretilen dosyalar:
- `exports/ticket_scan_full_report.csv` (tum biletler)
- `exports/ticket_scan_thy_only.csv` (yalniz THY/TK adaylari)
- `exports/ticket_scan_thy_missing_summary.csv` (THY icin eksik alan sayilari)
- `exports/ticket_scan_summary.json` (ozet)
