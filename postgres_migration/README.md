# PostgreSQL Migration Module

Ce dossier contient tout ce qui est lie aux migrations PostgreSQL pour Manifeed :

- `alembic/` : scripts et revisions Alembic
- `alembic.ini` : configuration Alembic
- `Dockerfile` : image one-shot de migration
- `requirements.txt` : dependances Python minimales pour executer les migrations

L'orchestration se fait depuis `../docker-compose.yml` via le service `db_migrations`
et depuis `../Makefile` via `make db-migrate` et `make db-reset`.
