# HTTPS Implementation Changes

## Overview
This document explains the changes made to the HTTPS handling in the Wink browser codebase.

## Changes Made

1. **Simplified Network Manager**
   - Removed the custom `SSLAdapter` implementation that was trying to reinvent functionality already available in the requests library
   - Now using the built-in HTTPS handling from the requests library, which is well-tested and secure
   - Configured a proper retry strategy using requests' `Retry` class

2. **Removed Insecure Fallbacks**
   - Removed code that would fall back to `verify=False` when SSL verification failed
   - This improves security by preventing connections to sites with invalid certificates

3. **Updated Dependencies**
   - Updated requests to version 2.31.0 for better HTTPS support
   - Added certifi as an explicit dependency for certificate verification
   - Updated urllib3 to a compatible version (>=2.0.7,<3.0)

4. **Improved Error Handling**
   - Simplified error handling across all HTTP methods
   - More consistent logging of errors

## Using the Virtual Environment

For proper isolation of dependencies, we now use a virtual environment:

### On Unix/macOS
```bash
# Create and set up the virtual environment
./setup_venv.sh

# Activate the virtual environment for manual work
source venv/bin/activate

# When finished
deactivate
```

### On Windows
```cmd
# Create and set up the virtual environment
setup_venv.bat

# Activate the virtual environment for manual work
venv\Scripts\activate.bat

# When finished
deactivate
```

## Testing Changes

A simple test script (`test_network.py`) has been created to verify that the simplified HTTPS implementation works correctly. This script:

1. Creates a requests session with a retry strategy
2. Sets up browser-like headers
3. Makes HTTPS requests to example sites
4. Reports success or failure

To run the test:
```bash
# With the virtual environment activated
python test_network.py
```

## JavaScript Engine
The JavaScript engine is now using dukpy as requested, which is a lightweight JavaScript engine that doesn't rely on browser technology. 