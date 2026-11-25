.PHONY: help setup install system-deps build release run calibration tracker-playback icons docs demo pictures footage clean pre-commit test test-docs benchmarks screens check lint format

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
DEMO ?= build/demo
PROJECT_OPTIONS = $(foreach project,$(PROJECT),--project $(project))
FOOTAGE_OPTIONS = $(if $(SPEC),--spec $(SPEC)) $(if $(OUTPUT),-o $(OUTPUT))

help:
	@echo $(Q)Available targets:$(Q)
	@echo $(Q)  make setup       - Set up development environment (uv); GPU auto-detected, GPU=0 forces CPU$(Q)
	@echo $(Q)  make pre-commit  - Install pre-commit hooks$(Q)
	@echo $(Q)  make system-deps - Install system packages required to build and run (apt on Debian-based Linux, Homebrew on macOS)$(Q)
	@echo $(Q)  make build       - Compile standalone executable (development deployment config: DEBUG, strict history); GPU auto-detected, GPU=0 forces CPU$(Q)
	@echo $(Q)  make release     - Compile standalone executable with the release deployment config (INFO, self-healing history); CPU only$(Q)
	@echo $(Q)  make test        - Run the test suite with coverage$(Q)
	@echo $(Q)  make test-docs   - Run the doctests$(Q)
	@echo $(Q)  make benchmarks  - Run the measured-duration suite$(Q)
	@echo $(Q)  make screens     - Run the screen scenarios: the application driven on a virtual display (needs Xvfb)$(Q)
	@echo $(Q)  make check       - Run pre-commit on every file, the doctests, the suite and the screen scenarios, and mark the commit they passed on for a push (needs Xvfb)$(Q)
	@echo $(Q)  make calibration - Measure reconstruction on the reference sounds; writes the renders and a report$(Q)
	@echo $(Q)  make tracker-playback BITPHASE=folder FAMITRACKER=FamiTracker.exe [PROJECT=song.stp] - Play exported projects (the corpus by default) in Bitphase, FamiTracker or both; reports every tick that differs from the app$(Q)
	@echo $(Q)  make icons       - Write the application icon suite from the mark into the package$(Q)
	@echo $(Q)  make docs        - Write the user documentation as HTML pages into the package$(Q)
	@echo $(Q)  make demo        - Make the demo tree (recordings, a library, reconstructions, a project) in DEMO=build/demo$(Q)
	@echo $(Q)  make pictures    - Draw the guide's and the README's pictures of the application from the demo tree (needs Xvfb)$(Q)
	@echo $(Q)  make footage [SPEC=reel.yaml] [OUTPUT=reel.mp4] - Film the Reconstructions tab through a timeline into a vertical video, the demo piece by default (needs Xvfb, ffmpeg)$(Q)
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
	$(PYTHON) scripts/bundle.py --gpu $(GPU)

release:
	$(PYTHON) scripts/bundle.py --release --gpu 0

system-deps:
	$(PYTHON) scripts/system_dependencies.py

run:
	uv run sampletones

calibration:
	uv run sampletones calibration

tracker-playback:
	$(if $(BITPHASE)$(FAMITRACKER),,$(error Give BITPHASE=folder, FAMITRACKER=path/to/FamiTracker.exe, or both))
	$(if $(BITPHASE),uv run sampletones tracker-playback bitphase --directory $(BITPHASE) $(PROJECT_OPTIONS))
	$(if $(FAMITRACKER),uv run sampletones tracker-playback famitracker --executable $(FAMITRACKER) $(PROJECT_OPTIONS))

icons:
	uv run python -m assets.icons

docs:
	uv run python -m assets.documentation

demo:
	uv run python -m assets.demo -o $(DEMO)

pictures:
	uv run python -m assets.pictures

footage:
	uv run python -m assets.footage $(FOOTAGE_OPTIONS)

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

screens:
	$(PYTHON) scripts/run_tests.py screens

check:
	$(PYTHON) scripts/check.py

lint:
	$(PYTHON) scripts/lint.py $(ARGS)

format:
	$(PYTHON) scripts/formatting.py
