# Transfer Modulu MVP

FastAPI tabanli backend MVP: dosya yukleme, saglik kontrolu ve temel transfer tablolari.

Detayli tasarim dokumani: `docs/spec.md`
AI Agent gelistirme akisi: `docs/ai-agent-developer-workflow.md`

## Hizli Baslangic

1. Docker Desktop'i acin.
2. Proje kokunde calistirin:

```bash
docker compose up --build -d
```

3. Endpoint kontrolleri:

```bash
curl http://localhost:8000/health
```

## Sprint 2 Test Adimlari (Real OCR + Parser v0)

1. Parser unit testlerini calistirin:

```bash
docker compose exec backend python -m pytest -q
```

2. Samples altindaki maskeli bir dosyayi upload edin:

```bash
curl -X POST "http://localhost:8000/upload" ^
  -H "accept: application/json" ^
  -H "Content-Type: multipart/form-data" ^
  -F "file=@C:/path/samples/ocr_ticket.png"
```

3. Cevaptan `id` degerini alin ve kaydi sorgulayin:

```bash
curl http://localhost:8000/uploads/{id}
```

4. Beklenen durum:

- Ilk anda `status: "pending"` gelebilir.
- Worker isledikten sonra `status: "processed"` olur.
- `parse_result` alani su formatta dolar:
  `{"method":"pdf_text|ocr","raw_text":"...","parsed":{...},"confidence":0-1,"needs_review":true|false}`.

## Airline Detection Sirasi

Parser asagidaki sinyallere gore havayolunu belirler:

1. Marka adi: `AJET/ANADOLUJET`, `SUNEXPRESS`, `PEGASUS`, `TURKISH AIRLINES/THY`
2. Ucus kodu:
   - `VF` -> `ajet`
   - `XQ` -> `sunexpress`
   - `PC` -> `pegasus`
   - `TK` -> `thy`
3. Hicbiri yoksa `unknown`

## Sample Veriler

- `samples/ajet_ticket_masked.txt`
- `samples/sunexpress_ticket_masked.txt`
- `samples/pegasus_ticket_masked.txt`
- `samples/thy_ticket_masked.txt`
- `samples/ocr_ticket.png`

## Sprint 3 Test Adimlari (Transfer Engine + Transfers API)

1. Servisleri ayağa kaldırın:

```bash
docker compose up --build -d
```

2. Örnek bir bilet dosyası yükleyin:

```bash
curl -X POST "http://localhost:8000/upload" ^
  -H "accept: application/json" ^
  -H "Content-Type: multipart/form-data" ^
  -F "file=@C:/path/samples/ocr_ticket.png"
```

3. Upload işlenene kadar bekleyip kontrol edin:

```bash
curl http://localhost:8000/uploads/{id}
```

4. Transfer kayıtlarını listeleyin:

```bash
curl http://localhost:8000/transfers
```

5. Filtre örnekleri:

```bash
curl "http://localhost:8000/transfers?status=unassigned"
curl "http://localhost:8000/transfers?airline=ajet"
curl "http://localhost:8000/transfers?needs_review=true"
```
