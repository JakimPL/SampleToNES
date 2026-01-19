.PHONY: pre_commit build install test clean help

UNAME_S := $(shell uname -s 2>/dev/null || echo Windows)

ifeq ($(UNAME_S),Windows)
	PYTHON := python
	SCRIPTS_DIR := scripts\windows
	SCRIPT_EXT := .bat
	RUN_SCRIPT :=
	BUILD_SCRIPT := install.bat
	EXECUTABLE := sampletones.exe
else
	PYTHON := python3
	SCRIPTS_DIR := scripts/linux
	SCRIPT_EXT := .sh
	RUN_SCRIPT := bash
	BUILD_SCRIPT := ./install.sh
	EXECUTABLE := sampletones
endif

help:
	@echo "Available targets:"
	@echo "  make pre_commit  - Install pre-commit hooks"
	@echo "  make build       - Compile standalone executable"
	@echo "  make install     - Install Python package locally"
	@echo "  make test        - Run unit tests with coverage"
	@echo "  make clean       - Remove build artifacts and cache files"
	@echo "  make lint        - Run linting (pylint, mypy)"
	@echo "  make format      - Auto-format code (isort, black)"
	@echo "  make run         - Run SampleToNES application"

pre_commit:
	$(RUN_SCRIPT) $(SCRIPTS_DIR)/pre_commit$(SCRIPT_EXT)

build:
	$(RUN_SCRIPT) $(BUILD_SCRIPT) --no-venv

install:
	$(RUN_SCRIPT) $(SCRIPTS_DIR)/install$(SCRIPT_EXT) --dev

test:
	$(RUN_SCRIPT) $(SCRIPTS_DIR)/tests$(SCRIPT_EXT)

clean:
	$(RUN_SCRIPT) $(SCRIPTS_DIR)/clean$(SCRIPT_EXT)

lint:
	$(RUN_SCRIPT) $(SCRIPTS_DIR)/lint$(SCRIPT_EXT)

pylint:
	$(RUN_SCRIPT) $(SCRIPTS_DIR)/pylint$(SCRIPT_EXT)

mypy:
	$(RUN_SCRIPT) $(SCRIPTS_DIR)/mypy$(SCRIPT_EXT)

format:
	$(RUN_SCRIPT) $(SCRIPTS_DIR)/format$(SCRIPT_EXT)

run:
	$(PYTHON) -m sampletones
