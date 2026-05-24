.PHONY: pre-commit build install setup test clean help

UNAME_S := $(shell uname -s 2>/dev/null || echo Windows)

ifeq ($(UNAME_S),Windows)
	SCRIPTS_DIR := scripts\windows
	SCRIPT_EXT := .bat
	RUN_SCRIPT :=
	BUILD_SCRIPT := install.bat
	EXECUTABLE := sampletones.exe
else
	SCRIPTS_DIR := scripts/linux
	SCRIPT_EXT := .sh
	RUN_SCRIPT := bash
	BUILD_SCRIPT := ./install.sh
	EXECUTABLE := sampletones
endif

help:
	@echo "Available targets:"
	@echo "  make setup       - Set up development environment (uv)"
	@echo "  make pre_commit  - Install pre-commit hooks"
	@echo "  make build       - Compile standalone executable"
	@echo "  make install     - Install Python package into build venv"
	@echo "  make test        - Run unit tests with coverage"
	@echo "  make clean       - Remove build artifacts and cache files"
	@echo "  make lint        - Run linting (pylint, mypy)"
	@echo "  make format      - Auto-format code (isort, black)"
	@echo "  make run         - Run SampleToNES application"

setup:
	uv sync --extra dev

build:
	$(RUN_SCRIPT) $(BUILD_SCRIPT) --no-venv

run:
	uv run python -m sampletones

clean:
	$(RUN_SCRIPT) $(SCRIPTS_DIR)/build/clean$(SCRIPT_EXT)

install:
	$(RUN_SCRIPT) $(SCRIPTS_DIR)/build/install$(SCRIPT_EXT) --dev

pre-commit:
	$(RUN_SCRIPT) $(SCRIPTS_DIR)/dev/pre_commit$(SCRIPT_EXT)

test:
	$(RUN_SCRIPT) $(SCRIPTS_DIR)/dev/tests$(SCRIPT_EXT)

lint:
	$(RUN_SCRIPT) $(SCRIPTS_DIR)/dev/lint$(SCRIPT_EXT)

pylint:
	$(RUN_SCRIPT) $(SCRIPTS_DIR)/dev/pylint$(SCRIPT_EXT)

mypy:
	$(RUN_SCRIPT) $(SCRIPTS_DIR)/dev/mypy$(SCRIPT_EXT)

format:
	$(RUN_SCRIPT) $(SCRIPTS_DIR)/dev/format$(SCRIPT_EXT)

schemas:
	$(RUN_SCRIPT) $(SCRIPTS_DIR)/schemas$(SCRIPT_EXT)
