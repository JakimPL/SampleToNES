@echo off
setlocal

echo Running linting with pylint...
python -m pylint src/sampletones
exit /b %ERRORLEVEL%
