@echo off
setlocal

echo Running doctests...
uv run python -m pytest src/ --doctest-modules --no-cov
set DOCTEST_EXIT=%ERRORLEVEL%

echo Running pytest with coverage...
uv run python -m pytest -n 6 --cov
set PYTEST_EXIT=%ERRORLEVEL%

if not %DOCTEST_EXIT%==0 (
    echo Tests failed.
    exit /b 1
)

if not %PYTEST_EXIT%==0 (
    echo Tests failed.
    exit /b 1
)

echo All tests passed.
exit /b 0
