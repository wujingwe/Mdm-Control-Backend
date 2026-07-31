.PHONY: install install-dev lint lint-fix format format-check test test-coverage typecheck run dev check archive

install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements.txt -r requirements-dev.txt

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

test-coverage:
	pytest --cov=app --cov-report=term-missing

archive:
	rm -f project.zip && git ls-files -z | grep -zvE '(^|/)\.' | xargs -0 zip project.zip

check: lint typecheck test
