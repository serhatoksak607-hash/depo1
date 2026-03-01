# Transfer Modulu MVP - Teknik Tasarim

## Amac

Bu proje, transfer operasyonu icin backend tarafinda calisan minimum urun (MVP) iskeletini saglar:

- Servis sagligi (`/health`)
- Dosya yukleme (`/upload`)
- Yukleme metadata kaydi (PostgreSQL)
- Gelecek is akislarina hazir temel veri modeli (`uploads`, `tickets`, `flight_segments`, `transfers`)

## Mimari

- API: FastAPI
- Veritabani: PostgreSQL
- Cache/altyapi saglik bagimliligi: Redis
- Calistirma ortami: Docker Compose

Servisler:

- `backend`: `http://localhost:8000`
- `postgres`: `localhost:5432` (`transfer_db`)
- `redis`: `localhost:6379`

## API Endpointleri

### GET `/health`

Servisin, PostgreSQL ve Redis baglantilarinin durumunu doner.

Ornek cevap:

```json
{
  "status": "ok",
  "database": "ok",
  "redis": "ok"
}
```

### POST `/upload`

Multipart `file` alir, dosyayi `storage/uploads` altina yazar, metadata kaydini `uploads` tablosuna ekler.

Kabul edilen uzantilar:

- `.pdf`
- `.jpg`
- `.jpeg`
- `.png`
- `.zip`

Kayit edilen alanlar:

- `original_filename`
- `stored_filename` (UUID tabanli)
- `content_type`
- `file_size`
- `file_path`
- `created_at`

## Veri Modeli (Minimal)

### `uploads`

- `id` (PK)
- `original_filename`
- `stored_filename` (unique)
- `content_type`
- `file_size`
- `file_path`
- `created_at`

### `tickets`

- `id` (PK)
- `pnr` (index)
- `passenger_name`
- `status`
- `created_at`

### `flight_segments`

- `id` (PK)
- `ticket_id` (FK -> tickets.id)
- `segment_order`
- `flight_number`
- `departure_airport`
- `arrival_airport`
- `departure_time`
- `arrival_time`

### `transfers`

- `id` (PK)
- `ticket_id` (FK -> tickets.id)
- `pickup_location`
- `dropoff_location`
- `pickup_time`
- `status`
- `created_at`

## Dizin Yapisi

```text
.
|-- backend/
|   |-- app/
|   |   |-- db.py
|   |   |-- main.py
|   |   `-- models.py
|   |-- Dockerfile
|   `-- requirements.txt
|-- storage/
|   `-- uploads/
|-- docs/
|   `-- spec.md
`-- docker-compose.yml
```
