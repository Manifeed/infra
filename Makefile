COMPOSE := $(shell if docker compose version >/dev/null 2>&1; then echo "docker compose"; elif docker-compose version >/dev/null 2>&1; then echo "docker-compose"; else echo "docker compose"; fi)
DC := $(COMPOSE) -f docker-compose.yml
DC_DEV := $(COMPOSE) -f docker-compose.yml -f docker-compose.dev.yml
CARGO ?= $(shell if command -v cargo >/dev/null 2>&1; then command -v cargo; elif [ -x "$(HOME)/.cargo/bin/cargo" ]; then printf '%s' "$(HOME)/.cargo/bin/cargo"; else printf '%s' cargo; fi)
.DEFAULT_GOAL := help

SERVICE ?=
SERVICES ?=
ADMIN_SERVICE_REPO_PATH ?= ../admin_service
AUTH_SERVICE_REPO_PATH ?= ../auth_service
CONTENT_SERVICE_REPO_PATH ?= ../content_service
FRONTEND_REPO_PATH ?= ../frontend
USER_SERVICE_REPO_PATH ?= ../user_service
WORKER_SERVICE_REPO_PATH ?= ../worker_service
WORKERS_REPO_PATH ?= ../workers
SERVICE_PYTEST_ARGS ?= tests -vv --color=yes --tb=short -ra
WORKER_CARGO_TEST_ARGS ?=
EMBEDDING_WORKER_CARGO_TEST_ARGS ?=
RUST_LINUX_X86_TARGET := x86_64-unknown-linux-gnu
DB_BACKUP_DIR ?= ./backups
DB_BACKUP_FILE ?= $(DB_BACKUP_DIR)/manifeed_$(shell date +%Y%m%d_%H%M%S).tar.gz
SQL_FILE ?=
DB_RESTORE_FILE ?= $(SQL_FILE)
DB_MIGRATION_SERVICE ?= db_migrations
QDRANT_BACKUP_DIR ?= ./backups/qdrant
QDRANT_SNAPSHOT_FILE ?=

CORE_INFRA_SERVICES := postgres redis qdrant
BACKEND_APPLICATION_SERVICES := auth_service user_service admin_service content_service worker_service public_api
APPLICATION_SERVICES := $(BACKEND_APPLICATION_SERVICES) frontend_admin edge_nginx
BUILDABLE_APPLICATION_SERVICES := public_api auth_service user_service admin_service content_service worker_service frontend_admin
BUILDABLE_SERVICES := $(DB_MIGRATION_SERVICE) $(BUILDABLE_APPLICATION_SERVICES)
RESETTABLE_APPLICATION_SERVICES := edge_nginx frontend_admin public_api auth_service user_service admin_service content_service worker_service

.PHONY: help dev-up dev-down dev-logs up build build-all build-missing build-db-migrations build-public-api build-auth-service build-user-service build-admin-service build-content-service build-worker-service build-frontend-admin build-traefik-dev down restart logs clean clean-all db-migrate db-reset db-backup db-recreate-from-sql db-restore qdrant-backup qdrant-reset qdrant-restore test-services test-public-api test-admin-service test-content-service test-auth-service test-user-service test-worker-service test-worker test-worker-rss test-worker-embedding build-worker-rss-native run-worker-rss-native build-worker-embedding-linux-x86 run-worker-embedding-linux-x86 release-workers release-workers-desktop release-workers-rss release-workers-embedding release-workers-dry-run check-worker-quality check-cargo

help:
	@printf '%s\n' 'Available targets:'
	@printf '%s\n' '  make up [SERVICE=name]'
	@printf '%s\n' '  make dev-up [SERVICE=name]'
	@printf '%s\n' '  make build [SERVICE=name]'
	@printf '%s\n' '  make build-traefik-dev'
	@printf '%s\n' '  make build-public-api'
	@printf '%s\n' '  make build-auth-service'
	@printf '%s\n' '  make build-user-service'
	@printf '%s\n' '  make build-admin-service'
	@printf '%s\n' '  make build-content-service'
	@printf '%s\n' '  make build-worker-service'
	@printf '%s\n' '  make build-frontend-admin'
	@printf '%s\n' '  make build-db-migrations'
	@printf '%s\n' '  make up SERVICE=public_api'
	@printf '%s\n' '  make up SERVICE=edge_nginx'
	@printf '%s\n' '  make up SERVICE=db_migrations'
	@printf '%s\n' '  make down'
	@printf '%s\n' '  make dev-down'
	@printf '%s\n' '  make logs [SERVICE=name]'
	@printf '%s\n' '  make dev-logs [SERVICE=name]'
	@printf '%s\n' '  make db-migrate'
	@printf '%s\n' '  make db-reset'
	@printf '%s\n' '  make db-backup [DB_BACKUP_FILE=./backups/file.tar.gz]'
	@printf '%s\n' '  make db-recreate-from-sql DB_RESTORE_FILE=./backups/file.tar.gz'
	@printf '%s\n' '  make db-restore DB_RESTORE_FILE=./backups/file.tar.gz'
	@printf '%s\n' '  make qdrant-backup [QDRANT_BACKUP_DIR=./backups/qdrant]'
	@printf '%s\n' '  make qdrant-reset'
	@printf '%s\n' '  make qdrant-restore QDRANT_SNAPSHOT_FILE=./backups/qdrant/your.snapshot'
	@printf '%s\n' '  make test-services'
	@printf '%s\n' '  make test-public-api'
	@printf '%s\n' '  make test-auth-service'
	@printf '%s\n' '  make test-user-service'
	@printf '%s\n' '  make test-admin-service'
	@printf '%s\n' '  make test-content-service'
	@printf '%s\n' '  make test-worker-service'
	@printf '%s\n' '  make test-worker'
	@printf '%s\n' '  make test-worker-embedding'
	@printf '%s\n' '  make check-worker-quality'
	@printf '%s\n' '  make release-workers [RELEASE_WORKER_FAMILIES="desktop rss embedding"]'
	@printf '%s\n' '  make release-workers-dry-run [RELEASE_WORKER_FAMILIES="desktop rss embedding"]'
	@printf '%s\n' '  make release-workers-desktop'
	@printf '%s\n' '  make release-workers-rss'
	@printf '%s\n' '  make release-workers-embedding'
	@printf '\n%s\n' 'Notes:'
	@printf '%s\n' '  - make up no longer forces docker rebuilds.'
	@printf '%s\n' '  - make dev-up also starts Traefik with a self-signed localhost certificate.'
	@printf '%s\n' '  - missing local images are built automatically once, then reused.'
	@printf '%s\n' '  - make build rebuilds all buildable images, or only SERVICE=name when provided.'

dev-up:
	@if [ -n "$(SERVICES)" ]; then \
		echo "Use SERVICE=name with 'make dev-up', not SERVICES=\"...\"."; \
		exit 1; \
	fi
	@if [ -n "$(SERVICE)" ]; then \
		case "$(SERVICE)" in \
			traefik_dev) \
				$(DC_DEV) up -d traefik_dev; \
				;; \
			postgres|redis|qdrant) \
				$(DC_DEV) up -d traefik_dev $(SERVICE); \
				;; \
			$(DB_MIGRATION_SERVICE)) \
				$(DC_DEV) up -d traefik_dev $(CORE_INFRA_SERVICES); \
				$(MAKE) build-missing SERVICE=$(DB_MIGRATION_SERVICE); \
				$(DC_DEV) run --rm --no-deps $(DB_MIGRATION_SERVICE); \
				;; \
			auth_service|user_service|admin_service|content_service|worker_service|public_api|frontend_admin|edge_nginx) \
				$(DC_DEV) up -d traefik_dev $(CORE_INFRA_SERVICES); \
				$(MAKE) build-missing SERVICE=$(DB_MIGRATION_SERVICE); \
				$(DC_DEV) run --rm --no-deps $(DB_MIGRATION_SERVICE); \
				$(MAKE) build-missing SERVICES="$(BUILDABLE_APPLICATION_SERVICES)"; \
				$(DC_DEV) up -d $(SERVICE); \
				;; \
			*) \
				printf 'Unknown service: %s\n' "$(SERVICE)"; \
				printf 'Available services: traefik_dev %s %s edge_nginx\n' "$(CORE_INFRA_SERVICES)" "$(BUILDABLE_SERVICES)"; \
				exit 1; \
				;; \
		esac; \
	else \
		$(DC_DEV) up -d traefik_dev $(CORE_INFRA_SERVICES); \
		$(MAKE) build-missing SERVICE=$(DB_MIGRATION_SERVICE); \
		$(DC_DEV) run --rm --no-deps $(DB_MIGRATION_SERVICE); \
		$(MAKE) build-missing SERVICES="$(BUILDABLE_APPLICATION_SERVICES)"; \
		$(DC_DEV) up -d $(APPLICATION_SERVICES); \
	fi

up:
	@if [ -n "$(SERVICES)" ]; then \
		echo "Use SERVICE=name with 'make up', not SERVICES=\"...\"."; \
		exit 1; \
	fi
	@if [ -n "$(SERVICE)" ]; then \
		case "$(SERVICE)" in \
			postgres|redis|qdrant) \
				$(DC) up -d $(SERVICE); \
				;; \
			$(DB_MIGRATION_SERVICE)) \
				$(DC) up -d $(CORE_INFRA_SERVICES); \
				$(MAKE) build-missing SERVICE=$(DB_MIGRATION_SERVICE); \
				$(DC) run --rm --no-deps $(DB_MIGRATION_SERVICE); \
				;; \
			auth_service|user_service|admin_service|content_service|worker_service|public_api|frontend_admin|edge_nginx) \
				$(DC) up -d $(CORE_INFRA_SERVICES); \
				$(MAKE) build-missing SERVICE=$(DB_MIGRATION_SERVICE); \
				$(DC) run --rm --no-deps $(DB_MIGRATION_SERVICE); \
				$(MAKE) build-missing SERVICES="$(BUILDABLE_APPLICATION_SERVICES)"; \
				$(DC) up -d $(SERVICE); \
				;; \
			*) \
				printf 'Unknown service: %s\n' "$(SERVICE)"; \
				printf 'Available services: %s\n' "$(CORE_INFRA_SERVICES) $(BUILDABLE_SERVICES) edge_nginx"; \
				exit 1; \
				;; \
		esac; \
	else \
		$(DC) up -d $(CORE_INFRA_SERVICES); \
		$(MAKE) build-missing SERVICE=$(DB_MIGRATION_SERVICE); \
		$(DC) run --rm --no-deps $(DB_MIGRATION_SERVICE); \
		$(MAKE) build-missing SERVICES="$(BUILDABLE_APPLICATION_SERVICES)"; \
		$(DC) up -d $(APPLICATION_SERVICES); \
	fi

build:
	@set -e; \
	services="$(SERVICES)"; \
	if [ -z "$$services" ] && [ -n "$(SERVICE)" ]; then services="$(SERVICE)"; fi; \
	if [ -z "$$services" ]; then services="$(BUILDABLE_SERVICES)"; fi; \
	for service in $$services; do \
		case "$$service" in \
			db_migrations|public_api|auth_service|user_service|admin_service|content_service|worker_service|frontend_admin) ;; \
			*) \
				printf 'Unknown buildable service: %s\n' "$$service"; \
				printf 'Buildable services: %s\n' "$(BUILDABLE_SERVICES)"; \
				exit 1; \
				;; \
		esac; \
	done; \
	$(DC) build $$services

build-all: build

build-missing:
	@set -e; \
	services="$(SERVICES)"; \
	if [ -z "$$services" ] && [ -n "$(SERVICE)" ]; then services="$(SERVICE)"; fi; \
	if [ -z "$$services" ]; then services="$(BUILDABLE_SERVICES)"; fi; \
	for service in $$services; do \
		case "$$service" in \
			db_migrations) image="manifeed_db_migrations:local" ;; \
			public_api) image="manifeed_public_api:local" ;; \
			auth_service) image="manifeed_auth_service:local" ;; \
			user_service) image="manifeed_user_service:local" ;; \
			admin_service) image="manifeed_admin_service:local" ;; \
			content_service) image="manifeed_content_service:local" ;; \
			worker_service) image="manifeed_worker_service:local" ;; \
			frontend_admin) image="manifeed_frontend_admin:local" ;; \
			*) \
				printf 'Unknown buildable service: %s\n' "$$service"; \
				printf 'Buildable services: %s\n' "$(BUILDABLE_SERVICES)"; \
				exit 1; \
				;; \
		esac; \
		if ! docker image inspect "$$image" >/dev/null 2>&1; then \
			printf 'Missing image for %s, building %s\n' "$$service" "$$image"; \
			$(DC) build "$$service"; \
		fi; \
	done

build-db-migrations:
	$(DC) build db_migrations

build-public-api:
	$(DC) build public_api

build-auth-service:
	$(DC) build auth_service

build-user-service:
	$(DC) build user_service

build-admin-service:
	$(DC) build admin_service

build-content-service:
	$(DC) build content_service

build-worker-service:
	$(DC) build worker_service

build-frontend-admin:
	$(DC) build frontend_admin

build-traefik-dev:
	$(DC_DEV) build traefik_dev

down:
	@if [ -n "$(SERVICE)" ]; then \
		$(DC) stop $(SERVICE); \
	else \
		$(DC) down; \
	fi

dev-down:
	@if [ -n "$(SERVICE)" ]; then \
		$(DC_DEV) stop $(SERVICE); \
	else \
		$(DC_DEV) down; \
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

dev-logs:
	@if [ -n "$(SERVICE)" ]; then \
		$(DC_DEV) logs -f $(SERVICE); \
	else \
		$(DC_DEV) logs -f; \
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
	$(DC) up -d $(CORE_INFRA_SERVICES)
	$(MAKE) build-missing SERVICE=$(DB_MIGRATION_SERVICE)
	$(DC) run --rm --no-deps $(DB_MIGRATION_SERVICE)

db-reset:
	$(DC) up -d $(CORE_INFRA_SERVICES)
	$(DC) stop $(RESETTABLE_APPLICATION_SERVICES) || true
	$(DC) exec -T postgres sh -lc 'set -e; admin_db="$${POSTGRES_DB:-manifeed_content}"; for db in "$${CONTENT_POSTGRES_DB:-manifeed_content}" "$${IDENTITY_POSTGRES_DB:-manifeed_identity}" "$${WORKERS_POSTGRES_DB:-manifeed_workers}"; do psql -v ON_ERROR_STOP=1 -U "$${POSTGRES_USER:-manifeed}" -d "$$admin_db" -c "DROP DATABASE IF EXISTS \"$$db\" WITH (FORCE);"; psql -v ON_ERROR_STOP=1 -U "$${POSTGRES_USER:-manifeed}" -d "$$admin_db" -c "CREATE DATABASE \"$$db\";"; done'
	$(MAKE) build-missing SERVICE=$(DB_MIGRATION_SERVICE)
	$(DC) run --rm --no-deps $(DB_MIGRATION_SERVICE)
	$(MAKE) qdrant-reset
	$(MAKE) build-missing SERVICES="$(BUILDABLE_APPLICATION_SERVICES)"
	$(DC) up -d $(APPLICATION_SERVICES)

db-backup:
	@backup_file="$(DB_BACKUP_FILE)"; \
	tmp_dir=$$(mktemp -d); \
	trap 'rm -rf "$$tmp_dir"' EXIT; \
	mkdir -p "$$(dirname "$$backup_file")"; \
	$(DC) up -d postgres; \
	for db_spec in content:"$${CONTENT_POSTGRES_DB:-manifeed_content}" identity:"$${IDENTITY_POSTGRES_DB:-manifeed_identity}" workers:"$${WORKERS_POSTGRES_DB:-manifeed_workers}"; do \
		label=$${db_spec%%:*}; \
		db_name=$${db_spec#*:}; \
		$(DC) exec -T postgres sh -lc 'pg_dump -U "$${POSTGRES_USER:-manifeed}" -d "'"$$db_name"'" --clean --if-exists --no-owner --no-privileges' > "$$tmp_dir/$$label.sql"; \
	done; \
	tar -czf "$$backup_file" -C "$$tmp_dir" content.sql identity.sql workers.sql; \
	printf 'Database backup bundle written to %s\n' "$$backup_file"

db-recreate-from-sql:
	@if [ -z "$(DB_RESTORE_FILE)" ]; then \
		echo "Usage: make db-recreate-from-sql DB_RESTORE_FILE=./backups/your_bundle.tar.gz"; \
		exit 1; \
	fi
	@if [ ! -f "$(DB_RESTORE_FILE)" ]; then \
		echo "DB_RESTORE_FILE not found: $(DB_RESTORE_FILE)"; \
		exit 1; \
	fi
	@tmp_dir=$$(mktemp -d); \
	trap 'rm -rf "$$tmp_dir"' EXIT; \
	tar -xzf "$(DB_RESTORE_FILE)" -C "$$tmp_dir"; \
	for sql_file in content.sql identity.sql workers.sql; do \
		if [ ! -f "$$tmp_dir/$$sql_file" ]; then \
			echo "Missing $$sql_file in $(DB_RESTORE_FILE)"; \
			exit 1; \
		fi; \
	done; \
	$(DC) up -d $(CORE_INFRA_SERVICES); \
	$(DC) stop $(RESETTABLE_APPLICATION_SERVICES) || true; \
	$(DC) exec -T postgres sh -lc 'set -e; admin_db="$${POSTGRES_DB:-manifeed_content}"; for db in "$${CONTENT_POSTGRES_DB:-manifeed_content}" "$${IDENTITY_POSTGRES_DB:-manifeed_identity}" "$${WORKERS_POSTGRES_DB:-manifeed_workers}"; do psql -v ON_ERROR_STOP=1 -U "$${POSTGRES_USER:-manifeed}" -d "$$admin_db" -c "DROP DATABASE IF EXISTS \"$$db\" WITH (FORCE);"; psql -v ON_ERROR_STOP=1 -U "$${POSTGRES_USER:-manifeed}" -d "$$admin_db" -c "CREATE DATABASE \"$$db\";"; done'; \
	$(DC) exec -T postgres sh -lc 'psql -v ON_ERROR_STOP=1 -U "$${POSTGRES_USER:-manifeed}" -d "$${CONTENT_POSTGRES_DB:-manifeed_content}"' < "$$tmp_dir/content.sql"; \
	$(DC) exec -T postgres sh -lc 'psql -v ON_ERROR_STOP=1 -U "$${POSTGRES_USER:-manifeed}" -d "$${IDENTITY_POSTGRES_DB:-manifeed_identity}"' < "$$tmp_dir/identity.sql"; \
	$(DC) exec -T postgres sh -lc 'psql -v ON_ERROR_STOP=1 -U "$${POSTGRES_USER:-manifeed}" -d "$${WORKERS_POSTGRES_DB:-manifeed_workers}"' < "$$tmp_dir/workers.sql"; \
	$(MAKE) build-missing SERVICES="$(BUILDABLE_APPLICATION_SERVICES)"; \
	$(DC) up -d $(APPLICATION_SERVICES); \
	printf 'Database bundle restored from %s\n' "$(DB_RESTORE_FILE)"

db-restore: db-recreate-from-sql

qdrant-backup:
	@set -e; \
	if [ -f .env ]; then set -a; . ./.env; set +a; fi; \
	port="$${QDRANT_PORT:-6333}"; \
	coll="$${QDRANT_COLLECTION_NAME:-article_embeddings}"; \
	backup_dir="$(QDRANT_BACKUP_DIR)"; \
	mkdir -p "$$backup_dir"; \
	$(DC) up -d qdrant; \
	sleep 2; \
	base_url="http://127.0.0.1:$$port"; \
	if [ -n "$$QDRANT_API_KEY" ]; then \
		coll_http=$$(curl -sS -o /dev/null -w '%{http_code}' -H "api-key: $$QDRANT_API_KEY" "$$base_url/collections/$$coll"); \
	else \
		coll_http=$$(curl -sS -o /dev/null -w '%{http_code}' "$$base_url/collections/$$coll"); \
	fi; \
	if [ "$$coll_http" = "404" ]; then \
		printf 'qdrant-backup skipped: collection "%s" does not exist yet (POST /snapshots returns 404). Index at least one embedding or fix QDRANT_COLLECTION_NAME.\n' "$$coll"; \
		exit 0; \
	fi; \
	if [ "$$coll_http" != "200" ]; then \
		printf 'qdrant-backup failed: GET %s/collections/%s returned HTTP %s\n' "$$base_url" "$$coll" "$$coll_http"; \
		exit 1; \
	fi; \
	if [ -n "$$QDRANT_API_KEY" ]; then \
		create_json=$$(curl -sS -f -X POST "$$base_url/collections/$$coll/snapshots?wait=true" -H "api-key: $$QDRANT_API_KEY"); \
	else \
		create_json=$$(curl -sS -f -X POST "$$base_url/collections/$$coll/snapshots?wait=true"); \
	fi; \
	snap_name=$$(printf '%s' "$$create_json" | python3 -c 'import json,sys; print(json.load(sys.stdin)["result"]["name"])'); \
	ts=$$(date +%Y%m%d_%H%M%S); \
	out_file="$$backup_dir/$${coll}_$${ts}_$${snap_name}"; \
	if [ -n "$$QDRANT_API_KEY" ]; then \
		curl -sS -f -o "$$out_file" "$$base_url/collections/$$coll/snapshots/$$snap_name" -H "api-key: $$QDRANT_API_KEY"; \
	else \
		curl -sS -f -o "$$out_file" "$$base_url/collections/$$coll/snapshots/$$snap_name"; \
	fi; \
	printf 'Qdrant snapshot written to %s\n' "$$out_file"

qdrant-reset:
	@set -e; \
	if [ -f .env ]; then set -a; . ./.env; set +a; fi; \
	port="$${QDRANT_PORT:-6333}"; \
	coll="$${QDRANT_COLLECTION_NAME:-article_embeddings}"; \
	$(DC) up -d qdrant; \
	sleep 2; \
	base_url="http://127.0.0.1:$$port"; \
	if [ -n "$$QDRANT_API_KEY" ]; then \
		http=$$(curl -sS -o /dev/null -w '%{http_code}' -X DELETE "$$base_url/collections/$$coll" -H "api-key: $$QDRANT_API_KEY"); \
	else \
		http=$$(curl -sS -o /dev/null -w '%{http_code}' -X DELETE "$$base_url/collections/$$coll"); \
	fi; \
	if [ "$$http" != "200" ] && [ "$$http" != "202" ] && [ "$$http" != "404" ]; then \
		printf 'qdrant-reset failed: DELETE %s/collections/%s returned HTTP %s\n' "$$base_url" "$$coll" "$$http"; \
		exit 1; \
	fi; \
	printf 'Qdrant collection %s reset\n' "$$coll"

qdrant-restore:
	@if [ -z "$(QDRANT_SNAPSHOT_FILE)" ]; then \
		echo "Usage: make qdrant-restore QDRANT_SNAPSHOT_FILE=./backups/qdrant/article_embeddings_YYYYMMDD_HHMMSS_....snapshot"; \
		exit 1; \
	fi
	@if [ ! -f "$(QDRANT_SNAPSHOT_FILE)" ]; then \
		echo "QDRANT_SNAPSHOT_FILE not found: $(QDRANT_SNAPSHOT_FILE)"; \
		exit 1; \
	fi
	@set -e; \
	if [ -f .env ]; then set -a; . ./.env; set +a; fi; \
	port="$${QDRANT_PORT:-6333}"; \
	coll="$${QDRANT_COLLECTION_NAME:-article_embeddings}"; \
	base_url="http://127.0.0.1:$$port"; \
	snapfile="$(QDRANT_SNAPSHOT_FILE)"; \
	$(DC) stop $(RESETTABLE_APPLICATION_SERVICES) || true; \
	$(DC) up -d qdrant; \
	sleep 2; \
	if [ -n "$$QDRANT_API_KEY" ]; then \
		curl -sS -f --connect-timeout 10 --max-time 3600 \
			-X POST "$$base_url/collections/$$coll/snapshots/upload?wait=true&priority=snapshot" \
			-H "api-key: $$QDRANT_API_KEY" \
			-F "snapshot=@$$snapfile"; \
	else \
		curl -sS -f --connect-timeout 10 --max-time 3600 \
			-X POST "$$base_url/collections/$$coll/snapshots/upload?wait=true&priority=snapshot" \
			-F "snapshot=@$$snapfile"; \
	fi; \
	$(MAKE) build-missing SERVICES="$(BUILDABLE_APPLICATION_SERVICES)"; \
	$(DC) up -d $(APPLICATION_SERVICES); \
	printf 'Qdrant collection %s restored from %s\n' "$$coll" "$$snapfile"

test-public-api:
	$(DC) run --rm --no-deps --build public_api sh -lc "python -m pytest $(SERVICE_PYTEST_ARGS)"

test-admin-service:
	$(DC) run --rm --no-deps --build admin_service sh -lc "PIP_ROOT_USER_ACTION=ignore python -m pip install --disable-pip-version-check --quiet pytest && python -m pytest $(SERVICE_PYTEST_ARGS)"

test-content-service:
	$(DC) run --rm --no-deps --build content_service sh -lc "PIP_ROOT_USER_ACTION=ignore python -m pip install --disable-pip-version-check --quiet pytest && python -m pytest $(SERVICE_PYTEST_ARGS)"

test-auth-service:
	$(DC) run --rm --no-deps --build auth_service sh -lc "python -m pytest $(SERVICE_PYTEST_ARGS)"

test-user-service:
	$(DC) run --rm --no-deps --build user_service sh -lc "python -m pytest $(SERVICE_PYTEST_ARGS)"

test-worker-service:
	$(DC) run --rm --no-deps --build worker_service sh -lc "python -m pytest $(SERVICE_PYTEST_ARGS)"

test-services: test-public-api test-admin-service test-content-service test-auth-service test-user-service test-worker-service

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

check-worker-quality: check-cargo
	cd $(WORKERS_REPO_PATH) && python3 ./scripts/check_file_lengths.py .
	cd $(WORKERS_REPO_PATH) && $(CARGO) clippy --workspace --all-targets

build-worker-rss-native: check-cargo
	cd $(WORKERS_REPO_PATH) && $(CARGO) build --release -p worker-rss

run-worker-rss-native: build-worker-rss-native
	$(WORKERS_REPO_PATH)/target/release/worker-rss

build-worker-embedding-linux-x86: check-cargo
	cd $(WORKERS_REPO_PATH) && $(CARGO) build --release -p worker-source-embedding --target $(RUST_LINUX_X86_TARGET)

run-worker-embedding-linux-x86: build-worker-embedding-linux-x86
	$(WORKERS_REPO_PATH)/target/$(RUST_LINUX_X86_TARGET)/release/worker-source-embedding

release-workers: check-cargo
	cd $(WORKERS_REPO_PATH) && bash ./installers/release-workers.sh $(foreach family,$(RELEASE_WORKER_FAMILIES),--family $(family))

release-workers-dry-run: check-cargo
	cd $(WORKERS_REPO_PATH) && bash ./installers/release-workers.sh --dry-run $(foreach family,$(RELEASE_WORKER_FAMILIES),--family $(family))

release-workers-desktop: check-cargo
	cd $(WORKERS_REPO_PATH) && bash ./installers/release-workers.sh --family desktop

release-workers-rss: check-cargo
	cd $(WORKERS_REPO_PATH) && bash ./installers/release-workers.sh --family rss

release-workers-embedding: check-cargo
	cd $(WORKERS_REPO_PATH) && bash ./installers/release-workers.sh --family embedding
