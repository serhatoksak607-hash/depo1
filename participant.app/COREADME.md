# Core Notlari

## QR ve Yolcu Havuzu Davranisi

- `allow_project_cross_vehicle = true` ve `person_vehicle_restricted = false` ise yolcu havuzu proje bazinda ortak kabul edilmelidir.
- Bu durumda yolcu herhangi bir uygun arac operasyonunda QR ile okutuldugunda veya manuel olarak islendiyse ayni projedeki diger arac listelerinden otomatik olarak dusmelidir.
- Islenen yolcu mevcut operasyon kartinda ve QR ekraninda `Geldi` veya `Islendi` olarak gorunmeye devam etmelidir.
- Ayni yolcu proje icindeki baska bir arac operasyonunda tekrar `uygun` olarak sunulmamalidir.
- Core tarafinda bu davranisin ideal kaynagi operasyon bazli degil, proje kapsami ve yolcu bazli islenme kaydi olmalidir.

## Participant Tema Kurallari

- Participant uygulamasinda proje tema ana rengi `turuncu`, ikinci renk `lacivert` olarak ele alinmalidir.
- Solid lacivert alanlar tek renk blok yerine `lacivert -> yesil` gecisli degrade yuzeyler olarak uygulanmalidir.
- Header, loading, welcome, hero ve footer yuzeyleri ayni tema ailesinde kalmalidir.
- Logo alaninda varsayilan olarak acente logosu kullanilir; proje bazli gorsel tanimliysa override edebilir.
- `formice.png` asset olcusu `1080x1080` olarak not edilmelidir.
- `urojinekoloji.jpg` asset olcusu `1920x774` olarak not edilmelidir.
