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
puis demarre le backend et le frontend.

Services exposes par defaut :

- backend : `http://localhost:8000`
- openapi : `http://localhost:8000/docs`
- frontend admin : `http://localhost:3000`
- postgres : `localhost:5432`

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
