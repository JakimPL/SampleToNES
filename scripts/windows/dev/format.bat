@echo off
setlocal

echo Formatting imports with isort...
python -m isort src/ tests/ || exit /b

echo Formatting code with black...
python -m black src/ tests/ || exit /b

echo Code formatting complete.
exit /b 0
