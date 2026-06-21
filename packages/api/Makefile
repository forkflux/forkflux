.PHONY: linters test alembic-upgrade alembic-revision run changelog

linters:
	@pre-commit run --all-files -c .pre-commit-config.yaml

test:
	@python -m pytest -vs tests/

alembic-upgrade:
	@alembic upgrade head

alembic-revision:
	@alembic revision --autogenerate -m "$(name)"

run:
	@uvicorn src.main:app --reload

changelog:
	@git cliff --unreleased --prepend CHANGELOG.md
