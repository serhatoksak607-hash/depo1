# Production Deployment Notes

## 1) Deployment model

Bu repo web uygulamasi ama Vercel-native bir yapi degil.

Uygun hedefler:
- Docker destekli VPS
- dedicated server
- container calistirabilen platformlar

Vercel'e uygun olmayan mevcut parcalar:
- FastAPI backend container yapisi
- PostgreSQL baglantisi
- Redis queue
- worker sureci
- kalici upload storage

Dogru ayrim:
- GitHub: kaynak kod
- sunucu: calisan uygulama
- Vercel: ancak ayrik frontend cikarsa

## 2) Environment

Create a real production env file from `.env.production.example`.

Minimum required hardening values:
- `APP_ENV=production`
- `PUBLIC_BASE_URL` set to your exact public domain
- `CORS_ORIGINS` set to your exact frontend domains
- `TRUSTED_HOSTS` set to your exact API hostnames
- `APP_ADMIN_PASS` changed from placeholder
- `COOKIE_SECURE=1`
- `COOKIE_SAMESITE=none` (if frontend and API are on different domains)

Do not keep wildcard values (`*`) in production for CORS/hosts.
Do not deploy with `CHANGE_ME` style credentials.

## 3) Reverse proxy and TLS

- Put API behind HTTPS (Nginx/Caddy/Cloud LB).
- Forward only required headers (`X-Forwarded-For`, `X-Forwarded-Proto`).
- Keep backend container private; expose only proxy port publicly.

## 4) Session behavior

- Admin DB auth uses HTTP-only cookie (`admin_db_session`).
- Idle timeout is controlled by `SESSION_IDLE_MINUTES`.
- Last 59-second warning popup logic in UI should call keepalive endpoint before timeout.

## 5) Start

```bash
docker compose up --build -d
```

## 6) Quick checks

```bash
curl https://YOUR_DOMAIN/health
```

Confirm:
- login works
- cookie has `Secure` and expected `SameSite`
- cross-domain requests allowed only for configured origins
- unknown host header is rejected by trusted host policy

## 7) GitHub publish checklist

- `.env` is not committed
- real secrets are not hardcoded in `docker-compose.yml`
- upload files are ignored by git
- `docker compose up --build -d` works locally before push
