PYTHON ?= python
BACKEND_DIR := backend
TF_DIR := infra
LOCAL_ENV_FILE := .env.local
LOCAL_TENANT_ID ?= tenant-local
LOCAL_USER_ID ?= user-local
PROPERTY_NAME ?= HQ
PROPERTY_ADDRESS ?= Main Street 1

.PHONY: format lint test migrate check-local-env migrate-local db-check-local test-local test-integration-local invoke-local-health invoke-local-list-properties invoke-local-create-property tf-fmt

format:
	cd $(BACKEND_DIR) && $(PYTHON) -m ruff format src tests migrations

lint:
	cd $(BACKEND_DIR) && $(PYTHON) -m ruff check src tests migrations

test:
	cd $(BACKEND_DIR) && $(PYTHON) -m pytest -q

migrate:
	cd $(BACKEND_DIR) && $(PYTHON) -m alembic upgrade head

check-local-env:
	cd $(BACKEND_DIR) && test -f $(LOCAL_ENV_FILE) || (echo "Missing $(BACKEND_DIR)/$(LOCAL_ENV_FILE). Copy $(BACKEND_DIR)/.env.local.example first." && exit 1)

migrate-local: check-local-env
	cd $(BACKEND_DIR) && set -a && . ./$(LOCAL_ENV_FILE) && set +a && DATABASE_URL="postgresql+psycopg://$$DB_USER:$$DB_PASSWORD@$$DB_HOST:$$DB_PORT/$$DB_NAME" $(PYTHON) -m alembic upgrade head

db-check-local: check-local-env
	cd $(BACKEND_DIR) && set -a && . ./$(LOCAL_ENV_FILE) && set +a && PGPASSWORD="$$DB_PASSWORD" psql -h "$$DB_HOST" -p "$$DB_PORT" -U "$$DB_USER" -d "$$DB_NAME" -c "\\dt"

test-local: check-local-env
	cd $(BACKEND_DIR) && set -a && . ./$(LOCAL_ENV_FILE) && set +a && $(PYTHON) -m pytest -q

test-integration-local: check-local-env
	cd $(BACKEND_DIR) && set -a && . ./$(LOCAL_ENV_FILE) && set +a && LEASEFLOW_RUN_DB_INTEGRATION=1 $(PYTHON) -m pytest -q tests/test_db_integration.py

invoke-local-health:
	cd $(BACKEND_DIR) && $(PYTHON) scripts/invoke_local.py health

invoke-local-list-properties: check-local-env
	cd $(BACKEND_DIR) && set -a && . ./$(LOCAL_ENV_FILE) && set +a && $(PYTHON) scripts/invoke_local.py list-properties --tenant-id "$(LOCAL_TENANT_ID)" --user-id "$(LOCAL_USER_ID)"

invoke-local-create-property: check-local-env
	cd $(BACKEND_DIR) && set -a && . ./$(LOCAL_ENV_FILE) && set +a && $(PYTHON) scripts/invoke_local.py create-property --tenant-id "$(LOCAL_TENANT_ID)" --user-id "$(LOCAL_USER_ID)" --name "$(PROPERTY_NAME)" --address "$(PROPERTY_ADDRESS)"

tf-fmt:
	cd $(TF_DIR) && terraform fmt -recursive
