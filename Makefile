.PHONY: help setup install system-deps build release run calibration clean pre-commit test test-docs benchmarks lint format

ifeq ($(OS),Windows_NT)
PYTHON := python
else
PYTHON := python3
endif

ifeq ($(OS)$(MSYSTEM),Windows_NT)
Q :=
else
Q := "
endif

GPU ?= auto

help:
	@echo $(Q)Available targets:$(Q)
	@echo $(Q)  make setup       - Set up development environment (uv); GPU auto-detected, GPU=0 forces CPU$(Q)
	@echo $(Q)  make pre-commit  - Install pre-commit hooks$(Q)
	@echo $(Q)  make system-deps - Install system packages required to build and run (apt on Debian-based Linux, Homebrew on macOS)$(Q)
	@echo $(Q)  make build       - Compile standalone executable (development deployment config: DEBUG, strict history)$(Q)
	@echo $(Q)  make release     - Compile standalone executable with the release deployment config (INFO, self-healing history)$(Q)
	@echo $(Q)  make test        - Run the test suite with coverage$(Q)
	@echo $(Q)  make test-docs   - Run the doctests$(Q)
	@echo $(Q)  make benchmarks  - Run the measured-duration suite$(Q)
	@echo $(Q)  make calibration - Measure reconstruction on the reference sounds; writes the renders and a report$(Q)
	@echo $(Q)  make clean       - Remove build artifacts and cache files$(Q)
	@echo $(Q)  make lint        - Run mypy and pylint (ARGS=--mypy or ARGS=--pylint for one of them)$(Q)
	@echo $(Q)  make format      - Auto-format code (isort, black)$(Q)
	@echo $(Q)  make run         - Run SampleToNES application$(Q)

setup:
	$(PYTHON) scripts/setup_environment.py --gpu $(GPU)

install:
	$(MAKE) setup
	$(MAKE) build

build:
	$(PYTHON) scripts/bundle.py

release:
	$(PYTHON) scripts/bundle.py --release

system-deps:
	$(PYTHON) scripts/system_dependencies.py

run:
	uv run sampletones

calibration:
	uv run sampletones calibration

clean:
	$(PYTHON) scripts/clean.py

pre-commit:
	$(PYTHON) scripts/hooks.py

test:
	$(PYTHON) scripts/run_tests.py suite

test-docs:
	$(PYTHON) scripts/run_tests.py doctests

benchmarks:
	$(PYTHON) scripts/run_tests.py benchmarks

lint:
	$(PYTHON) scripts/lint.py $(ARGS)

format:
	$(PYTHON) scripts/formatting.py
