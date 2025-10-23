# Game Plan: Integrating Fluidics with file_handler System

## Overview

This game plan outlines how to update the Fluidics code to integrate with the file_handler system, following the same patterns used by the Scope class. The goal is to make Fluidics operate as an independent component that communicates with the Experiment system through file-based communication, similar to how Scope currently works.

## Current System Analysis

### How Scope and Experiment Interact with file_handler

1. **FileHandler Integration**: Both Scope and Experiment use FileHandler for:
   - State persistence (JSON files)
   - Task management (CSV files)
   - Progress tracking (text files)
   - Status communication (text files)

2. **Scope's Autonomous Operation**:
   - Runs independently in foreground mode
   - Monitors `scope_task.txt` for task triggers
   - Creates detailed tasks in `Scope_tasks.csv`
   - Updates status in `Scope_status.txt`
   - Tracks progress via `Scope_task_idx.txt`

3. **Experiment's Task Management**:
   - Creates high-level tasks in `Experiment_tasks.csv`
   - Triggers scope tasks via `scope_task.txt`
   - Monitors scope status and progress
   - Manages experiment state in `Experiment_state.json`

### Current Fluidics System

1. **Legacy Communication**: Uses `XXX_Status.txt` files for communication
2. **Foreground Operation**: Runs in foreground with continuous monitoring loop (similar to Scope)
3. **Protocol-driven**: Executes predefined protocols with pandas DataFrame `steps`
4. **Hardware-specific**: Has subclasses for different fluidics setups
5. **Autonomous**: Already has autonomous operation with `run()` method and monitoring loop
6. **Task Structure**: Already uses pandas DataFrames for protocol steps (can be used as Fluidics_tasks)
7. **Missing**: File-based task persistence and progress tracking

## Integration Strategy

### Phase 1: Core Infrastructure Updates

#### 1.1 Update Fluidics Class Constructor
- **File**: `Fluidics/fluidics.py`
- **Changes**:
  - Add `FileHandler` initialization
  - Replace legacy `XXX_Status.txt` file handling with file_handler methods
  - Add system state directory parameter
  - Initialize fluidics status to "Idle"
  - Keep existing `run()` method structure but update communication

```python
def __init__(self, system_state_dir: str = None, enable_hardware: bool = True):
    self.log('Fluidics initialization')
    
    # Initialize file handler first
    self.file_handler = FileHandler(system_state_dir)
    
    # Initialize hardware connection with proper error handling
    self.hardware_enabled = False
    if enable_hardware:
        self._initialize_hardware()
    
    # Fluidics configuration
    self.status = "Idle"
    self.monitoring_active = False
    self.monitoring_interval = 1.0  # seconds
    
    # Initialize fluidics status
    self.file_handler.save_fluidics_status("Idle")
```

#### 1.2 Update Existing Methods
- **File**: `Fluidics/fluidics.py`
- **Changes**:
  - Update `run()` method to use file_handler instead of `XXX_Status.txt`
  - Update `read_communication()` to use file_handler methods
  - Update `update_communication()` to use file_handler methods
  - Add `_initialize_hardware()`: Initialize pump and valve connections
  - Modify `process_fluidics_task()`: Process fluidics task if trigger file exists
  - Add `_process_fluidics_task()`: Process the fluidics task when triggered

#### 1.3 Update FileHandler Class
- **File**: `file_handler.py`
- **Add Methods**:
  - `create_fluidics_task_trigger()`: Create fluidics task trigger file
  - `read_fluidics_task_trigger()`: Read fluidics task trigger file
  - `remove_fluidics_task_trigger()`: Remove fluidics task trigger file

### Phase 2: Task Processing System

#### 2.1 Update Existing Task Processing
- **File**: `Fluidics/fluidics.py`
- **Changes**:
  - Modify `execute_protocol()` to save `steps` DataFrame as `Fluidics_tasks.csv`
  - Add progress tracking with `Fluidics_task_idx.txt`
  - Add status checking in `run()` method to monitor system status
  - Update `_process_fluidics_task()` to load and execute saved tasks

#### 2.2 Task Data Structure
- **Format**: Use existing `steps` DataFrame from protocols
- **Columns**: Current protocol steps + `['start_time', 'end_time']` for timing
- **Integration**: Save `steps` as `Fluidics_tasks.csv` using existing FileHandler schema

#### 2.3 Protocol Integration
- **File**: `Fluidics/Protocols/Protocol.py`
- **Updates**:
  - Add timing tracking to protocol steps (start_time, end_time columns)
  - Integrate with file_handler for task progress
  - Add error handling and status updates
  - Ensure steps DataFrame has required columns for Fluidics_tasks schema

### Phase 3: Communication Protocol

#### 3.1 File-Based Communication
- **Trigger File**: `fluidics_task.txt` (similar to `scope_task.txt`)
- **Status File**: `Fluidics_status.txt`
- **Task File**: `Fluidics_tasks.csv`
- **Progress File**: `Fluidics_task_idx.txt`

#### 3.2 Communication Flow
1. **Experiment** creates fluidics task triggers in `fluidics_task.txt`
2. **Fluidics** monitors `fluidics_task.txt` and processes tasks when detected
3. **Fluidics** creates detailed fluidics tasks in `Fluidics_tasks.csv`
4. **Fluidics** updates execution status in `Fluidics_status.txt`
5. **System** tracks progress via `Fluidics_task_idx.txt`
6. **Fluidics** handles its own status changes (Paused, Stopped, Resume) independently

### Phase 4: Autonomous Operation

#### 4.1 Update Existing Monitoring Loop
- **File**: `Fluidics/fluidics.py`
- **Changes**:
  - Update existing `run()` method to use file_handler communication
  - Replace `XXX_Status.txt` monitoring with `fluidics_task.txt` monitoring
  - Add status checking to monitor system-wide status changes (like Scope does)
  - Keep existing foreground operation model
  - Add proper error handling and status updates
  - Maintain full control over status handling (Paused, Stopped, Resume)

#### 4.2 Status Management
- **Status States**: Idle, Running, Complete, Error
- **Status Updates**: Real-time status updates during protocol execution
- **Error Handling**: Proper error states and recovery
- **Independent Control**: Each component (Scope/Fluidics) handles its own status logic
- **Resume Functionality**: Full control over complex operations like resume

### Phase 5: Integration with Experiment System

#### 5.1 Experiment Task Creation
- **File**: `experiment.py`
- **Updates**:
  - Add fluidics task creation in `create_tasks()` method
  - Add fluidics task trigger creation using `create_fluidics_task_trigger()`
  - Add fluidics progress monitoring
  - Update task coordination to handle dependencies between scope and fluidics

#### 5.2 Task Coordination
- **Sequencing**: Ensure proper sequencing between fluidics and scope tasks
- **Dependencies**: Handle dependencies between different task types
- **Error Propagation**: Proper error handling across components

## Implementation Steps

### Step 1: Update Fluidics Base Class
1. Modify `Fluidics.__init__()` to use FileHandler
2. Add hardware initialization with error handling
3. Update `run()`, `read_communication()`, and `update_communication()` methods to use file_handler
4. Replace `XXX_Status.txt` communication with file_handler methods

### Step 2: Implement Task Processing
1. Modify existing `execute_protocol()` method to save `steps` DataFrame as `Fluidics_tasks.csv`
2. Add progress tracking with `Fluidics_task_idx.txt` 
3. Add status checking to `run()` method to monitor system status
4. Update protocol execution to track timing and progress

### Step 3: Add FileHandler Methods
1. Add fluidics task trigger methods to FileHandler (`create_fluidics_task_trigger`, etc.)
2. Ensure proper schema validation for fluidics tasks
3. Add error handling for file operations
4. Keep scope and fluidics methods separate for independence

### Step 4: Update Communication Protocol
1. Replace `XXX_Status.txt` with file_handler methods
2. Implement independent status management for fluidics
3. Add progress tracking using file_handler methods
4. Update existing `run()` method to monitor `fluidics_task.txt`
5. Keep scope and fluidics status handling independent

### Step 5: Integration Testing
1. Test fluidics task creation from experiment
2. Test autonomous fluidics operation (existing `run()` method)
3. Test communication with experiment system
4. Test error handling and recovery

## Key Differences from Scope Implementation

### Task Structure
- **Scope**: Creates new imaging tasks from experiment data
- **Fluidics**: Uses existing protocol `steps` DataFrames as tasks
- **Solution**: Save existing `steps` as `Fluidics_tasks.csv` and track progress

### Hardware Integration
- **Scope**: Uses Micro-Manager core (pycromanager)
- **Fluidics**: Uses serial communication for pumps and valves
- **Solution**: Add hardware abstraction layer with simulation mode

### Task Complexity
- **Scope**: Simple imaging tasks (position + channel)
- **Fluidics**: Complex multi-step protocols with existing step structure
- **Solution**: Use existing `steps` DataFrame and add timing/progress tracking

### Timing Requirements
- **Scope**: Fast imaging operations
- **Fluidics**: Long-running protocols with incubation times
- **Solution**: Add proper timing and progress reporting to existing steps

## Benefits of Independent Component Architecture

1. **Flexibility**: Each component (Scope/Fluidics) has full control over its own logic
2. **Maintainability**: Clear separation of concerns between components
3. **Resume Functionality**: Full control over complex operations like resume
4. **Modularity**: Independent operation of both components
5. **Debugging**: Easy to inspect communication files for both systems
6. **Scalability**: Can run on different machines if needed
7. **Future Extensibility**: Easy to add new components without affecting existing ones

## Migration Strategy

### Backward Compatibility
- Keep existing Protocol class methods
- Maintain existing hardware interfaces
- Add new methods alongside old ones initially

### Gradual Migration
1. Phase 1: Add fluidics file_handler methods
2. Phase 2: Update Fluidics to use file_handler methods
3. Phase 3: Implement task processing and status management
4. Phase 4: Update Experiment to coordinate with fluidics
5. Phase 5: Remove legacy fluidics communication code

### Testing Strategy
- Unit tests for each new method
- Integration tests with experiment system
- Hardware simulation for testing without equipment
- End-to-end testing with real protocols

## File Structure Changes

### New Files
- `Fluidics/fluidics_task_processor.py`: Task processing logic
- `Fluidics/hardware_interface.py`: Hardware abstraction layer

### Modified Files
- `Fluidics/fluidics.py`: Core fluidics class updates
- `file_handler.py`: Add fluidics task trigger methods
- `experiment.py`: Add fluidics task creation and monitoring

### Configuration Files
- Update `Fluidics_tasks` schema in FileHandler
- Add fluidics-specific state management

## Success Criteria

1. **Functional**: Fluidics can process tasks from experiment system
2. **Autonomous**: Fluidics runs independently and monitors for tasks
3. **Reliable**: Proper error handling and status reporting
4. **Integrated**: Seamless communication with experiment system
5. **Maintainable**: Clear code structure and documentation

## Timeline Estimate

- **Phase 1**: 1 day (Core infrastructure - simpler since Fluidics already has autonomous operation)
- **Phase 2**: 1-2 days (Task processing - use existing steps DataFrame)
- **Phase 3**: 1 day (Communication protocol - replacing existing file communication)
- **Phase 4**: 1 day (Update existing monitoring loop + status checking)
- **Phase 5**: 2-3 days (Integration and testing)

**Total**: 6-8 days for complete implementation (further reduced due to existing task structure)

## Risk Mitigation

1. **Hardware Dependencies**: Implement simulation mode for testing
2. **Protocol Complexity**: Start with simple protocols and expand
3. **Timing Issues**: Add proper error handling and timeouts
4. **Integration Issues**: Test each phase thoroughly before proceeding
5. **Legacy Code**: Maintain backward compatibility during transition

This game plan provides a comprehensive roadmap for integrating the Fluidics system with the file_handler architecture, ensuring consistency with the existing Scope implementation while maintaining the flexibility and reliability of the current system.
