# Manifeed Infra

Repo d'orchestration locale du split multi-repo Manifeed.

## Arborescence attendue

```text
Manifeed_multiRepo/
├── admin_service/
├── content_service/
├── docs/
├── frontend/
├── infra/
│   ├── postgres_migration/
│   ├── backups/
│   ├── nginx/
│   ├── docker-compose.yml
│   └── Makefile
├── worker_service/
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
puis demarre `admin_service`, `content_service`, `public_api`, `worker_service`, le frontend et l'edge Nginx.

Services exposes par defaut :

- edge Nginx : `http://localhost:8080`
- postgres : `localhost:5432`

## Commandes utiles

```bash
make logs
make up SERVICE=admin_service
make up SERVICE=content_service
make up SERVICE=db_migrations
make db-migrate
make db-backup
make db-recreate-from-sql SQL_FILE=./backups/manifeed_dump.sql
make test-services
make test-worker
make test-worker-embedding
```

## Variables de chemins

- `ADMIN_SERVICE_REPO_PATH`
- `CONTENT_SERVICE_REPO_PATH`
- `FRONTEND_REPO_PATH`
- `WORKER_SERVICE_REPO_PATH`
- `WORKERS_REPO_PATH`
- `RSS_FEEDS_HOST_PATH`

Les valeurs par defaut pointent vers les repos freres sous `../`.

## Edge Nginx

La configuration Nginx locale est centralisee dans `infra/nginx/` :

- `nginx/nginx.conf` : point d'entree principal du conteneur
- `nginx/conf.d/edge.conf` : routage edge, headers de securite, rate limiting et proxy
- `nginx/snippets/` : directives partagees
- `nginx/errors/` : page d'erreur HTML et assets associes

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
