.PHONY: install install-dev lint lint-fix format format-check test test-coverage typecheck run dev check archive

install:
	uv sync

install-dev:
	uv sync

run:
	uv run python -m app.main

dev:
	uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

lint:
	uv run ruff check --fix . && uv run ruff format .

typecheck:
	uv run mypy app/

test:
	uv run pytest -v

test-coverage:
	uv run pytest --cov=app --cov-report=term-missing

archive:
	rm -f project.zip && git ls-files -z | grep -zvE '(^|/)\.' | xargs -0 zip project.zip

check: lint typecheck test
