@echo off
setlocal

echo Running type checking with mypy...
python -m mypy src/sampletones
set MYPY_EXIT=%ERRORLEVEL%

echo Running linting with pylint...
python -m pylint src/sampletones
set PYLINT_EXIT=%ERRORLEVEL%

if not %MYPY_EXIT%==0 (
    echo Linting failed.
    exit /b 1
)

if not %PYLINT_EXIT%==0 (
    echo Linting failed.
    exit /b 1
)

echo All linting checks passed.
exit /b 0
