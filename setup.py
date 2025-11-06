#!/usr/bin/env python3
"""
Setup script for pyScope - Automated Microscope Control System
"""

from setuptools import setup, find_packages
import os

# Read the README file for long description
def read_readme():
    with open("README.md", "r", encoding="utf-8") as fh:
        return fh.read()

# Read requirements from a requirements.txt file if it exists
def read_requirements():
    requirements = []
    if os.path.exists("requirements.txt"):
        with open("requirements.txt", "r", encoding="utf-8") as fh:
            requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]
    return requirements

# Get version from __init__.py or set default
def get_version():
    version = "1.0.0"  # Default version
    try:
        # Try to read version from a version file
        if os.path.exists("version.txt"):
            with open("version.txt", "r", encoding="utf-8") as fh:
                version = fh.read().strip()
    except:
        pass
    return version

setup(
    name="pyscope",
    version=get_version(),
    author="pyScope Development Team",
    author_email="",
    description="Automated Microscope Control System for high-throughput imaging experiments",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/pyScope",  # Update with actual repository URL
    project_urls={
        "Bug Reports": "https://github.com/yourusername/pyScope/issues",
        "Source": "https://github.com/yourusername/pyScope",
        "Documentation": "https://github.com/yourusername/pyScope#readme",
    },
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: Bio-Informatics",
        "Topic :: Scientific/Engineering :: Medical Science Apps.",
        "License :: OSI Approved :: MIT License",  # Update with actual license
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=[
        "pandas>=1.3.0",
        "numpy>=1.20.0",
        "pycromanager>=0.12.0",
        "matplotlib>=3.3.0",
        "scipy>=1.7.0",
        "scikit-image>=0.18.0",
        "tifffile>=2021.0.0",
        "tqdm>=4.60.0",
        "pyserial>=3.5",
        "requests>=2.25.0",
    ],
    extras_require={
        "dev": [
            "pytest>=6.0",
            "pytest-cov>=2.0",
            "black>=21.0",
            "flake8>=3.8",
            "mypy>=0.800",
            "pre-commit>=2.0",
            "tox>=3.0",
            "jupyter>=1.0.0",
            "ipykernel>=6.0.0",
            "ipython>=7.0.0",
        ],
        "docs": [
            "sphinx>=4.0",
            "sphinx-rtd-theme>=0.5",
        ],
    },
    entry_points={
        "console_scripts": [
            "pyscope=experiment:main",
            "pyscope-gui=gui:main",
            "pyscope-scope=Scope.scope:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.json", "*.csv", "*.txt", "*.md", "*.png", "*.pos"],
        "Plates": ["*.json"],
        "State": ["*.json", "*.csv", "*.txt", "*.log", "*.pos"],
        "Fluidics": ["*.txt", "*.ino"],
        "Fluidics/Diagrams": ["*.png"],
        "Fluidics/Pumps/Arduino_Syringe_V2": ["*.txt", "*.ino"],
    },
    data_files=[
        ("", ["README.md", "run_experiment.bat", "create_shortcut.ps1"]),
    ],
    keywords="microscope, automation, imaging, micro-manager, fluidics, bioinformatics",
    zip_safe=False,
)
