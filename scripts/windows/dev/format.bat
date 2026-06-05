@echo off
setlocal

echo Formatting imports with isort...
uv run python -m isort src/ tests/ || exit /b

echo Formatting code with black...
uv run python -m black src/ tests/ || exit /b

echo Code formatting complete.
exit /b 0
