check:
	poetry run black boltz_client
	poetry run isort boltz_client
	poetry run mypy boltz_client
	poetry run flake8 .
	poetry run pylint boltz_client
