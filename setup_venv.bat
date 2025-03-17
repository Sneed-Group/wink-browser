@echo off
REM Script to set up virtual environment and install dependencies

echo Setting up virtual environment...

REM Create the virtual environment if it doesn't exist
if not exist venv (
  echo Creating virtual environment...
  python -m venv venv
  echo Virtual environment created.
) else (
  echo Using existing virtual environment.
)

REM Activate the virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip

REM Install dependencies
echo Installing dependencies from requirements.txt...
pip install -r requirements.txt

REM Run our test script to verify the network implementation
echo Running test script...
python test_network.py

echo Done!

REM You can uncomment the line below to keep the environment active
REM echo Virtual environment is active. Use 'deactivate' when finished.

REM Deactivate the virtual environment
call deactivate

echo Virtual environment deactivated. You can activate it again with 'venv\Scripts\activate.bat' 