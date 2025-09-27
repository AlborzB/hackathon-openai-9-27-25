PY ?= python

.PHONY: test
test:
	$(PY) -m pytest -q

.PHONY: test-cov
test-cov:
	$(PY) -m pytest --cov=memory_broker --cov-report=term-missing -q

