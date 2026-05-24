@echo off
setlocal

echo Running type checking with mypy...
if "%~1"=="" (
    uv run python -m mypy
) else (
    uv run python -m mypy %*
)
exit /b %ERRORLEVEL%
