@echo off
setlocal EnableExtensions

set "SCRIPT_DIR=%~dp0"
call "%SCRIPT_DIR%\..\lib\root.bat" || exit /b 1

set "PROJECT_DIR=%SCRIPT_DIR%..\..\.."
set "VENV_DIR=%PROJECT_DIR%\.venv-build"
set "VENV_PY=%VENV_DIR%\Scripts\python.exe"

set RELEASE=0
set BUNDLE_MODE=--onefile
set RELEASE_HOOK=
:parse_args
if "%~1"=="" goto build
if "%~1"=="--release" (
    echo Release build: onedir bundle, injecting release deployment configuration
    set RELEASE=1
    set BUNDLE_MODE=--onedir
    set RELEASE_HOOK=--runtime-hook scripts\release_env_hook.py
)
shift
goto parse_args

:build
if "%RELEASE%"=="1" (
    set EXECUTABLE=bin\sampletones\sampletones.exe
) else (
    set EXECUTABLE=bin\sampletones.exe
)

call "%SCRIPT_DIR%preflight.bat" %* || exit /b 1
call "%SCRIPT_DIR%icons.bat" || exit /b 1

if exist "bin\sampletones.exe" (
    echo Removing the previous artifact: bin\sampletones.exe
    del /Q "bin\sampletones.exe" || exit /b 1
)

if exist "bin\sampletones\" (
    echo Removing the previous artifact: bin\sampletones
    rmdir /S /Q "bin\sampletones" || exit /b 1
)

echo Building executable...
"%VENV_PY%" -m PyInstaller --name sampletones ^
    %BUNDLE_MODE% ^
    --noconfirm ^
    --distpath bin ^
    --icon "src\sampletones_assets\icons\sampletones.ico" ^
    --add-data "src\sampletones_assets\icons;assets\icons" ^
    --add-data "src\sampletones_assets\fonts;assets\fonts" ^
    --add-data "src\sampletones_config;config" ^
    --add-data "src\sampletones_player\driver\binary;sampletones_player\driver\binary" ^
    --copy-metadata sampletones ^
    --exclude-module PIL ^
    %RELEASE_HOOK% ^
    "src\sampletones\__main__.py" || exit /b

if not exist "%EXECUTABLE%" (
    echo Build failed: PyInstaller produced no executable at %EXECUTABLE%.>&2
    exit /b 1
)

echo Verifying the bundle...
"%EXECUTABLE%" --self-check
if errorlevel 1 (
    echo Build failed: %EXECUTABLE% did not pass its self-check.>&2
    exit /b 1
)

if "%RELEASE%"=="1" (
    copy /Y LICENSE bin\sampletones\LICENSE >nul || exit /b 1
    copy /Y THIRD-PARTY-NOTICES.md bin\sampletones\THIRD-PARTY-NOTICES.md >nul || exit /b 1
    copy /Y THIRD-PARTY-LICENSES.txt bin\sampletones\THIRD-PARTY-LICENSES.txt >nul || exit /b 1
    echo Bundled notices: LICENSE, THIRD-PARTY-NOTICES.md, THIRD-PARTY-LICENSES.txt
)

echo Build complete: .\%EXECUTABLE%

exit /b 0
