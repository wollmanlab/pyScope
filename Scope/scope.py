import time
import os
import json
import pandas as pd
from pycromanager import Core
from typing import Dict, Any
from file_handler import FileHandler
import numpy as np
import tkinter as tk
from tkinter import messagebox
import threading

class Scope:
    def __init__(self, enable_core: bool = True):
        """
        Initialize the Scope class.
        
        Args:
            enable_core (bool): Whether to initialize Micro-Manager core connection
        """
        # Initialize file handler first
        self.file_handler = FileHandler()
        self.log('Scope initialization')
        self.enable_core = enable_core
        if self.enable_core:
            self._initialize_core()
        
        # Scope configuration
        self.acquisition_start_time = time.time()
        self.blocking = True
        self.remember_state = True


        self.tolerance = {'X': 0.1, 'Y': 0.1, 'Z': 0.1,'Exposure': 0.1}
        self.overtime_warning = 0
        self.limits = {
            'X': (0, 10000), 'Y': (0, 10000), 'Z': (0, 10000), 
            'Exposure': (0, 10000), 'Binning': ['1', '2', '4'], 
            'Channel': ['FarRed', 'DeepBlue', 'Green', 'Orange'], 
            'Time': (0, 1e8)
        }
        self.offsets = {'X': 0, 'Y': 0, 'Z': 0}
        self.axis_mapping = {'stage_x': 'plate_x', 'stage_y': 'plate_y'}
        self.overlap = 0.1
        
        # Microscope state
        self.state = {
            'X': None, 'Y': None, 'Z': None, 'Exposure': None, 
            'Channel': None, 'Binning': None, 'ImageShape': None, 'PixelSize': None
        }
        
        # Task management
        # self.positions = pd.DataFrame(columns=['position_name', 'well', 'X', 'Y', 'Z'])
        # self.imaging_tasks = pd.DataFrame(columns=['task_name', 'protocol', 'group', 'round', 'well', 'position_name', 'channel', 'X', 'Y', 'Z', 'start_time', 'end_time'])
        # self.current_imaging_task_idx = 0
        # self.status = "Idle"
        
        # # Autonomous operation settings
        # self.monitoring_active = False
        # self.monitoring_interval = 1.0  # seconds
        
        self.log('Scope initialization complete')
    
    def log(self, message, level='info'):
        """Log messages using FileHandler's logging system."""
        self.file_handler.log(message, level=level, system_prefix='Scope')

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
        self.busy = True
        message = current_message.split(':')[-1]
        self.status = "Running:"+message
        self.execute_protocol(message)
        self.status = "Finished:"+message
        self.busy = False

    def execute_protocol(self, message):
        """Execute the protocol."""
        self.log(f"Executing Protocol: {message}")
        protocol,chambers,name,other = self.decode_message(message)
        if protocol == 'SetInitialFocus': #FIXME "SetInitialFocus*[['A1', 'A2','A3','B1']]*ManualWell" 
            self.log(f"Setting initial focus for: {chambers}, {name}, {other}")
            self.set_initial_focus(chambers,name,other)
        elif protocol == 'FilterPositions': #FIXME "FilterPositions*[['A1', 'A2','A3','B1']]*Draw" 
            self.log(f"Filtering positions for: {chambers}, {name}, {other}")
            # self.filter_positions(chambers,name,other)
        elif protocol == 'SetFocus': #FIXME "SetFocus*[['A1', 'A2','A3','B1']]*RelativePlane" 
            self.log(f"Setting focus for: {chambers}, {name}, {other}")
            # self.set_focus(chambers,name,other)
        elif protocol == 'Acquire': #FIXME "Acquire*[['A1', 'A2']]*hybe11" 
            tasks = self.create_tasks(protocol,chambers,name,other) #FIXME
            self.file_handler.save_tasks("Scope", tasks)
            self.summarize_protocol(tasks) #FIXME
            if not self.simulate:
                for idx,task in tasks.iterrows():
                    self.file_handler.save_task_idx("Scope", idx)
                    self.execute_task(task) #FIXME
        else:
            self.log(f"Unknown protocol: {protocol}", level='warning')
                
        # Clean up task files after protocol completion (both real and simulated)
        self.file_handler.save_task_idx("Scope", 0)
        self.file_handler.delete_tasks("Scope")
        self.status = "Idle"
        self.simulate = False

    def decode_message(self, message):
        """Decode the message."""
        protocol,chambers,other = message.split('*')
        if '+' in other:
            name = other.split('+')[0]
            other = other.split('+')[1]
        else:
            name = other
            other = ''
        chambers = chambers[1:-1].split(',')
        if '!' in other:
            other = other.split('!')[0]
            self.simulate = True
        else:
            self.simulate = False
        return protocol,chambers,name,other

    def create_tasks(self, protocol, chambers, name, other):
        """Create tasks based on the protocol, chambers, name, and other."""
        self.log(f"Creating tasks for: Protocol={protocol}, Chambers={chambers}, Name={name}, Other={other}")
        tasks = self.create_imaging_tasks(self,positions=None, channels=None, zindexes=None, timepoints=None, imaging_order='tpcz')
        return tasks

    def _initialize_core(self):
        """Initialize Micro-Manager core connection."""
        try:
            self.core = Core()
            self.core_enabled = True
            self.log("Micro-Manager core connection established")
        except Exception as e:
            self.log(f"Micro-Manager is not running: {e}", level='warning')
            self.core = None
            self.core_enabled = False
    
    # def start_autonomous_monitoring(self, use_threading=False):
    #     """Start autonomous monitoring for scope tasks."""
    #     if self.monitoring_active:
    #         self.log("Monitoring is already active", level='warning')
    #         return
        
    #     self.monitoring_active = True
    #     self.log("Starting autonomous monitoring")
        
    #     if use_threading:
    #         # Start monitoring in a separate thread (legacy mode)
    #         import threading
    #         self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
    #         self.monitoring_thread.start()
    #     else:
    #         # Run monitoring in foreground (default behavior)
    #         self._monitoring_loop()
    
    # def _monitoring_loop(self):
    #     """Internal monitoring loop that runs in foreground by default."""
    #     try:
    #         while self.monitoring_active:
    #             # Check for scope task triggers
    #             if self.process_scope_task():
    #                 self.log("Task completed, continuing monitoring")
                
    #             # Sleep for monitoring interval
    #             time.sleep(self.monitoring_interval)
                
    #     except Exception as e:
    #         self.log(f"Error in monitoring loop: {e}", level='error')
    #     finally:
    #         self.stop_monitoring()
    
    # def stop_monitoring(self):
    #     """Stop autonomous monitoring."""
    #     self.monitoring_active = False
    #     self.log("Stopping autonomous monitoring")
        
    #     # Wait for monitoring thread to finish if it exists (only in threading mode)
    #     if hasattr(self, 'monitoring_thread') and self.monitoring_thread.is_alive():
    #         self.monitoring_thread.join(timeout=2.0)  # Wait up to 2 seconds
        
    #     self.status = "Idle"
    
    # def process_scope_task(self):
    #     """Process scope task by monitoring Experiment task_idx and status."""
    #     try:
    #         # Check if scope status allows execution
    #         scope_status = self.file_handler.get_status("Scope")
    #         if scope_status in ["stopped", "paused"]:
    #             return False
            
    #         # Get current experiment task index
    #         exp_task_idx = self.file_handler.get_task_idx("Experiment")
            
    #         # Get experiment tasks to see what task we should execute
    #         exp_tasks = self.file_handler.get_tasks("Experiment")
            
    #         if exp_tasks.empty or exp_task_idx > len(exp_tasks) or exp_task_idx < 1:
    #             return False
            
    #         # Get the current experiment task (convert 1-based index to 0-based for iloc)
    #         current_task = exp_tasks.iloc[exp_task_idx - 1]
            
    #         # Check if this task has scope work to do
    #         scope_protocol = current_task.get('Scope_Protocol')
    #         if not scope_protocol or pd.isna(scope_protocol):
    #             return False
            
    #         self.log(f"Processing experiment task {exp_task_idx}: {scope_protocol}")
    #         self._process_scope_task_from_experiment(current_task)
    #         return True
            
    #     except Exception as e:
    #         self.log(f"Error processing scope task: {e}", level='error')
    #         return False
    
    # def _process_scope_task_from_experiment(self, experiment_task_row):
    #     """Process the scope task from experiment task data."""
    #     try:
    #         self.log(f"Processing scope task from experiment: {experiment_task_row}")
            
    #         # Update status to Running
    #         self.status = "Running"
            
    #         # Load positions from file
    #         self.positions = self.file_handler.Positions
            
    #         # Create imaging tasks based on the experiment task data
    #         self._create_imaging_tasks_from_experiment_task(experiment_task_row)
            
    #         # Execute acquisition
    #         self._execute_acquisition()
            
    #         # Update status to Complete
    #         self.status = "Complete"
            
    #         self.log("Scope task processing completed")
            
    #     except Exception as e:
    #         self.log(f"Error processing scope task: {e}", level='error')
    #         self.status = "Error"
    
    # def _create_imaging_tasks_from_experiment_task(self, experiment_task_row):
    #     """Create imaging tasks based on experiment task row data."""
    #     try:
    #         # Extract scope information from the experiment task row
    #         scope_protocol = experiment_task_row.get('Scope_Protocol')
    #         scope_group = experiment_task_row.get('Scope_Group')
    #         scope_round = experiment_task_row.get('Scope_Round')
            
    #         if not scope_protocol or pd.isna(scope_protocol):
    #             self.log("No scope protocol specified in experiment task", level='error')
    #             return
            
    #         self.log(f"Creating imaging tasks for: Protocol={scope_protocol}, Group={scope_group}, Round={scope_round}")
            
    #         # Load experiment state to get channels and group assignments
    #         exp_state = self.file_handler.get_state("Experiment")
    #         channels = exp_state.get('selected_channels', [])
    #         group_assignments = exp_state.get('group_assignments', {})
            
    #         self.log(f"Available channels: {channels}")
    #         self.log(f"Group assignments: {group_assignments}")
            
    #         # Find wells that belong to this scope group
    #         wells_in_group = [well for well, group in group_assignments.items() if group == scope_group]
            
    #         if not wells_in_group:
    #             self.log(f"No wells found for group '{scope_group}'", level='warning')
    #             return
            
    #         self.log(f"Wells in group '{scope_group}': {wells_in_group}")
            
    #         # Create imaging tasks for each well in the group
    #         scope_tasks = []
            
    #         for well in wells_in_group:
    #             well_positions = self.positions[self.positions['well'] == well]
                
    #             for _, position in well_positions.iterrows():
    #                 for channel in channels:
    #                     task_name = f"{scope_protocol}_{scope_group}_R{scope_round}_{well}_{position['position_name']}_{channel}"
                        
    #                     scope_task = {
    #                         'task_name': task_name,
    #                         'protocol': scope_protocol,
    #                         'group': scope_group,
    #                         'round': scope_round,
    #                         'well': well,
    #                         'position_name': position['position_name'],
    #                         'channel': channel,
    #                         'X': position['X'],
    #                         'Y': position['Y'],
    #                         'Z': position['Z'],
    #                         'start_time': None,
    #                         'end_time': None
    #                     }
    #                     scope_tasks.append(scope_task)
            
    #         # Save scope tasks
    #         if scope_tasks:
    #             self.imaging_tasks = pd.DataFrame(scope_tasks)
    #             self.file_handler.save_tasks("Scope", self.imaging_tasks)
    #             self.log(f"Created {len(scope_tasks)} imaging tasks for group '{scope_group}'")
    #         else:
    #             self.log("No imaging tasks created", level='warning')
                
    #     except Exception as e:
    #         self.log(f"Error creating imaging tasks: {e}", level='error')
    #         raise
    
    # def _execute_acquisition(self):
    #     """Execute the acquisition sequence."""
    #     try:
    #         self.update_state()
    #         self.acquisition_start_time = time.time()
            
    #         for imaging_task_idx, (_, row) in enumerate(self.imaging_tasks.iterrows()):
    #             self.file_handler.save_task_idx("Scope", imaging_task_idx)
                
    #             # Set position and channel for this task
    #             self.set('XYZ', (row['X'], row['Y'], row['Z']))
    #             self.set('Channel', row['channel'])
                
    #             # Update task start time
    #             self.imaging_tasks.at[imaging_task_idx, 'start_time'] = time.time()
    #             self.file_handler.save_tasks("Scope", self.imaging_tasks)
                
    #             # Capture image
    #             image = self.snapImage()
    #             self.log(f'Image {row["task_name"]} acquired')
    #             del image
                
    #             # Update task end time
    #             self.imaging_tasks.at[imaging_task_idx, 'end_time'] = time.time()
    #             self.file_handler.save_tasks("Scope", self.imaging_tasks)
            
    #         self.log("Acquisition completed successfully")
            
    #     except Exception as e:
    #         self.log(f"Error during acquisition: {e}", level='error')
    #         raise
    
    def create_imaging_tasks(self, well=None, positions=None, channels=None, zindexes=None, timepoints=None, imaging_order='tpcz'):
        """
        DEPRECATED: This method is not used in autonomous mode.
        Use _create_imaging_tasks_from_experiment_task instead.
        
        Creates a pandas DataFrame of imaging tasks
        Args:
            well (str): The region of interest to image. makes positions if None
            positions (dictionary): keys are names values are a dictionary of Position values (X,Y,Z)
            channels (dictionary): keys are names values are a dictionary of Channel values (Channel,Exposure,Binning))
            zindexes (dictionary): keys are names values are a dictionary of zindex values (Z).
            timepoints (dictionary): keys are names values are a dictionary of timepoint values (Time).
            imaging_order (str): The order of the imaging. (t=timepoint, p=position, c=channel, z=zindex)
        Returns:
            imaging_tasks: A pandas DataFrame of imaging tasks
        """
        self.log('Creating Imaging Tasks (DEPRECATED METHOD)', level='warning')
        if positions is None:
            if well is None:
                self.log('Using Current Position', level='info')
                positions = {'Pos': {'X': self.X, 'Y': self.Y, 'Z': self.Z, 'X_index': 0, 'Y_index': 0, 'Z_index': 0}}
            else:
                self.log(f'Using Well: {well}', level='info')
                well_positions = self.positions[self.positions['well'] == well]
                if well_positions.empty:
                    raise ValueError(f"Well '{well}' not found in positions.")
                
                # Convert to the expected dictionary format
                positions = {}
                for _, row in well_positions.iterrows():
                    positions[row['position_name']] = {
                        'X': row['X'], 
                        'Y': row['Y'], 
                        'Z': row['Z']
                    }
                self.log(f'Positions: {len(positions.keys())}', level='info')
        else:
            if not isinstance(positions, dict):
                self.log(f'Positions must be a dictionary', level='error')
                raise Exception(f'Positions must be a dictionary')
            self.log(f'Positions: {len(positions.keys())}', level='info')

        if channels is None:
            self.log('Using Current Channel', level='info')
            self.log('Using Current Exposure', level='info')
            channels = {'Current': {'Channel': self.Channel, 'Exposure': self.Exposure, 'Binning': self.Binning}}
        else:
            if not isinstance(channels, dict):
                self.log(f'Channels must be a dictionary', level='error')
                raise Exception(f'Channels must be a dictionary')
            self.log(f'Using Channels: {channels}', level='info')

        if zindexes is None:
            self.log('Using Single Z Index', level='info')
            imaging_order = imaging_order.replace('z', '')
            zindexes = {'0': {'Z_relative': 0, 'Z_index': 0}}
        else:
            if not isinstance(zindexes, dict):
                self.log(f'Z Indexes must be a dictionary', level='error')
                raise Exception(f'Z Indexes must be a dictionary')
            self.log(f'Using Z Indexes: {zindexes}', level='info')

        if timepoints is None:  # do only a single timepoint
            self.log('Using Single Timepoint', level='info')
            imaging_order = imaging_order.replace('t', '')
            timepoints = {'0': {'Time': 0}}  # Relative
        else:  # Use Timepoints
            if not isinstance(timepoints, dict):
                self.log(f'Timepoints must be a dictionary', level='error')
                raise Exception(f'Timepoints must be a dictionary')
        
        order_mapper = {'p': positions, 'c': channels, 'z': zindexes, 't': timepoints}

        # check that imaging_order is a valid order
        if not all(order in order_mapper.keys() for order in imaging_order):
            self.log(f'Invalid imaging order: {imaging_order}', level='error')
            raise Exception(f'Invalid imaging order: {imaging_order}')

        imaging_tasks = {'': {}}
        for order in imaging_order:
            new_imaging_tasks = {}
            for previous_task_name, previous_task_values in imaging_tasks.items():
                for task_name, task_values in order_mapper[order].items():
                    new_task_name = f'{previous_task_name}_{task_name}'
                    new_imaging_tasks[new_task_name] = previous_task_values
                    for task_key, task_key_value in task_values.items():
                        new_imaging_tasks[new_task_name][task_key] = task_key_value
            imaging_tasks = new_imaging_tasks
            del new_imaging_tasks
        
        # Convert dictionary to DataFrame
        imaging_tasks_list = []
        for task_name, task_values in imaging_tasks.items():
            task_row = {'task_name': task_name}
            task_row.update(task_values)
            imaging_tasks_list.append(task_row)
        
        imaging_tasks_df = pd.DataFrame(imaging_tasks_list)
        self.log(f'Imaging Tasks: {len(imaging_tasks_df)}', level='info')
        return imaging_tasks_df

    def snapImage(self):
        """Capture an image using the microscope core."""
        if not self.core_enabled:
            self.log("Core not available - simulating image capture", level='warning')
            # Simulate image capture for testing without Micro-Manager
            time.sleep(0.1)  # Simulate capture time
            return None
        
        try:
            self.core.snap_image()
            tagged_image = self.core.get_tagged_image()
            pixels = np.array(tagged_image.pix, dtype=np.uint16)
            height = tagged_image.tags["Height"]
            width = tagged_image.tags["Width"]
            image = pixels.reshape(height, width)
            return image
        except Exception as e:
            self.log(f"Error capturing image: {e}", level='error')
            raise

    def update_state(self, state=None):
        """Update the current microscope state."""
        self.log('Update Current State')
        if state is None:
            state = self.state
        else:
            if isinstance(state, dict): 
                for key, value in state.items(): 
                    self.set(key, value)
            elif state is not None: 
                self.log(f'State must be a dictionary', level='error')
        
        remember_state = self.remember_state
        self.remember_state = False
        
        # Create a copy of keys to avoid modification during iteration
        state_keys = list(self.state.keys())
        for key in state_keys:
            try: 
                state[key] = self.get(key)
            except Exception as e:
                self.log(f'{key} is not a valid state key', level='warning')
                if key in state:
                    del state[key]
        
        self.state = state
        self.remember_state = remember_state
        self.file_handler.save_state("Scope", self.state)
        return state

    def already_set(self, key, value):
        """Check if a state value is already set within tolerance."""
        if not self.check_state(key): 
            return False
        if key in self.tolerance.keys():
            if key == 'Binning':
                if str(value) == str(self.get(key)):
                    return True
                else:
                    self.log(f'{key}: {value} is not a valid binning. Possible values: {self.limits[key]}', level='error')
                    return False
            if abs(self.state[key] - value) < self.tolerance[key]:
                self.log(f'{key}: {value} is within tolerance of {self.state[key]}', level='debug')
                return True
            else:
                return False
        else:
            complete = self.state[key] == value
            if complete:
                self.log(f'{key}: {value} is the same as the current state', level='debug')
            return complete

    def check_state(self, key):
        """Check if a state key exists and has a value."""
        return key in self.state and self.state[key] is not None

    def is_valid(self, key, value):
        """Validate if a value is within limits for a given key."""
        if not key in self.state.keys():
            if key in ['XYZ', 'XY']:  # Special handling for compound keys
                pass  # These are handled below
            else:
                self.log(f'{key} is not a valid key', level='error')
                return False
                
        if isinstance(value, type(None)): 
            self.log(f'{key}: {value} is None', level='warning')
            return False
            
        if key in self.limits.keys():
            if isinstance(self.limits[key], list):
                if value not in self.limits[key]: 
                    self.log(f'{key}: {value} is not a valid {key}. Possible values: {self.limits[key]}', level='error')
                    return False
            else:
                if value < self.limits[key][0] or value > self.limits[key][1]:
                    self.log(f'{key}: {value} is out of bounds {self.limits[key]}', level='error')
                    return False
        elif key == 'XY':
            if len(value) != 2: 
                self.log(f'XY must be a tuple of length 2', level='error')
                return False
            for i, key in enumerate(['X', 'Y']):
                if not self.is_valid(key, value[i]): 
                    self.log(f'{key}: {value[i]} is out of bounds {self.limits[key]}', level='error')
                    return False
        elif key == 'XYZ':
            if len(value) != 3: 
                self.log(f'XYZ must be a tuple of length 3', level='error')
                return False
            for i, key in enumerate(['X', 'Y', 'Z']):
                if not self.is_valid(key, value[i]): 
                    self.log(f'{key}: {value[i]} is out of bounds {self.limits[key]}', level='error')
                    return False
        return True 

    def set(self, key, value):
        """Set a microscope parameter."""
        if self.already_set(key, value): 
            return
        if not self.is_valid(key, value): 
            return
        
        # If core is not available, just update state for simulation
        if not self.core_enabled:
            self.log(f"Core not available - simulating {key}: {value}", level='warning')
            self.state[key] = value
            return
        
        try:
            if key == 'X': 
                self.core.set_xy_position(value, self.Y)
            elif key == 'Y': 
                self.core.set_xy_position(self.X, value)
            elif key == 'Z': 
                self.core.set_position(value)
            # elif key == 'XY':
            #     if len(value) != 2: 
            #         self.log(f'XY must be a tuple of length 2', level='error')
            #     self.core.set_xy_position(value[0], value[1])
            #     # self.state['X'] = value[0]
            #     # self.state['Y'] = value[1]
            # elif key == 'XYZ':
            #     if len(value) != 3: 
            #         self.log(f'XYZ must be a tuple of length 3', level='error')
            #     self.set('XY', value[0:2])
            #     self.set('Z', value[2])
            elif key == 'Exposure': 
                self.core.set_exposure(value)
            elif key == 'Channel': 
                self.core.set_config(key, value)
            elif key == 'Binning': 
                self.core.set_property('Camera', 'Binning', str(int(value)))
            elif key == 'Time': 
                value = self.acquisition_start_time + value
                while time.time() < value:
                    self.log(f'Waiting for {value-time.time()} seconds', level='debug')
                    time.sleep(value-time.time())
                if (time.time() - self.acquisition_start_time > self.overtime_warning) & (self.overtime_warning != 0):
                    self.log(f'Overtime Warning: {time.time() - self.acquisition_start_time} seconds', level='warning')
            else: 
                self.log(f'{key} is not a valid key', level='error')
            
            if self.blocking: 
                self.core.wait_for_device(self.core.get_xy_stage_device())
                self.core.wait_for_device(self.core.get_focus_device())
                while not self.already_set(key, value):
                    self.log(f'{key}: {value} is not the current value {self.get(key)}', level='debug')
                    time.sleep(0.1)
            self.log(f'{key}: {value}', level='debug')
            self.state[key] = value
            
        except Exception as e:
            self.log(f"Error setting {key} to {value}: {e}", level='error')
            raise

    def get(self, key):
        """Get a microscope parameter value."""
        if self.remember_state and self.state[key] is not None:
            self.log(f'{key}: {self.state[key]} Using Previous State', level='debug')
            return self.state[key]
        
        # If core is not available, return stored state or default values
        if not self.core_enabled:
            if key in self.state and self.state[key] is not None:
                return self.state[key]
            else:
                # Return default values for simulation
                defaults = {'X': 0, 'Y': 0, 'Z': 0, 'Exposure': 100, 'Channel': 'FarRed', 'Binning': '1'}
                if key in defaults:
                    self.log(f"Core not available - returning default {key}: {defaults[key]}", level='warning')
                    self.state[key] = defaults[key]
                    return defaults[key]
                else:
                    self.log(f'{key} is not a valid key', level='error')
                    return None
        
        try:
            if key == 'X': 
                value = self.core.get_x_position()
            elif key == 'Y': 
                value = self.core.get_y_position()
            elif key == 'Z': 
                value = self.core.get_position()
            # elif key == 'XY':
            #     value = (self.X, self.Y)
            # elif key == 'XYZ':
                # value = (self.X, self.Y, self.Z)
            elif key == 'Exposure': 
                value = self.core.get_exposure()
            elif key == 'Channel': 
                value = self.core.get_current_config(key)
            elif key == 'Binning': 
                value = str(self.core.get_property('Camera', 'Binning'))
            elif key == 'ImageShape':
                image_width_pixels = self.core.get_image_width()
                image_height_pixels = self.core.get_image_height()
                value = (image_height_pixels, image_width_pixels)
            elif key == 'PixelSize':
                value = self.core.get_pixel_size_um()
            else: 
                self.log(f'{key} is not a valid key', level='error')
                return None
            
            self.log(f'{key}: {value}', level='debug')
            self.state[key] = value
            return value
            
        except Exception as e:
            self.log(f"Error getting {key}: {e}", level='error')
            raise

    # Property accessors for convenience
    @property
    def X(self): 
        return self.get('X')
    @X.setter
    def X(self, value): 
        return self.set('X', value)
    
    @property
    def Y(self): 
        return self.get('Y')
    @Y.setter
    def Y(self, value): 
        return self.set('Y', value)
    
    @property
    def Z(self): 
        return self.get('Z')
    @Z.setter
    def Z(self, value): 
        return self.set('Z', value)
    
    @property
    def XY(self): 
        return (self.get('X'), self.get('Y'))
    @XY.setter
    def XY(self, value): 
        self.set('X', value[0])
        self.set('Y', value[1])
        return
    
    @property
    def XYZ(self): 
        return (self.get('X'), self.get('Y'), self.get('Z'))
    @XYZ.setter
    def XYZ(self, value): 
        self.set('X', value[0])
        self.set('Y', value[1])
        self.set('Z', value[2])
        return 
    
    @property
    def Exposure(self): 
        return self.get('Exposure')
    @Exposure.setter
    def Exposure(self, value): 
        return self.set('Exposure', value)
    
    @property
    def Channel(self): 
        return self.get('Channel')
    @Channel.setter
    def Channel(self, value): 
        return self.set('Channel', value)
    
    @property
    def Binning(self): 
        return self.get('Binning')
    @Binning.setter
    def Binning(self, value):
        return self.set('Binning', str(value))
    
    @property
    def ImageShape(self): 
        if not self.enable_core:
            return self.config['ImageShape']
        return self.get('ImageShape')
    
    @property
    def PixelSize(self): 
        if not self.enable_core:
            return self.config['PixelSize']
        return self.get('PixelSize')
    
    @property
    def image_width_um(self): 
        if not self.enable_core:
            return self.config['ImageShape'][1] * self.config['PixelSize']
        return self.ImageShape[1] * self.PixelSize
    
    @property
    def image_height_um(self): 
        if not self.enable_core:
            return self.config['ImageShape'][0] * self.config['PixelSize']
        return self.ImageShape[0] * self.PixelSize
    
    @property
    def fov_info(self): 
        print(self.config)
        print(self.image_width_um, self.image_height_um, self.overlap)
        return {'X': self.image_width_um, 'Y': self.image_height_um, 'Overlap': self.overlap}
    
    @property
    def status(self):
        """Get scope status from file handler."""
        return self.file_handler.get_status("Scope")
    
    @status.setter
    def status(self, value):
        """Set scope status and save to file handler."""
        self.file_handler.save_status("Scope", value)

    def set_initial_focus(self, chambers, name, other):
        self.log(f"Setting initial focus for chambers: {chambers}, mode: {name}")
        positions = self.file_handler.Positions
        
        if name == 'ManualPlate':
            self._show_focus_popup("Please adjust the focus for the plate using the microscope controls.\n\nClick OK when you are satisfied with the focus.")
            current_z = self.Z
            positions['Z'] = current_z
            self.log(f"Updated all {len(positions)} positions with Z = {current_z}")
        elif name == 'ManualWell':
            for i, well in enumerate(chambers):
                self._show_focus_popup(f"Please adjust the focus for well {well} using the microscope controls.\n\nClick OK when you are satisfied with the focus.\n\nWell {i+1} of {len(chambers)}")
                current_z = self.Z
                well_mask = positions['well'] == well
                positions.loc[well_mask, 'Z'] = current_z
                self.log(f"Updated {well_mask.sum()} positions for well {well} with Z = {current_z}")
        else:
            self.log(f"Unknown focus mode: {name}", level='error')
            return
        
        self.file_handler.save_positions(positions)
        self.log("Initial focus setting completed and positions saved")

    def _show_focus_popup(self, message):
        """Show an independent popup window for focus adjustment."""
        result = threading.Event()
        popup_result = [None]
        
        def show_popup():
            root = tk.Tk()
            root.title("Manual Focus Adjustment")
            root.geometry("400x200")
            root.resizable(False, False)
            root.attributes('-topmost', True)
            
            # Apply dark theme colors
            root.configure(bg='#2b2b2b')
            
            frame = tk.Frame(root, bg='#2b2b2b')
            frame.pack(expand=True, fill='both', padx=20, pady=20)
            
            label = tk.Label(frame, text=message, wraplength=350, justify='center',
                           bg='#2b2b2b', fg='#ffffff', font=('Arial', 10))
            label.pack(expand=True, fill='both')
            
            def on_ok():
                popup_result[0] = True
                root.destroy()
                result.set()
            
            button = tk.Button(frame, text="OK", command=on_ok, width=10, height=2,
                             bg='#404040', fg='#ffffff', font=('Arial', 10),
                             activebackground='#606060', activeforeground='#ffffff')
            button.pack(pady=10)
            
            root.protocol("WM_DELETE_WINDOW", on_ok)
            root.mainloop()
        
        popup_thread = threading.Thread(target=show_popup, daemon=True)
        popup_thread.start()
        result.wait()


# def main():
#     """Main function for standalone scope execution."""
#     import argparse
    
#     parser = argparse.ArgumentParser(description='Autonomous Scope Controller')
#     parser.add_argument('--no-core', action='store_true', help='Disable Micro-Manager core connection')
#     args = parser.parse_args()
#     try:
#         # Initialize scope
#         enable_core = not args.no_core
#         scope = Scope( enable_core=enable_core)
#         scope.continuous_monitoring()
#     except KeyboardInterrupt:
#         scope.log("Shutdown requested by user")
#     except Exception as e:
#         scope.log(f"Fatal error: {e}", level='error')
#     finally:
#         scope.log("Scope controller shutting down")


# if __name__ == "__main__":
#     main()