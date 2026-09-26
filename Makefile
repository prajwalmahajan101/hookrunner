# hookrunner — dev convenience targets.

.PHONY: help venv install compile sync hooks lint fmt test cov clean

VENV := .venv
PY := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

help:  ## Show available targets
	@grep -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-12s %s\n", $$1, $$2}'

venv:  ## Create the virtualenv
	python -m venv $(VENV)
	$(PIP) install --quiet --upgrade pip pip-tools

compile:  ## Regenerate requirements/*.txt from *.in (+ pyproject)
	$(VENV)/bin/pip-compile --quiet --output-file=requirements/base.txt requirements/base.in
	$(VENV)/bin/pip-compile --quiet --output-file=requirements/dev.txt requirements/dev.in

sync:  ## Install pinned dev deps into the venv (editable project)
	$(VENV)/bin/pip-sync requirements/dev.txt
	$(PIP) install --quiet -e .

install: venv compile sync hooks  ## Full dev setup: venv + compile + sync + hooks

hooks:  ## Install pre-commit git hooks
	$(VENV)/bin/pre-commit install

lint:  ## Ruff lint
	$(VENV)/bin/ruff check .

fmt:  ## Ruff format
	$(VENV)/bin/ruff format .

test:  ## Run tests
	$(PY) -m pytest

cov:  ## Run tests with coverage
	$(PY) -m pytest --cov-report=term-missing

clean:  ## Remove caches + coverage artifacts
	rm -rf .ruff_cache .mypy_cache .pytest_cache .coverage htmlcov coverage.xml
