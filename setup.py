#!/usr/bin/env python3
"""
Wink Browser Setup
"""

from setuptools import setup, find_packages

# Read requirements from requirements.txt
with open('requirements.txt') as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]

# Read long description from README.md
with open('README.md', 'r', encoding='utf-8') as f:
    long_description = f.read()

setup(
    name="wink-browser",
    version="1.0.0",
    description="A modern, privacy-focused web browser built in Python",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Wink Browser Team",
    author_email="team@winkbrowser.example.com",
    url="https://github.com/yourusername/wink-browser",
    packages=find_packages(),
    include_package_data=True,
    entry_points={
        "console_scripts": [
            "wink-browser=browser_engine.main:main",
        ],
    },
    install_requires=requirements,
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: X11 Applications",
        "Environment :: Win32 (MS Windows)",
        "Environment :: MacOS X",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Internet :: WWW/HTTP :: Browsers",
    ],
    keywords="browser, privacy, web, html5, css3",
    project_urls={
        "Bug Reports": "https://github.com/yourusername/wink-browser/issues",
        "Source": "https://github.com/yourusername/wink-browser",
    },
) 