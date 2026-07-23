.PHONY: install install-dev lint lint-fix format format-check test test-coverage run dev check

install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements.txt -r requirements-dev.txt

run:
	python3 -m app.main

dev:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

lint:
	ruff check .

lint-fix:
	ruff check --fix .

format:
	ruff format .

format-check:
	ruff format --check .

test:
	pytest -v

test-coverage:
	pytest --cov=app --cov-report=term-missing

check: lint format-check test
