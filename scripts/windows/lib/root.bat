if not exist "%~dp0..\..\..\src\sampletones\" (
    echo ERROR: SampleToNES project root not found.>&2
    exit /b 1
)

cd /d "%~dp0..\..\.." || exit /b 1
exit /b 0
