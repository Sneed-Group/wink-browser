#!/usr/bin/env python3
"""
Build script for creating desktop binaries of Wink Browser for macOS, Linux, and Windows.
Using PyInstaller to create standalone executables.
"""

import os
import sys
import shutil
import argparse
import platform
import subprocess

def parse_arguments():
    """Parse command line arguments for the build process."""
    parser = argparse.ArgumentParser(description="Build Wink Browser desktop binary")
    parser.add_argument('--platform', choices=['auto', 'mac', 'linux', 'windows'], 
                      default='auto', help='Target platform (default: auto-detect)')
    parser.add_argument('--onefile', action='store_true', 
                      help='Build a single executable file (default: False)')
    parser.add_argument('--icon', type=str, default=None, 
                      help='Path to icon file (.ico for Windows, .icns for macOS)')
    parser.add_argument('--name', type=str, default='WinkBrowser', 
                      help='Name of the output executable')
    parser.add_argument('--clean', action='store_true', 
                      help='Clean build directory before building')
    return parser.parse_args()

def detect_platform():
    """Auto-detect the current platform."""
    system = platform.system().lower()
    if 'darwin' in system:
        return 'mac'
    elif 'linux' in system:
        return 'linux'
    elif 'windows' in system:
        return 'windows'
    else:
        print(f"Unsupported platform: {system}")
        sys.exit(1)

def check_dependencies():
    """Check if PyInstaller is installed."""
    try:
        import PyInstaller
        print("PyInstaller is already installed.")
    except ImportError:
        print("Installing PyInstaller...")
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'PyInstaller'])
        print("PyInstaller installed successfully.")

def clean_build_directories():
    """Clean build and dist directories."""
    dirs_to_clean = ['build', 'dist']
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            print(f"Cleaning {dir_name}/ directory...")
            shutil.rmtree(dir_name)
    
    # Also remove any .spec files
    for file in os.listdir('.'):
        if file.endswith('.spec'):
            os.remove(file)
            print(f"Removed {file}")

def get_platform_specific_args(target_platform, args):
    """Get platform-specific arguments for PyInstaller."""
    platform_args = []
    
    # Common arguments
    if args.onefile:
        platform_args.append('--onefile')
    else:
        platform_args.append('--windowed')  # Creates a folder with executables
    
    # Platform-specific icons
    if args.icon:
        platform_args.extend(['--icon', args.icon])
    elif target_platform == 'mac':
        # Default icon for macOS if available
        if os.path.exists('images/wink_icon.icns'):
            platform_args.extend(['--icon', 'images/wink_icon.icns'])
    elif target_platform == 'windows':
        # Default icon for Windows if available
        if os.path.exists('images/wink_icon.ico'):
            platform_args.extend(['--icon', 'images/wink_icon.ico'])
    
    # Add app name to Info.plist on macOS
    if target_platform == 'mac':
        platform_args.extend(['--name', args.name])
        platform_args.append('--osx-bundle-identifier=com.winkbrowser.app')
    
    return platform_args

def build_binary(target_platform, args):
    """Build the binary for the specified platform."""
    print(f"Building for platform: {target_platform}")
    
    # Get platform-specific arguments
    platform_args = get_platform_specific_args(target_platform, args)
    
    # Base PyInstaller command
    cmd = [
        'pyinstaller',
        '--noconfirm',
        '--clean',
        '--add-data=images:images',  # Include images folder
        f'--name={args.name}'
    ]
    
    # Add platform-specific arguments
    cmd.extend(platform_args)
    
    # Add the main script
    cmd.append('main.py')
    
    # Execute PyInstaller
    print("Running command:", ' '.join(cmd))
    subprocess.check_call(cmd)
    
    print(f"\nBuild completed successfully!")
    if args.onefile:
        print(f"Executable can be found in the dist/ directory")
    else:
        print(f"Application bundle can be found in the dist/{args.name}/ directory")

def main():
    """Main function to build the desktop binary."""
    args = parse_arguments()
    
    # Determine target platform
    target_platform = args.platform
    if target_platform == 'auto':
        target_platform = detect_platform()
    
    # Check for PyInstaller
    check_dependencies()
    
    # Clean previous builds if requested
    if args.clean:
        clean_build_directories()
    
    # Build the binary
    build_binary(target_platform, args)

if __name__ == "__main__":
    main() 