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

Before `make up`, configure the remote GPU services explicitly:

- `EMBEDDING_SERVICE_URL`
- `EMBEDDING_SERVICE_API_KEY`
- `NER_SERVICE_URL`
- `NER_SERVICE_API_KEY`

`infra` no longer builds or runs `ner_service`, and it does not assume that
`ner_service` or `bge-m3_inference` share a Docker network with the rest of
the stack.

For the full local developer stack with Traefik and a self-signed certificate
for `https://localhost`:

```bash
cp .env.example .env
make dev-up
```

## What `make up` Does

`make up` starts `postgres`, `redis`, and `qdrant`, runs the one-shot
`db_migrations` service, then starts `auth_service`, `user_service`,
`admin_service`, `content_service`, `indexer_service`, `worker_service`,
`public_api`, `frontend_admin`, and `edge_nginx`.

GPU inference remains external and is consumed only over HTTP.

## Networking

- Internal application services stay on the internal Docker network managed by
  `infra`.
- `ner_service` and `bge-m3_inference` are now expected to be reachable over
  their configured HTTP URLs, including when they run on separate GPU hosts.
- `docker-compose.dev.yml` still adds a local Traefik entrypoint on ports `80`,
  `443`, and `8088`.

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
make test-indexer-service
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
