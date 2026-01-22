@echo off
setlocal

echo Running type checking with mypy...
if "%~1"=="" (
    python -m mypy src/sampletones
) else (
    python -m mypy %*
)
exit /b %ERRORLEVEL%
