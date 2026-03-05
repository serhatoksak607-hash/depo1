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

## Olcek ve Yetki Gereksinimleri (Kaynak Dokuman)

Bu bolum, canli hedef mimari icin sabit referanstir. Hata ayiklama ve yeni gelistirmeler bu kurallara gore kontrol edilir.

### Hedef olcek (yaklasik)

- 1,000,000 katilimci
- 50,000 organizasyon projesi
- 1,000 acente
- 4,000 acente yetkilisi
- 400 arac firmasi
- 4,000 surucu hesabi
- 2,000 desk gorevlisi
- 20 SaaS ekip kullanicisi

### Rol ve erisim modeli

- `saas_superadmin`: tum tenant/proje/modul/veri erisimi
- `tenant_admin` (acente): kendi tenant altindaki tum projeler
- `tenant_manager` (acente yetkilisi): sadece atanmis projeler + atanmis moduller
- `desk_agent`: atanmis proje bazli erisim (part-time destek senaryosu dahil)
- `supplier_admin` (arac firmasi): atandigi projeler + kendi rezervasyon/proje no alanlari
- `driver`: sadece kendisine atanmis transferler

### Zorunlu erisim kurallari

- Tum listeleme ve yazma islemlerinde `tenant_id` + `project_id` filtrelemesi zorunlu
- Yetki karari sadece role gore degil, atama tablolari ile birlikte verilir
- Pasif proje durumunda veri degisikligi engellenir (read-only)
- Sadece SaaS superadmin tum tenant/projeleri gorebilir

### Gerekli atama tablolari

- `user_project_access (user_id, project_id, role_scope, is_active)`
- `user_module_access (user_id, module_name, can_read, can_write)`
- `supplier_project_access (supplier_company_id, project_id, is_active)`
- `driver_transfer_assignments (driver_user_id, transfer_id, assigned_at, status)`
- `reservation_external_refs (supplier_company_id, project_id, local_ref, external_ref)`

### Performans ve veri katmani

- Buyuk tablolar icin birlesik index:
- `module_data (module_name, project_id, created_at desc)`
- `transfers (project_id, driver_id, pickup_time)`
- `user_project_access (user_id, project_id)`
- Listeleme: server-side pagination/cursor (UI tarafinda sonsuz offset taramasi yok)
- Arama: full-text/trigram benzeri indeksli arama

### Surucu paneli ve SMS akisi

- Surucuya SMS ile tek-kullanim veya kisa omurlu baglanti gonderilir
- Link token yalnizca ilgili surucunun atanmis transferlerini acar
- Token sure dolunca/iptalde kullanilamaz olur

### Hata geri donus kontrol listesi

Her erisim/sorgu hatasinda asagidaki sira izlenir:

1. Kullanici rolu dogru mu?
2. Kullanici ilgili projeye atanmis mi?
3. Proje aktif mi/pasif mi?
4. Tenant ve project filtreleri sorguya uygulandi mi?
5. Gerekli index var mi, sorgu tam taramaya mi dusuyor?
6. Log/Audit kaydi olustu mu?
