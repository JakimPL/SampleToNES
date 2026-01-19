@echo off
setlocal

echo Running unit test...
python -m pytest src/ --doctest-modules --no-cov
set DOCTEST_EXIT=%ERRORLEVEL%

python -m pytest --cov=src/sampletones
set PYTEST_EXIT=%ERRORLEVEL%

if not %DOCTEST_EXIT%==0 (
    echo Unit tests failed.
    exit /b 1
)

if not %PYTEST_EXIT%==0 (
    echo Unit tests failed.
    exit /b 1
)

echo All tests passed.
exit /b 0
