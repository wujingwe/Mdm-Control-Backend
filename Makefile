.PHONY: install install-dev lint lint-fix format format-check test test-integration test-coverage typecheck run dev check archive

install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements.txt

run:
	python3 -m app.main

dev:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

lint:
	ruff check --fix . && ruff format .

typecheck:
	mypy app/

test:
	pytest -v

# Runs the MariaDB integration suite against the database in INTEGRATION_DB_URL.
# Truncates every table in that database between tests — never point it at dev data.
INTEGRATION_DB_URL := $(shell grep '^INTEGRATION_DB_URL=' .env | cut -d= -f2-)
test-integration:
	DB_URL=$(INTEGRATION_DB_URL) MOCK_DB=false pytest tests-integration -v

test-coverage:
	pytest --cov=app --cov-report=term-missing

archive:
	rm -f project.zip && git ls-files -z | grep -zvE '(^|/)\.' | xargs -0 zip project.zip

check: lint typecheck test
