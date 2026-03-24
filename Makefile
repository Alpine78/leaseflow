PYTHON ?= python
BACKEND_DIR := backend
TF_DIR := infra

.PHONY: format lint test migrate tf-fmt

format:
	cd $(BACKEND_DIR) && $(PYTHON) -m ruff format src tests migrations

lint:
	cd $(BACKEND_DIR) && $(PYTHON) -m ruff check src tests migrations

test:
	cd $(BACKEND_DIR) && $(PYTHON) -m pytest -q

migrate:
	cd $(BACKEND_DIR) && $(PYTHON) -m alembic upgrade head

tf-fmt:
	cd $(TF_DIR) && terraform fmt -recursive
