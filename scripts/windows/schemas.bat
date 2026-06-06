@echo off
setlocal enabledelayedexpansion

set START_DIR=%CD%
set SCRIPT_DIR=%~dp0
set SCHEMAS_DIR=%SCRIPT_DIR%..\..\src\sampletones_schemas
cd /d "%SCHEMAS_DIR%"

where flatc >nul 2>&1 || (
	echo flatc not found in PATH. Install the FlatBuffers compiler and retry. >&2
	exit /b 2
)

flatc --help 2>&1 | findstr /C:"--python" >nul || (
	echo flatc does not appear to support Python generation (--python^). >&2
	echo Please install a flatc binary built with Python support. >&2
	exit /b 3
)

echo Removing existing .py files under %SCHEMAS_DIR%...
for /r "%SCHEMAS_DIR%" %%f in (*.py) do (
	del /f /q "%%f" 2>nul
)

set DEFINITIONS_DIR=%SCHEMAS_DIR%\definitions
echo Generating Python bindings for all .fbs files in: %DEFINITIONS_DIR%...
set TARGET_DIR=%SCHEMAS_DIR%\..

set FBS_COUNT=0
set FBS_FILES=
for /f "delims=" %%f in ('dir /b /s "%DEFINITIONS_DIR%\*.fbs" 2^>nul ^| sort') do (
	set /a FBS_COUNT+=1
	set FBS_FILES=!FBS_FILES! "%%f"
)

if %FBS_COUNT% equ 0 (
	echo no .fbs files found >&2
	exit /b 0
)

echo Found %FBS_COUNT% .fbs files.
flatc --python -I "%DEFINITIONS_DIR%" -o "%TARGET_DIR%" %FBS_FILES%

echo Running pre-commit on generated files...
set PY_FILES=
for /r "%TARGET_DIR%" %%f in (*.py) do (
	set PY_FILES=!PY_FILES! "%%f"
)
if defined PY_FILES (
	pre-commit run black --files %PY_FILES%
)

echo Generation finished.
