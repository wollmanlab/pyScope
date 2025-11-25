import time
import os
import re
import json
import pickle
import pandas as pd
import numpy as np
import ast
import tifffile
from file_handler import FileHandler
from Processing.image_processing import calculate_corrections
from Processing.stitching import stitch_acquisition

class Processing:
    """Base class for image processing operations.
    
    Provides file-based communication, logging, and continuous monitoring
    for image processing tasks like flat-field correction and stitching.
    
    Attributes:
        file_handler (FileHandler): File handler instance for state management.
        device (str): Device name (class name).
        last_message (str): Last status message received.
        busy (bool): Whether system is currently executing a protocol.
    """
    
    def __init__(self):
        """Initialize the Processing class.
        
        Sets up file handler and initializes state management.
        """
        self.file_handler = FileHandler()
        self.device = self.__class__.__name__
        self.last_message = ""
        self.busy = False
        self.log('Processing initialization complete')
    
    def log(self, message, level='info'):
        """Log messages using FileHandler's logging system.
        
        Args:
            message (str): Message to log.
            level (str): Log level ('debug', 'info', 'warning', 'error').
                Defaults to 'info'.
        """
        self.file_handler.log(message, level=level, system_prefix='Processing')

    def continuous_monitoring(self):
        """Run continuous monitoring loop for autonomous operation.
        
        Monitors processing_task.txt for new commands and executes protocols accordingly.
        Continues until 'stop' command is received or an error occurs.
        Sets status to 'idle' when terminated.
        """
        self.last_message = ''
        self.log('Continuous monitoring started')
        crashed = False
        try:
            while True:
                status = self.status
                if self.last_message != status:
                    self.last_message = status
                    self.log(f"New Message: {status}")
                    if status == 'offline':
                        self.status = 'idle'
                if 'stop' in status.lower():
                    self.log('Continuous monitoring stopped by user')
                    break
                elif "Command" in status:
                    self.interpret_command(status)
                
                time.sleep(1)
        except Exception as e:
            self.log(f"Error in continuous monitoring: {e}", level='error')
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

    def execute_protocol(self, message):
        """Execute a protocol based on command message.
        
        Routes protocol execution to appropriate handler. Supported protocols:
        - Stitch: Stitch acquisition images with flat-field correction
        
        Args:
            message (str): Protocol command message in format 'Protocol*chambers*name*other'.
        """
        self.log(f"Executing Protocol: {message}")
        protocol, chambers, name, other = self.decode_message(message)
        if protocol == 'Stitch':
            self.log(f"Stitching acquisition for: {chambers}, {name}, {other}")
            self.stitch(chambers, name, other)
        else:
            self.log(f"Unknown protocol: {protocol}", level='warning')
        self.file_handler.save_task_idx("Processing", 0)
        self.file_handler.delete_tasks("Processing")

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
                - name (str): Protocol name parameter (e.g., acquisition name)
                - other (str): Additional parameters
        """
        parts = message.split('*')
        if len(parts) < 3:
            self.log(f"Invalid message format: {message}", level='error')
            return None, [], '', ''
        
        protocol = parts[0]
        chambers = ast.literal_eval(parts[1])
        name = parts[2]
        other = parts[3] if len(parts) > 3 else ''
        
        if '!' in other:
            other = other.split('!')[0]
            self.simulate = True
        else:
            self.simulate = False
        
        return protocol, chambers, name, other

    def find_acquisition_directories(self, acquisition_name, chambers):
        """Find the most recent acquisition directories for given acquisition name and chambers.
        
        Args:
            acquisition_name (str): Name of the acquisition (e.g., 'hybe1', 'preview').
            chambers (list): List of chamber/well names (e.g., ['A', 'B']).
        
        Returns:
            dict: Dictionary mapping chamber names to acquisition directory paths.
                Returns empty dict if no acquisitions found.
        """
        acquisition_dirs = {}
        for chamber in chambers:
            acquisition_dir = self.file_handler.find_latest_acquisition(acquisition_name, chamber)
            if acquisition_dir is None:
                self.log(f"No acquisition found for {acquisition_name} in chamber {chamber}", level='warning')
            else:
                acquisition_dirs[chamber] = acquisition_dir
                self.log(f"Found acquisition for {chamber}: {acquisition_dir}")
        return acquisition_dirs

    def get_channels_from_metadata(self, acquisition_dir):
        """Get list of channels from metadata file.
        
        Args:
            acquisition_dir (str): Path to acquisition directory.
        
        Returns:
            list: List of unique channel names, or empty list if metadata not found.
        """
        metadata_path = os.path.join(acquisition_dir, 'Metadata.txt')
        if not os.path.exists(metadata_path):
            self.log(f"Metadata file not found: {metadata_path}", level='error')
            return []
        
        try:
            metadata = pd.read_csv(metadata_path, delimiter='\t')
            if 'Channel' not in metadata.columns:
                self.log("No 'Channel' column in metadata", level='error')
                return []
            channels = metadata['Channel'].unique().tolist()
            self.log(f"Found channels: {channels}")
            return channels
        except Exception as e:
            self.log(f"Error reading metadata: {e}", level='error')
            return []

    def _sanitize_filename(self, name):
        """Sanitize a string for use in filenames.
        
        Args:
            name (str): String to sanitize.
        
        Returns:
            str: Sanitized string safe for filenames.
        """
        sanitized = re.sub(r'[<>:"/\\|?*]', '_', str(name))
        sanitized = sanitized.replace(' ', '_')
        return sanitized

    def get_groups_from_metadata(self, acquisition_dir, channel=None):
        """Get list of groups from metadata file.
        
        Args:
            acquisition_dir (str): Path to acquisition directory.
            channel (str, optional): Filter groups by channel. If None, returns all groups.
        
        Returns:
            list: List of unique group names, or empty list if metadata not found.
        """
        metadata_path = os.path.join(acquisition_dir, 'Metadata.txt')
        if not os.path.exists(metadata_path):
            self.log(f"Metadata file not found: {metadata_path}", level='error')
            return []
        
        try:
            metadata = pd.read_csv(metadata_path, delimiter='\t')
            if channel is not None:
                metadata = metadata[metadata['Channel'] == channel]
            if 'Group' not in metadata.columns:
                self.log("No 'Group' column in metadata", level='warning')
                return []
            groups = metadata['Group'].unique().tolist()
            self.log(f"Found groups: {groups}")
            return groups
        except Exception as e:
            self.log(f"Error reading metadata: {e}", level='error')
            return []

    def stitch(self, chambers, acquisition_name, other):
        """Main stitching protocol.
        
        For each channel in the acquisition:
        1. Calculate flat-field (FF) and constant corrections
        2. Save FF and constant as TIF files
        3. For each group of positions, stitch images using FF and constant
        4. Save stitched images as TIF files
        
        Args:
            chambers (list): List of chamber/well names to process.
            acquisition_name (str): Name of the acquisition (e.g., 'hybe1').
            other (str): Additional parameters (currently unused).
        """
        self.log(f"Starting stitch protocol for {acquisition_name} with chambers {chambers}")
        
        acquisition_dirs = self.find_acquisition_directories(acquisition_name, chambers)
        if not acquisition_dirs:
            self.log("No acquisition directories found", level='error')
            return
        # Calculate Flat-Field and Constant for all channels in all acquisitions
        all_channels = set()
        for acquisition_dir in np.unique(list(acquisition_dirs.values())):
            channels = self.get_channels_from_metadata(acquisition_dir)
            all_channels.update(channels)
            for channel in channels:
                self.log(f"Calculating corrections for channel {channel}")
                try:
                    constant, FF = calculate_corrections(
                        acquisition_dir,
                        channel=channel,
                        zindex=0,
                        metadata_filename='Metadata.txt',
                        group=None,
                        position_names=None,
                        n_samples=25,
                        bin=4,
                        output_pixel_size=None
                    )
                    FF_path = os.path.join(acquisition_dir, f'FF_{channel}.tif')
                    constant_path = os.path.join(acquisition_dir, f'constant_{channel}.tif')
                    tifffile.imwrite(FF_path, FF.astype(np.float32))
                    tifffile.imwrite(constant_path, constant.astype(np.float32))
                    self.log(f"Saved FF to {FF_path}")
                    self.log(f"Saved constant to {constant_path}")
                except Exception as e:
                    self.log(f"Error calculating corrections: {e}", level='error')
                    continue
        
        if not all_channels:
            self.log("No channels found in any acquisition", level='error')
            return
        
        use_idx_stitch = 'idx_stitch' in other.lower() if other else False
        
        self.log(f"Processing channels: {sorted(all_channels)}")
        for chamber, acquisition_dir in acquisition_dirs.items():
            self.log(f"Processing chamber {chamber} in {acquisition_dir}")
            chamber_metadata = pd.read_csv(os.path.join(acquisition_dir, 'Metadata.txt'), delimiter='\t')
            channels_in_dir = chamber_metadata['Channel'].unique().tolist()
            for channel in channels_in_dir:
                channel_metadata = chamber_metadata[chamber_metadata['Channel'] == channel]
                self.log(f"Processing channel: {channel}")
                FF = tifffile.imread(os.path.join(acquisition_dir, f'FF_{channel}.tif'))
                constant = tifffile.imread(os.path.join(acquisition_dir, f'constant_{channel}.tif'))
                groups = channel_metadata['Group'].unique().tolist()
                if not groups:
                    self.log(f"No groups found for channel {channel}, stitching all positions together")
                    groups = [None]
                
                for group in groups:
                    group_metadata = channel_metadata[channel_metadata['Group'] == group]
                    if group is None:
                        group_name = 'all'
                        position_names = None
                    else:
                        group_name = self._sanitize_filename(group)
                        position_names = group_metadata['Position'].unique().tolist()
                        if not position_names:
                            self.log(f"No positions found for group {group}, skipping", level='warning')
                            continue
                    
                    self.log(f"Stitching group {group_name} for channel {channel} (idx_stitch={use_idx_stitch})")
                    try:
                        if use_idx_stitch:
                            canvas, pixel2stage, idx_canvas, posname_idx_mapper = stitch_acquisition(
                                acquisition_dir,
                                channel,
                                zindex=0,
                                metadata_filename='Metadata.txt',
                                image_processor=None,
                                registration_dict={},
                                border=10,
                                stitch_rotate=0,
                                stitch_flipud=False,
                                stitch_fliplr=False,
                                bin=1,
                                idx_stitch=True,
                                output_pixel_size=5,
                                position_names=position_names,
                                FF=FF,
                                constant=constant,
                                verbose=True,
                                avg_overlap=False
                            )
                            
                            stitch_path = os.path.join(acquisition_dir, f'stitched_{channel}_{group_name}.tif')
                            pixel2stage_path = os.path.join(acquisition_dir, f'pixel2stage_{channel}_{group_name}.pkl')
                            idx_canvas_path = os.path.join(acquisition_dir, f'idx_canvas_{channel}_{group_name}.tif')
                            posname_idx_mapper_path = os.path.join(acquisition_dir, f'posname_idx_mapper_{channel}_{group_name}.json')
                            
                            canvas = np.clip(canvas, 0, 2**16-1).astype(np.uint16)
                            tifffile.imwrite(stitch_path, canvas)
                            self.log(f"Saved stitched image to {stitch_path}")
                            
                            with open(pixel2stage_path, 'wb') as f:
                                pickle.dump(pixel2stage, f)
                            self.log(f"Saved pixel2stage to {pixel2stage_path}")
                            
                            idx_canvas_uint16 = np.clip(idx_canvas, 0, 2**16-1).astype(np.uint16)
                            tifffile.imwrite(idx_canvas_path, idx_canvas_uint16)
                            self.log(f"Saved idx_canvas to {idx_canvas_path}")
                            
                            with open(posname_idx_mapper_path, 'w') as f:
                                json.dump(posname_idx_mapper, f, indent=2)
                            self.log(f"Saved posname_idx_mapper to {posname_idx_mapper_path}")
                        else:
                            canvas, pixel2stage = stitch_acquisition(
                                acquisition_dir,
                                channel,
                                zindex=0,
                                metadata_filename='Metadata.txt',
                                image_processor=None,
                                registration_dict={},
                                border=10,
                                stitch_rotate=0,
                                stitch_flipud=False,
                                stitch_fliplr=False,
                                bin=1,
                                idx_stitch=False,
                                output_pixel_size=5,
                                position_names=position_names,
                                FF=FF,
                                constant=constant,
                                verbose=True,
                                avg_overlap=False
                            )
                            
                            stitch_path = os.path.join(acquisition_dir, f'stitched_{channel}_{group_name}.tif')
                            canvas = np.clip(canvas, 0, 2**16-1).astype(np.uint16)
                            tifffile.imwrite(stitch_path, canvas)
                            self.log(f"Saved stitched image to {stitch_path}")
                    except Exception as e:
                        self.log(f"Error stitching group {group_name}: {e}", level='error')
                        continue
        
        self.log("Stitch protocol completed")

    @property
    def status(self):
        """Get processing status from file handler."""
        return self.file_handler.get_status("Processing", read_only=False)
    
    @status.setter
    def status(self, value):
        """Set processing status and save to file handler."""
        self.file_handler.save_status("Processing", value)

    def check_status(self):
        """Check current processing status from status file.
        
        Returns:
            str: Current status string from Processing_status.txt.
        """
        return self.file_handler.get_status("Processing", read_only=False)

    @property
    def name(self):
        """Get the name of the class."""
        return self.__class__.__name__

if __name__ == '__main__':
    processing = Processing()
    while True:
        processing.continuous_monitoring()

