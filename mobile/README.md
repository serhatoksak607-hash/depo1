# Creatro Mobile (Expo)

## 1) Kurulum

```bash
cd mobile
npm install
```

## 2) API adresi

Uygulama `EXPO_PUBLIC_API_BASE` kullanır.

- Android emulator: `http://10.0.2.2:8000`
- iOS simulator: `http://127.0.0.1:8000`
- Gerçek cihaz: `http://<PC_LAN_IP>:8000`

PowerShell:

```powershell
$env:EXPO_PUBLIC_API_BASE="http://127.0.0.1:8000"
npm run start
```

## 3) Çalıştırma

```bash
npm run start
```

Expo QR ile Android/iOS cihazda açılabilir.

## 4) Akış

- Login (`/auth/login`)
- Profil çek (`/auth/me`)
- Proje seçimi gerekiyorsa (`/projects` + `/auth/active-project`)
- Ana sayfada `visible_modules` ile modül listesi
- Modül butonları backend web modül URL’lerini açar.
