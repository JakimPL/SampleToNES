@echo off
setlocal

echo Running type checking with mypy...
python -m mypy src/sampletones
exit /b %ERRORLEVEL%
