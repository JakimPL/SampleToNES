@echo off
setlocal EnableExtensions

set "SCRIPT_DIR=%~dp0"
call "%SCRIPT_DIR%\..\lib\root.bat" || exit /b 1

set "PROJECT_DIR=%SCRIPT_DIR%..\..\.."
set "VENV_DIR=%PROJECT_DIR%\.venv-build"
set "VENV_PY=%VENV_DIR%\Scripts\python.exe"

set RELEASE=0
:parse_args
if "%~1"=="" goto check
if "%~1"=="--release" set RELEASE=1
shift
goto parse_args

:check
echo Checking the build environment...

if not exist "%VENV_PY%" (
    echo ERROR: build interpreter not found at %VENV_PY%.>&2
    echo Run install.bat from the project root to create the build environment.>&2
    exit /b 1
)

"%VENV_PY%" -c "import pyaudio" >nul 2>&1
if errorlevel 1 (
    echo ERROR: the build interpreter cannot import pyaudio, so the bundle would carry no audio playback.>&2
    echo Run install.bat from the project root to reinstall the dependencies.>&2
    exit /b 1
)

echo pyaudio: available

"%VENV_PY%" -c "import tkinter" >nul 2>&1
if errorlevel 1 goto missing_tkinter

echo tkinter: available
exit /b 0

:missing_tkinter
if "%RELEASE%"=="1" (
    echo ERROR: the build interpreter cannot import tkinter, so a release bundle would open no file dialogs.>&2
    echo Install Python from python.org or the Microsoft Store, which both include Tk, then build again.>&2
    exit /b 1
)

echo WARNING: the build interpreter cannot import tkinter.
echo This bundle opens no file dialogs. Install Python from python.org or the Microsoft Store to include Tk.
exit /b 0
