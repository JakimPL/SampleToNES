@echo off
setlocal

echo Running doctests...
uv run python -m pytest src/ --doctest-modules --no-cov
set DOCTEST_EXIT=%ERRORLEVEL%

echo Running pytest with coverage...
uv run python -m pytest -n 6 --cov --ignore=tests/benchmarks
set PYTEST_EXIT=%ERRORLEVEL%

echo Running benchmarks...
uv run python -m pytest tests/benchmarks --no-cov
set BENCHMARK_EXIT=%ERRORLEVEL%

if not %DOCTEST_EXIT%==0 (
    echo Tests failed.
    exit /b 1
)

if not %PYTEST_EXIT%==0 (
    echo Tests failed.
    exit /b 1
)

if not %BENCHMARK_EXIT%==0 (
    echo Tests failed.
    exit /b 1
)

echo All tests passed.
exit /b 0
