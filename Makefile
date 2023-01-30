check:
	poetry run black boltz_client
	poetry run isort boltz_client
	poetry run mypy boltz_client
	poetry run flake8 boltz_client
	poetry run pylint boltz_client
