.PHONY: pre-commit build release system-deps setup test ftm-samples clean help

UNAME_S := $(shell uname -s 2>/dev/null || echo Windows)

ifeq ($(UNAME_S),Windows)
	SCRIPTS_DIR := scripts\windows
	SCRIPT_EXT := .bat
	RUN_SCRIPT :=
	BUILD_SCRIPT := install.bat
	EXECUTABLE := sampletones.exe
	PYTHON := python
else
	SCRIPTS_DIR := scripts/linux
	SCRIPT_EXT := .sh
	RUN_SCRIPT := bash
	BUILD_SCRIPT := ./install.sh
	EXECUTABLE := sampletones
	PYTHON := python3
endif

BUILD_COMMAND := $(RUN_SCRIPT) $(BUILD_SCRIPT)
RELEASE_COMMAND := $(RUN_SCRIPT) $(BUILD_SCRIPT) --release
SYSTEM_DEPS_COMMAND := bash scripts/linux/build/dependencies.sh

ifeq ($(UNAME_S),Darwin)
	MACOS_SOURCE_ONLY := bash scripts/macos/source_only.sh
	BUILD_COMMAND := $(MACOS_SOURCE_ONLY) 'make build'
	RELEASE_COMMAND := $(MACOS_SOURCE_ONLY) 'make release'
	SYSTEM_DEPS_COMMAND := $(MACOS_SOURCE_ONLY) 'make system-deps'
endif

GPU ?= auto
GPU_EXTRA :=
ifeq ($(filter 0,$(GPU)),)
ifneq ($(filter setup,$(MAKECMDGOALS)),)
	GPU_EXTRA := $(shell $(PYTHON) scripts/detect_cuda.py --extra)
endif
endif

help:
	@echo "Available targets:"
	@echo "  make setup       - Set up development environment (uv); GPU auto-detected, GPU=0 forces CPU"
	@echo "  make pre-commit  - Install pre-commit hooks"
	@echo "  make system-deps - Install system packages required to build and run (Debian-based)"
	@echo "  make build       - Compile standalone executable (respects current deployment config)"
	@echo "  make release     - Compile standalone executable with the release deployment config"
	@echo "  make test        - Run unit tests with coverage"
	@echo "  make ftm-samples - Emit example .ftm files to build/ftm via the integration suite"
	@echo "  make clean       - Remove build artifacts and cache files"
	@echo "  make lint        - Run linting (pylint, mypy)"
	@echo "  make format      - Auto-format code (isort, black)"
	@echo "  make run         - Run SampleToNES application"

setup:
	uv sync --group dev $(if $(GPU_EXTRA),--extra $(GPU_EXTRA),)
	uv tool install --force $(if $(GPU_EXTRA),".[$(GPU_EXTRA)]",.)

install:
	make setup
	make build

build:
	$(BUILD_COMMAND)

release:
	$(RELEASE_COMMAND)

system-deps:
	$(SYSTEM_DEPS_COMMAND)

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

calibration:
	uv run scripts/calibration.py --all

lint:
	$(RUN_SCRIPT) $(SCRIPTS_DIR)/dev/lint$(SCRIPT_EXT)

pylint:
	$(RUN_SCRIPT) $(SCRIPTS_DIR)/dev/pylint$(SCRIPT_EXT)

mypy:
	$(RUN_SCRIPT) $(SCRIPTS_DIR)/dev/mypy$(SCRIPT_EXT)

format:
	$(RUN_SCRIPT) $(SCRIPTS_DIR)/dev/format$(SCRIPT_EXT)

