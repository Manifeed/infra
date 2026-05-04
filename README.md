# Manifeed Infra

Repo d'orchestration locale du split multi-repo Manifeed.

## Arborescence attendue

```text
Manifeed_multiRepo/
├── auth_service/
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
├── public_api/
├── shared_backend/
├── user_service/
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

`make up` lance `postgres`, `redis` et `qdrant`, applique les migrations Alembic via
`db_migrations`, puis demarre `auth_service`, `user_service`, `admin_service`,
`content_service`, `worker_service`, `public_api`, le frontend et l'edge Nginx.

Le `up` ne force plus de rebuild Docker. Il ne construit une image locale que si
elle n'existe pas encore. Pour reconstruire explicitement une image, utilisez
`make build SERVICE=<service>` ou une cible `build-*`.

Tous les services backend buildent maintenant depuis la racine du monorepo et
embarquent `shared_backend` via une wheel locale construite pendant le build
Docker.

Le trafic edge ne doit etre pris qu'une fois `public_api` declare `healthy`, ce
qui repose maintenant sur `GET /internal/ready` et son code HTTP `200` quand
la gateway est reellement prete.

Services exposes par defaut :

- edge Nginx : `http://localhost`
- postgres : `localhost:5432`

## Commandes utiles

```bash
make logs
make build
make build SERVICE=public_api
make build-public-api
make build-auth-service
make build-user-service
make build-admin-service
make build-content-service
make build-worker-service
make build-frontend-admin
make up SERVICE=admin_service
make up SERVICE=public_api
make up SERVICE=db_migrations
make db-migrate
make db-backup
make db-recreate-from-sql DB_RESTORE_FILE=./backups/manifeed_dump.tar.gz
make test-services
make test-public-api
make test-user-service
make test-worker-service
make test-worker
make test-worker-embedding
```

## Variables de chemins

- `MANIFEED_MULTI_REPO_PATH`
- `ADMIN_SERVICE_REPO_PATH`
- `AUTH_SERVICE_REPO_PATH`
- `CONTENT_SERVICE_REPO_PATH`
- `FRONTEND_REPO_PATH`
- `USER_SERVICE_REPO_PATH`
- `WORKER_SERVICE_REPO_PATH`
- `WORKERS_REPO_PATH`
- `RSS_FEEDS_HOST_PATH`

`MANIFEED_MULTI_REPO_PATH` pointe vers la racine du monorepo pour les builds
backend. Les autres variables restent utiles pour les montages de code source
en local.

## Edge Nginx

La configuration Nginx locale est centralisee dans `infra/nginx/` :

- `nginx/nginx.conf` : point d'entree principal du conteneur
- `nginx/conf.d/edge.conf` : routage edge, headers de securite, rate limiting et proxy
- `nginx/snippets/` : directives partagees
- `nginx/errors/` : page d'erreur HTML et assets associes

Contrat edge actuel :

- `/api/*` -> `public_api`
- `/workers/api/*` -> `worker_service`
- `/` et `/_next/*` -> `frontend_admin`

Les releases workers sont donc telechargees via l'edge, mais servent toujours
des artefacts fournis par `worker_service`.

## Base de donnees et migrations

L'infra porte les operations de maintenance PostgreSQL :

- les fichiers de migration vivent dans `infra/postgres_migration/`
- `make db-migrate` applique ces revisions via le service `db_migrations`
- `make db-reset` recree les bases `content`, `identity` et `workers`, puis reapplique les migrations
- `make db-backup` et `make db-restore` manipulent directement PostgreSQL depuis `infra`

## Sauvegarde et restauration SQL

Sauvegarde des trois bases PostgreSQL dans une archive `tar.gz` :

```bash
make db-backup
```

Chemin personnalise :

```bash
make db-backup DB_BACKUP_FILE=./backups/preprod_20260319.tar.gz
```

Restauration complete des bases `content`, `identity` et `workers` depuis une archive :

```bash
make db-recreate-from-sql DB_RESTORE_FILE=./backups/preprod_20260319.tar.gz
```

Alias equivalent :

```bash
make db-restore DB_RESTORE_FILE=./backups/preprod_20260319.tar.gz
```
