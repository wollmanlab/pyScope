# pyScope: Automated Microscope Control System

## Overview

pyScope is a comprehensive Python-based automated microscope control system designed for high-throughput imaging experiments on well plates. The system integrates microscope control, fluidics management, position planning, and experiment orchestration into a unified platform with a modern graphical interface.

## Main Goals

The primary objectives of pyScope are:

1. **Automated Experiment Execution**: Orchestrate complex multi-round imaging experiments with integrated fluidics protocols
2. **Precise Position Management**: Generate and manage imaging positions for various well plate configurations with automatic tiling
3. **Microscope Integration**: Provide seamless control of microscope parameters (position, channels, exposure, binning) via Micro-Manager
4. **State Persistence**: Maintain experiment state across sessions with robust file-based state management
5. **Modern GUI Interface**: Offer an intuitive graphical interface with real-time monitoring and control
6. **Modular Architecture**: Enable independent operation of system components (scope, fluidics, experiment management)

## System Architecture

### Core Components

#### 1. **Experiment Class** (`experiment.py`)
- **Purpose**: Central orchestrator for experiment management
- **Key Features**:
  - Experiment state management and persistence
  - Task creation and scheduling for scope and fluidics systems
  - Status monitoring (Running, Paused, Stopped, Reset, Recover)
  - Progress tracking for fluidics and scope tasks
  - System recovery and reset capabilities
  - Multi-round experiment support with group-based processing
  - File-based communication with scope and fluidics components

#### 2. **Scope Class** (`Scope/scope.py`)
- **Purpose**: Microscope control and image acquisition
- **Key Features**:
  - Micro-Manager integration via pycromanager
  - **Independent operation** with continuous monitoring loop
  - Protocol-based task execution (SetInitialFocus, FilterPositions, Acquire)
  - Position and channel control with state validation
  - Image acquisition with timing tracking
  - Simulation mode for testing without hardware
  - File-based communication with experiment system
  - Dynamic system-specific scope class loading (e.g., CyanScope, OrangeScope)

#### 3. **Positions Class** (`Scope/positions.py`)
- **Purpose**: Well plate position planning and management
- **Key Features**:
  - Automatic tiling for circular and rectangular wells
  - Support for rotated rectangular wells
  - Grid-based plate layout generation (96-well, etc.)
  - Coordinate transformation (plate to stage coordinates)
  - Position validation against stage limits
  - JSON-based plate configuration storage

#### 4. **FileHandler Class** (`file_handler.py`)
- **Purpose**: Centralized file operations and data persistence
- **Key Features**:
  - Schema-based CSV file management
  - JSON state file handling
  - Plate configuration storage and retrieval
  - Task progress tracking files
  - Robust error handling and validation

#### 5. **GUI Module** (`gui.py`)
- **Purpose**: Modern graphical user interface for system control
- **Key Features**:
  - Dark theme with modern styling and responsive design
  - Real-time status monitoring for all system components
  - Integrated experiment configuration and position management
  - System-specific GUI initialization (e.g., Cyan, Orange systems)
  - StatusPanel and StatePanel components for unified system control
  - Launch/kill functionality for independent component operation
  - Progress visualization and error handling
  - Multi-threaded operation support with automatic updates

#### 6. **Autofocus Class** (`Scope/autofocus.py`)
- **Purpose**: Autofocus functionality (currently minimal implementation)
- **Status**: Placeholder for future autofocus algorithms

### Data Flow

```
GUI Interface → Experiment Configuration → Task Generation → Component Execution
       ↓                    ↓                        ↓                    ↓
System Control    State Persistence    Progress Tracking    Data Storage
       ↓                    ↓                        ↓                    ↓
Launch/Kill      File Communication    Status Monitoring    Results Output
```

### Component Communication Architecture

The pyScope system uses a **file-based communication** approach where components run independently and communicate through shared files in the `State` directory:

#### Independent Component Operation
- **GUI** (`gui.py`): Main interface, manages experiment creation and system control
- **Experiment** (`experiment.py`): Runs with GUI, manages experiment state and task creation
- **Scope** (`Scope/scope.py`): Runs independently, monitors for scope tasks via continuous monitoring
- **Fluidics** (`Fluidics/fluidics.py`): Runs independently, monitors for fluidics tasks via file_handler integration

#### File-Based Communication Flow
1. **GUI** initializes system-specific components (Experiment, Scope, Fluidics)
2. **Experiment** creates tasks and writes them to `Experiment_tasks.csv`
3. **Experiment** creates scope task triggers in `scope_task.txt`
4. **Scope** monitors `scope_task.txt` and processes tasks when detected
5. **Scope** creates detailed scope tasks in `Scope_tasks.csv`
6. **Scope** updates status in `Scope_status.txt`
7. **GUI** monitors scope status and progress via file system
8. **Fluidics** monitors status via file_handler system and executes protocols independently

#### Benefits of This Architecture
- **Modularity**: Each component can be started/stopped independently
- **Reliability**: File-based communication is robust and recoverable
- **Debugging**: Easy to inspect communication files for troubleshooting
- **Scalability**: Components can run on different machines if needed
- **Flexibility**: Easy to add new components or modify communication protocols

## Key Features

### Experiment Management
- **Multi-round Experiments**: Support for complex protocols with multiple hybridization rounds
- **Group-based Processing**: Organize wells into groups for different treatments
- **Protocol Integration**: Combine fluidics protocols with imaging protocols
- **State Recovery**: Resume interrupted experiments from saved state
- **Task Structure**: Comprehensive task schema supporting:
  - **Scope Tasks**: Automated imaging with protocol, group, and round tracking
  - **Fluidics Tasks**: Automated fluid handling protocols
  - **Experiment Tasks**: Manual experiment events requiring user interaction
  - **Processing Tasks**: Manual data processing and analysis events

### Position Planning
- **Automatic Tiling**: Generate optimal imaging positions with configurable overlap
- **Well Shape Support**: Handle circular and rectangular wells with rotation
- **Plate Templates**: Pre-configured templates for common plate formats
- **Coordinate Systems**: Transform between plate and stage coordinate systems

### Microscope Control
- **Multi-channel Imaging**: Support for FarRed, DeepBlue, Green, Orange channels
- **Parameter Control**: Exposure time, binning, position (X, Y, Z)
- **Independent Operation**: Continuous monitoring and task execution (runs independently)
- **File-based Communication**: Monitors experiment tasks via file system
- **Hardware Integration**: Micro-Manager core integration with fallback simulation
- **Protocol Support**: SetInitialFocus, FilterPositions, Acquire protocols
- **System-specific Classes**: Dynamic loading of system-specific scope classes (CyanScope, OrangeScope, etc.)

### User Interface
- **Modern Dark Theme**: Professional appearance with consistent styling
- **Real-time Monitoring**: Live status updates and progress tracking for all components
- **System-specific GUI**: Automatic detection and initialization of system-specific components
- **Integrated Control**: Launch/kill functionality for independent component operation
- **Configuration Tools**: Intuitive setup for experiments and positions
- **Error Handling**: Clear error messages and recovery options
- **Responsive Design**: Adaptive layout with proper window management

## File Structure

```
pyScope/
├── experiment.py          # Main experiment orchestrator
├── gui.py                 # Modern graphical interface
├── file_handler.py        # File operations and state management
├── run_experiment.bat     # Windows batch file for easy launching
├── Scope/                  # Scope-related modules
│   ├── scope.py           # Microscope control (base class)
│   ├── cyanscope.py       # Cyan-specific scope implementation
│   ├── positions.py       # Position planning and management
│   └── autofocus.py      # Autofocus (minimal implementation)
├── Fluidics/              # Fluidics-related modules
│   ├── fluidics.py        # Base fluidics class
│   ├── cyanfluidics.py    # Cyan-specific fluidics implementation
│   ├── GUI.py            # Legacy fluidics GUI
│   ├── Protocols/        # Protocol definitions
│   ├── Pumps/            # Pump control modules
│   └── Valves/           # Valve control modules
├── State/                  # Runtime state files
│   ├── Experiment_state.json
│   ├── Scope_state.json
│   ├── Positions.csv
│   └── [task and status files]
└── Plates/               # Plate configurations
    ├── example.json
    └── example_6.json
```

## System-Specific Architecture

The pyScope system uses dynamic class loading to support different microscope setups:

### System Detection and Initialization
- **Automatic Detection**: System name derived from PC hostname (e.g., "CyanScope" → "Cyan")
- **Dynamic Loading**: GUI automatically loads appropriate system-specific classes
- **Modular Design**: Each system can have custom implementations of Scope and Fluidics

### System-Specific Classes
- **Scope Classes**: `CyanScope`, `OrangeScope`, etc. (inherited from base `Scope`)
- **Fluidics Classes**: `CyanFluidics`, `OrangeFluidics`, etc. (inherited from base `Fluidics`)
- **GUI Integration**: System-specific GUI initialization with appropriate components

### Import Structure
```python
# System-specific imports (handled automatically by GUI)
from Scope.cyanscope import CyanScope
from Fluidics.cyanfluidics import CyanFluidics

# Base class imports
from Scope.scope import Scope
from Scope.positions import Positions
from Scope.autofocus import Autofocus
```

## Usage Examples

### Easy System Launch
```bash
# Windows: Use the batch file for easy launching
run_experiment.bat

# Manual launch (if needed)
python experiment.py
```

### Basic Experiment Setup
```python
from experiment import Experiment
from Scope.positions import Positions

# Initialize experiment
experiment = Experiment()

# Configure experiment
experiment.update_experiment_state({
    'groups': ['Group1', 'Group2'],
    'num_hybes': 3,
    'fluidics_protocols': ['ProtocolA', 'ProtocolB'],
    'selected_channels': ['FarRed', 'Green']
})

# Create positions
positions = Positions(
    fov_info={'X': 200, 'Y': 200, 'Overlap': 0.1},
    limits={'X': (0, 10000), 'Y': (0, 10000), 'Z': (0, 1000)}
)

# Load plate configuration
positions.load_plate_from_json('example_6')

# Generate tasks
experiment.create_tasks()
```

### Autonomous Scope Operation
```python
from Scope.scope import Scope

# Initialize scope with continuous monitoring (default)
scope = Scope()
scope.continuous_monitoring()  # Runs continuously, monitoring for tasks

# Scope will automatically process tasks as they become available
# Tasks are triggered via scope_task.txt file
```

### Standalone Scope Execution
```bash
# Run scope independently (for testing or manual operation)
python Scope/scope.py

# Run scope without Micro-Manager core (simulation mode)
python Scope/scope.py --no-core
```

## System Operation Flow

### Complete Experiment Workflow

The pyScope system follows this comprehensive workflow:

1. **System Launch**: 
   - Run `run_experiment.bat` or `python experiment.py`
   - GUI automatically detects system type and initializes appropriate components

2. **Experiment Configuration**:
   - GUI provides integrated interface for experiment setup
   - Configure groups, rounds, protocols, and channels
   - Set up plate configurations and position management

3. **Position Management**:
   - Create positions using GUI tools (manual, grid, or file-based)
   - Positions class handles tiling, coordinate transformation, and validation
   - Save positions to CSV for experiment use

4. **Task Generation**:
   - Experiment class creates tasks based on configuration
   - Tasks include both scope and fluidics protocols
   - Tasks saved to `Experiment_tasks.csv`

5. **Component Execution**:
   - Scope monitors `scope_task.txt` for imaging tasks
   - Fluidics monitors status files for fluid handling tasks
   - Each component executes tasks independently

6. **Progress Monitoring**:
   - GUI provides real-time status updates
   - Progress tracking via file-based communication
   - Error handling and recovery mechanisms

### File-Based Communication Protocol

The system uses a robust file-based communication protocol where components interact through shared files:

#### Communication Flow
1. **GUI** initializes and manages all system components
2. **Experiment** creates high-level tasks in `Experiment_tasks.csv`
3. **Experiment** creates scope task triggers in `scope_task.txt` with task details
4. **Scope** monitors `scope_task.txt` and processes tasks when detected
5. **Scope** creates detailed imaging tasks in `Scope_tasks.csv`
6. **Scope** updates execution status in `Scope_status.txt`
7. **GUI** tracks progress via `Scope_task_idx.txt` and status files
8. **Fluidics** uses legacy `XXX_Status.txt` communication (integration planned)

#### Key Communication Files
- **`Experiment_tasks.csv`**: High-level experiment tasks with columns for:
  - Scope tasks: `Scope` column with protocol commands
  - Fluidics tasks: `Fluidics` column with protocol commands
  - Task metadata: `task_name`, `group`, `round`
- **`scope_task.txt`**: Task trigger file with experiment task data
- **`Scope_tasks.csv`**: Detailed imaging tasks (position, channel, coordinates)
- **`Scope_status.txt`**: Current scope status (Idle, Running, Complete, Error)
- **`Scope_task_idx.txt`**: Current task index for progress tracking
- **`Positions.csv`**: Well positions with coordinates for imaging
- **`Fluidics_status.txt`**: Current fluidics status via file_handler system
- **`Fluidics_state.json`**: Fluidics state persistence via file_handler
- **`Fluidics.log`**: Fluidics logging via file_handler system

## Current Status

### Implemented Features
- ✅ Complete system architecture with modular components
- ✅ Micro-Manager integration for microscope control
- ✅ Comprehensive position planning and management
- ✅ File-based state persistence and recovery
- ✅ Modern GUI with dark theme and responsive design
- ✅ Multi-round experiment support with group-based processing
- ✅ Task scheduling and progress tracking
- ✅ Plate configuration system with JSON support
- ✅ Error handling and validation
- ✅ **Independent scope operation** with continuous monitoring
- ✅ **File-based communication** between experiment, scope, and fluidics components
- ✅ **Robust task processing** from experiment tasks to scope execution
- ✅ **System-specific class loading** (CyanScope, OrangeScope, etc.)
- ✅ **Easy launch system** with batch file support

### Partially Implemented
- ⚠️ **Autofocus**: Basic class structure exists but needs algorithm implementation

## Dependencies

### Core Dependencies
- `pandas`: Data manipulation and analysis
- `numpy`: Numerical computations
- `tkinter`: GUI framework (included with Python)
- `pycromanager`: Micro-Manager integration
- `json`: Configuration file handling

### Optional Dependencies
- `matplotlib`: Plotting and visualization (for position visualization)
- `threading`: Multi-threaded operations
- `logging`: Advanced logging capabilities

## Installation and Setup

1. **Install Python Dependencies**:
   ```bash
   pip install pandas numpy pycromanager
   ```

2. **Install Micro-Manager**: 
   - Download and install Micro-Manager
   - Ensure pycromanager can connect to the core

3. **Configure System**:
   - Set up `State` directory for runtime files
   - Create plate configurations in `Plates` directory
   - Configure microscope parameters in experiment setup

4. **Launch System**:
   ```bash
   # Windows: Easy launch
   run_experiment.bat
   
   # Manual launch
   python experiment.py
   ```

## Contributing

The pyScope system is designed for extensibility. Key areas for contribution:

1. **Autofocus Algorithms**: Implement focus quality metrics and optimization strategies
2. **Hardware Integration**: Add support for additional microscope and fluidics hardware
3. **User Interface**: Enhance GUI with additional features and improved usability
4. **Data Processing**: Add image processing and analysis capabilities
5. **Documentation**: Improve user guides and API documentation

## License

[License information to be added]

## Contact

[Contact information to be added]