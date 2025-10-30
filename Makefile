PY=python
PIP=pip

setup:
	$(PY) -m venv .venv
	. .venv/bin/activate && $(PIP) install -U pip && $(PIP) install -r requirements.txt

run:
	. .venv/bin/activate && PYTHONPATH=. $(PY) -m agent.main

test:
	. .venv/bin/activate && PYTHONPATH=. pytest -q

lint:
	. .venv/bin/activate && ruff check .

format:
	. .venv/bin/activate && ruff check . --fix && black .
