linters:
	@pre-commit run --all-files -c .pre-commit-config.yaml

export-openapi:
	@python -m scripts.export_openapi
