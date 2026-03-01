# AI Agent Developer Workflow

Bu dokuman, bu repoda AI agent ile calisirken izlenecek pratik gelistirme akisidir.

## 1. Gorevi netlestir

- Tek satir hedef yaz: ne yapilacak, beklenen cikti ne.
- Basari kriterini tanimla: hangi test veya endpoint sonucu dogru sayilacak.
- Kapsam disi konulari belirt: bu turnde ne yapilmayacak.

## 2. Ortami hazirla

- Docker Engine acik olmali.
- Proje kokunde servisleri baslat:

```bash
docker compose up --build -d
```

- Durumu kontrol et:

```bash
docker compose ps
curl http://localhost:8000/health
```

## 3. Hizli kesif yap

- Ilgili dosyalari tara (`README.md`, `docs/spec.md`, `backend/app/*`).
- Degisiklikten etkilenecek endpoint/model/servisleri not et.
- Gerekirse kucuk bir uygulama plani cikar (3-5 adim).

## 4. Uygula

- Degisiklikleri kucuk ve hedefe yonelik parcalar halinde yap.
- API degisiyorsa request/response sozlesmesini koru veya acikca guncelle.
- Gerekirse migration yerine MVP seviyesinde model degisikligini belgeye isle.

## 5. Dogrula

- Pozitif senaryo testi: beklenen girdi ile basarili sonuc.
- Negatif senaryo testi: gecersiz girdi ile dogru hata kodu/mesaji.
- Saglik testi: degisiklik sonrasi `/health` hala `200` olmali.

Ornek:

```bash
curl http://localhost:8000/health
curl -X POST "http://localhost:8000/upload" -F "file=@sample.pdf;type=application/pdf"
curl -X POST "http://localhost:8000/upload" -F "file=@sample.txt;type=text/plain"
```

## 6. Ciktiyi paketle

- Ne degisti: dosya bazli ozet.
- Nasil dogrulandi: komut + sonuc.
- Risk/eksik: varsa acik kalan noktalar.

## 7. Versiyonla

- Uygun commit at.
- Surum gerekiyorsa tag olustur:

```bash
git tag -a v0.1 -m "Transfer Module MVP v0.1"
git push origin v0.1
```

## Kisa kontrol listesi

- [ ] Servisler ayakta mi?
- [ ] Pozitif test gecti mi?
- [ ] Negatif test gecti mi?
- [ ] Dokuman guncellendi mi?
- [ ] Gerekirse tag pushlandi mi?
