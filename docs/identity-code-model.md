# Identity Code Model

Bu doküman, CreaTRO SaaS içinde firma, kullanıcı, kişi ve proje bazlı kimlik/kod modelini sabit referans olarak tanımlar.

## Amaç

- Firma kodlarını standartlaştırmak
- Kullanıcıyı kişi kaydından ayırmak
- Aynı kişinin farklı projelerde farklı rol alabilmesini desteklemek
- Proje bazlı kısa, QR uyumlu operasyon kodu üretmek
- Teknik veritabanı `id` alanlarını kullanıcıya görünen iş kodlarından ayırmak

## Temel İlke

- Veritabanı teknik `id` alanları korunur.
- Kullanıcıya görünen kodlar ayrı alanlar olarak tutulur.
- Global kimlik ile proje içi operasyon kimliği birbirinden ayrılır.

## Kod Türleri

### 1. Firma Kodu

- Acente firmaları: `A001` ... `A999`
- Taşıma / araç firmaları: `T001` ... `T999`
- Kod tekrar kullanılmaz.

Örnekler:

- `A001`
- `A014`
- `T002`

### 2. Global Kullanıcı Kodu

- Format: `U0001` ... `U9999`
- Sisteme giriş hesabına aittir.
- Bir kullanıcı birden fazla firmada ve projede görev alabilir.
- Kullanıcı kodu firmaya bağlı değildir.

Örnekler:

- `U0001`
- `U0042`

### 3. Global Kişi Kodu

- Format: `P000001` ... devam eden sabit uzunluklu seri
- Katılımcı, konuşmacı, moderatör, refakatçi, firma çalışanı veya son kullanıcı olabilen gerçek kişiyi temsil eder.
- Aynı kişi sistem genelinde tek bir kişi kaydına sahip olur.

Örnekler:

- `P000001`
- `P004521`

### 4. Proje Kodu

- Format: `AA01` ... `ZZ99`
- Seri akışı:
  - `AA01` ... `AA99`
  - `AB01` ... `AB99`
  - ...
  - `ZZ01` ... `ZZ99`

Örnekler:

- `AA01`
- `AA02`
- `AB01`

### 5. Proje İçi Kişi / Kullanıcı Kodu

- Her projede yeniden üretilir
- Global kişi veya global kullanıcı kodunun yerine geçmez
- QR ve saha operasyonu için kullanılır
- Uzunluk: `6`
- Tip: random alfanumerik

Önerilen karakter seti:

- `ABCDEFGHJKLMNPQRSTUVWXYZ123456789`

Kurallar:

- `I` yok
- `O` yok
- `0` yok
- Kod proje içinde tekil olmalıdır

Örnekler:

- `A7M4Q2`
- `L9X2R5`
- `B3K8ZT`

## QR / Karekod Formatı

QR içeriği aşağıdaki birleşik formatı kullanır:

- `ProjeKodu-KatilimTuru-Kimlik`

Örnekler:

- `AA01-K-A7M4Q2`
- `AA01-S-B9R2L7`
- `AB03-M-X4T8N3`

Alanlar:

- `AA01`: proje kodu
- `K`, `S`, `M`: proje içi rol / katılım türü kısa kodu
- `A7M4Q2`: proje içi random kimlik

## Rol Mantığı

Aynı kişi farklı projelerde farklı roller alabilir.

Örnek:

- aynı kişi bir projede `katılımcı`
- başka projede `konuşmacı`
- başka projede `moderatör`

Bu nedenle kişi kimliği ile proje rolü ayrılmalıdır.

## Önerilen Rol Kodları

- `K`: Katılımcı
- `S`: Speaker / Konuşmacı
- `M`: Moderatör
- `R`: Refakatçi
- `F`: Firma Yetkilisi
- `T`: Tercüman
- `D`: Driver
- `G`: Greeter / Karşılama

## Veri Modeli Önerisi

### Global tablolar

- `companies`
  - teknik `id`
  - `company_code`
  - `company_type`

- `persons`
  - teknik `id`
  - `person_code`
  - kişi ana bilgileri

- `users`
  - teknik `id`
  - `user_code`
  - `person_id`
  - login ve auth alanları

- `projects`
  - teknik `id`
  - `project_code`

### İlişki tabloları

- `user_company_access`
  - kullanıcı hangi firmalarda çalışıyor

- `user_project_access`
  - kullanıcı hangi projeleri görüyor / yönetiyor

- `project_people`
  - `project_id`
  - `person_id`
  - `project_person_code`
  - `role_code`
  - proje içi operasyon alanları

## Kritik Mimari Kararlar

- Global kişi kodu sabit kalır.
- Proje içi kişi kodu her projede değişir.
- Kullanıcı kodu login hesabına aittir ve globaldir.
- Firma kodu firmaya aittir ve globaldir.
- QR içinde global kişi kodu değil proje içi kimlik kullanılır.
- Kullanıcıya görünen operasyon kodları teknik veritabanı `id` alanlarının yerini almaz.

## Uygulama Notu

Bu model şu an karar/spec seviyesinde kabul edilmiştir.

Uygulama yapılırken:

1. yeni kolonlar eklenmeli
2. unique index kuralları tanımlanmalı
3. kod üreticileri transaction içinde çalışmalı
4. eski veriler için migration stratejisi belirlenmeli
5. QR üretimi `project_people` tablosundaki proje içi kod üzerinden yapılmalı
