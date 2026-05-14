# PostgreSQL Migration Module

This directory contains the full PostgreSQL migration runtime for Manifeed.

## Layout

- `alembic/`: shared Alembic environment and script template
- `alembic/versions/content/`: independent content DB history
- `alembic/versions/identity/`: independent identity DB history
- `alembic/versions/workers/`: independent workers DB history
- `alembic_content.ini`: Alembic config for the content database
- `alembic_identity.ini`: Alembic config for the identity database
- `alembic_workers.ini`: Alembic config for the workers database
- `migrate_all.py`: creates missing databases and applies all three histories
- `Dockerfile`: one-shot migration image
- `requirements.txt`: minimal Python dependencies required to run migrations

## Execution

The module is orchestrated from `../docker-compose.yml` through the
`db_migrations` service and from `../Makefile` through:

- `make db-migrate`
- `make db-reset`
