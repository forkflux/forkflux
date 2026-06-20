.PHONY: linters test

linters:
	@pre-commit run --all-files -c .pre-commit-config.yaml

test:
	@python -m pytest -vs tests/
