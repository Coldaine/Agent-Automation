PY?=python

# Cross-platform dev commands using uv (no manual activation needed)
# Requires: uv (https://github.com/astral-sh/uv)

setup:
	uv sync || (uv venv && uv pip install -r requirements.txt)

run:
	uv run -m agent.main

test:
	uv run -m pytest -q

lint:
	uv run ruff check .

format:
	# Ruff autofix only (Black removed)
	uv run ruff check . --fix
