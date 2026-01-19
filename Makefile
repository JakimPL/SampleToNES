.PHONY: pre_commit build install test clean help

UNAME_S := $(shell uname -s 2>/dev/null || echo Windows)

ifeq ($(UNAME_S),Linux)
	PYTHON := python3
	VENV_ACTIVATE := source .venv/bin/activate
	BUILD_SCRIPT := ./install.sh
	EXECUTABLE := sampletones
else ifeq ($(UNAME_S),Darwin)
	PYTHON := python3
	VENV_ACTIVATE := source .venv/bin/activate
	BUILD_SCRIPT := ./install.sh
	EXECUTABLE := sampletones
else
	PYTHON := python
	VENV_ACTIVATE := .venv\Scripts\activate
	BUILD_SCRIPT := install.bat
	EXECUTABLE := sampletones.exe
endif

help:
	@echo "Available targets:"
	@echo "  make pre_commit  - Install pre-commit hooks"
	@echo "  make build       - Compile standalone executable"
	@echo "  make install     - Install Python package locally"
	@echo "  make test        - Run unit tests with coverage"
	@echo "  make clean       - Remove build artifacts and cache files"

pre_commit:
	@echo "Installing pre-commit hooks..."
	$(PYTHON) -m pip install pre-commit
	pre-commit install
	pre-commit install --hook-type pre-push
	@echo "Pre-commit hooks installed successfully."

build:
	@echo "Building standalone executable..."
ifeq ($(UNAME_S),Windows)
	$(BUILD_SCRIPT)
else
	bash $(BUILD_SCRIPT)
endif

install:
	@echo "Installing package locally..."
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install ".[dev]"
	@echo "Installation complete. Run 'sampletones' to start the application."

test:
	@echo "Running tests with coverage..."
	$(PYTHON) -m pytest src/ --doctest-modules --no-cov
	$(PYTHON) -m pytest --cov=src/sampletones
	@echo "Coverage report generated in htmlcov/"

clean:
	@echo "Cleaning build artifacts..."
ifeq ($(UNAME_S),Windows)
	-if exist build rmdir /s /q build
	-if exist dist rmdir /s /q dist
	-if exist htmlcov rmdir /s /q htmlcov
	-if exist .coverage del /q .coverage
	-if exist *.spec del /q *.spec
	-if exist $(EXECUTABLE) del /q $(EXECUTABLE)
	-for /d /r . %%d in (__pycache__) do @if exist "%%d" rmdir /s /q "%%d"
	-for /d /r . %%d in (*.egg-info) do @if exist "%%d" rmdir /s /q "%%d"
	-del /s /q *.pyc 2>nul
else
	rm -rf build/ dist/ *.spec htmlcov/ .coverage
	rm -f $(EXECUTABLE)
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
endif
	@echo "Clean complete."
