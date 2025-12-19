.PHONY: setup dev test lint format typecheck

# Python executable in venv
PYTHON := venv/bin/python
PIP := venv/bin/pip
UVICORN := venv/bin/uvicorn
PYTEST := venv/bin/pytest
RUFF := venv/bin/ruff
MYPY := venv/bin/mypy

setup:
	@if [ ! -d "venv" ]; then \
		echo "Creating virtual environment..."; \
		python3 -m venv venv; \
	fi
	$(PIP) install --upgrade pip
	$(PIP) install -e ".[dev]"
	@echo "Setup complete! Activate with: source venv/bin/activate"

dev:
	$(UVICORN) app.main:app --host 0.0.0.0 --port 8000 --reload

test:
	$(PYTEST)

lint:
	$(RUFF) check .

format:
	$(RUFF) format .

typecheck:
	$(MYPY) .

