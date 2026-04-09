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

## Urun Mimarisi

Bu platform tek uygulama gibi gorunse de urun ailesi olarak ayrismalidir:

- `Core / Cekirdek`
  kimlik, proje, yetki, tema, sponsor, bildirim ve ortak veri katmani
- `SaaS Yonetim Uygulamasi`
  tenant/acente yonetimi, paketler, entegrasyonlar, destek ve platform ayarlari
- `Acente / Operasyon Web Uygulamasi`
  kayit, konaklama, transfer, toplanti, tercuman, duyurular, muhasebe ve yonetim
- `Arac Operasyon Web Uygulamasi`
  arac planlama, surucu atama, rota, doluluk ve transfer operasyon akisi
- `Participant Uygulamasi`
  katilimci odakli toplanti, rezervasyonlar, duyurular, QR ve sponsor akislari
- `Surucu Uygulamasi`
  gorevler, yolcu listesi, rota, QR ve durum guncelleme
- `Greeter Uygulamasi`
  karsilama listesi, QR, bildirim ve yonlendirme akisi

Su an net ayrim:
- `http://localhost:3000` acente / operasyon web sistemi
- `participant.app` participant istemcisi

## Participant Uygulamasi

Repo içinde Expo tabanlı bir participant istemcisi de bulunur:
- klasor: `participant.app`
- urun adi: `Creatro Participant`
- kullanım: katılımcı odaklı login, proje seçimi ve toplantı/rezervasyon/duyuru akışları

Participant iş kuralları:
- login ve header tarafında varsayılan görsel acente logosudur
- alt proje görseli tanımlıysa acente logosunun yerine proje görseli gelir
- tema önceliği acente renkleridir; proje tema renkleri varsa onlar override eder
- participant ana sponsor logosu plaka alanının yerini alır
- hero kartta `Toplantı Modülü` yer alır
- alt kartlar: `Program Akışı`, `Bildiriler`, `Sertifikalar`, `Kurslar`
- `Masraflarım` yerine `Duyurular`
- `Görevlerim` yerine `Rezervasyonlarım`
- `Rezervasyonlarım` içinde transfer ve konaklama detayları görünür
- participant QR okutulduğunda:
  - transfer akışı için transfer sponsoru teşekkür görseli
  - kayıt veya konaklama akışı için kayıt-konaklama sponsoru teşekkür görseli

Gelecek notları:
- `modules-ui` tarafındaki destek butonu ileride SaaS yönetim paneline bağlanacak
- SaaS ekibi için SMS ve WhatsApp bağlantıları açılacak
- gelen destek mesajları için bildirim akışı eklenecek

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
2. Gerçek şifreleri sadece sunucudaki `.env` içinde tut.
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

## Participant Tema Notlari

- Participant uygulamasinda proje tema ana rengi `turuncu`, ikinci renk `lacivert` kabul edilir.
- Solid lacivert yuzeyler tek renk blok yerine `lacivert -> yesil` gecisli degrade olarak uygulanir.
- Header, loading, welcome ve footer yuzeyleri ayni tema ailesini izler.
- Logo alaninda acente logosu veya proje gorseli kullanilir.
- `formice.png` asset olcusu `1080x1080` olarak not edildi.
- `urojinekoloji.jpg` asset olcusu `1920x774` olarak not edildi.
- Hero gorselinde organizasyon banneri korunur; gerekiyorsa hero yuksekligi buyutulur, logo alaninda ise goruntu kirpilmaz.
