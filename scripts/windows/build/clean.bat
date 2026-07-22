@echo off
setlocal

echo Cleaning build artifacts...
if exist bin rmdir /s /q bin 2>nul
if exist build rmdir /s /q build 2>nul
if exist dist rmdir /s /q dist 2>nul
if exist htmlcov rmdir /s /q htmlcov 2>nul
if exist .coverage del /q .coverage 2>nul
if exist *.spec del /q *.spec 2>nul
for /d /r . %%d in (__pycache__) do @if exist "%%d" rmdir /s /q "%%d" 2>nul
for /d /r . %%d in (*.egg-info) do @if exist "%%d" rmdir /s /q "%%d" 2>nul
del /s /q *.pyc 2>nul

echo Clean complete.
exit /b 0
