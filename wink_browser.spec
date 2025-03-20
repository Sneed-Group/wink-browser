"""
PyInstaller spec file for Wink Browser.
This file provides more advanced customization options for the build process.
"""

import os
import sys
import platform

# Detect the current platform
system = platform.system().lower()
is_mac = 'darwin' in system
is_windows = 'win' in system
is_linux = 'linux' in system

# Application name
app_name = 'WinkBrowser'

# Icon path based on platform
icon_file = None
if is_mac and os.path.exists('images/wink_icon.icns'):
    icon_file = 'images/wink_icon.icns'
elif is_windows and os.path.exists('images/wink_icon.ico'):
    icon_file = 'images/wink_icon.ico'
elif is_linux and os.path.exists('images/wink_icon.png'):
    icon_file = 'images/wink_icon.png'

# Define data files to include
datas = [
    ('images', 'images'),  # Include all files in the images directory
]

# Define any binary files to include
binaries = []

# Define hidden imports that might be missed by the automatic analysis
hidden_imports = [
    'tkinter',
    'PIL',
    'json',
    'lxml',
    'cssutils',
    'html5lib',
    'dukpy',
]

# Create the Analysis object
a = Analysis(
    ['main.py'],  # Script to run
    pathex=[os.path.abspath(os.getcwd())],
    binaries=binaries,
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

# Create the PYZ object
pyz = PYZ(a.pure, a.zipped_data, cipher=None)

# Create the executable
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=app_name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # Set to True for terminal output, False for no terminal
    icon=icon_file,
)

# Create the collection
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name=app_name,
)

# Create a macOS application bundle
if is_mac:
    app = BUNDLE(
        coll,
        name=f'{app_name}.app',
        icon=icon_file,
        bundle_identifier='com.winkbrowser.app',
        info_plist={
            'NSHighResolutionCapable': 'True',
            'CFBundleShortVersionString': '1.0.0',
            'CFBundleVersion': '1.0.0',
            'NSRequiresAquaSystemAppearance': 'False',  # For dark mode support
            'NSAppleScriptEnabled': False,
            'CFBundleDisplayName': app_name,
            'CFBundleName': app_name,
            'CFBundleDocumentTypes': [],
            'CFBundleTypeExtensions': ['html', 'htm', 'xhtml'],
            'CFBundleTypeIconFile': 'wink_icon.icns',
            'CFBundleURLTypes': [
                {
                    'CFBundleURLName': 'Web URL',
                    'CFBundleURLSchemes': ['http', 'https'],
                }
            ]
        }
    ) 