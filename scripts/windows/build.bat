@echo off
setlocal

echo Building executable...
pip install pyinstaller || exit /b

pyinstaller --name sampletones ^
    --onefile ^
    --distpath . ^
    --icon "src\sampletones\assets\icons\sampletones.ico" ^
    --add-data "src\sampletones\assets\icons;assets\icons" ^
    --add-data "src\sampletones\assets\fonts;assets\fonts" ^
    "src\sampletones\__main__.py" || exit /b

if exist sampletones.exe (
    echo Build complete: .\sampletones.exe
) else (
    echo Build failed.
    exit /b 1
)

exit /b 0
