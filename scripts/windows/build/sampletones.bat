@echo off
setlocal enabledelayedexpansion

call "%~dp0..\lib\root.bat" || exit /b 1

set "EXTRAS="

:parse_args
if "%~1"=="" goto install
if "%~1"=="--dev" (
    if defined EXTRAS (
        set "EXTRAS=!EXTRAS!,dev"
    ) else (
        set "EXTRAS=dev"
    )
)
if "%~1"=="--gpu" (
    if defined EXTRAS (
        set "EXTRAS=!EXTRAS!,gpu"
    ) else (
        set "EXTRAS=gpu"
    )
)
shift
goto parse_args

:install
echo Installing dependencies...
pip install --upgrade pip

if defined EXTRAS (
    echo Installing with extras: !EXTRAS!
    pip install ".[!EXTRAS!]"
) else (
    pip install .
)

echo sampletones Python package installed successfully.
exit /b 0
