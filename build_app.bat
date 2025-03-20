@echo off
:: Build script for Wink Browser on Windows systems

:: Print usage information
if "%1"=="--help" (
    echo Usage: build_app.bat [options]
    echo Options:
    echo   --help          Show this help message
    echo   --platform      Specify target platform (mac^|linux^|windows^)
    echo   --onefile       Build a single executable file
    echo   --clean         Clean build directory before building
    echo   --name NAME     Specify custom app name
    echo   --icon PATH     Specify custom icon path
    echo.
    echo Example: build_app.bat --platform windows --clean
    exit /b 0
)

:: Check if Python is available
python --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo Python could not be found. Please install Python 3.8+ before continuing.
    exit /b 1
)

:: Activate virtual environment if it exists
if exist venv\Scripts\activate.bat (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
)

:: Install PyInstaller if not already installed
python -c "import PyInstaller" >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo Installing PyInstaller...
    python -m pip install PyInstaller
)

:: Build the application
echo Building Wink Browser...
python build_desktop.py %*

echo Build process completed! 