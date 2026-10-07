# Deploying Coach Studio

The app is one FastAPI service that serves both the API and the single-page
frontend, plus a PostgreSQL database. Deploying to an HTTPS host is what unlocks
**push notifications** and **"Install app"** on real phones (both require a
secure origin), and means no more running a server on your laptop.

Everything ships in a container ([Dockerfile](Dockerfile)) that runs
`alembic upgrade head` on boot, so migrations apply automatically on every deploy.

---

## 1. Generate production secrets (do NOT reuse the dev ones)

**VAPID keys** (for push). Run locally:

```bash
cd backend
.venv/bin/python - <<'PY'
import base64
from py_vapid import Vapid01
from cryptography.hazmat.primitives import serialization
v = Vapid01(); v.generate_keys()
pub = v.public_key.public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
priv = v.private_key.private_numbers().private_value.to_bytes(32, "big")
print("VAPID_PUBLIC_KEY =", base64.urlsafe_b64encode(pub).rstrip(b"=").decode())
print("VAPID_PRIVATE_KEY=", base64.urlsafe_b64encode(priv).rstrip(b"=").decode())
PY
```

`SECRET_KEY` is generated for you by Render (`generateValue: true`). On other
hosts set a long random value yourself.

---

## 2. Deploy on Render (simplest — provisions DB + HTTPS automatically)

1. Push this repo to GitHub.
2. Render → **New → Blueprint** → select the repo. It reads
   [render.yaml](render.yaml) and creates the web service + Postgres.
   (If Render complains about a plan name, pick a current one in the dashboard.)
3. In the service's **Environment**, fill the secrets left as `sync:false`:
   - `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY`, `VAPID_SUBJECT` (e.g. `mailto:you@example.com`)
   - `ANTHROPIC_API_KEY` (optional — enables AI drill ideas + photo import)
4. Deploy. `DATABASE_URL` is injected from the managed DB, `COOKIE_SECURE=true`
   is set, and migrations run on boot. Visit the service URL — it's HTTPS, so
   install-to-home-screen and push work.

---

## 3. Any other Docker host (Fly.io, Railway, a VM…)

Build and run the same image; provide these env vars:

| Variable | Notes |
|---|---|
| `DATABASE_URL` | `postgresql://…` (a `postgres://` URL is auto-normalized) |
| `SECRET_KEY` | long random string |
| `COOKIE_SECURE` | `true` in production |
| `ANTHROPIC_API_KEY` | optional (AI + photo import) |
| `VAPID_PUBLIC_KEY` / `VAPID_PRIVATE_KEY` / `VAPID_SUBJECT` | push notifications |

```bash
docker build -t coach-studio .
docker run -p 8000:8000 --env-file prod.env coach-studio
```

The container listens on `$PORT` (default 8000) and binds `0.0.0.0`.

---

## Notes
- The frontend uses same-origin relative URLs, so it works under any domain with no rebuild.
- Push/installability need HTTPS (or `localhost`); they will not work over a plain-IP `http://` origin.
- Run `backend/tests` before deploying: `cd backend && .venv/bin/python -m pytest tests -q` (needs Postgres up — `docker compose up -d db`).
