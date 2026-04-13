# Manifeed Infra

Repo d'orchestration locale du split multi-repo Manifeed.

## Arborescence attendue

```text
Manifeed_multiRepo/
├── api/
├── backend/
├── docs/
├── frontend/
├── infra/
│   ├── postgres_migration/
│   ├── backups/
│   ├── docker-compose.yml
│   └── Makefile
└── workers/
```

Le catalogue RSS reste un depot externe et peut etre monte via `RSS_FEEDS_HOST_PATH`.

## Demarrage rapide

```bash
cp .env.example .env
make help
make up
```

`make up` lance PostgreSQL, applique les migrations Alembic via le service `db_migrations`,
puis demarre le backend, le frontend et la gateway Nginx locale.

Services exposes par defaut :

- app gateway : `http://localhost:3000`
- openapi backend via gateway : `http://localhost:3000/docs`
- postgres : `localhost:5432`

Le navigateur appelle desormais directement le backend sur le meme host via la gateway :

- `GET/POST /api/*` vers le backend FastAPI
- `GET/POST /workers/*` vers le backend FastAPI
- toutes les autres pages vers Next.js

## Commandes utiles

```bash
make logs
make up SERVICE=backend
make up SERVICE=db_migrations
make db-migrate
make db-backup
make db-recreate-from-sql SQL_FILE=./backups/manifeed_dump.sql
make test-backend
make test-worker
make test-worker-embedding
make export-openapi
```

## Variables de chemins

- `BACKEND_REPO_PATH`
- `FRONTEND_REPO_PATH`
- `WORKERS_REPO_PATH`
- `API_REPO_PATH`
- `RSS_FEEDS_HOST_PATH`

Les valeurs par defaut pointent vers les repos freres sous `../`.

## Base de donnees et migrations

L'infra porte les operations de maintenance PostgreSQL :

- les fichiers de migration vivent dans `infra/postgres_migration/`
- `make db-migrate` applique ces revisions via le service `db_migrations`
- `make db-reset` recree le schema `public` avec `psql`, puis reapplique les migrations
- `make db-backup` et `make db-restore` manipulent directement PostgreSQL depuis `infra`

## Sauvegarde et restauration SQL

Sauvegarde de la base dans `./backups/` :

```bash
make db-backup
```

Chemin personnalise :

```bash
make db-backup DB_BACKUP_FILE=./backups/preprod_20260319.sql
```

Recreation complete de la base a partir d'un dump SQL :

```bash
make db-recreate-from-sql SQL_FILE=./backups/preprod_20260319.sql
```

Alias equivalent :

```bash
make db-restore SQL_FILE=./backups/preprod_20260319.sql
```
