@echo off
setlocal

echo Installing pre-commit hooks...
uv run pre-commit install || exit /b
uv run pre-commit install --hook-type pre-commit --hook-type pre-push || exit /b
echo Pre-commit hooks installed successfully.

exit /b 0
