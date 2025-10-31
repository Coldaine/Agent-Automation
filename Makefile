PY?=python

# Cross-platform dev commands using uv (no manual activation needed)
# Requires: uv (https://github.com/astral-sh/uv)

setup:
	uv sync || (uv venv && uv pip install -r requirements.txt)

run:
	uv run -m agent.main

test:
	uv run -m pytest -q

smoke:
	uv run -m pytest -q -k action_contract

live-center:
	uv run python run_once_center.py

verify-last:
	uv run python verify_last_run.py --center-tol 8 --require-verify

run-basic-sequence:
	uv run python run_sequence_basic.py

run-dry:
	uv run -m agent.main --config config.yaml --dry_run true

run-live:
	uv run -m agent.main --config config.yaml --dry_run false

lint:
	uv run ruff check .

format:
	# Ruff autofix only (Black removed)
	uv run ruff check . --fix
