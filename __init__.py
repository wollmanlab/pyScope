"""
pyScope: Automated Microscope Control System

A comprehensive Python-based automated microscope control system designed for 
high-throughput imaging experiments on well plates. The system integrates 
microscope control, fluidics management, position planning, and experiment 
orchestration into a unified platform with a modern graphical interface.

Main Components:
- Experiment: Central orchestrator for experiment management
- Scope: Microscope control and image acquisition
- Positions: Well plate position planning and management
- FileHandler: Centralized file operations and data persistence
- GUI: Modern graphical user interface for system control
"""

__version__ = "1.0.0"
__author__ = "Zachary Hemminger"
__email__ = "zehemminger@gmail.com"

# Import main classes for easy access
from .experiment import Experiment
from .file_handler import FileHandler

# Import scope components
from .Scope.scope import Scope
from .Scope.positions import Positions
from .Scope.autofocus import Autofocus

# Import fluidics components
from .Fluidics.fluidics import Fluidics

__all__ = [
    "Experiment",
    "FileHandler", 
    "Scope",
    "Positions",
    "Autofocus",
    "Fluidics",
]
