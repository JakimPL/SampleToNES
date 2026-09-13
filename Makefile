.PHONY: help setup install system-deps build release run clean pre-commit test benchmarks lint format \
	ftm-samples nsf-samples nsf-render compression-report compression-study icons player calibration \
	check-import-boundary check-tag-names check-unused-tags check-rendered-literals check-language-keys \
	check-palette-colors check-shortcut-actions

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
	PYTHON := python
	Q :=
else
	PYTHON := python3
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
	@echo $(Q)  make test        - Run the doctests, the covered suite and the benchmarks$(Q)
	@echo $(Q)  make benchmarks  - Run the measured-duration suite on its own$(Q)
	@echo $(Q)  make ftm-samples - Emit example .ftm files to build/ftm via the integration suite$(Q)
	@echo $(Q)  make nsf-samples - Emit example .nsf files to build/nsf via the integration suite$(Q)
	@echo $(Q)  make nsf-render  - Render the .nsf files in build/nsf to waves with ffmpeg$(Q)
	@echo $(Q)  make compression-report - Measure the song codec into build/compression$(Q)
	@echo $(Q)  make compression-study - Measure the song codec over the projects and stems on this machine; the report lands in Documents/SampleToNES/compression (ARGS=--quick for a short run)$(Q)
	@echo $(Q)  make icons       - Generate the icon suite into src/sampletones_assets/icons$(Q)
	@echo $(Q)  make player      - Assemble the NES player driver with cc65$(Q)
	@echo $(Q)  make calibration - Score the reconstruction corpus; the report lands in Documents/SampleToNES/calibration$(Q)
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

clean:
	$(PYTHON) scripts/clean.py

pre-commit:
	$(PYTHON) scripts/hooks.py

test:
	$(PYTHON) scripts/run_tests.py

benchmarks:
	$(PYTHON) scripts/run_tests.py --only benchmarks

lint:
	$(PYTHON) scripts/lint.py $(ARGS)

format:
	$(PYTHON) scripts/formatting.py

ftm-samples: export SAMPLETONES_FTM_OUTPUT_DIR := build/ftm
ftm-samples:
	uv run python -m pytest tests/integration/famitracker

nsf-samples: export SAMPLETONES_NSF_OUTPUT_DIR := build/nsf
nsf-samples:
	uv run python -m pytest tests/integration/nsf

nsf-render: nsf-samples
	uv run scripts/nsf_render.py

compression-report: export SAMPLETONES_COMPRESSION_OUTPUT_DIR := build/compression
compression-report:
	uv run python -m pytest tests/integration/nsf/test_compression_report.py

compression-study:
	uv run scripts/compression_study.py $(ARGS)

icons:
	uv run --group assets python scripts/assets/icons.py

player:
	uv run scripts/player.py

check-import-boundary:
	uv run scripts/checks/import_boundary.py --all

check-tag-names:
	uv run scripts/checks/tag_names.py --all

check-unused-tags:
	uv run scripts/checks/unused_tags.py

check-rendered-literals:
	uv run scripts/checks/rendered_literals.py

check-language-keys:
	uv run scripts/checks/language_keys.py

check-palette-colors:
	uv run scripts/checks/palette_colors.py

check-shortcut-actions:
	uv run scripts/checks/shortcut_actions.py

calibration:
	uv run scripts/calibration.py
