# Transfer Modulu MVP - Backend Iskeleti

Bu repo, Transfer Modulu MVP icin FastAPI tabanli bir backend iskeleti icerir.

## Icerik

- FastAPI backend
- `docker-compose.yml` (PostgreSQL + Redis + Backend)
- `/health` endpoint
- `/upload` endpoint (PDF/JPG/PNG/ZIP)
- `storage/uploads` klasoru
- `uploads` tablosu (uygulama acilisinda otomatik olusturulur)

## Calistirma

1. Docker Desktop'i acin.
2. Proje kok dizininde su komutu calistirin:

```bash
docker compose up --build
```

3. Backend ayaga kalktiginda API:

```text
http://localhost:8000
```

## Test

### 1) Health kontrolu

```bash
curl http://localhost:8000/health
```

Beklenen ornek cevap:

```json
{
  "status": "ok",
  "database": "ok",
  "redis": "ok"
}
```

### 2) Upload endpoint testi

```bash
curl -X POST "http://localhost:8000/upload" ^
  -H "accept: application/json" ^
  -H "Content-Type: multipart/form-data" ^
  -F "file=@C:/path/ornek.pdf"
```

Not:
- Sadece `.pdf`, `.jpg`, `.jpeg`, `.png`, `.zip` uzantilari kabul edilir.
- Yuklenen dosyalar host tarafinda `storage/uploads` altina yazilir.
- Kayit bilgileri PostgreSQL icindeki `uploads` tablosuna eklenir.

## Servisler

- Backend: `http://localhost:8000`
- Postgres: `localhost:5432` (`postgres/postgres`, db: `transfer_db`)
- Redis: `localhost:6379`
