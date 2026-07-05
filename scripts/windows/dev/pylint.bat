@echo off
setlocal

echo Running linting with pylint...
if "%~1"=="" (
    uv run python -m pylint src/sampletones
) else (
    uv run python -m pylint %*
)
exit /b %ERRORLEVEL%
