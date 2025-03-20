# Building Wink Browser Desktop Binaries

This guide explains how to build standalone desktop binaries of Wink Browser for macOS, Linux, and Windows.

## Prerequisites

- Python 3.8+ (Python 3.13 recommended)
- pip package manager
- All dependencies installed (`pip install -r requirements.txt`)
- Platform-specific dependencies (see below)

### Platform-Specific Dependencies

#### macOS
- Xcode Command Line Tools: `xcode-select --install`
- For optional native UI enhancements: `brew install pkg-config cairo gobject-introspection`

#### Linux
- Basic build tools: `sudo apt-get install build-essential`
- For Tkinter: `sudo apt-get install python3-tk`
- For optional native UI enhancements: `sudo apt-get install python3-dev pkg-config libcairo2-dev libgirepository1.0-dev`

#### Windows
- Microsoft Visual C++ Build Tools (if building certain dependencies from source)

## Building the Binary

We provide a convenient build script that handles the process of creating a desktop binary for your platform:

```bash
# Basic usage (auto-detects your platform)
python build_desktop.py

# For a single file executable
python build_desktop.py --onefile

# To specify a platform
python build_desktop.py --platform mac
python build_desktop.py --platform linux
python build_desktop.py --platform windows

# Clean previous builds
python build_desktop.py --clean

# Specify custom app name
python build_desktop.py --name "My Wink Browser"

# Specify custom icon
python build_desktop.py --icon path/to/icon.icns  # macOS (.icns file)
python build_desktop.py --icon path/to/icon.ico   # Windows (.ico file)
```

## Build Output

The build process will create:

- For `--onefile` option: A single executable file in the `dist/` directory
- Without `--onefile`: A directory containing the app bundle in `dist/[app_name]/`

### Output Locations by Platform

- **macOS**: `dist/WinkBrowser.app` (application bundle)
- **Linux**: `dist/WinkBrowser/WinkBrowser` (executable in directory) or `dist/WinkBrowser` (single file)
- **Windows**: `dist\WinkBrowser\WinkBrowser.exe` (executable in directory) or `dist\WinkBrowser.exe` (single file)

## Customization Options

### Icons

For the best experience, provide platform-specific icons:

- macOS: `.icns` format, recommended size 1024x1024
- Windows: `.ico` format, multiple sizes (16x16 to 256x256)
- Linux: PNG files of various sizes

By default, the build script will look for:
- `images/wink_icon.icns` for macOS
- `images/wink_icon.ico` for Windows

### Additional Resources

You can add additional data files to your application bundle by modifying the `--add-data` parameter in the build script.

## Troubleshooting

### Missing Modules

If you encounter "missing module" errors during the build process:

1. Ensure all dependencies are installed: `pip install -r requirements.txt`
2. Try using the `--clean` option to start fresh: `python build_desktop.py --clean`

### Platform-Specific Issues

#### macOS

- If you get code signing errors, you can either:
  - Sign the app with your developer certificate
  - Use without signing (users will need to bypass Gatekeeper)

#### Linux

- If Tkinter is missing: `sudo apt-get install python3-tk`
- For missing shared libraries: Install the relevant `-dev` packages

#### Windows

- If PyInstaller fails, try running as administrator
- Ensure Visual C++ Redistributable is installed

## Cross-Platform Building

PyInstaller generally requires building on the target platform:
- To build a Windows exe, build on Windows
- To build a macOS app, build on macOS
- To build a Linux binary, build on Linux

## License

The Wink Browser and all its components are licensed under the MIT License. See LICENSE file for details. 