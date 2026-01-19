@echo off
setlocal

echo Installing pre-commit hooks...
python -m pip install pre-commit || exit /b
pre-commit install || exit /b
pre-commit install --hook-type pre-push || exit /b
echo Pre-commit hooks installed successfully.

exit /b 0
