.PHONY: linters test changelog

linters:
	@pre-commit run --all-files -c .pre-commit-config.yaml

test:
	@python -m pytest -vs tests/

changelog:
	@git cliff --unreleased -o CHANGELOG.md
