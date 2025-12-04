import time
import os
import json
import pandas as pd
from typing import Dict
from Scope.positions import Positions
from Scope.autofocus import Autofocus
# from gui import GUI_COLORS, GUI_FONTS, apply_dark_theme, create_dark_style, create_title_label, create_error_label, create_button
from file_handler import FileHandler

class Experiment():
    """Central orchestrator for experiment management and task execution.
    
    The Experiment class coordinates multi-round imaging experiments with integrated
    fluidics protocols. It manages task creation, scheduling, and execution for both
    Scope and Fluidics systems through file-based communication.
    
    Attributes:
        file_handler (FileHandler): File handler instance for state management.
        tasks (pd.DataFrame): DataFrame containing experiment tasks with columns for
            each system (Scope, Fluidics).
        positions (pd.DataFrame): DataFrame containing well positions with columns:
            group, well, autofocus_group, x, y, z.
    """
    
    def __init__(self):
        """Initialize the Experiment class.
        
        Loads tasks and positions from file handler. Creates empty DataFrames if
        no existing data is found.
        """
        self.file_handler = FileHandler()
        self.file_handler.verbose = True
        self.log('Init')
        try:
            self.tasks = self.file_handler.get_tasks("Experiment")
            self.log(f'Tasks loaded successfully: {self.tasks}')
        except:
            self.log(f'No tasks found - creating empty tasks dataframe')
            self.tasks = pd.DataFrame(columns=['task_name','group','round','fluidics_protocol','fluidics_group','fluidics_round'])
        try:
            self.positions = self.file_handler.Positions
            self.log(f'Positions loaded successfully: {self.positions}')
        except:
            self.log(f'No Positions Found: creating empty positions dataframe')
            self.positions = pd.DataFrame(columns=['group','well','autofocus_group','x','y','z'])
    
    def log(self, message, level='info'):
        """Log messages using FileHandler's logging system.
        
        Args:
            message (str): Message to log.
            level (str): Log level ('debug', 'info', 'warning', 'error').
                Defaults to 'info'.
        """
        self.file_handler.log(message, level=level, system_prefix='Experiment')
    
    @property
    def status(self):
        """Get experiment status from file handler.
        
        Returns:
            str: Current experiment status (e.g., 'Running:message', 'Paused:message', 'Stopped:message','Finished:message').
        """
        return self.file_handler.get_status("Experiment")
    
    @status.setter
    def status(self, value):
        """Set experiment status and save to file handler.
        
        Args:
            value (str): New status value to set.
        """
        self.file_handler.save_status("Experiment", value)

    def continuous_monitoring(self):
        """Run continuous monitoring loop for autonomous operation.
        
        Monitors status file for commands and executes protocols accordingly.
        Continues until 'Stop' command is received or an error occurs.
        Sets status to 'offline' when terminated.
        """
        self.last_message = ''
        self.log('Continuous monitoring started')
        crashed = False
        try:
            while True:
                status = self.status
                if self.last_message!=status:
                    self.last_message = status
                    self.log(f"New Message: {status}")
                if 'Stop' in status:
                    self.log('Continuous monitoring stopped by user')
                    break
                elif "Command" in status:
                    self.interpret_command(status)
                time.sleep(1)
        except Exception as e:
            self.log(f"Error in continuous monitoring: {e}", level='warning')
            crashed = True
        finally:
            if not crashed:
                self.status = "offline"
            else:
                self.status = f"Crashed:{self.status.split(':')[-1]}"
            self.log('Continuous monitoring terminated - status set to offline')

    def interpret_command(self, current_message):
        """Interpret and execute command from status file.
        
        Parses command message and executes the corresponding protocol.
        Updates status to 'Running' during execution and 'Finished' on completion.
        
        Args:
            current_message (str): Command message in format 'Command:<protocol>'.
        """
        self.log(f"Interpreting Command: {current_message}")
        self.busy = True
        message = current_message.split(':')[-1]
        self.status = "Running:"+message
        self.execute_protocol(message)
        self.status = "Finished:"+message
        self.busy = False

    def is_busy(self, device):
        """Check if a device is currently busy.
        
        A device is considered busy if its status contains 'Running', 'Command',
        or 'Paused'.
        
        Args:
            device (str): Device name to check (e.g., 'Scope', 'Fluidics').
        
        Returns:
            bool: True if device is busy, False otherwise.
        """
        status = self.file_handler.get_status(device)
        if 'Running' in status:
            return True
        if 'Command' in status:
            return True
        elif 'Paused' in status:
            return True  
        elif 'Crashed' in status:
            return True        
        else:
            return False

    def wait_until_not_busy(self, device):
        """Wait until a device is no longer busy.
        
        Blocks execution and polls device status every second until the device
        becomes available.
        
        Args:
            device (str): Device name to wait for (e.g., 'Scope', 'Fluidics').
        """
        start_time = time.time()
        while self.is_busy(device):
            self.log(f"Device {device} is busy, waiting until not busy, {int(time.time() - start_time)} seconds",level='info')
            time.sleep(30)
        self.log(f"Device {device} is not busy after {int(time.time() - start_time)} seconds",level='info')

    def execute_protocol(self, message):
        """Execute a protocol based on command message.
        
        Routes protocol execution to appropriate handler based on message content.
        
        Args:
            message (str): Protocol command message. Supported commands:
                - 'Execute Tasks': Execute all tasks in Experiment_tasks.csv
                - 'Create Tasks': Create tasks from experiment configuration
        """
        if 'Execute Tasks' in message:
            self.execute_task()
        elif 'Create Tasks' in message:
            self.create_tasks()
        else:
            self.log(f"Unknown protocol: {message}", level='warning')


    def execute_task(self):
        """Execute all tasks in the experiment task list.
        
        Iterates through all tasks, waiting for each device to be available
        before triggering task execution. Stops if Scope status contains 'stop'.
        Updates task index for progress tracking.
        """
        self.tasks = self.file_handler.get_tasks("Experiment")
        for idx, task in self.tasks.iterrows():
            # add pause checing for statusfile for experiment
            if 'stop' in self.file_handler.get_status("Experiment",read_only=False).lower():
                self.log("Experiment is stopped, stopping experiment", level='warning')
                return
            if 'stop' in self.file_handler.get_status("Scope",read_only=False).lower():
                self.log("Scope is stopped, stopping experiment", level='warning')
                return
            self.file_handler.save_task_idx("Experiment", idx)
            # Wait for all to be available
            for device in self.tasks.columns:
                # if task[device] is not None:
                self.wait_until_not_busy(device)
            # Execute the tasks
            for device in self.tasks.columns:
                if str(task[device]) != 'idle':
                    self.file_handler.save_status(device, "Command:"+str(task[device]))
                else:
                    self.file_handler.save_status(device, "idle")
        self.file_handler.save_task_idx("Experiment", 0)


    def _reset_system(self):
        """Clear all files in State directory and reset system to initial state.
        
        Removes all files and directories in the State directory, clears internal
        state attributes, and sets status to 'Running'.
        
        Returns:
            bool: True if reset successful, False otherwise.
        """
        try:
            self.log('Resetting system to initial state...')
            
            if os.path.exists(self.file_handler.system_state_dir):
                for filename in os.listdir(self.file_handler.system_state_dir):
                    file_path = os.path.join(self.file_handler.system_state_dir, filename)
                    try:
                        if os.path.isfile(file_path):
                            os.remove(file_path)
                            self.log(f'Removed file: {filename}')
                        elif os.path.isdir(file_path):
                            import shutil
                            shutil.rmtree(file_path)
                            self.log(f'Removed directory: {filename}')
                    except Exception as e:
                        self.log(f'Error removing {filename}: {e}', level='warning')
            
            self.acquisition_start_time = time.time()
            # self.state = {'X':None,'Y':None,'Z':None,'Exposure':None,'Channel':None,'Binning':None,'ImageShape':None,'PixelSize':None}
            self.status = "Running"
            
            if hasattr(self, 'tasks'):
                delattr(self, 'tasks')
            if hasattr(self, 'imaging_tasks'):
                delattr(self, 'imaging_tasks')
            if hasattr(self, 'positions'):
                delattr(self, 'positions')
            # State attributes are no longer stored in self - they're loaded from JSON files via properties
            
            self.log('System reset completed successfully')
            return True
            
        except Exception as e:
            self.log(f'Error resetting system: {e}', level='error')
            return False

    def _recover_state(self):
        """Load all saved state files to recover experiment state.
        
        Validates that required files exist (Experiment_tasks.csv, Positions.csv,
        Experiment_state.json) before allowing recovery.
        
        Returns:
            bool: True if recovery successful, False otherwise.
        
        Raises:
            Exception: If required state files are missing.
        """
        try:
            self.log('Recovering experiment state from saved files...')
            
            # Check if tasks file exists
            tasks_df = self.file_handler.get_tasks("Experiment")
            if tasks_df.empty:
                self.log('No Experiment_tasks.csv found - cannot recover without tasks', level='error')
                raise Exception("Cannot recover: Experiment_tasks.csv not found")
            
            # Check if positions file exists
            positions_df = self.file_handler.Positions
            if positions_df.empty:
                self.log('No positions file found - cannot recover without positions', level='error')
                raise Exception("Cannot recover: Positions.csv not found")
            
            # Check if experiment state file exists
            exp_state = self.file_handler.get_state("Experiment")
            if not exp_state:
                self.log('No Experiment_state.json found - cannot recover without experiment configuration', level='error')
                raise Exception("Cannot recover: Experiment_state.json not found")
            
            # All required files exist - state is available via properties
            self.log('State recovery completed successfully - all state available via properties')
            return True
            
        except Exception as e:
            self.log(f'Error recovering state: {e}', level='error')
            return False


    def _read_status(self): #FIXME: Update to handle cases better
        """Read status from status file and handle special status values.
        
        Reads Experiment_status.txt and handles special status values:
        - 'Paused': Waits in loop until status changes
        - 'Reset': Calls _reset_system() and updates status
        - 'Recover': Calls _recover_state() and updates status
        - 'Stopped': Raises exception to stop execution
        
        Raises:
            Exception: If status is 'Stopped' or if reset/recovery fails.
        """
        try:
            status_file = os.path.join(self.file_handler.system_state_dir, "Experiment_status.txt")
            if os.path.exists(status_file):
                with open(status_file, 'r') as f:
                    new_status = f.read().strip()
                
                if new_status == "Paused":
                    self.log(f'Status is Paused, waiting for status change...')
                    while new_status == "Paused":
                        time.sleep(1)
                        try:
                            with open(status_file, 'r') as f:
                                new_status = f.read().strip()
                        except Exception as e:
                            self.log(f'Error reading status file during pause: {e}', level='warning')
                            time.sleep(1)
                            continue
                    
                    if new_status == "Stopped":
                        self.log(f'Status changed from Paused to Stopped - cancelling operation')
                        raise Exception("Experiment stopped by user")
                    elif new_status == "Running":
                        self.log(f'Status changed from Paused to Running - resuming operation')
                    else:
                        self.log(f'Status changed from Paused to {new_status}')
                
                if new_status != self.status:
                    self.log(f'Status changed from {self.status} to {new_status}')
                    self.status = new_status
                    
                if new_status == "Reset":
                    self.log(f'Status is Reset - clearing all files and resetting system...')
                    if self._reset_system():
                        self.log(f'System reset successful - status remains Running')
                    else:
                        self.log(f'System reset failed - changing status to Stopped')
                        with open(status_file, 'w') as f:
                            f.write("Stopped")
                        self.status = "Stopped"
                        raise Exception("Experiment stopped due to reset failure")
                
                if new_status == "Recover":
                    self.log(f'Status is Recover - attempting state recovery...')
                    if self._recover_state():
                        self.log(f'State recovery successful - changing status to Running')
                        with open(status_file, 'w') as f:
                            f.write("Running")
                        self.status = "Running"
                    else:
                        self.log(f'State recovery failed - changing status to Stopped')
                        with open(status_file, 'w') as f:
                            f.write("Stopped")
                        self.status = "Stopped"
                        raise Exception("Experiment stopped due to recovery failure")
                
                if new_status == "Stopped":
                    self.log(f'Status is Stopped - cancelling operation')
                    raise Exception("Experiment stopped by user")
                    
            else:
                self.log('status.txt not found - entering pause state until status file is created', level='warning')
                while not os.path.exists(status_file):
                    time.sleep(1)
                    try:
                        if os.path.exists(status_file):
                            break
                    except Exception as e:
                        self.log(f'Error checking for status file during pause: {e}', level='warning')
                        time.sleep(1)
                        continue
                
                try:
                    with open(status_file, 'r') as f:
                        new_status = f.read().strip()
                    self.log(f'Status file created with status: {new_status}')
                except Exception as e:
                    self.log(f'Error reading newly created status file: {e}', level='warning')
                    new_status = "Running"
        except Exception as e:
            if "Experiment stopped by user" in str(e):
                raise  # Re-raise the stop exception
            self.log(f'Error reading status file: {e}', level='warning')

    def create_tasks(self): #FIXME: Single String for each system and add in setup too
        """Create experiment tasks from configuration.
        
        Generates a task list based on experiment state configuration including:
        - Setup tasks: SetFocus, Acquire preview, FilterPositions, SetupAutoFocus
        - Main tasks: Fluidics and Scope protocols organized by group and round
        
        Tasks are saved to Experiment_tasks.csv with columns for each system
        (Scope, Fluidics). Each task row contains protocol commands for the
        appropriate systems.
        
        The task structure depends on the number of groups:
        - Single group: Sequential execution of protocols across rounds
        - Multiple groups: Nested loops (rounds -> protocols -> groups)
        
        Returns:
            None: Tasks are saved to file via FileHandler.
        """
        systems = ['Scope','Fluidics']#,'Processing']
        self.tasks = pd.DataFrame(columns=systems)
        
        # Get experiment state
        exp_state = self.file_handler.get_state("Experiment")
        groups = exp_state.get('groups', [])
        num_hybes = exp_state.get('num_hybes', 0)
        fluidics_protocols = exp_state.get('fluidics_protocols', [])
        group_assignments = exp_state.get('group_assignments', {})
        fluidics_well_assignments = exp_state.get('fluidics_well_assignments', {})
        filtering_method = exp_state.get('position_filtering', 'Draw')
        autofocus_method = exp_state.get('autofocus_method', 'Relative')
        acquisition_focus_method = exp_state.get('acquisition_focus', 'Plane')
        preview_focus_method = exp_state.get('preview_focus', 'ManualWell')
        skip_first_fluidics_task = exp_state.get('skip_first_fluidics_task', True)
        # Check if we have the required data    
        if not groups or not fluidics_protocols or num_hybes == 0:
            self.log("Cannot create tasks: missing required experiment configuration", level='warning')
            return
        
        # Debug information
        self.log(f"Creating tasks with:")
        self.log(f"  Groups: {groups}")
        self.log(f"  Protocols: {fluidics_protocols}")
        self.log(f"  Rounds: {num_hybes}")
        self.log(f"  Group assignments: {group_assignments}")
        self.log(f"  Fluidics well assignments: {fluidics_well_assignments}")
        
        # Load positions to get wells
        positions_df = self.file_handler.Positions
        available_wells = positions_df['well'].unique()
        self.log(f"  Available wells: {list(available_wells)}")

        # First There are some setup tasks that need to be created
        task_number = 0
        chambers = list(available_wells)
        self.tasks.loc[task_number,'Scope'] = f"SetFocus*{str(chambers)}*{preview_focus_method}"
        task_number += 1
        self.tasks.loc[task_number,'Scope'] = f"Acquire*{str(chambers)}*preview"
        task_number += 1
        self.tasks.loc[task_number,'Scope'] = f"FilterPositions*{str(chambers)}*{filtering_method}"
        task_number += 1
        self.tasks.loc[task_number,'Scope'] = f"SetFocus*{str(chambers)}*{acquisition_focus_method}"
        task_number += 1
        self.tasks.loc[task_number,'Scope'] = f"SetupAutoFocus*{str(chambers)}*{autofocus_method}"
        task_number += 1
        self.tasks.loc[task_number,'Scope'] = f"Acquire*{str(chambers)}*preview"
        task_number += 1
        self.tasks.loc[task_number,'Scope'] = f"ManualReview*{str(chambers)}*UserInput"
        task_number += 1
        

        first_stitch_tracked = set()
        
        if len(groups) == 1:
            group = groups[0]
            group_wells = [well for well in positions_df['well'].unique() if group_assignments.get(well) == group]
            scope_wells = str([group_assignments.get(well, '') for well in group_wells])
            fluidics_wells = str([fluidics_well_assignments.get(well, '') for well in group_wells])
            self.log(f"  Single group '{group}' has wells: {group_wells}, fluidics wells: '{fluidics_wells}'")
            
            for round in range(num_hybes):
                for fluidics_protocol in fluidics_protocols: # ['Strip', 'Hybe']
                    fluidics_command = f"{fluidics_protocol}*{fluidics_wells}*{str(round+1)}" # e.g. 'Strip*['A', 'B']*1'
                    scope_command = f"Acquire*{group_wells}*{fluidics_protocol+str(round+1)}" # e.g. 'Acquire*['A', 'B']*Strip1'
                    task_number += 1
                    self.tasks.loc[task_number,'Fluidics'] = fluidics_command
                    task_number += 1
                    self.tasks.loc[task_number,'Scope'] = scope_command
                    
                    stitch_command = f"Stitch*{str(group_wells)}*{fluidics_protocol+str(round+1)}" #e.g. 'Stitch*['A', 'B']*Strip1'
                    stitch_key = f"{group}_{fluidics_protocol}"
                    if stitch_key not in first_stitch_tracked:
                        stitch_command += "+idx_stitch" #e.g. 'Stitch*['A', 'B']*Strip1+idx_stitch'
                        first_stitch_tracked.add(stitch_key)
                    # self.tasks.loc[task_number+1,'Processing'] = stitch_command
        else:
            for round in range(num_hybes):
                for fluidics_protocol in fluidics_protocols: # ['Strip', 'Hybe']
                    for group in groups: # ['Group 1', 'Group 2']
                        group_wells = [well for well in positions_df['well'].unique() if group_assignments.get(well) == group]
                        fluidics_wells = str([fluidics_well_assignments.get(well, '') for well in group_wells])
                        fluidics_command = f"{fluidics_protocol}*{fluidics_wells}*{str(round+1)}" # e.g. 'Strip*['A', 'B']*1'
                        scope_command = f"Acquire*{group_wells}*{fluidics_protocol+str(round+1)}" # e.g. 'Acquire*['A', 'B']*Strip1'
                        
                        task_number += 1
                        self.tasks.loc[task_number,'Fluidics'] = fluidics_command
                        self.tasks.loc[task_number+1,'Scope'] = scope_command
                        
                        stitch_command = f"Stitch*{str(group_wells)}*{fluidics_protocol+str(round+1)}" #e.g. 'Stitch*['A', 'B']*Strip1'
                        stitch_key = f"{group}_{fluidics_protocol}"
                        if stitch_key not in first_stitch_tracked:
                            stitch_command += "+idx_stitch" #e.g. 'Stitch*['A', 'B']*Strip1+idx_stitch'
                            first_stitch_tracked.add(stitch_key)
                        # self.tasks.loc[task_number+2,'Processing'] = stitch_command

        if skip_first_fluidics_task:
            # find the first fluidics task and delete it
            fluidics_idxs = [idx for idx, task in self.tasks.iterrows() if not pd.isna(task['Fluidics'])]
            self.tasks.loc[fluidics_idxs[0],'Fluidics'] = self.tasks.loc[0,'Fluidics']

        self.tasks[self.tasks.isna()] = "idle"
        self.file_handler.save_tasks("Experiment", self.tasks)
        
        # Tasks created successfully - no GUI needed for now
        self.log("Tasks created and saved successfully")


if __name__ == '__main__':
    import socket
    from gui import create_experiment_gui
    
    # Get PC name and use it as the system
    pc_name = socket.gethostname()
    system = pc_name.split('Scope')[0].capitalize()
    create_experiment_gui(system=system)