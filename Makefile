.PHONY: pre-commit build setup test ftm-samples clean help

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
	@echo "  make setup       - Set up development environment (uv; append GPU=1 for CUDA support)"
	@echo "  make pre-commit  - Install pre-commit hooks"
	@echo "  make build       - Compile standalone executable"
	@echo "  make test        - Run unit tests with coverage"
	@echo "  make ftm-samples - Emit example .ftm files to build/ftm via the integration suite"
	@echo "  make clean       - Remove build artifacts and cache files"
	@echo "  make lint        - Run linting (pylint, mypy)"
	@echo "  make format      - Auto-format code (isort, black)"
	@echo "  make run         - Run SampleToNES application"

setup:
	uv sync --group dev $(if $(filter 1,$(GPU)),--extra gpu,)
	uv tool install --force $(if $(filter 1,$(GPU)),".[gpu]",.)

build:
	$(RUN_SCRIPT) $(BUILD_SCRIPT) --no-venv

run:
	uv run sampletones

clean:
	$(RUN_SCRIPT) $(SCRIPTS_DIR)/build/clean$(SCRIPT_EXT)

pre-commit:
	$(RUN_SCRIPT) $(SCRIPTS_DIR)/dev/pre_commit$(SCRIPT_EXT)

test:
	$(RUN_SCRIPT) $(SCRIPTS_DIR)/dev/tests$(SCRIPT_EXT)

ftm-samples:
	SAMPLETONES_FTM_OUTPUT_DIR=build/ftm uv run python -m pytest tests/integration/famitracker

check-import-boundary:
	uv run scripts/check_import_boundary.py --all

lint:
	$(RUN_SCRIPT) $(SCRIPTS_DIR)/dev/lint$(SCRIPT_EXT)

pylint:
	$(RUN_SCRIPT) $(SCRIPTS_DIR)/dev/pylint$(SCRIPT_EXT)

mypy:
	$(RUN_SCRIPT) $(SCRIPTS_DIR)/dev/mypy$(SCRIPT_EXT)

format:
	$(RUN_SCRIPT) $(SCRIPTS_DIR)/dev/format$(SCRIPT_EXT)

