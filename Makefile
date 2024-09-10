down:
	podman-compose -f ./docker-compose-dev.yml down -t 1

start: down build
	podman-compose -f ./docker-compose-dev.yml run --service-ports --rm dev bash

build: down
	podman-compose -f ./docker-compose-dev.yml build

clear:
	python -Bc "import pathlib; [p.unlink() for p in pathlib.Path('.').rglob('*.py[co]')]"
	python -Bc "import pathlib; [p.rmdir() for p in pathlib.Path('.').rglob('__pycache__')]"

build_doc:
	rm -rf ./docs/build/* && sphinx-build -M html docs/source docs/build -v
