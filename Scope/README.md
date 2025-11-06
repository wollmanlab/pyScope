# Scope Module

The Scope module provides comprehensive microscope control and image acquisition functionality for pyScope. It integrates with Micro-Manager via pycromanager and operates independently with continuous monitoring for automated experiment execution.

## Overview

The Scope module is responsible for:
- **Microscope Control**: Direct hardware control via Micro-Manager (position, channels, exposure, binning)
- **Image Acquisition**: Automated multi-channel, multi-position imaging with Z-stack support
- **Position Management**: Integration with the Positions class for coordinate-based imaging
- **Autofocus**: Multiple autofocus strategies (None, Relative, ImageScan)
- **Focus Setting**: Manual and plane-based focus setting at different hierarchical levels
- **Position Filtering**: Interactive ROI selection for filtering imaging positions
- **Independent Operation**: Continuous monitoring loop for autonomous task execution

## Architecture

### Core Classes

#### `Scope` (Base Class)
The main microscope control class that provides:
- Micro-Manager core integration
- State management (X, Y, Z, Channel, Exposure, Binning, etc.)
- Protocol execution (SetFocus, FilterPositions, SetupAutoFocus, Acquire)
- File-based communication with Experiment system
- Continuous monitoring for autonomous operation

**Key Features:**
- Property-based access to microscope parameters (`scope.X`, `scope.Y`, `scope.Z`, `scope.Channel`, etc.)
- Automatic state validation and tolerance checking
- Blocking/non-blocking stage movement
- Simulation mode when Micro-Manager core is unavailable
- Dynamic channel detection from Micro-Manager configuration files

#### `Positions` (`positions.py`)
Well plate position planning and management:
- Automatic tiling for circular and rectangular wells
- Support for rotated rectangular wells
- Grid-based plate layout generation (96-well, etc.)
- Coordinate transformation (plate to stage coordinates)
- Position validation against stage limits
- JSON-based plate configuration storage

**Key Methods:**
- `add_well()`: Generate tiling positions for a single well
- `add_well_grid()`: Generate positions for a grid of wells
- `load_plate_from_json()`: Load plate configuration from JSON file
- `load_positions_from_files()`: Load positions from Micro-Manager (.pos) or CSV files

#### `Autofocus` (`autofocus.py`)
Autofocus functionality with multiple strategies:

**Base Class: `Autofocus`**
- Placeholder implementation (no autofocus)

**`ImageScanAutofocus`**
- Z-stack scanning with configurable windows (coarse, medium, fine)
- Focus metric calculation using edge detection
- Background subtraction and filtering options

**`RelativeAutofocus`**
- Sets focus relative to reference points at different hierarchical levels (Plate, Well, Group)
- Supports stitched and manual setup methods
- Rigid transformation-based focus adjustment
- Reference point persistence via CSV files

### System-Specific Implementations

#### `CyanScope` (`cyanscope.py`)
System-specific implementation for the Cyan microscope:
- Inherits all functionality from base `Scope` class
- Custom configuration (limits, offsets, axis mapping)
- System-specific Micro-Manager config path
- Hardware-specific parameters (image shape, pixel size)

**Note**: Other system-specific implementations (e.g., `OrangeScope`) follow the same pattern.

## Key Protocols

### SetFocus
Sets focus for positions at different hierarchical levels:
- **Manual**: User manually adjusts focus for each level (Plate, Well, Group, Position)
- **Manual Plane**: User selects reference points, system fits a plane and applies to all positions

**Usage:**
```
SetFocus*['A1', 'A2']*Manual Well*None
```

### FilterPositions
Filters imaging positions using interactive ROI selection:
- Stitches preview acquisition
- Interactive drawing interface for ROI selection
- Filters positions based on selected ROIs
- Updates position groups based on ROI assignments

**Usage:**
```
FilterPositions*['A1', 'A2']*None*None
```

### SetupAutoFocus
Configures autofocus system:
- Sets up autofocus groups based on hierarchical level
- For RelativeAutofocus: Selects reference points and finds focus
- Saves reference points for future use

**Usage:**
```
SetupAutoFocus*['A', 'B', 'C']*Relative Well*None
```

### Acquire
Main image acquisition protocol:
- Multi-channel imaging with configurable exposure and delays
- Z-stack support with configurable steps
- Autofocus integration (updates focus per autofocus group)
- Group-based acquisition with preview stitching
- Progress tracking via file-based communication

**Usage:**
```
Acquire*['A1', 'A2']*hybe11*{'additional': 'parameters'}
```

## File-Based Communication

The Scope module communicates with the Experiment system through files in the `State` directory:

### Input Files
- **`scope_task.txt`**: Task trigger file with protocol commands
- **`Positions.csv`**: Well positions with coordinates for imaging
- **`Experiment_state.json`**: Experiment configuration (channels, exposure, etc.)

### Output Files
- **`Scope_tasks.csv`**: Detailed imaging tasks (position, channel, coordinates)
- **`Scope_status.txt`**: Current scope status (Idle, Running, Finished, Error)
- **`Scope_task_idx.txt`**: Current task index for progress tracking
- **`Scope_state.json`**: Current microscope state persistence
- **`Scope.log`**: Logging output

### Status Values
- `Idle`: Ready for new tasks
- `Running:<protocol>`: Currently executing a protocol
- `Finished:<protocol>`: Protocol completed successfully
- `Error:<message>`: Error occurred during execution
- `Offline`: Scope monitoring stopped

## Usage Examples

### Basic Initialization

```python
from Scope.scope import Scope

# Initialize with Micro-Manager core
scope = Scope(enable_core=True)

# Initialize without core (simulation mode)
scope = Scope(enable_core=False)
```

### System-Specific Initialization

```python
from Scope.cyanscope import CyanScope

# Initialize Cyan-specific scope
scope = CyanScope(enable_core=True)
```

### Continuous Monitoring (Autonomous Operation)

```python
# Start continuous monitoring loop
scope.continuous_monitoring()

# Scope will automatically:
# - Monitor scope_task.txt for new tasks
# - Execute protocols when detected
# - Update status and progress files
# - Continue until stopped
```

### Manual Microscope Control

```python
# Set position
scope.X = 1000.0
scope.Y = 2000.0
scope.Z = 500.0
# Or use combined property
scope.XYZ = (1000.0, 2000.0, 500.0)

# Set imaging parameters
scope.Channel = 'FarRed'
scope.Exposure = 100.0  # milliseconds
scope.Binning = '2'

# Capture image
image = scope.snapImage()
```

### Position Management

```python
from Scope.positions import Positions

# Initialize positions with microscope configuration
positions = Positions(
    fov_info={'X': 200, 'Y': 200, 'Overlap': 0.1},
    offsets={'X': 0, 'Y': 0, 'Z': 0},
    axis_mapping={'stage_x': 'plate_x', 'stage_y': 'plate_y'},
    limits={'X': (0, 10000), 'Y': (0, 10000), 'Z': (0, 1000)}
)

# Load plate configuration
positions.load_plate_from_json('example_6')

# Or add wells manually
positions.add_well('A1', {
    'center': {'X': 0, 'Y': 0, 'Z': 0},
    'shape': 'circle',
    'dimensions': {'radius': 3000}
})

# Access positions
well_positions = positions.get_well_positions('A1')
```

### Autofocus Setup

```python
from Scope.autofocus import RelativeAutofocus

# Initialize autofocus
autofocus = RelativeAutofocus(level='well', setup_method='stitched')

# Setup autofocus (selects reference points and finds focus)
autofocus.setup(scope)

# During acquisition, autofocus updates focus per group
autofocus.update_focus(scope, 'A1')

# Get focus for a position
focus_z = autofocus.focus(scope, X=1000, Y=2000, position_name='WellA1_Xi0_Yi0', goto=True)
```

## Configuration

### Micro-Manager Configuration
The Scope module reads channel configurations from Micro-Manager config files:
- Default: `Configs/Scope_config.cfg`
- System-specific: `Configs/CyanScope_config.cfg` (for CyanScope)

The config file should contain `ConfigGroup,Channel,<ChannelName>` entries for each available channel.

### Scope Configuration
Each system-specific scope class defines:
- **`limits`**: Valid ranges for X, Y, Z, Exposure, Binning, Channel
- **`offsets`**: Stage coordinate offsets
- **`axis_mapping`**: Mapping between plate and stage coordinate systems
- **`tolerance`**: Tolerance values for state checking
- **`ImageShape`**: Camera image dimensions (pixels)
- **`PixelSize`**: Pixel size in microns

## Integration with Processing Module

The Scope module integrates with the Processing module for:
- **Stitching**: Stitches preview acquisitions for position filtering and focus setting
- **Image Processing**: Optional image processing during acquisition (via ImageProcessor)
- **Registration**: Supports registration dictionaries for position correction

## Dependencies

- `pycromanager`: Micro-Manager integration
- `pandas`: Data manipulation
- `numpy`: Numerical operations
- `scipy`: Scientific computing (optimization, filtering)
- `tifffile`: TIFF image I/O
- `matplotlib`: Visualization (for interactive ROI selection)
- `tkinter`: GUI components (for focus popups)

## Logging

The Scope module uses the FileHandler logging system:
- Logs are written to `State/Scope.log`
- Log levels: `debug`, `info`, `warning`, `error`
- System prefix: `Scope` (or specific class name for subclasses)

## Error Handling

- **Micro-Manager Connection**: Falls back to simulation mode if core unavailable
- **Invalid Parameters**: Validates all parameters against limits before setting
- **Stage Movement**: Waits for stage to reach target position with timeout
- **Task Interruption**: Checks for stop commands during long-running protocols
- **File I/O**: Robust error handling for all file operations

## Future Enhancements

- Enhanced autofocus algorithms
- Multi-point focus plane fitting improvements
- Real-time image preview during acquisition
- Advanced registration algorithms
- Support for additional hardware configurations

