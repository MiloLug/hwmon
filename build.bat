@echo off
REM Build script for creating hwmon.exe

echo ====================================
echo Building HW Monitor Executable
echo ====================================
echo.

echo Cleaning previous builds...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist __pycache__ rmdir /s /q __pycache__

echo.
echo Building executable...
uv run --group build pyinstaller --clean hwmon.spec

if errorlevel 1 (
    echo.
    echo Build failed!
    exit /b 1
)

echo.
echo ====================================
echo Build completed successfully!
echo ====================================
echo.
echo Executable location: dist\hwmon.exe
echo File size: 
dir dist\hwmon.exe | find "hwmon.exe"
echo.
echo You can now run: dist\hwmon.exe
echo.
