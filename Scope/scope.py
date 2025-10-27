import time
import os
import json
import ast
import pandas as pd
from pycromanager import Core
from typing import Dict, Any
from file_handler import FileHandler
import numpy as np
import tkinter as tk
from tkinter import messagebox
import threading
from datetime import datetime

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

        self.config = {}
        self.config['MM_config_path'] = 'C:\GitRepos\pyScope\Configs\Scope_config.cfg'


        self.tolerance = {'X': 0.1, 'Y': 0.1, 'Z': 0.1,'Exposure': 0.1}
        self.overtime_warning = 0
        self.limits = {
            'X': (0, 10000), 'Y': (0, 10000), 'Z': (0, 10000), 
            'Exposure': (0, 10000), 'Binning': ['1', '2', '4'], 
            'Channel': [],  # Will be populated dynamically from config
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
        
        # Update channel limits from config file
        self._update_channel_limits()
        
        self.log('Scope initialization complete')
    
    def _update_channel_limits(self):
        """Update the channel limits from the configuration file."""
        try:
            channels = self.get_available_channels_from_config()
            if channels:
                self.limits['Channel'] = channels
                self.log(f"Updated channel limits: {channels}")
            else:
                # Fallback to default channels
                self.limits['Channel'] = ['FarRed', 'DeepBlue', 'Green', 'Orange']
                self.log("Using default channel limits", level='warning')
        except Exception as e:
            self.log(f"Error updating channel limits: {e}", level='error')
            # Fallback to default channels
            self.limits['Channel'] = ['FarRed', 'DeepBlue', 'Green', 'Orange']
    
    def get_available_channels_from_config(self):
        """
        Parse the Micro-Manager configuration file to extract available channels.
        
        Returns:
            list: List of available channel names
            
        Raises:
            FileNotFoundError: If the config file doesn't exist
            ValueError: If the config file format is invalid
        """
        try:
            config_path = self.config.get('MM_config_path')
            if not config_path:
                self.log("No MM_config_path specified in config", level='warning')
                return []
            
            if not os.path.exists(config_path):
                self.log(f"Config file not found: {config_path}", level='warning')
                return []
            channels = []
            with open(config_path, 'r') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    
                    # Look for ConfigGroup lines with Channel presets
                    if line.startswith('ConfigGroup,Channel,'):
                        try:
                            parts = line.split(',')
                            if len(parts) >= 3:
                                channel_name = parts[2]  # Third part is the channel name
                                channels.append(channel_name)
                                self.log(f"Found channel: {channel_name}", level='debug')
                        except Exception as e:
                            self.log(f"Error parsing line {line_num}: {line} - {e}", level='warning')
                            continue
            
            # Remove duplicates while preserving order
            unique_channels = []
            for channel in channels:
                if channel not in unique_channels:
                    unique_channels.append(channel)
            
            self.log(f"Extracted {len(unique_channels)} channels from config: {unique_channels}")
            return unique_channels
            
        except Exception as e:
            self.log(f"Error reading config file {config_path}: {e}", level='error')
            return []
    
    def log(self, message, level='info'):
        """Log messages using FileHandler's logging system."""
        self.file_handler.log(message, level=level, system_prefix='Scope')

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

    def continuous_monitoring(self):
        self.last_message = ''
        self.log('Continuous monitoring started')
        try:
            while True:
                status = self.status
                if self.last_message!=status:
                    self.last_message = status
                    self.log(f"New Message: {status}")
                if 'stop' in status.lower():
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
            self.log("Not implemented yet")
            # self.set_focus(chambers,name,other)
        elif protocol == 'Acquire': #FIXME "Acquire*[['A1', 'A2']]*hybe11" 
            self.log(f"Acquiring images for: {chambers}, {name}, {other}")
            self.acquire(chambers,name,other)
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

    def acquire(self,chambers,acquisition_name,other,acquisition_data=None,positions=None):
        if acquisition_data is None:
            acquisition_data = self.file_handler.get_state("Experiment")
        if len(other) > 0:
            other = ast.literal_eval(other)
            acquisition_data.update(other)
            # example: For Preview you might only want one channel
            # other = "{'selected_channels': ['DeepBlue'], 'channel_exposure': {'DeepBlue': 5}, 'channel_delay': {'DeepBlue': 5}.'steps': {'start': 0, 'end': 0, 'dz': 0}}""

        channels = {}
        for channel in acquisition_data['selected_channels']:
            channels[channel] = {
                'Channel': channel,
                'Exposure': acquisition_data['channel_exposure'][channel],
                'Delay': acquisition_data['channel_delay'][channel]
            }
        dZ = acquisition_data['steps']
        if dZ['start'] == dZ['end']:
            steps = [float(dZ['start'])]   
        else:
            steps = [float(i) for i in np.arange(dZ['start'], dZ['end'], dZ['dz'])]
        if positions is None:
            positions = self.file_handler.Positions
            positions = positions[positions['well'].isin(chambers)]
        self.file_handler.save_tasks("Scope", positions)
        current_idx = 0
        self.file_handler.save_task_idx("Scope", current_idx)

        for chamber in chambers:
            chamber_acquisition_name = f"{acquisition_name}_Well-{chamber}"
            self.log(f"Acquiring images for: {chamber}")
            self.file_handler.setup_acquisition(chamber_acquisition_name)
            chamber_positions = positions[positions['well'] == chamber].copy()
            # chamber_positions = self.AutoFocus.update_focus(chamber_positions)#FIXME: self.autofocus()
            for _, position in chamber_positions.iterrows():
                self.log(f"Acquiring images for: {position['position_name']}")
                current_idx+=1
                self.file_handler.save_task_idx("Scope", current_idx)
                self.XYZ = (position['X'], position['Y'], position['Z'])
                # Channel First 
                starting_Z = position['Z']
                # starting_Z = self.AutoFocus.update_focus(position) #FIXME:
                for z_index,step in enumerate(steps):
                    if step != 0:
                        Z = starting_Z + step
                        self.Z = Z
                    for channel_name, channel in channels.items():
                        self.Channel = channel['Channel']
                        self.Exposure = channel['Exposure']
                        if channel['Delay'] > 0:
                            previous_autoshutter_state = self.Autoshutter
                            self.Autoshutter = False
                            self.Shutter = True 
                            time.sleep(channel['Delay']/1000)
                        image = self.snapImage()
                        time_stamp = datetime.now()
                        time_stamp_image = time.time()
                        if channel['Delay'] > 0:
                            self.Autoshutter = previous_autoshutter_state
                            self.Shutter = False
                        image_info = {}
                        image_info['Position'] = position['position_name']
                        image_info['Channel'] = channel['Channel']
                        image_info['Exposure'] = channel['Exposure']
                        image_info['PixelSize'] = self.PixelSize
                        image_info['XY'] = (position['X'], position['Y'])
                        image_info['X'] = position['X']
                        image_info['Y'] = position['Y']
                        image_info['Z'] = position['Z'] + step
                        image_info['Zindex'] = z_index
                        image_info['Well'] = chamber
                        image_info['acq'] = chamber_acquisition_name
                        image_info['Scope'] = self.name
                        image_info['Time'] = time_stamp
                        image_info['TimestampImage'] = time_stamp_image
                        self.file_handler.save_image(image, image_info)
            self.file_handler.finalize_acquisition()

    def snapImage(self):
        """Capture an image using the microscope core."""
        if not self.core_enabled:
            self.log("Core not available - simulating image capture", level='warning')
            # FIXME: Simulate image capture for testing without Micro-Manager
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
                Z = self.Z
                self.Z = self.limits['Z'][0] # move to bottom of the plate
                self.X = positions[positions['well'] == well]['X'].median()
                self.Y = positions[positions['well'] == well]['Y'].median()
                self.Z = Z # move back to the original z position
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
            elif key == 'Autoshutter':
                self.core.set_auto_shutter(bool(value))
            elif key == 'Shutter':
                self.core.set_shutter_open(bool(value))
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
            elif key == 'Autoshutter':
                value = self.core.get_auto_shutter()
            elif key == 'Shutter':
                value = self.core.get_shutter_open()
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
    def Autoshutter(self): 
        return self.get('Autoshutter')
    @Autoshutter.setter
    def Autoshutter(self, value):
        return self.set('Autoshutter', bool(value))

    @property
    def Shutter(self): 
        return self.get('Shutter')
    @Shutter.setter
    def Shutter(self, value):
        return self.set('Shutter', bool(value))
    
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
    def available_channels(self):
        """Get available channels from the Micro-Manager configuration file."""
        channels = self.get_available_channels_from_config()
        if not channels:
            # Fallback to hardcoded channels if config parsing fails
            self.log("Using fallback channel list", level='warning')
            return ['FarRed', 'DeepBlue', 'Green', 'Orange']
        return channels
    
    @property
    def status(self):
        """Get scope status from file handler."""
        return self.file_handler.get_status("Scope")
    
    @status.setter
    def status(self, value):
        """Set scope status and save to file handler."""
        self.file_handler.save_status("Scope", value)
    
    @property
    def name(self):
        """Get the name of the class."""
        return self.__class__.__name__
