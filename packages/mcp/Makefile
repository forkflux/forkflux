.PHONY: linters test changelog run

linters:
	@pre-commit run --all-files -c .pre-commit-config.yaml

test:
	@python -m pytest -vs tests/

changelog:
	@git cliff --unreleased --prepend CHANGELOG.md

run:
	@uvicorn forkflux_mcp.main:app --host 0.0.0.0 --port 8080  --reload
