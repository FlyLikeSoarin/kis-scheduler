all: setup, run

setup:
	python3.9 -m venv venv
	./venv/bin/pip install -r requirements.txt

run:
	./venv/bin/python -m uvicorn app.main:app

lint:
	isort --check .
	black --check --diff .

format:
	isort .
	black .