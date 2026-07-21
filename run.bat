@echo off
setlocal

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Creating virtual environment...
    python -m venv .venv

    if errorlevel 1 (
        echo Failed to create virtual environment.
        pause
        exit /b 1
    )

    echo Activating virtual environment...
    call ".venv\Scripts\activate.bat"

    echo Installing dependencies...
    python -m pip install -r requirements.txt
) else (
    echo Activating existing virtual environment...
    call ".venv\Scripts\activate.bat"
)

echo Setting project root...
set "PYTHONPATH=%CD%"

echo Running main.py...
python "scripts\main.py"

pause