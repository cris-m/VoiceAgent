# Nginx

Reverse proxy that fronts the client, backend, and agent services behind a single port. In dev it listens on `:8080` and proxies to the running containers. In production it sits at the edge with TLS in front of it.

For overall architecture see [`../docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md).

## Layout

```
nginx/
├── Dockerfile
└── config/
    ├── nginx-dev.conf   Dev: proxies to Vite (HMR) + backend + agent
    ├── nginx.conf       Production: proxies built client assets + backend + agent
    └── proxy.conf       Shared upstream block + common proxy headers
```

The dev image and the production image are the same Dockerfile. The compose file picks which config to mount.

## Routes

| Path | Upstream | Notes |
|---|---|---|
| `/api/v1/voice/ws` | `backend:8000` | WebSocket upgrade. Long timeouts and `proxy_buffering off` so audio frames flow without sitting in a buffer. |
| `/api/v1/*` | `backend:8000` | All other backend HTTP routes. Must come before `/api/` so it matches first. |
| `/api/*` | `agent:8000` | LangGraph SDK passthrough (threads, runs, streams). |
| `/ws/*` | `agent:8000` | LangGraph WebSocket. |
| `/static/*` | `backend:8000` | Generated narrations, music, and clone audio. |
| `/health` | nginx | Returns 200 from nginx itself, no upstream call. |
| `/` | client | Vite dev server in dev, the built `dist/` in production. |

The order of `location` blocks matters. `/api/v1/` is a longer prefix and must come before `/api/`, otherwise every backend call would be sent to the agent.

## Dev versus prod

`nginx-dev.conf` differences from `nginx.conf`:

- Listens on a single host (`server_name localhost`) instead of accepting any host.
- Proxies `/` straight to the Vite dev server so HMR works.
- Allows the WebSocket upgrade for `/` so Vite's HMR socket connects.
- Uses Docker's embedded resolver (`resolver 127.0.0.11`) so service-name DNS resolves at runtime when containers restart.

`nginx.conf` differences:

- Serves the built client bundle directly with cache-control rules per asset type (long-cache for hashed JS/CSS/fonts, no-cache for HTML).
- Accepts any host; the load balancer in front of it terminates TLS and forwards X-Forwarded-Proto.
- No HMR or dev-only relaxations.

## Run it

The dev stack mounts the dev config:

```bash
docker compose -f ../docker-compose.dev.yml up -d nginx
# Open http://localhost:8080
```

Test config syntax against either file without starting the stack:

```bash
docker run --rm \
  -v "$PWD/config/nginx-dev.conf:/etc/nginx/nginx.conf:ro" \
  -v "$PWD/config/proxy.conf:/etc/nginx/proxy.conf:ro" \
  nginx:1.27-alpine nginx -t
```

## WebSocket support

Voice mode requires the WebSocket upgrade headers to flow through. The dev config sets these in the `/api/v1/voice/ws` block:

```nginx
proxy_http_version 1.1;
proxy_set_header Upgrade $http_upgrade;
proxy_set_header Connection $connection_upgrade;
proxy_read_timeout 86400;
proxy_send_timeout 86400;
proxy_buffering off;
```

The 24-hour read timeout is intentional. Voice conversations stay open for a long time, and a shorter timeout silently kills the orb after a quiet pause.

## Caching

The production config caches static assets aggressively and refuses to cache HTML:

- `*.js`, `*.css`, `*.png`, `*.woff2`, etc.: `Cache-Control: public, max-age=31536000, immutable` (one year).
- `*.html`: `Cache-Control: no-cache` so a fresh deploy always serves the new entry point.
- `/static/` (generated audio): `expires -1` so a regenerated narration is never served stale.

## Production checklist

This config doesn't terminate TLS itself. Put a load balancer or a TLS-terminating proxy in front of it. Suggested setup:

1. Provision a TLS cert (Let's Encrypt via Certbot, or a managed cert from your cloud).
2. Terminate TLS at the LB and forward HTTP to nginx on port 80, with `X-Forwarded-Proto: https`.
3. Set the backend `CORS_ORIGINS` to your production domain.
4. Pin the nginx image tag (`nginx:1.27-alpine` rather than `nginx:alpine`).
5. Set `client_max_body_size` to whatever your largest narration / cloning upload is. Default is 1MB which will reject voice clone uploads.

## Common issues

- **502 Bad Gateway**. The upstream container is not running or is not yet healthy. Check `docker compose logs backend` or `agent`. The dev config relies on Docker's embedded DNS, so a container that hasn't started yet looks like a DNS failure.
- **WebSocket disconnects after 60 seconds**. Something in front of nginx is enforcing a shorter idle timeout. Check the load balancer or any reverse proxy ahead of nginx.
- **CORS errors in the browser**. CORS is handled by the backend, not nginx. Set `CORS_ORIGINS` in `backend/.env` to the origin the browser shows.
- **Voice cloning upload fails with 413**. Bump `client_max_body_size` in the relevant `location` block.
