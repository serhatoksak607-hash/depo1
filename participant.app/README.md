# Creatro Participant (Expo)

Bu klasör katılımcı uygulamasının Expo tabanlı istemcisidir.

## Kurulum

```bash
cd participant.app
npm install
```

## API adresi

Uygulama `EXPO_PUBLIC_API_BASE` kullanır.

- Android emulator: `http://10.0.2.2:8000`
- iOS simulator: `http://127.0.0.1:8000`
- Gerçek cihaz: `http://<PC_LAN_IP>:8000`

PowerShell:

```powershell
$env:EXPO_PUBLIC_API_BASE="http://127.0.0.1:8000"
npm run start
```

## Akış

- Login ve header tarafında varsayılan görsel acente logosudur.
- Alt proje için özel görsel tanımlıysa acente logosunun yerine o görsel kullanılır.
- Tema önceliği acente renkleridir; proje tema renkleri tanımlıysa onlar override eder.
- Ana sponsor alanı participant tarafında plaka yerine kullanılır.
- Hero kartta `Toplantı Modülü` yer alır.
- Hero altında `Program Akışı`, `Bildiriler`, `Sertifikalar`, `Kurslar` kartları bulunur.
- `Masraflarım` yerine `Duyurular`, `Görevlerim` yerine `Rezervasyonlarım` kullanılır.
- `Rezervasyonlarım` içinde transfer ve konaklama bilgileri görünür; ileride değişiklik talebi açılabilir.
- Katılımcı QR okutulduğunda:
  - transfer akışı için transfer sponsoru teşekkür görseli,
  - kayıt veya konaklama akışı için kayıt-konaklama sponsoru teşekkür görseli açılır.

## Vercel

Bu Expo istemcisi web preview olarak Vercel'e deploy edilebilir.
Bu, native iOS/Android paketinin yerine geçmez; web preview sunar.

## APK / Android Build

Participant istemcisi web düzeni korunarak Android APK olarak da alınabilir.

Hazir komutlar:

```bash
cd participant.app
npm run build:apk
```

Production Android bundle:

```bash
cd participant.app
npm run build:aab
```

Notlar:
- APK için Expo EAS hesabında login gerekir.
- preview profili `.apk`, production profili `.aab` üretir.
- Android package kimliği: `com.creatro.participant`
