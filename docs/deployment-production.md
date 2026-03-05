# Production Deployment Notes

## 1) Environment

Create a real production env file from `.env.production.example`.

Minimum required hardening values:
- `APP_ENV=production`
- `CORS_ORIGINS` set to your exact frontend domains
- `TRUSTED_HOSTS` set to your exact API hostnames
- `COOKIE_SECURE=1`
- `COOKIE_SAMESITE=none` (if frontend and API are on different domains)

Example:
- `PUBLIC_BASE_URL=https://www.micetro.org`
- `CORS_ORIGINS=https://www.micetro.org,https://micetro.org`
- `TRUSTED_HOSTS=www.micetro.org,micetro.org`

Do not keep wildcard values (`*`) in production for CORS/hosts.

## 2) Reverse proxy and TLS

- Put API behind HTTPS (Nginx/Caddy/Cloud LB).
- Forward only required headers (`X-Forwarded-For`, `X-Forwarded-Proto`).
- Keep backend container private; expose only proxy port publicly.

## 3) Session behavior

- Admin DB auth uses HTTP-only cookie (`admin_db_session`).
- Idle timeout is controlled by `SESSION_IDLE_MINUTES`.
- Last 59-second warning popup logic in UI should call keepalive endpoint before timeout (already supported by session refresh paths).

## 4) Start

```bash
docker compose up --build -d
```

## 5) Quick checks

```bash
curl https://YOUR_DOMAIN/health
```

Confirm:
- login works
- cookie has `Secure` and expected `SameSite`
- cross-domain requests allowed only for configured origins
- unknown host header is rejected by trusted host policy
