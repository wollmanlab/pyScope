from math import e
import time
import os
import json
import ast
import pandas as pd
import traceback
from pycromanager import Core,Studio
from typing import Dict, Any
from file_handler import FileHandler
from Scope.autofocus import Autofocus, ImageScanAutofocus, RelativeAutofocus
from Processing.stitching import stitch_acquisition, interactive_roi_selection, interactive_coordinate_selection, filter_positions
import numpy as np
from scipy.optimize import minimize
import tkinter as tk
from tkinter import messagebox
import threading
from datetime import datetime
import tifffile
import matplotlib.pyplot as plt

class Scope:
    """Base class for microscope control and image acquisition.
    
    Provides Micro-Manager integration, state management, protocol execution,
    and autonomous operation through file-based communication. Supports
    position management, autofocus, and multi-channel imaging.
    
    Attributes:
        file_handler (FileHandler): File handler instance for state management.
        core (Core): Micro-Manager core instance (None if not connected).
        core_enabled (bool): Whether Micro-Manager core is connected.
        state (Dict[str, Any]): Current microscope state (X, Y, Z, Channel, etc.).
        limits (Dict): Valid ranges for microscope parameters.
        tolerance (Dict): Tolerance values for state checking.
        AutoFocus (Autofocus): Autofocus instance for focus management.
    """
    
    def __init__(self, enable_core: bool = True):
        """Initialize the Scope class.
        
        Sets up Micro-Manager connection, loads configuration, and initializes
        state management. Falls back to simulation mode if Micro-Manager is
        not available.
        
        Args:
            enable_core (bool): Whether to initialize Micro-Manager core connection.
                Defaults to True.
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
        self.remember_state = False

        self.config = {}
        self.config['MM_config_path'] = 'C:\GitRepos\pyScope\Configs\Scope_config.cfg'


        self.tolerance = {'X': 0.1, 'Y': 0.1, 'Z': 0.1,'Exposure': 0.1}
        self.overtime_warning = 0
        self.limits = {
            'X': (0, 10000), 'Y': (0, 10000), 'Z': (0, 10000), 
            'Shutter': (False, True),'Autoshutter': (False, True),
            'Exposure': (0, 10000), 'Binning': ['1', '2', '4'], 
            'Channel': [],  # Will be populated dynamically from config
            'Time': (0, 1e8)
        }
        self.offsets = {'X': 0, 'Y': 0, 'Z': 0}
        self.axis_mapping = {'stage_x': 'plate_x', 'stage_y': 'plate_y'}
        self.overlap = 0.1 # may want different overlap for different projects / exps
        
        # Microscope state
        self.state = {
            'X': None, 'Y': None, 'Z': None, 'Exposure': None, 
            'Channel': None, 'Binning': None, 'ImageShape': None, 'PixelSize': None
        }
        self._update_channel_limits()
        self.level_mapper = {'Plate':'plate','Well':'well','Group':'group','Position':'position_name'}
        self.log('Scope initialization complete')
        self.AutoFocus = Autofocus()
    
    def _update_channel_limits(self):
        """Update channel limits from Micro-Manager configuration file.
        
        Parses the config file to extract available channels and updates
        self.limits['Channel']. Falls back to default channels if parsing fails.
        """
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
        """Log messages using FileHandler's logging system.
        
        Args:
            message (str): Message to log.
            level (str): Log level ('debug', 'info', 'warning', 'error').
                Defaults to 'info'.
        """
        self.file_handler.log(message, level=level, system_prefix='Scope')

    def _initialize_core(self):
        """Initialize Micro-Manager core connection.
        
        Attempts to connect to Micro-Manager core. Sets core_enabled to False
        and core to None if connection fails (simulation mode).
        """
        try:
            self.core = Core()
            # self.studio = Studio()
            self.core_enabled = True
            self.log("Micro-Manager core connection established")
        except Exception as e:
            self.log(f"Micro-Manager is not running: {e}", level='warning')
            self.core = None
            self.core_enabled = False

    def continuous_monitoring(self):
        """Run continuous monitoring loop for autonomous operation.
        
        Monitors scope_task.txt for new commands and executes protocols accordingly.
        Continues until 'stop' command is received or an error occurs.
        Sets status to 'idle' when terminated.
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
                    if status =='offline':
                        self.status = 'idle'
                if 'stop' in status.lower():
                    self.log('Continuous monitoring stopped by user')
                    break
                elif "Command" in status:
                    self.interpret_command(status)
                
                time.sleep(1)
        except Exception as e:
            error_traceback = traceback.format_exc()
            self.log(f"Error in continuous monitoring: {e}\n{error_traceback}", level='warning')
            crashed = True
        finally:
            if not crashed:
                self.status = "offline"
            else:
                self.status = f"Crashed:{self.status.split('Command:')[-1].split('Running:')[-1]}"
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
        message = current_message.split('Command:')[-1]
        self.status = "Running:"+message
        self.execute_protocol(message)
        self.status = "Finished:"+message
        self.busy = False

    def execute_protocol(self, message):
        """Execute a protocol based on command message.
        
        Routes protocol execution to appropriate handler. Supported protocols:
        - SetFocus: Set focus for positions
        - FilterPositions: Filter imaging positions using ROI selection
        - SetupAutoFocus: Configure autofocus system
        - Acquire: Main image acquisition protocol
        
        Args:
            message (str): Protocol command message in format 'Protocol*chambers*name*other'.
        """
        self.log(f"Executing Protocol: {message}")
        protocol,chambers,name,other = self.decode_message(message)
        if protocol == 'SetFocus': #FIXME "SetFocus*['A1', 'A2','A3','B1']*ManualWell" 
            self.log(f"Setting focus for: {chambers}, {name}, {other}")
            self.set_focus(chambers,name,other)
        elif protocol == 'FilterPositions': #FIXME "FilterPositions*['A1', 'A2']*None" 
            self.log(f"Filtering positions for: {chambers}, {name}, {other}")
            self.filter_positions(chambers)
        elif protocol == 'SetupAutoFocus': #FIXME "SetupAutoFocus*['A', 'B', 'C', 'D', 'E', 'F']*Relative"
            self.setup_autofocus()
        elif protocol == 'Acquire': #FIXME "Acquire*['A1', 'A2']*hybe11" 
            self.log(f"Acquiring images for: {chambers}, {name}, {other}")
            self.acquire(chambers,name,other)
        elif protocol == 'ManualReview':
            self.log(f"Manual reviewing images for: {chambers}, {name}, {other}")
            self.manual_review(chambers,name,other)
        else:
            self.log(f"Unknown protocol: {protocol}", level='warning')
        # Clean up task files after protocol completion (both real and simulated)
        self.file_handler.save_task_idx("Scope", 0)
        self.file_handler.delete_tasks("Scope")
        self.simulate = False

    def decode_message(self, message):
        """Decode protocol command message into components.
        
        Parses message format: 'Protocol*chambers*name*other'
        Handles optional '+' separator and '!' simulation flag.
        
        Args:
            message (str): Protocol command message.
        
        Returns:
            tuple: (protocol, chambers, name, other) where:
                - protocol (str): Protocol name
                - chambers (list): List of chamber/well names
                - name (str): Protocol name parameter
                - other (str): Additional parameters
        """
        self.log(f"Decoding message: {message}",level='debug')
        self.log(f"Message type: {type(message)}",level='debug')
        self.log(f"{message.split('*')}",level='debug')
        protocol,chambers,other = message.split('*')
        if '+' in other:
            self.log(f"Message contains +: {other}",level='debug')
            name = other.split('+')[0]
            other = other.split('+')[1]
        else:
            name = other
            other = ''
        # chambers = chambers[1:-1].split(',')
        chambers = ast.literal_eval(chambers)
        if '!' in other:
            other = other.split('!')[0]
            self.simulate = True
        else:
            self.simulate = False
        return protocol,chambers,name,other

    def stitch_previews(self, chambers):
        """Stitch preview acquisitions for specified chambers.
        
        Creates stitched images with position indexing for each chamber.
        Results are stored in self.stitched dictionary.
        
        Args:
            chambers (list): List of chamber/well names to stitch.
        """
        positions = self.file_handler.Positions
        for chamber in chambers:
            chamber_positions = positions[positions['well'] == chamber].copy()

            canvas, pixel2stage, idx_canvas, posname_idx_mapper = stitch_acquisition(
                self.file_handler.find_latest_acquisition('preview',chamber), 
                self.file_handler.get_state('Experiment')['preview_channels'][0],
                zindex=0,
                metadata_filename='Metadata.txt',
                image_processor=None,
                registration_dict={},
                border=2000,
                stitch_rotate=0,
                stitch_flipud=False,
                stitch_fliplr=False,
                output_pixel_size=50,
                idx_stitch=True,
                position_names=chamber_positions['position_name'].unique(),
                verbose=False
            )
            self.stitched[chamber] = {}
            self.stitched[chamber]['canvas'] = canvas
            self.stitched[chamber]['pixel2stage'] = pixel2stage
            self.stitched[chamber]['idx_canvas'] = idx_canvas
            self.stitched[chamber]['posname_idx_mapper'] = posname_idx_mapper

    def filter_positions(self, chambers):
        """Filter imaging positions using interactive ROI selection.
        
        Stitches preview acquisitions and allows user to select regions of
        interest. Updates positions DataFrame with filtered positions and
        assigns groups based on ROI selections.
        
        Args:
            chambers (list): List of chamber/well names to filter positions for.
        """
        filtering_method = self.file_handler.get_state('Experiment')['position_filtering']
        if filtering_method == 'None':
            return
        positions = self.file_handler.Positions
        updated_positions = []
        for chamber in chambers:
            self.log(f"Filtering positions for: {chamber}",level='info')
            chamber_positions = positions[positions['well'] == chamber].copy()
            self.log(f"Stitching preview for: {chamber}",level='info')
            canvas, pixel2stage, idx_canvas, posname_idx_mapper = stitch_acquisition(
                self.file_handler.find_latest_acquisition('preview',chamber), 
                self.file_handler.get_state('Experiment')['preview_channels'][0],
                zindex=0,
                metadata_filename='Metadata.txt',
                image_processor=None,
                registration_dict={},
                border=2000,
                stitch_rotate=0,
                stitch_flipud=False,
                stitch_fliplr=False,
                output_pixel_size=50,
                idx_stitch=True,
                position_names=chamber_positions['position_name'].unique(),
                verbose=False
            )

            if filtering_method == 'Draw':
                self.log(f"Interactive ROI selection for: {chamber}",level='info')
                mask,canvas_rgb = interactive_roi_selection(canvas,message = 'Select areas that you want \n to image one region at a time')
                positions_to_keep = filter_positions(idx_canvas[:,:,0], mask, posname_idx_mapper)
                chamber_positions = chamber_positions[chamber_positions['position_name'].isin(positions_to_keep.keys())]
                for idx,row in chamber_positions.iterrows():
                    chamber_positions.loc[idx,'group'] = f"{chamber}-{positions_to_keep[row['position_name']]}"
                # chamber_positions['group'] = f"{chamber}-{chamber_positions['position_name'].map(positions_to_keep)}"
                # self.stitched[chamber]['canvas_rgb'] = canvas_rgb

            updated_positions.append(chamber_positions)
        positions = pd.concat(updated_positions)
        self.file_handler.save_positions(positions)

    # def set_position_focus(self,chambers):
    #     focus_method = self.file_handler.get_state('Experiment')['acquisition_focus']
    #     if focus_method == 'None':
    #         return
    #     positions = self.file_handler.Positions
    #     focus_positions = []
    #     for chamber in chambers:
    #         chamber_positions = positions[positions['well'] == chamber].copy()
    #         if len(chamber_positions) == 0:
    #             self.log(f"No positions found for {chamber}",level='error')
    #             continue
    #         groups = chamber_positions['group'].unique()
    #         for group in groups:
    #             group_positions = chamber_positions[chamber_positions['group'] == group].copy()
    #             canvas, pixel2stage, idx_canvas, posname_idx_mapper = stitch_acquisition(
    #                 self.file_handler.find_latest_acquisition('preview',chamber), 
    #                 self.file_handler.get_state('Experiment')['preview_channels'][0],
    #                 zindex=0,
    #                 metadata_filename='Metadata.txt',
    #                 image_processor=None,
    #                 registration_dict={},
    #                 border=2000,
    #                 stitch_rotate=0,
    #                 stitch_flipud=False,
    #                 stitch_fliplr=False,
    #                 output_pixel_size=50,
    #                 idx_stitch=True,
    #                 position_names=group_positions['position_name'].unique()
    #             )
    #             points = interactive_coordinate_selection(canvas, message = 'Select a few areas where you want to set focus')
    #             group_focus_positions = pd.DataFrame(columns=['X','Y','Z','well','group'])
    #             group_Z = group_positions['Z'].median()
    #             for i,point in enumerate(points):
    #                 if not self.is_valid('X',point[0]):
    #                     self.log(f"Invalid X: {point[0]}",level='error')
    #                     continue
    #                 if not self.is_valid('Y',point[1]):
    #                     self.log(f"Invalid Y: {point[1]}",level='error')
    #                     continue
    #                 group_focus_positions.loc[i] = [point[0], point[1], group_Z, chamber, group]
    #             focus_positions.append(group_focus_positions)

    #     focus_positions = pd.concat(focus_positions)
    #     self.file_handler.save_focus_positions(focus_positions)

    #     if 'Manual' in focus_method:
    #         self.log(f"Manual focus positions",level='info')
    #         # FIXME: Iterate through with popup

    #     elif 'Scan' in focus_method:
    #         self.log(f"Scanning for focus positions",level='info')
    #         # FIXME: for loop with ImageScanAutofocus
    #     else:
    #         self.log(f"Unknown focus method: {focus_method}",level='error')
    #         return

    #     # FIXME:Use these focus positions to extrapolate to the other positions
                

            

    def setup_autofocus(self):
        """Configure autofocus system based on experiment configuration.
        
        Initializes appropriate autofocus strategy (None, Relative, ImageScan)
        based on experiment state and calls setup method if needed.
        """
        autofocus_method = self.file_handler.get_state('Experiment')['autofocus_method']
        level = autofocus_method.split(' ')[-1]
        method = autofocus_method.split(f" {level}")[0]
        if method == 'None':
            self.AutoFocus = Autofocus()
        elif method == 'Relative':
            self.AutoFocus = RelativeAutofocus(level=self.level_mapper[level])
            self.AutoFocus.setup(self)
        elif method == 'ImageScan':
            self.AutoFocus = ImageScanAutofocus()
            self.AutoFocus.setup(self)
        else:
            self.log(f"Unknown autofocus method: {autofocus_method}",level='error')
            return

    def manual_review(self, chambers, name, other):
        """Manual review of setup.
        pause the experiment to allow the user to review the setup.
        displays a gui asking the user to click okay when done.
        Args:
            chambers (list): List of chamber/well names to review images for.
        """
        self.log(f"Manual reviewing setup for: {chambers}, {name}, {other}",level='info')
        self._show_focus_popup("Please review the setup and click okay when done")


    # def setup(self,chambers,name,other):
    #     positions = self.file_handler.Positions
    #     if not 'group' in positions.columns:
    #         positions['group'] = positions['well']
    #         self.file_handler.save_positions(positions)
    #     updated_positions = []
    #     autofocus_method = self.file_handler.get_state('Experiment')['autofocus_method']
    #     if autofocus_method == 'None':
    #         self.AutoFocus = Autofocus()
    #     elif autofocus_method == 'Relative':
    #         self.AutoFocus = RelativeAutofocus()
    #     elif autofocus_method == 'ImageScan':
    #         self.AutoFocus = ImageScanAutofocus()
    #     else:
    #         self.log(f"Unknown autofocus method: {autofocus_method}",level='error')
    #         return

    #     for chamber in chambers:
    #         chamber_positions = positions[positions['well'] == chamber].copy()
    #         if len(chamber_positions) == 0:
    #             self.log(f"No positions found for {chamber}",level='error')
    #             continue
    #         acquisition_dir = self.file_handler.find_latest_acquisition('preview',chamber)
    #         if acquisition_dir is None:
    #             self.log(f"No acquisition found for {chamber}",level='error')
    #             continue
    #         channel = self.file_handler.get_state('Experiment')['preview_channels'][0]
    #         if channel is None:
    #             self.log(f"No channel found for {chamber}",level='error')
    #             continue

    #         # Load Preview and stitch it
    #         canvas, pixel2stage, idx_canvas, posname_idx_mapper = stitch_acquisition(
    #             acquisition_dir, 
    #             channel,
    #             zindex=0,
    #             metadata_filename='Metadata.txt',
    #             image_processor=None,
    #             registration_dict={},
    #             border=2000,
    #             stitch_rotate=0,
    #             stitch_flipud=False,
    #             stitch_fliplr=False,
    #             output_pixel_size=50,
    #             idx_stitch=True,
    #             position_names=chamber_positions['position_name'].unique()
    #         )

    #         # Filter positions
    #         filtering_method = self.file_handler.get_state('Experiment')['position_filtering']
    #         if filtering_method == 'Draw':
    #             mask,canvas_rgb = interactive_roi_selection(canvas,message = 'Select areas that you want \n to image one region at a time')
    #             positions_to_keep = filter_positions(idx_canvas, mask, posname_idx_mapper)

    #             if len(positions_to_keep)==0:
    #                 self.log(f"No positions to keep for {chamber}",level='error')
    #                 continue
    #             chamber_positions = chamber_positions[chamber_positions['position_name'].isin(positions_to_keep.keys())]
    #             chamber_positions['group'] = chamber_positions['position_name'].map(positions_to_keep)
    #         updated_positions.append(chamber_positions)

    #         # Focus Specific Task
    #         focus_method = self.file_handler.get_state('Experiment')['acquisition_focus']



    #         autofocus_method = self.file_handler.get_state('Experiment')['autofocus_method']

            
    #     positions = pd.concat(updated_positions)
    #     self.file_handler.save_positions(positions)



    def acquire(self, chambers, acquisition_name, other, acquisition_data=None, positions=None):
        """Main image acquisition protocol.
        
        Acquires multi-channel, multi-position images with Z-stack support.
        Integrates with autofocus system and saves images with metadata.
        
        Args:
            chambers (list): List of chamber/well names to acquire images for.
            acquisition_name (str): Name for the acquisition (e.g., 'preview', 'hybe11').
            other (str): Additional acquisition parameters as string (will be parsed).
            acquisition_data (dict, optional): Acquisition configuration dictionary.
                If None, loads from Experiment state. Defaults to None.
            positions (pd.DataFrame, optional): Positions DataFrame to use.
                If None, loads from file handler. Defaults to None.
        """
        if acquisition_data is None:
            acquisition_data = self.file_handler.get_state("Experiment")
        if len(other) > 0: # Update acquisition_data with other
            other = ast.literal_eval(other)
            acquisition_data.update(other)

        channels = {}
        if acquisition_name == 'preview':
            
            selected_channels = acquisition_data['preview_channels']
        else:
            selected_channels = acquisition_data['selected_channels']
        for channel in selected_channels:
            channels[channel] = {
                'Channel': channel,
                'Exposure': acquisition_data['channel_exposure'][channel],
                'Delay': acquisition_data['channel_delay'][channel]
            }
        self.log(f"Channels: {channels}")
        dZ = acquisition_data['steps']
        if dZ['start'] == dZ['end']:
            steps = [float(dZ['start'])]   
        else:
            steps = [float(i) for i in np.arange(dZ['start'], dZ['end'], dZ['dz'])]
        self.log(f"Steps: {steps}")
        if positions is None:
            positions = self.file_handler.Positions
            positions = positions[positions['well'].isin(chambers)]
        if not 'autofocus_group' in positions.columns:
            positions['autofocus_group'] = positions['group']
        self.log(f"Positions: {positions.shape}")
        self.file_handler.save_tasks("Scope", positions)
        current_idx = 0
        self.file_handler.save_task_idx("Scope", current_idx)
        try:
            if self.AutoFocus.level=='plate':
                self.AutoFocus.update_focus(self,'plate')
        except Exception as e:
            self.log(f"Did not perform Plate autofocus: {e}",level='warning')
        
        for chamber in chambers:
            chamber_acquisition_name = f"{acquisition_name}_Well-{chamber}"
            self.log(f"Acquiring images for: {chamber}",level='info')
            self.file_handler.setup_acquisition(chamber_acquisition_name)
            chamber_positions = positions[positions['well'] == chamber].copy()
            autofocus_groups = chamber_positions['autofocus_group'].unique()
            for autofocus_group in autofocus_groups:
                self.log(f"Acquiring images for autofocus group: {autofocus_group}",level='info')
                autofocus_group_positions = chamber_positions[chamber_positions['autofocus_group'] == autofocus_group]
                do_autofocus = True
                try:
                    if self.AutoFocus.level=='plate':
                        do_autofocus = False
                except Exception as e:
                    self.log(f"Error checking autofocus: {e}",level='warning')
                if do_autofocus:
                    self.AutoFocus.update_focus(self,autofocus_group)
                groups = autofocus_group_positions['group'].unique()
                for group in groups:
                    group_positions = autofocus_group_positions[autofocus_group_positions['group'] == group]
                    for idx,(_, position) in enumerate(group_positions.iterrows()):
                        if 'stop' in self.check_status().lower():
                            self.log("Scope is stopped", level='warning')
                            return
                        self.log(f"Acquiring images for: {position['position_name']}",level='debug')
                        current_idx+=1
                        self.file_handler.save_task_idx("Scope", current_idx)
                        self.XYZ = (position['X'], position['Y'], position['Z'])
                        starting_Z = self.AutoFocus.focus(self,position['X'],position['Y'],position['position_name'],goto=True)
                        # Channel First 
                        # if idx%10 == 0: # To reduce overhead of saving state
                        self.file_handler.save_state("Scope", self.state)
                        for z_index,step in enumerate(steps):
                            if 'stop' in self.check_status().lower():
                                self.log("Scope is stopped", level='warning')
                                return
                            if step != 0:
                                Z = starting_Z + step
                                self.Z = Z
                            for channel_name, channel in channels.items():
                                if 'stop' in self.check_status().lower():
                                    self.log("Scope is stopped", level='warning')
                                    return
                                self.Channel = channel['Channel']
                                self.Exposure = channel['Exposure']
                                if channel['Delay'] > 0:
                                    previous_autoshutter_state = self.Autoshutter
                                    self.Autoshutter = False
                                    self.Shutter = True 
                                    time.sleep(channel['Delay']/1000)
                                # self.update_state()
                                # self.file_handler.save_state("Scope", self.state)
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
                                image_info['Group'] = position['group']
                                image_info['Scope'] = self.name
                                image_info['Time'] = time_stamp
                                image_info['TimestampImage'] = time_stamp_image
                                self.file_handler.save_image(image, image_info)
                    # Stitch group unless it only has one position
                    if len(group_positions) > 1:
                        self.display_preview(group_positions,name=f"{self.file_handler.acquisition_name} {group}",channels=channels,acquisition_dir=self.file_handler.acquisition_dir)
            self.file_handler.finalize_acquisition()


    def snapImage(self):
        """Capture an image using the microscope core.
        
        Returns:
            np.ndarray: 2D image array (uint16). Returns None if core is not enabled.
        
        Raises:
            Exception: If image capture fails.
        """
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
            image = np.fliplr(image)
            return image
        except Exception as e:
            self.log(f"Error capturing image: {e}", level='error')
            raise

    def set_focus(self, chambers, name, other):
        """Set focus for positions at different hierarchical levels.
        
        Routes to appropriate focus method based on name parameter.
        Supported methods: Manual, Manual Plane.
        
        Args:
            chambers (list): List of chamber/well names.
            name (str): Focus method and level (e.g., 'Manual Well', 'Manual Plane Group').
            other (str): Additional parameters.
        """
        if name == 'None':
            return
        level = name.split(' ')[-1]
        method = name.split(f" {level}")[0]
        if method == 'Manual':
            self.manual_focus(chambers,level,other)
        elif method == 'Manual Plane':
            self.manual_plane_focus(chambers,level,other)
        else:
            self.log(f"Unknown focus method: {method}", level='error')
            return

    def manual_focus(self, chambers, level, other):
        """Manually set flat focus for positions at a hierarchical level.
        
        User manually adjusts focus for each position at the specified level.
        
        Args:
            chambers (list): List of chamber/well names.
            level (str): Hierarchical level ('Plate', 'Well', 'Group', 'Position').
            other (str): Additional parameters.
        """ 

        positions = self.file_handler.Positions
        positions = positions[positions['well'].isin(chambers)]
        if level == 'Plate':
            self._show_focus_popup("Please adjust the focus for the plate using the microscope controls.\n\nClick OK when you are satisfied with the focus.")
            current_z = self.Z
            positions['Z'] = current_z
            self.log(f"Updated all {len(positions)} positions with Z = {current_z}")
        else:
            groups = positions[self.level_mapper[level]].unique()
            for i,group in enumerate(groups):
                group_positions = positions[positions[self.level_mapper[level]] == group]
                Z = self.Z
                self.Z = self.limits['Z'][0] # move to bottom of the plate
                self.XY = (group_positions['X'].median(), group_positions['Y'].median())
                self.Z = Z # move back to the original z position
                self._show_focus_popup(f"Please adjust the focus for group {group} using the microscope controls.\n\nClick OK when you are satisfied with the focus.\n\nGroup {i+1} of {len(groups)}")
                current_z = self.Z
                positions.loc[group_positions.index, 'Z'] = current_z
                self.log(f"Updated {len(group_positions)} positions for group {group} with Z = {current_z}")
        self.file_handler.save_positions(positions)

    def manual_plane_focus(self, chambers, level, other):
        """Set focus using manually defined reference points to fit a plane.
        
        User selects reference points interactively, system fits a plane through
        them, and applies the plane to all positions at the specified level.
        
        Args:
            chambers (list): List of chamber/well names.
            level (str): Hierarchical level ('Plate', 'Well', 'Group', 'Position').
            other (str): Additional parameters.
        """
        all_positions = self.file_handler.Positions
        positions = all_positions[all_positions['well'].isin(chambers)]
        groups = positions[self.level_mapper[level]].unique()
        if os.path.exists(os.path.join(self.file_handler.system_state_dir,f'reference_points.csv')):
            reference_points = pd.read_csv(os.path.join(self.file_handler.system_state_dir,f'reference_points.csv'))
            self.log(f"Using existing reference points from {os.path.join(self.file_handler.system_state_dir,f'reference_points.csv')}")
        else:
            # First select the reference points for each group
            reference_points = pd.DataFrame(columns=['X','Y','Z',level])
            ref_idx = 0
            for group in groups:
                group_positions = positions[positions[self.level_mapper[level]] == group]
                well = group_positions['well'].unique()[0]
                acquisition_dir = self.file_handler.find_latest_acquisition('preview',well)
                if acquisition_dir is None:
                    self.log(f"No acquisition found for {well}",level='error')
                    continue
                channel = self.file_handler.get_state('Experiment')['preview_channels'][0]
                if channel is None:
                    self.log(f"No channel found for {well}",level='error')
                    continue
                
                canvas, pixel2stage, idx_canvas, posname_idx_mapper = stitch_acquisition(
                    acquisition_dir, 
                    channel,
                    zindex=0,
                    metadata_filename='Metadata.txt',
                    image_processor=None,
                    registration_dict={},
                    border=2000,
                    stitch_rotate=0,
                    stitch_flipud=False,
                    stitch_fliplr=False,
                    output_pixel_size=50,
                    idx_stitch=True,
                    position_names=group_positions['position_name'].unique(),
                    verbose=False
                )
                points = []
                extra_message = ''
                n_points = 5
                while len(points)<n_points:
                    points = interactive_coordinate_selection(canvas, message = f"Select atleast {n_points} areas where you want to set focus{extra_message}")
                    if len(points)<n_points:
                        extra_message = f"\n\nYou need to select atleast 4 points. You have selected {len(points)}"
                for point in points:
                    stage_coordinates = pixel2stage(point[0], point[1])
                    if not self.is_valid('X',stage_coordinates[0]):
                        self.log(f"{group} Invalid X: {stage_coordinates[0]}",level='error')
                    if not self.is_valid('Y',stage_coordinates[1]):
                        self.log(f"{group} Invalid Y: {stage_coordinates[1]}",level='error')
                    if not self.is_valid('Z',group_positions['Z'].median()):
                        self.log(f"{group} Invalid Z: {group_positions['Z'].median()}",level='error')
                    
                    reference_points.loc[ref_idx,'X'] = stage_coordinates[0]
                    reference_points.loc[ref_idx,'Y'] = stage_coordinates[1]
                    reference_points.loc[ref_idx,'Z'] = group_positions['Z'].median()
                    reference_points.loc[ref_idx,level] = group
                    reference_points.loc[ref_idx,'well'] = group_positions['well'].unique()[0]
                    ref_idx+=1
                
            # Now iterate through these and manually set focus
            current_group = ''
            i = 0
            for reference_point_idx,reference_point in reference_points.iterrows():
                i+=1
                if reference_point['well'] != current_group:
                    Z = self.Z
                    self.Z = self.limits['Z'][0] # move to bottom of the plate
                    current_group = reference_point['well']
                    self.Z = reference_point['Z']
                self.XY = (reference_point['X'], reference_point['Y'])
                # self.Z = reference_point['Z']
                self._show_focus_popup(f"Please adjust the focus using the microscope controls.\n\nClick OK when you are satisfied with the focus.\n\n {i} of {len(reference_points)}")
                current_z = self.Z
                reference_points.loc[reference_point_idx,'Z'] = current_z

            #save reference points to file

            reference_points.to_csv(os.path.join(self.file_handler.system_state_dir,f'reference_points.csv'),index=False)

        # Use the reference points to set the focus for the rest of the group
        for group in groups:
            group_positions = positions[positions[self.level_mapper[level]] == group]
            group_reference_points = reference_points[reference_points[level] == group]
            X_ref = group_reference_points['X'].values.astype(float)
            Y_ref = group_reference_points['Y'].values.astype(float)
            Z_ref = group_reference_points['Z'].values.astype(float)
            
            # Robust plane fitting: minimize median residual (robust to outliers)
            if len(group_reference_points) >= 3:
                # Objective function: median absolute residual
                def median_residual(coeffs):
                    a, b, c = coeffs
                    residuals = np.abs(Z_ref - (a * X_ref + b * Y_ref + c))
                    return np.median(residuals)
                
                # Use least squares as initial guess
                A = np.column_stack([X_ref, Y_ref, np.ones(len(X_ref))])
                Z = np.array(Z_ref)
                coeffs_init, _, _, _ = np.linalg.lstsq(A, Z, rcond=None)
                
                # Minimize median residual
                result = minimize(median_residual, coeffs_init, method='Nelder-Mead')
                if result.success:
                    a, b, c = result.x
                    median_res = median_residual([a, b, c])
                    self.log(f"Fitted robust plane for {group} (minimizing median residual): Z = {a:.4f}*X + {b:.4f}*Y + {c:.4f}, median residual = {median_res:.4f}")
                else:
                    # Fallback to least squares if optimization failed
                    a, b, c = coeffs_init
                    self.log(f"Fitted plane for {group} (fallback, optimization failed): Z = {a:.4f}*X + {b:.4f}*Y + {c:.4f}")
            else:
                # Fallback to least squares if fewer than 3 reference points
                A = np.column_stack([X_ref, Y_ref, np.ones(len(X_ref))])
                Z = np.array(Z_ref)
                coeffs, residuals, rank, s = np.linalg.lstsq(A, Z, rcond=None)
                a, b, c = coeffs
                self.log(f"Fitted plane for {group} (fallback, <3 points): Z = {a:.4f}*X + {b:.4f}*Y + {c:.4f}")
            
            # Predict Z for each position in the group
            X_pos = group_positions['X'].values
            Y_pos = group_positions['Y'].values
            Z_predicted = a * X_pos + b * Y_pos + c
            # Update Z values in the full positions DataFrame
            for idx, pos_idx in enumerate(group_positions.index):
                all_positions.loc[pos_idx, 'Z'] = Z_predicted[idx]
            self.log(f"Updated {len(group_positions)} positions for {group} with predicted Z values")
        self.file_handler.save_positions(all_positions)


    def display_preview(self, positions, name=None, channels=None, acquisition_dir=None):
        """Stitch and display a preview of a group of positions.
        
        Creates a stitched image from multiple positions and displays it.
        Used for preview generation during acquisition.
        
        Args:
            positions (pd.DataFrame): DataFrame containing position information.
            name (str, optional): Name for the preview. Defaults to None.
            channels (dict, optional): Channel configuration dictionary. Defaults to None.
            acquisition_dir (str, optional): Acquisition directory path. If None,
                finds latest preview acquisition. Defaults to None.
        """
        self.log(f"Stitching group of {len(positions)} positions",level='info')
        well = positions['well'].unique()[0]
        if acquisition_dir is None:
            acquisition_dir = self.file_handler.find_latest_acquisition('preview',well)
        if name is None:
            name = os.path.basename(acquisition_dir)
        if channels is None:
            # load metadata from acquisition
            metadata = self.file_handler.load_metadata(acquisition_dir)
            channels = metadata['Channel'].unique()
        else:
            channels = list(channels.keys())
        for channel in channels:
            stitched, pixel2stage= stitch_acquisition(
                acquisition_dir, 
                channel,
                zindex=0,
                metadata_filename='Metadata.txt',
                image_processor=None,
                registration_dict={},
                border=2000,
                stitch_rotate=0,
                stitch_flipud=False,
                stitch_fliplr=False,
                output_pixel_size=5,
                idx_stitch=False,
                position_names=positions['position_name'].unique(),
                verbose=False
            )
            vmin = stitched[stitched>0].min()
            vmax = np.percentile(stitched[stitched>0],99)
            # Save Stitched as tif for imageJ viewing
            fname = os.path.join(acquisition_dir,f"{name.replace(' ','__')}__{channel}.tif")
            tifffile.imwrite(fname, stitched)
            self.log(f"Saved stitched image to {fname}",level='debug')
            fig, ax = plt.subplots(figsize=(10,10))
            im = ax.imshow(stitched, cmap='gray', interpolation='nearest', vmin=vmin, vmax=vmax)
            plt.colorbar(im, ax=ax)
            ax.set_title(f"{name} {channel}")
            ax.invert_yaxis()
            non_zero_mask = stitched > 0
            if np.any(non_zero_mask):
                y_sum = np.sum(non_zero_mask, axis=1)
                x_sum = np.sum(non_zero_mask, axis=0)
                y_nonzero = np.where(y_sum > 0)[0]
                x_nonzero = np.where(x_sum > 0)[0]
                if len(y_nonzero) > 0 and len(x_nonzero) > 0:
                    y_min, y_max = y_nonzero[0], y_nonzero[-1]
                    x_min, x_max = x_nonzero[0], x_nonzero[-1]
                    padding = 50
                    y_min = max(0, y_min - padding)
                    y_max = min(stitched.shape[0], y_max + padding)
                    x_min = max(0, x_min - padding)
                    x_max = min(stitched.shape[1], x_max + padding)
                    ax.set_xlim(x_min, x_max)
                    ax.set_ylim(y_min, y_max)
            fig.savefig(fname.replace('.tif','.pdf'))
            self.log(f"Saved preview plot to {fname.replace('.tif','.pdf')}",level='debug')
            plt.close(fig)
            # plt.show(block=False)


    def _show_focus_popup(self, message):
        """Show an independent popup window for focus adjustment."""
        result = threading.Event()
        popup_result = [None]
        
        def show_popup():
            root = tk.Tk()
            root.title("Manual Event")
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
        """Update the current microscope state.
        
        Reads current state from Micro-Manager core and updates internal state
        dictionary. If state dict is provided, uses that instead.
        
        Args:
            state (dict, optional): State dictionary to use. If None, reads from core.
                Defaults to None.
        """
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
        if key == 'XY':
            if not self.check_state('X'):
                return False
            if not self.check_state('Y'):
                return False
        else:
            if not self.check_state(key): 
                return False
        if key in self.tolerance.keys():
            if key == 'Binning':
                if str(value) == str(self.get(key)):
                    return True
                else:
                    # self.log(f'{key}: {value} is not a valid binning. Possible values: {self.limits[key]}', level='error')
                    return False
            
            if abs(self.state[key] - value) < self.tolerance[key]:
                # self.log(f'{key}: {value} is within tolerance of {self.state[key]}', level='debug')
                return True
            else:
                return False
        elif key == 'XY':
            if not self.already_set('X', value[0]):
                # self.log(f'X: {value[0]} is not set', level='warning')
                return False
            if not self.already_set('Y', value[1]):
                # self.log(f'Y: {value[1]} is not set', level='warning')
                return False
            return True
        else:
            complete = self.state[key] == value
            # if complete:
                # self.log(f'{key}: {value} is the same as the current state', level='debug')
            return complete

    def check_state(self, key):
        """Check if a state key exists and has a value.
        
        Args:
            key (str): State key to check.
        
        Returns:
            bool: True if key exists and has a non-None value, False otherwise.
        """
        return key in self.state and self.state[key] is not None

    def is_valid(self, key, value):
        """Validate if a value is within limits for a given key.
        
        Checks if value is within the valid range defined in self.limits.
        Special handling for compound keys like 'XYZ' and 'XY'.
        
        Args:
            key (str): Parameter key to validate.
            value: Value to validate (can be single value or tuple for compound keys).
        
        Returns:
            bool: True if value is valid, False otherwise.
        """
        if not key in self.limits.keys():
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
        """Set a microscope parameter value.
        
        Validates value, updates state, and applies to Micro-Manager core.
        Skips if value is already set (if already_set returns True).
        
        Args:
            key (str): Parameter key (e.g., 'X', 'Y', 'Z', 'Channel', 'Exposure').
            value: Value to set.
        """
        if self.already_set(key, value): 
            return
        if not self.is_valid(key, value): 
            return
        
        if not self.core_enabled:
            self.log(f"Core not available - simulating {key}: {value}", level='warning')
            self.state[key] = value
            return
        
        try:
            if key == 'X': 
                self.core.set_xy_position(float(value), float(self.Y))
            elif key == 'Y': 
                self.core.set_xy_position(float(self.X), float(value))
            elif key == 'XY':
                self.core.set_xy_position(float(value[0]), float(value[1]))
            elif key == 'Z':
                self.log(f"Moving Z to {float(value)}", level='info')
                self.core.set_position(float(value))
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
            
            if (self.blocking) & (key in ['X', 'Y', 'Z','XY']): #FIXME: maybe this only needs to be called when setting stage position
                max_wait_time = 30#s
                start_time = time.time()
                while time.time() - start_time < max_wait_time:
                    try: # timeout warning for waiting for stage to move FIXME:
                        if 'Z' in key:
                            self.core.wait_for_device(self.core.get_focus_device())
                        else:
                            self.core.wait_for_device(self.core.get_xy_stage_device())
                        break
                    except Exception as e:
                        self.log(f"Waited for {key} for {time.time() - start_time} seconds", level='debug')
                        self.log(f"Error waiting for {key}: {e}", level='warning')
                        time.sleep(0.05)
                check_idx = 0
                while not self.already_set(key, value):
                    if 'Z' in key:
                        self.core.set_position(float(value))
                        self.core.wait_for_device(self.core.get_focus_device())
                    else:
                        self.core.set_xy_position(float(value[0]), float(value[1]))
                        self.core.wait_for_device(self.core.get_xy_stage_device())
                    self.log(f"Failed to move {key} try {check_idx} times to {float(value)}", level='info')
                    check_idx += 1
                    time.sleep(0.05)

            if key == 'XY':
                self.log(f'X: {value[0]}', level='debug')
                self.state['X'] = value[0]
                self.log(f'Y: {value[1]}', level='debug')
                self.state['Y'] = value[1]
            else:
                self.log(f'{key}: {value}', level='debug')
                self.state[key] = value
            
        except Exception as e:
            self.log(f"Error setting {key} to {value}: {e}", level='error')
            raise

    def get(self, key):
        """Get a microscope parameter value.
        
        Returns current value from state dictionary or reads from Micro-Manager core.
        
        Args:
            key (str): Parameter key (e.g., 'X', 'Y', 'Z', 'Channel', 'Exposure').
        
        Returns:
            Value of the parameter from state or core.
        """
        # if self.remember_state and self.state[key] is not None:
        #     self.log(f'{key}: {self.state[key]} Using Previous State', level='debug')
        #     return self.state[key]
        
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
            elif key == 'XY':
                value = (self.X, self.Y)
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
            if key == 'XY':
                self.log(f'X: {value[0]}', level='debug')
                self.state['X'] = value[0]
                self.log(f'Y: {value[1]}', level='debug')
                self.state['Y'] = value[1]
            else:
                self.log(f'{key}: {value}', level='debug')
                self.state[key] = value
            # self.log(f'{key}: {value}', level='debug')
            # self.state[key] = value
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
        self.set('XY', value)
        # self.set('X', value[0])
        # self.set('Y', value[1])
        return    
    @property
    def XYZ(self): 
        return (self.get('X'), self.get('Y'), self.get('Z'))
    @XYZ.setter
    def XYZ(self, value): 
        self.set('XY', value[0:2])
        # self.set('X', value[0])
        # self.set('Y', value[1])
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
        return self.ImageShape[1] * self.PixelSize
    
    @property
    def image_height_um(self): 
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
            self.log("Using fallback channel list", level='warning')
            return ['FarRed', 'DeepBlue', 'Green', 'Orange']
        return sorted(channels)
    
    @property
    def position_filtering_options(self):
        """Get available position filtering options."""
        return ['None', 'Draw']
    
    @property
    def set_focus_options(self):
        """Get available preview focus options."""
        levels = ['Plate','Well','Group','Position']
        methods  = ['Manual','Manual Plane']
        options = ['None']
        for method in methods:
            for level in levels:
                if (method == 'Manual Plane') & (level == 'Plate'):
                    continue
                if (method == 'Manual Plane') & (level == 'Position'):
                    continue
                options.append(f'{method} {level}')
        return options
    
    @property
    def autofocus_method_options(self):
        """Get available autofocus method options."""
        levels = ['Plate','Well','Group','Position'] 
        methods = ['Relative']
        options = ['None']
        for method in methods:
            for level in levels:
                options.append(f'{method} {level}')
        return options
    
    @property
    def status(self):
        """Get scope status from file handler."""
        return self.file_handler.get_status("Scope")
    
    @status.setter
    def status(self, value):
        """Set scope status and save to file handler."""
        self.file_handler.save_status("Scope", value)

    def check_status(self):
        """Check current scope status from status file.
        
        Returns:
            str: Current status string from Scope_status.txt.
        """
        return self.file_handler.get_status("Scope", read_only=False)
    @property
    def name(self):
        """Get the name of the class."""
        return self.__class__.__name__

import socket
import importlib

if __name__ == "__main__":
    # Determine system type from PC name
    pc_name = socket.gethostname()
    # Find which part before 'Scope' is system
    if 'Scope' in pc_name:
        system = pc_name.split('Scope')[0].capitalize()
        module_name = f"Scope.{system.lower()}scope"
        print(f"Using {system} scope")
    else:
        # fallback to default system name
        print("No system found, using default scope")
        module_name = f"Scope.scope"
    try:
        module = importlib.import_module(module_name)
        class_name = f"{system}Scope"
        scope_class = getattr(module, class_name)
    except Exception as e:
        print(f"Error loading specific scope module: {e}")
        from Scope.scope import Scope
        scope_class = Scope
        
    scope = scope_class(enable_core=True)
    scope.file_handler.verbose = True
    scope.continuous_monitoring()
