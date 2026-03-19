COMPOSE := $(shell if docker compose version >/dev/null 2>&1; then echo "docker compose"; elif docker-compose version >/dev/null 2>&1; then echo "docker-compose"; else echo "docker compose"; fi)
DC := $(COMPOSE) -f docker-compose.yml
CARGO ?= $(shell if command -v cargo >/dev/null 2>&1; then command -v cargo; elif [ -x "$(HOME)/.cargo/bin/cargo" ]; then printf '%s' "$(HOME)/.cargo/bin/cargo"; else printf '%s' cargo; fi)
.DEFAULT_GOAL := help
SERVICE ?=
BACKEND_REPO_PATH ?= ../backend
WORKERS_REPO_PATH ?= ../workers
API_REPO_PATH ?= ../api
BACKEND_PYTEST_ARGS ?= tests -vv --color=yes --tb=short -ra
WORKER_CARGO_TEST_ARGS ?=
EMBEDDING_WORKER_CARGO_TEST_ARGS ?=
RUST_LINUX_X86_TARGET := x86_64-unknown-linux-gnu
DB_BACKUP_DIR ?= ./backups
DB_BACKUP_FILE ?= $(DB_BACKUP_DIR)/manifeed_$(shell date +%Y%m%d_%H%M%S).sql
SQL_FILE ?=

.PHONY: help up build down restart logs clean clean-all db-migrate db-reset db-backup db-recreate-from-sql db-restore test-backend test-worker test-worker-rss test-worker-embedding build-worker-rss-native run-worker-rss-native build-worker-embedding-linux-x86 run-worker-embedding-linux-x86 bundle-worker-embedding-linux export-openapi check-cargo

help:
	@printf '%s\n' 'Available targets:'
	@printf '%s\n' '  make up [SERVICE=name]'
	@printf '%s\n' '  make down'
	@printf '%s\n' '  make logs [SERVICE=name]'
	@printf '%s\n' '  make db-migrate'
	@printf '%s\n' '  make db-reset'
	@printf '%s\n' '  make db-backup [DB_BACKUP_FILE=./backups/file.sql]'
	@printf '%s\n' '  make db-recreate-from-sql SQL_FILE=./backups/file.sql'
	@printf '%s\n' '  make db-restore SQL_FILE=./backups/file.sql'
	@printf '%s\n' '  make test-backend'
	@printf '%s\n' '  make test-worker'
	@printf '%s\n' '  make test-worker-embedding'
	@printf '%s\n' '  make export-openapi'

up:
	@if [ -n "$(SERVICE)" ]; then \
		$(DC) up -d $(SERVICE) --build; \
	else \
		$(DC) up -d --build; \
	fi

build:
	@if [ -n "$(SERVICE)" ]; then \
		$(DC) build $(SERVICE); \
	else \
		$(DC) build; \
	fi

down:
	@if [ -n "$(SERVICE)" ]; then \
		$(DC) stop $(SERVICE); \
	else \
		$(DC) down; \
	fi

restart:
	@if [ -n "$(SERVICE)" ]; then \
		$(DC) restart $(SERVICE); \
	else \
		$(DC) restart; \
	fi

logs:
	@if [ -n "$(SERVICE)" ]; then \
		$(DC) logs -f $(SERVICE); \
	else \
		$(DC) logs -f; \
	fi

clean:
	@if [ -n "$(SERVICE)" ]; then \
		$(DC) rm -f -s $(SERVICE); \
	else \
		$(DC) down --remove-orphans; \
	fi

clean-all:
	@if [ -n "$(SERVICE)" ]; then \
		$(DC) rm -f -s -v $(SERVICE); \
	else \
		$(DC) down -v --remove-orphans --rmi local; \
		docker system prune -af --volumes; \
	fi

db-migrate:
	$(DC) up -d postgres
	$(DC) run --rm --no-deps backend python -c "from app.services.migration_service import run_db_migrations; run_db_migrations()"

db-reset:
	$(DC) up -d postgres
	$(DC) stop backend
	$(DC) run --rm --no-deps backend python -c "from sqlalchemy import create_engine, text; import os; engine=create_engine(os.environ['DATABASE_URL']); conn=engine.connect(); trans=conn.begin(); conn.execute(text('DROP SCHEMA IF EXISTS public CASCADE')); conn.execute(text('CREATE SCHEMA public')); trans.commit(); conn.close()"
	$(DC) run --rm --no-deps backend python -c "from app.services.migration_service import run_db_migrations; run_db_migrations()"
	$(DC) up -d backend

db-backup:
	@backup_file="$(DB_BACKUP_FILE)"; \
	mkdir -p "$$(dirname "$$backup_file")"; \
	$(DC) up -d postgres; \
	$(DC) exec -T postgres sh -lc 'pg_dump -U "$${POSTGRES_USER:-manifeed}" -d "$${POSTGRES_DB:-manifeed}" --clean --if-exists --no-owner --no-privileges' > "$$backup_file"; \
	printf 'Database backup written to %s\n' "$$backup_file"

db-recreate-from-sql:
	@if [ -z "$(SQL_FILE)" ]; then \
		echo "Usage: make db-recreate-from-sql SQL_FILE=./backups/your_dump.sql"; \
		exit 1; \
	fi
	@if [ ! -f "$(SQL_FILE)" ]; then \
		echo "SQL_FILE not found: $(SQL_FILE)"; \
		exit 1; \
	fi
	$(DC) up -d postgres
	$(DC) stop backend
	$(DC) exec -T postgres sh -lc 'psql -v ON_ERROR_STOP=1 -U "$${POSTGRES_USER:-manifeed}" -d "$${POSTGRES_DB:-manifeed}" -c "DROP SCHEMA IF EXISTS public CASCADE; CREATE SCHEMA public;"'
	$(DC) exec -T postgres sh -lc 'psql -v ON_ERROR_STOP=1 -U "$${POSTGRES_USER:-manifeed}" -d "$${POSTGRES_DB:-manifeed}"' < "$(SQL_FILE)"
	$(DC) up -d backend
	@printf 'Database restored from %s\n' "$(SQL_FILE)"

db-restore: db-recreate-from-sql

test-backend:
	$(DC) run --rm --no-deps --build backend sh -lc "PIP_ROOT_USER_ACTION=ignore python -m pip install --disable-pip-version-check --quiet pytest && python -m pytest $(BACKEND_PYTEST_ARGS)"

check-cargo:
	@if [ ! -x "$(CARGO)" ] && ! command -v "$(CARGO)" >/dev/null 2>&1; then \
		echo "cargo not found. Install Rust with rustup or add cargo to PATH."; \
		echo "Expected binary at: $(CARGO)"; \
		exit 127; \
	fi

test-worker-rss: check-cargo
	cd $(WORKERS_REPO_PATH) && $(CARGO) test -p worker-rss $(WORKER_CARGO_TEST_ARGS)

test-worker: test-worker-rss

test-worker-embedding: check-cargo
	cd $(WORKERS_REPO_PATH) && $(CARGO) test -p worker-source-embedding $(EMBEDDING_WORKER_CARGO_TEST_ARGS)

build-worker-rss-native: check-cargo
	cd $(WORKERS_REPO_PATH) && $(CARGO) build --release -p worker-rss

run-worker-rss-native: build-worker-rss-native
	$(WORKERS_REPO_PATH)/target/release/worker-rss

build-worker-embedding-linux-x86: check-cargo
	cd $(WORKERS_REPO_PATH) && $(CARGO) build --release -p worker-source-embedding --target $(RUST_LINUX_X86_TARGET)

run-worker-embedding-linux-x86: build-worker-embedding-linux-x86
	$(WORKERS_REPO_PATH)/target/$(RUST_LINUX_X86_TARGET)/release/worker-source-embedding

bundle-worker-embedding-linux: check-cargo
	cd $(WORKERS_REPO_PATH) && ./installers/linux/worker-source-embedding/build-bundle.sh

export-openapi:
	MANIFEED_BACKEND_PATH=$(BACKEND_REPO_PATH) $(API_REPO_PATH)/scripts/export_openapi.sh
