@echo off
setlocal

echo Running linting with pylint...
if "%~1"=="" (
    python -m pylint src/sampletones
) else (
    python -m pylint %*
)
exit /b %ERRORLEVEL%
