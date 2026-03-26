.PHONY = all format

all:
	pip3 install -e .

format:
	black main.py setup.py
	black core/*.py
	black core/rules/*.py
	black differ/*.py