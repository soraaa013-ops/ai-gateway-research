PYTHON ?= python3
VENV := .venv/bin

.PHONY: install poc test demo
install:
	$(PYTHON) -m venv .venv
	$(VENV)/python -m pip install -r poc/requirements.lock

poc:
	$(VENV)/python -m poc.run

test:
	$(VENV)/python -m pytest -c poc/pytest.ini -q --junitxml=poc/.runtime/junit.xml

demo:
	@test -n "$(CREDENTIALS)" || (echo 'Usage: make demo CREDENTIALS=poc/.runtime/<run>/credentials.json'; exit 1)
	$(VENV)/python -m poc.demo "$(CREDENTIALS)"
