.PHONY: help setup install build release system-deps run clean pre-commit test \
	ftm-samples check-import-boundary check-tag-names check-unused-tags \
	check-language-keys check-palette-colors calibration lint pylint mypy format

ifeq ($(OS),Windows_NT)
ifeq ($(MSYSTEM),)
UNAME_S := Windows
else
UNAME_S := $(shell uname -s)
endif
else
UNAME_S := $(shell uname -s)
endif

ifeq ($(UNAME_S),Windows)
	SCRIPTS_DIR := scripts/windows
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

ifeq ($(UNAME_S),Windows)
script = $(subst /,\,$(SCRIPTS_DIR)/$(1)$(SCRIPT_EXT))
else
script = $(RUN_SCRIPT) $(SCRIPTS_DIR)/$(1)$(SCRIPT_EXT)
endif

ifeq ($(UNAME_S),Windows)
Q :=
else
Q := "
endif

BUILD_COMMAND := $(RUN_SCRIPT) $(BUILD_SCRIPT)
RELEASE_COMMAND := $(RUN_SCRIPT) $(BUILD_SCRIPT) --release
SYSTEM_DEPS_COMMAND := bash scripts/linux/build/dependencies.sh
SETUP_ENV :=

ifeq ($(UNAME_S),Darwin)
	MACOS_NO_BUNDLE := bash scripts/macos/build/no_bundle.sh
	BUILD_COMMAND := $(MACOS_NO_BUNDLE) 'make build'
	RELEASE_COMMAND := $(MACOS_NO_BUNDLE) 'make release'
	SYSTEM_DEPS_COMMAND := bash scripts/macos/build/dependencies.sh
	SETUP_ENV := ARCHFLAGS="-arch $(shell uname -m)"
endif

GPU ?= auto
GPU_EXTRA :=
ifeq ($(filter 0,$(GPU)),)
ifneq ($(filter setup,$(MAKECMDGOALS)),)
	GPU_EXTRA := $(shell $(PYTHON) scripts/detect_cuda.py --extra)
endif
endif

help:
	@echo $(Q)Available targets:$(Q)
	@echo $(Q)  make setup       - Set up development environment (uv); GPU auto-detected, GPU=0 forces CPU$(Q)
	@echo $(Q)  make pre-commit  - Install pre-commit hooks$(Q)
	@echo $(Q)  make system-deps - Install system packages required to build and run (Debian-based, or Homebrew on macOS)$(Q)
	@echo $(Q)  make build       - Compile standalone executable (respects current deployment config)$(Q)
	@echo $(Q)  make release     - Compile standalone executable with the release deployment config$(Q)
	@echo $(Q)  make test        - Run unit tests with coverage$(Q)
	@echo $(Q)  make ftm-samples - Emit example .ftm files to build/ftm via the integration suite$(Q)
	@echo $(Q)  make clean       - Remove build artifacts and cache files$(Q)
	@echo $(Q)  make lint        - Run linting (pylint, mypy)$(Q)
	@echo $(Q)  make format      - Auto-format code (isort, black)$(Q)
	@echo $(Q)  make run         - Run SampleToNES application$(Q)

setup:
	$(SETUP_ENV) uv sync --group dev $(if $(GPU_EXTRA),--extra $(GPU_EXTRA),)
	$(SETUP_ENV) uv tool install --force $(if $(GPU_EXTRA),".[$(GPU_EXTRA)]",.)

install:
	$(MAKE) setup
	$(MAKE) build

build:
	$(BUILD_COMMAND)

release:
	$(RELEASE_COMMAND)

system-deps:
	$(SYSTEM_DEPS_COMMAND)

run:
	uv run sampletones

clean:
	$(call script,build/clean)

pre-commit:
	$(call script,dev/pre_commit)

test:
	$(call script,dev/tests)

ftm-samples: export SAMPLETONES_FTM_OUTPUT_DIR := build/ftm
ftm-samples:
	uv run python -m pytest tests/integration/famitracker

check-import-boundary:
	uv run scripts/checks/import_boundary.py --all

check-tag-names:
	uv run scripts/checks/tag_names.py --all

check-unused-tags:
	uv run scripts/checks/unused_tags.py

check-language-keys:
	uv run scripts/checks/language_keys.py

check-palette-colors:
	uv run scripts/checks/palette_colors.py

calibration:
	uv run scripts/calibration.py --all

lint:
	$(call script,dev/lint)

pylint:
	$(call script,dev/pylint)

mypy:
	$(call script,dev/mypy)

format:
	$(call script,dev/format)
