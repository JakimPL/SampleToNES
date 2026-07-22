@echo off
setlocal

set RELEASE_HOOK=
:parse_args
if "%~1"=="" goto build
if "%~1"=="--release" (
    echo Release build: injecting release deployment configuration
    set RELEASE_HOOK=--runtime-hook scripts\release_env_hook.py
)
shift
goto parse_args

:build
echo Building executable...
pip install pyinstaller || exit /b

pyinstaller --name sampletones ^
    --onefile ^
    --distpath bin ^
    --icon "src\sampletones_assets\icons\sampletones.ico" ^
    --add-data "src\sampletones_assets\icons;assets\icons" ^
    --add-data "src\sampletones_assets\fonts;assets\fonts" ^
    --add-data "src\sampletones_config;config" ^
    --copy-metadata sampletones ^
    %RELEASE_HOOK% ^
    "src\sampletones\__main__.py" || exit /b

if exist bin\sampletones.exe (
    echo Build complete: .\bin\sampletones.exe
) else (
    echo Build failed.
    exit /b 1
)

exit /b 0
