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
    def __init__(self):
        self.file_handler = FileHandler()
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
            self.positions = pd.DataFrame(columns=['well','x','y','z'])
    
    def log(self, message, level='info'):
        """Log messages using FileHandler's logging system."""
        self.file_handler.log(message, level=level, system_prefix='Experiment')
    
    @property
    def status(self):
        """Get experiment status from file handler."""
        return self.file_handler.get_status("Experiment")
    
    @status.setter
    def status(self, value):
        """Set experiment status and save to file handler."""
        self.file_handler.save_status("Experiment", value)

    def continuous_monitoring(self):
        self.last_message = ''
        self.log('Continuous monitoring started')
        try:
            while True:
                status = self.status
                if self.last_message!=status:
                    self.last_message = status
                    self.log(f"New Message: {status}")
                if status == "Stop":
                    self.log('Continuous monitoring stopped by user')
                    break
                elif "Command" in status:
                    self.interpret_command(status)
                time.sleep(1)
        finally:
            self.status = "offline"
            self.log('Continuous monitoring terminated - status set to offline')

    def interpret_command(self, current_message):
        """Interpret message from other software."""
        self.log(f"Interpreting Command: {current_message}")


    def _reset_system(self):
        """Clear all files in State directory and reset system to initial state"""
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
        """Load all saved state files to recover experiment state"""
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
        """Read status from status.txt file and update self.status. Handles Paused status with sleep loop."""
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
        task_number = 0
        systems = ['Scope','Fluidics','Experiment']
        self.tasks = pd.DataFrame(columns=systems)
        
        # Get experiment state
        exp_state = self.file_handler.get_state("Experiment")
        groups = exp_state.get('groups', [])
        num_hybes = exp_state.get('num_hybes', 0)
        fluidics_protocols = exp_state.get('fluidics_protocols', [])
        group_assignments = exp_state.get('group_assignments', {})
        fluidics_well_assignments = exp_state.get('fluidics_well_assignments', {})
        
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
        
        if len(groups) == 1:
            group = groups[0]
            # Get wells for this group
            group_wells = [well for well in positions_df['well'].unique() if group_assignments.get(well) == group]
            # Get fluidics wells for this group
            scope_wells = ''.join([group_assignments.get(well, '')+',' for well in group_wells])[:-1]
            fluidics_wells = ''.join([fluidics_well_assignments.get(well, '')+',' for well in group_wells])[:-1]
            self.log(f"  Single group '{group}' has wells: {group_wells}, fluidics wells: '{fluidics_wells}'")
            
            for round in range(num_hybes):
                for fluidics_protocol in fluidics_protocols:
                    fluidics_command = f"{fluidics_protocol}*[{fluidics_wells}]*{fluidics_protocol+str(round+1)}"
                    scope_command = f"Acquire*[{scope_wells}]*{fluidics_protocol+str(round+1)}"
                    task_number += 1
                    self.tasks.loc[task_number,'Fluidics'] = fluidics_command
                    task_number += 1
                    self.tasks.loc[task_number,'Scope'] = scope_command

        else:
            for round in range(num_hybes):
                for fluidics_protocol in fluidics_protocols:
                    for group in groups:
                        group_wells = [well for well in positions_df['well'].unique() if group_assignments.get(well) == group]
                        scope_wells = ''.join([group_assignments.get(well, '')+',' for well in group_wells])[:-1]
                        fluidics_wells = ''.join([fluidics_well_assignments.get(well, '')+',' for well in group_wells])[:-1]
                        fluidics_command = f"{fluidics_protocol}*[{fluidics_wells}]*{fluidics_protocol+str(round+1)}"
                        scope_command = f"Acquire*[{group_wells}]*{fluidics_protocol+str(round+1)}"
                        
                        task_number += 1
                        self.tasks.loc[task_number,'Fluidics'] = fluidics_command
                        self.tasks.loc[task_number+1,'Scope'] = scope_command

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