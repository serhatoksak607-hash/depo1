# Creatro Participant (Expo)

Bu klasor katilimci uygulamasinin Expo tabanli istemcisidir.

## Kurulum

```bash
cd participant.app
npm install
```

## API adresi

Uygulama `EXPO_PUBLIC_API_BASE` kullanir.

- Android emulator: `http://10.0.2.2:8000`
- iOS simulator: `http://127.0.0.1:8000`
- Gercek cihaz: `http://<PC_LAN_IP>:8000`

PowerShell:

```powershell
$env:EXPO_PUBLIC_API_BASE="http://127.0.0.1:8000"
npm run start
```

## Akis

- Login ve header tarafinda varsayilan gorsel acenta logosudur.
- Alt proje icin ozel gorsel tanimliysa acenta logosunun yerine o gorsel kullanilir.
- Tema onceligi acenta renkleridir; proje tema renkleri tanimliysa onlar override eder.
- Ana sponsor alani participant tarafinda plaka yerine kullanilir.
- Hero kartta `Toplanti Modulu` yer alir.
- Hero altinda `Program Akisi`, `Bildiriler`, `Sertifikalar`, `Kurslar` kartlari bulunur.
- `Masraflarim` yerine `Duyurular`, `Gorevlerim` yerine `Rezervasyonlarim` kullanilir.
- `Rezervasyonlarim` icinde transfer ve konaklama bilgileri gorunur; ileride degisiklik talebi acilabilir.
- Katilimci QR okutuldugunda:
  - transfer akisi icin transfer sponsoru tesekkur gorseli,
  - kayit veya konaklama akisi icin kayit-konaklama sponsoru tesekkur gorseli acilir.

## Vercel

Bu Expo istemcisi web preview olarak Vercel'e deploy edilebilir.
Bu, native iOS/Android paketinin yerine gecmez; web preview sunar.
