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

## Sprint 1 Test Adimlari (Upload Processing Pipeline)

1. Upload gonderin:

```bash
curl -X POST "http://localhost:8000/upload" ^
  -H "accept: application/json" ^
  -H "Content-Type: multipart/form-data" ^
  -F "file=@C:/path/ornek.pdf"
```

2. Cevaptan `id` degerini alin ve kaydi sorgulayin:

```bash
curl http://localhost:8000/uploads/{id}
```

3. Beklenen durum:

- Ilk anda `status: "pending"` gelebilir.
- Worker isledikten sonra `status: "processed"` olur.
- `parse_result` alani su formatta dolar:
  `{"raw_text":"...","method":"pdf_text"}` veya
  `{"raw_text":"OCR_NOT_IMPLEMENTED","method":"ocr_placeholder"}`.
