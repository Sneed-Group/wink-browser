#!/bin/bash
# Build script for Wink Browser on Unix-like systems (macOS/Linux)

# Make script exit on error
set -e

# Print usage information
function show_help {
    echo "Usage: ./build_app.sh [options]"
    echo "Options:"
    echo "  --help          Show this help message"
    echo "  --platform      Specify target platform (mac|linux|windows)"
    echo "  --onefile       Build a single executable file"
    echo "  --clean         Clean build directory before building"
    echo "  --name NAME     Specify custom app name"
    echo "  --icon PATH     Specify custom icon path"
    echo
    echo "Example: ./build_app.sh --platform mac --clean"
}

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "Python 3 could not be found. Please install Python 3.8+ before continuing."
    exit 1
fi

# Parse command line arguments
ARGS=""
while [[ $# -gt 0 ]]; do
    case $1 in
        --help)
            show_help
            exit 0
            ;;
        --platform|--onefile|--clean|--name|--icon)
            if [[ $1 == "--platform" || $1 == "--name" || $1 == "--icon" ]]; then
                if [[ -z $2 || $2 == --* ]]; then
                    echo "Error: $1 requires an argument"
                    exit 1
                fi
                ARGS="$ARGS $1 $2"
                shift 2
            else
                ARGS="$ARGS $1"
                shift
            fi
            ;;
        *)
            echo "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Make sure virtual environment is active if it exists
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
fi

# Install PyInstaller if not already installed
if ! python3 -c "import PyInstaller" &> /dev/null; then
    echo "Installing PyInstaller..."
    python3 -m pip install PyInstaller
fi

# Run the Python build script with the passed arguments
echo "Building Wink Browser..."
python3 build_desktop.py $ARGS

echo "Build process completed!" 