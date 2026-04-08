# Live Bridge

Bu klasor `localhost:3000` uzerindeki ekranlari Playwright ile canli kontrol etmek icindir.

Amac:
- DOM ve buton davranisini dogrulamak
- console/network hatalarini yakalamak
- tablo, modal, popup ve filtre akislarini test etmek

Ilk kurulum:
- `npm install`
- `npx playwright install chromium`

Hazir komutlar:
- `npm run open:kayit`
- `npm run open:transfer`
- `npm run smoke:kayit`
- `npm run smoke:transfer`

Not:
- Login/session hazir oldugunda sayfa dogrudan acilir.
- Gerekirse sonra otomatik login helper da eklenebilir.
