.PHONY = all format

all:
	pip3 install -e .

format:
	black main.py setup.py