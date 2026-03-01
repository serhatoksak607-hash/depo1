# Etkinlik Operasyon Platformu Tasarımı

Bu proje, etkinlik/kongre operasyonlarını uçtan uca yönetmek için modüler bir platform tasarımı sunar.
Aşağıdaki kapsam, ilettiğiniz 5 ana modülü temel alır ve birbirleriyle entegre çalışacak şekilde kurgulanmıştır.

## 1) Kayıt Modülü

### Amaç
- Katılımcıların kişisel bilgilerini toplamak.
- Her kişiye sistem içi tekil bir ID atamak.
- ID ile eşlenmiş QR kod üretmek.
- Katılımcının hangi gün/salonlara erişebileceğini merkezi kurallardan yönetmek.

### Temel veri alanları
- Katılımcı ID (tekil)
- Ad, Soyad, Kurum, Ünvan, İletişim
- Kayıt tipi (konuşmacı, firma temsilcisi, ziyaretçi vb.)
- Kayıt sponsoru
- Erişim kuralları (gün, saat aralığı, salon listesi)
- QR hash/token

### Çalışma mantığı
1. Kayıt tamamlanınca sistem bir `participant_id` üretir.
2. QR içeriğine doğrudan açık veri yerine imzalı token yazılır.
3. Giriş noktasında QR okutulduğunda sistem:
   - Kişiyi bulur,
   - O anki tarih/saat/salon için yetkisini kontrol eder,
   - Geçiş logunu tutar.
4. Gün/salon yetkileri sonradan güncellenirse aynı QR token yeni kuralları otomatik uygular.

---

## 2) Konaklama Modülü

### Amaç
- Kim, kiminle, hangi otelde, hangi günler kalıyor takibi.
- Karmaşık faturalama/sponsor senaryolarını yönetmek.

### Temel veri alanları
- Otel bilgisi (4-5 farklı otel)
- Oda tipi (SGL/DBL/TWIN)
- Oda paylaşımı (oda arkadaşları)
- Giriş/çıkış tarihleri
- Faturalama modeli:
  - Tek kişiye tam fatura
  - Yarı yarıya paylaşım
  - 1 kişi SGL, diğer kişi DBL-SGL farkı öder
- Sponsor kırılımı:
  - Kayıt sponsoru
  - Konaklama sponsoru
  - Kalem bazlı sponsor (oda, vergi, transfer vb.)

### Önerilen yaklaşım
- Faturalamayı `kalem bazlı ledger` mantığında tutun.
- Her gece için kişi başına ayrı konaklama satırı üretin.
- Sponsor atamasını satır bazında yapın (tek sponsorda toplu da atanabilir).
- Böylece mutabakat ve raporlama muhasebe modülüne temiz akar.

---

## 3) Toplantı Modülü

### Amaç
- Katılımcıların hangi gün/saat/salonlara gireceğini yönetmek.
- Duyuru ve bildirim göndermek.
- Etkileşimli alt modüller eklemek.

### Temel fonksiyonlar
- Oturum/salon takvimi
- Yetki matrisi (kişi x oturum/salon)
- Kapı geçiş doğrulama (QR doğrulama ile entegre)
- Anlık bildirim/duyuru (mobil, SMS, e-posta)

### Genişletilebilir alt modüller
- Soru-cevap / quiz (Kahoot benzeri)
- Sertifika üretimi:
  - Katılım eşiklerine göre otomatik sertifika
  - PDF üretim + doğrulama kodu
- Devam takibi ve CME/puan toplama

---

## 4) Transfer Modülü

### Amaç
- Uçuş bileti belgelerinden (ZIP/PDF/JPG) otomatik veri çıkarımı.
- Transfer listesi oluşturma.

### Girdi ve işleme hattı
1. Dosya algılama:
   - ZIP ise içeriği aç,
   - PDF/JPG/PNG ise doğrudan işleme al.
2. Metin çıkarımı:
   - Dijital PDF ise metin extraction,
   - Görsel/PDF görüntüsü ise OCR.
3. Havayolu tespiti:
   - AJet, Pegasus, SunExpress, THY şablonları.
4. Şablon bazlı parser:
   - PNR, yolcu adı, uçuş no, tarih/saat, kalkış/varış.
5. Çoklu senaryo algılama:
   - Tek yön,
   - Gidiş-dönüş tek bilet,
   - Aktarmalı,
   - 2 ayrı bilet.

### Kayıt isimlendirme önerisi
- `ad_soyad_gidiş`
- `ad_soyad_dönüş`
- `ad_soyad_gidiş&dönüş`
- Aktarma ekleri için:
  - `ad_soyad_aktarmalı_gidiş`
  - Ek biletler: `ad_soyad_aktarma`

### Operasyonel öneri
- “İlk varış havalimanı” seçim ekranı mutlaka manuel doğrulama içersin.
- Otomatik eşleşmede güven skoru üretin; düşük skorluları insan onayına düşürün.

---

## 5) Muhasebe ve Finans Modülü

### Amaç
- Firma/kişi bazlı mutabakat ve hesap takibi.
- Proforma kesimi ve e-posta gönderimi.
- İleri aşamada müşteri fatura sistemine uyumlu excel çıktıları.

### Temel fonksiyonlar
- Cari hesap kartları (firma + kişi)
- Borç/alacak hareketleri
- Kalem bazlı sponsor etkisi
- Proforma üretimi (şablonlu)
- Mail gönderim ve log takibi
- Mutabakat raporları

### Sonraki aşama
- Excel tasarım modülü:
  - Müşteri formatı eşleştirme
  - Kolon/başlık dönüştürme
  - Toplu dışa aktarma ve gönderim

---

## Önerilen Ortak Veri Modeli (Özet)

- `participants` (katılımcı)
- `registrations` (kayıt)
- `access_policies` (gün/salon yetkisi)
- `hotels`, `rooms`, `stays` (konaklama)
- `billing_items` (kalem bazlı mali kayıt)
- `sponsors`, `sponsorship_allocations` (sponsor dağılımı)
- `sessions`, `halls`, `attendance_logs` (toplantı)
- `tickets`, `flight_segments`, `transfers` (transfer)
- `invoices`, `proformas`, `reconciliations` (finans)

---

## Teknik Mimari Önerisi

- **Backend:** Modüler monolith ile başlamak (hızlı ilerleme + kolay bakım)
- **Veritabanı:** PostgreSQL
- **Dosya depolama:** S3 uyumlu obje depolama
- **OCR/Belge işleme:** Asenkron queue (worker mimarisi)
- **Yetkilendirme:** Rol bazlı + firma bazlı veri izolasyonu
- **Audit log:** Kritik tüm işlemler için zorunlu

### Neden modüler monolith?
- Başlangıçta hızlı geliştirme sağlar.
- İhtiyaç olgunlaştıkça transfer/OCR gibi yoğun modüller microservice’e ayrılabilir.

---

## Yol Haritası (Pratik)

1. **Faz 1 (MVP):** Kayıt + QR + temel toplantı erişimi
2. **Faz 2:** Konaklama + sponsor/faturalama kuralları
3. **Faz 3:** Transfer OCR + manuel doğrulama ekranı
4. **Faz 4:** Muhasebe mutabakat + proforma + e-posta
5. **Faz 5:** Excel adaptörü ve gelişmiş entegrasyonlar

---

## Kritik Başarı Kriterleri

- QR doğrulama hızının yüksek olması (kapıda bekleme olmaması)
- Sponsor/fatura kural motorunun esnekliği
- Uçuş bileti parser’ında insan doğrulama akışının iyi tasarlanması
- Tüm modüllerde izlenebilirlik (audit + raporlama)

Bu tasarım, verdiğiniz operasyon gerçekliğine uygun şekilde esnek ve büyüyebilir bir temel sunar.
