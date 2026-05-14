# Manifeed Infra

Local orchestration repo for the Manifeed multi-repo stack.

## Expected Workspace Layout

```text
Manifeed_multiRepo/
├── admin_service/
├── auth_service/
├── content_service/
├── frontend/
├── indexer_service/
├── infra/
│   ├── backups/
│   ├── nginx/
│   ├── postgres_migration/
│   ├── docker-compose.yml
│   ├── docker-compose.dev.yml
│   └── Makefile
├── public_api/
├── shared_backend/
├── user_service/
├── worker_service/
└── workers/
```

The RSS catalog remains an external repository and can be mounted through
`RSS_FEEDS_HOST_PATH`.

## Quick Start

```bash
cp .env.example .env
make help
make up
```

For the full local developer stack with Traefik and a self-signed certificate
for `https://localhost`:

```bash
cp .env.example .env
make dev-up
```

The first run builds `manifeed_traefik_dev:local`, creates the local
certificate, and exposes:

- `https://localhost`
- `http://localhost` redirected to HTTPS
- `https://traefik.localhost` for the Traefik dashboard

## What `make up` Does

`make up` starts `postgres`, `redis`, and `qdrant`, runs the one-shot
`db_migrations` service, then starts `auth_service`, `user_service`,
`admin_service`, `content_service`, `indexer_service`, `worker_service`,
`public_api`, `frontend_admin`, and `edge_nginx`.

`make up` does not force Docker rebuilds anymore. Missing local images are
built once and then reused. Use `make build SERVICE=<service>` or one of the
`build-*` targets when you want a fresh rebuild.

## Networking

- Stateful services are internal-only by default. `postgres`, `redis`, and
  `qdrant` do not publish host ports in the main compose file.
- `edge_nginx` is internal-only as well. Production-style ingress is expected
  to come from Traefik through the external Docker network
  `${TRAEFIK_NETWORK_NAME:-traefik_proxy}`.
- `docker-compose.dev.yml` adds a local Traefik entrypoint on ports `80`,
  `443`, and `8088`.

Expected public traffic flow:

`Client -> Traefik HTTPS/domain -> nginx internal HTTP -> public_api -> internal services`

## Useful Commands

```bash
make logs
make dev-logs
make build
make build SERVICE=public_api
make build-traefik-dev
make up SERVICE=admin_service
make up SERVICE=public_api
make up SERVICE=db_migrations
make dev-up SERVICE=edge_nginx
make db-migrate
make db-reset
make db-backup
make db-recreate-from-sql DB_RESTORE_FILE=./backups/manifeed_dump.tar.gz
make qdrant-backup
make qdrant-reset
make qdrant-restore QDRANT_SNAPSHOT_FILE=./backups/qdrant/your.snapshot
make test-services
make test-public-api
make test-auth-service
make test-user-service
make test-admin-service
make test-content-service
make test-worker-service
make test-worker
```

## Repository and Path Variables

- `PUBLIC_API_REPO_PATH`
- `SHARED_BACKEND_REPO_PATH`
- `ADMIN_SERVICE_REPO_PATH`
- `AUTH_SERVICE_REPO_PATH`
- `CONTENT_SERVICE_REPO_PATH`
- `INDEXER_SERVICE_REPO_PATH`
- `FRONTEND_REPO_PATH`
- `USER_SERVICE_REPO_PATH`
- `WORKER_SERVICE_REPO_PATH`
- `WORKERS_REPO_PATH`
- `RSS_FEEDS_HOST_PATH`
- `RSS_FEEDS_REPOSITORY_PATH`

## Edge Nginx

The local Nginx edge configuration lives in `infra/nginx/`:

- `nginx/nginx.conf`: container entrypoint config
- `nginx/conf.d/edge.conf`: routing, security headers, rate limiting, and proxy rules
- `nginx/snippets/`: shared directives
- `nginx/errors/`: HTML error pages and static assets

Current edge contract:

- `/api/*` -> `public_api`
- `/install` -> `public_api`
- `/workers/api/*` -> `worker_service`
- `/` and `/_next/*` -> `frontend_admin`

After editing `nginx/conf.d/edge.conf`, reload Nginx with:

```bash
docker compose exec edge_nginx nginx -s reload
```

## PostgreSQL Migrations

All PostgreSQL migration assets live in `infra/postgres_migration/`.

The migration service now runs three independent Alembic histories:

- `alembic_content.ini` -> `alembic/versions/content/1_0_baseline.py`
- `alembic_identity.ini` -> `alembic/versions/identity/1_0_baseline.py`
- `alembic_workers.ini` -> `alembic/versions/workers/1_0_baseline.py`

This keeps `content`, `identity`, and `workers` fully separated while still
using the same `db_migrations` container.

Useful database targets:

- `make db-migrate`: create missing databases and apply all three baselines
- `make db-reset`: recreate `content`, `identity`, and `workers`, then apply migrations
- `make db-backup`: export all three PostgreSQL databases into one `tar.gz`
- `make db-restore`: recreate and restore the bundled SQL dumps

## SQL Backup and Restore

Create a bundled backup:

```bash
make db-backup
```

Use a custom output path:

```bash
make db-backup DB_BACKUP_FILE=./backups/preprod_20260319.tar.gz
```

Restore the full bundle:

```bash
make db-recreate-from-sql DB_RESTORE_FILE=./backups/preprod_20260319.tar.gz
```

Alias:

```bash
make db-restore DB_RESTORE_FILE=./backups/preprod_20260319.tar.gz
```

## Qdrant Backup and Restore

Qdrant maintenance commands use the internal Docker network instead of host
port publishing, so the default stack stays private.

- `make qdrant-backup`
- `make qdrant-reset`
- `make qdrant-restore QDRANT_SNAPSHOT_FILE=./backups/qdrant/your.snapshot`
