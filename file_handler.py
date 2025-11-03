import os
import json
import pandas as pd
import glob
import time
import logging
import shutil
from datetime import datetime
from typing import Dict, Any, Optional, List
import tifffile
import numpy as np


class FileHandler:
    """
    Centralized file handler for consistent file operations across all classes.
    Manages all State directory file operations.
    """
    
    def __init__(self, system_state_dir: str = None,log_level: str = 'debug',verbose: bool = False):
        """
        Initialize the FileHandler.
        
        Args:
            system_state_dir (str): Directory path for system state files
        """
        self.log_level = log_level
        self.verbose = verbose
        if system_state_dir is None:
            # First look for a pointer
            pointer_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "file_handler_pointer.txt")
            if os.path.exists(pointer_file):
                with open(pointer_file, 'r') as f:
                    self.system_state_dir = f.read().strip()
            else:
                self.system_state_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "State")
        else:
            self.system_state_dir = system_state_dir
            with open(pointer_file, 'w') as f:
                f.write(self.system_state_dir)
                       
        if not os.path.exists(self.system_state_dir):
            os.makedirs(self.system_state_dir)
            self.log(f"Created State directory: {self.system_state_dir}", level='info', system_prefix='FileHandler')
        else:
            self.log(f"Using existing State directory: {self.system_state_dir}", level='info', system_prefix='FileHandler')
        
        self.acquisition_dir: Optional[str] = None
        self.acquisition_name: Optional[str] = None
        self._acquisition_active = False
        self._metadata_columns = None
        self._metadata_path = None
        self._metadata_cache: Dict[str, pd.DataFrame] = {}
        self._metadata_path_cache: Dict[str, str] = {}
    
    @property
    def dataset_path(self) -> str:
        """
        Get the current dataset path based on experiment state.
        
        Returns:
            str: Full path to the dataset directory
        """
        experiment_state = self.get_state("Experiment")
        save_path = experiment_state.get('save_path', '')
        user_name = experiment_state.get('user_name', '')
        project_name = experiment_state.get('project_name', '')
        experiment_name = experiment_state.get('experiment_name', '')
        return os.path.join(save_path, user_name, project_name, experiment_name)
    
    
    def log(self, message: str, level: str = 'info', system_prefix: str = 'FileHandler'):
        """
        Log messages with level support, similar to fileu.update_user structure.
        Sets up logging system lazily on first call.
        
        Args:
            message (str): The message to log
            level (str): Log level ('debug', 'info', 'warning', 'error', 'critical')
            system_prefix (str): System prefix to determine which log files to use (e.g., 'FileHandler', 'Experiment', 'Scope', 'Fluidics')
        """
        if system_prefix == 'FileHandler':
            loggers = [system_prefix]
        else:
            loggers = ['FileHandler',system_prefix]
        for logger_name in loggers:
            log = logging.getLogger(logger_name)
            
            # Check if handler already exists for this logger to avoid duplicates
            log_file_path = os.path.join(self.system_state_dir, f"{logger_name}.log")
            handler_exists = any(
                isinstance(h, logging.FileHandler) and h.baseFilename == log_file_path 
                for h in log.handlers
            )
            
            if not handler_exists:
                class_handler = logging.FileHandler(log_file_path, mode='a')
                class_handler.setLevel(logging.DEBUG)
                formatter = logging.Formatter('%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s', 
                                            datefmt='%H:%M:%S')
                class_handler.setFormatter(formatter)
                log.addHandler(class_handler)
            
            # Set logger level to DEBUG to capture all messages
            if self.log_level == 'debug':
                log.setLevel(logging.DEBUG)
            elif self.log_level == 'info':
                log.setLevel(logging.INFO)
            elif self.log_level == 'warning':
                log.setLevel(logging.WARNING)
            elif self.log_level == 'error':
                log.setLevel(logging.ERROR)
            elif self.log_level == 'critical':
                log.setLevel(logging.CRITICAL)
            
            # Format message differently for FileHandler log to include system prefix
            if logger_name == 'FileHandler' and system_prefix != 'FileHandler':
                formatted_message = f"[{system_prefix}] {message}"
            else:
                formatted_message = message
            
            # Log based on level
            if level.lower() == 'debug':
                log.debug(formatted_message)
            elif level.lower() == 'info':
                log.info(formatted_message)
            elif level.lower() == 'warning':
                log.warning(formatted_message)
            elif level.lower() == 'error':
                log.error(formatted_message)
            elif level.lower() == 'critical':
                log.critical(formatted_message)
            else:
                log.info(formatted_message)  # Default to info

        # Also print to console for immediate feedback
        if self.verbose:
            print(f"[{logger_name}]{datetime.now().strftime('%H:%M:%S')} {level} {message}")
        # print(f"[{logger_name}]{datetime.now().strftime('%H:%M:%S')} {level} {message}")
        if level.lower() == 'error':
            raise Exception(message)
    
    
    def _load_csv(self, file_path: str, default_columns: List[str] = None) -> pd.DataFrame:
        """Load CSV file."""
        try:
            if os.path.exists(file_path):
                return pd.read_csv(file_path)
            else:
                return pd.DataFrame(columns=default_columns) if default_columns else pd.DataFrame()
        except Exception as e:
            self.log(f'Error loading {file_path}: {e}', level='warning', system_prefix='FileHandler')
            return pd.DataFrame(columns=default_columns) if default_columns else pd.DataFrame()
    
    def _save_csv(self, df: pd.DataFrame, file_path: str):
        """Save DataFrame to CSV."""
        try:
            if not df.empty:
                df.to_csv(file_path, index=False)
        except Exception as e:
            self.log(f'Error saving CSV to {file_path}: {e}', level='warning', system_prefix='FileHandler')
    
    def _get_positions_file_path(self) -> str:
        """Get the positions file path."""
        return os.path.join(self.system_state_dir, "Positions.csv")
    
    # Shared Files
    @property
    def Positions(self) -> pd.DataFrame:
        """Load positions from Positions.csv file."""
        positions_file = self._get_positions_file_path()
        default_columns = ['position_name', 'well', 'X', 'Y', 'Z']
        return self._load_csv(positions_file, default_columns)
    
    def save_positions(self, positions_df: pd.DataFrame):
        """Save positions to Positions.csv file."""
        positions_file = self._get_positions_file_path()
        self._save_csv(positions_df, positions_file)
    
    # Generic file operations that can handle any system prefix
    def _get_state_file_path(self, system_prefix: str) -> str:
        """Get the state file path for a given system prefix."""
        return os.path.join(self.system_state_dir, f"{system_prefix}_state.json")
    
    def _get_tasks_file_path(self, system_prefix: str) -> str:
        """Get the tasks file path for a given system prefix."""
        return os.path.join(self.system_state_dir, f"{system_prefix}_tasks.csv")
    
    def _get_task_idx_file_path(self, system_prefix: str) -> str:
        """Get the task index file path for a given system prefix."""
        return os.path.join(self.system_state_dir, f"{system_prefix}_task_idx.txt")
    
    def _get_status_file_path(self, system_prefix: str) -> str:
        """Get the status file path for a given system prefix."""
        return os.path.join(self.system_state_dir, f"{system_prefix}_status.txt")
    
    def get_state(self, system_prefix: str) -> Dict[str, Any]:
        """Generic method to load state from any system's state file."""
        try:
            state_file = self._get_state_file_path(system_prefix)
            if os.path.exists(state_file):
                with open(state_file, 'r') as f:
                    return json.load(f)
            else:
                return {}
        except Exception as e:
            self.log(f'Error loading {system_prefix} state: {e}', level='warning', system_prefix=system_prefix)
            return {}
    
    def save_state(self, system_prefix: str, state: Dict[str, Any]):
        """Generic method to save state to any system's state file."""
        try:
            state_file = self._get_state_file_path(system_prefix)
            
            # # Ensure state is serializable (special handling for Scope)
            # if system_prefix == "Scope":
            #     serializable_state = {}
            #     for key, value in state.items():
            #         if value is None:
            #             serializable_state[key] = None
            #         elif isinstance(value, (str, int, float, bool)):
            #             serializable_state[key] = value
            #         elif isinstance(value, (list, tuple)):
            #             serializable_state[key] = list(value)
            #         elif isinstance(value, dict):
            #             serializable_state[key] = value
            #         else:
            #             serializable_state[key] = str(value)
            #     state = serializable_state
            
            with open(state_file, 'w') as f:
                json.dump(state, f, indent=4)
            self.log(f'{system_prefix} state saved to {state_file}', level='info', system_prefix=system_prefix)
        except Exception as e:
            self.log(f'Error saving {system_prefix} state: {e}', level='warning', system_prefix=system_prefix)
    
    def get_tasks(self, system_prefix: str) -> pd.DataFrame:
        """Generic method to load tasks from any system's tasks file."""
        tasks_file = self._get_tasks_file_path(system_prefix)
        return self._load_csv(tasks_file)
    
    def save_tasks(self, system_prefix: str, tasks_df: pd.DataFrame):
        """Generic method to save tasks to any system's tasks file."""
        tasks_file = self._get_tasks_file_path(system_prefix)
        self._save_csv(tasks_df, tasks_file)
    
    def get_task_idx(self, system_prefix: str) -> int:
        """Generic method to load task index from any system's task index file."""
        try:
            idx_file = self._get_task_idx_file_path(system_prefix)
            if os.path.exists(idx_file):
                with open(idx_file, 'r') as f:
                    return int(f.read().strip())
            else:
                return 0
        except Exception as e:
            self.log(f'Error loading {system_prefix} task index: {e}', level='warning', system_prefix=system_prefix)
            return 0
    
    def save_task_idx(self, system_prefix: str, task_idx: int):
        """Generic method to save task index to any system's task index file."""
        try:
            task_idx_file = self._get_task_idx_file_path(system_prefix)
            with open(task_idx_file, 'w') as f:
                f.write(str(task_idx))
            self.log(f'{system_prefix} task index {task_idx} saved to {task_idx_file}', level='info', system_prefix=system_prefix)
        except Exception as e:
            self.log(f'Error saving {system_prefix} task index: {e}', level='warning', system_prefix=system_prefix)
    
    def get_status(self, system_prefix: str, read_only: bool = True) -> str:
        """Generic method to load status from any system's status file.
        
        Args:
            system_prefix: The system prefix (e.g., "Fluidics", "Scope", "Experiment")
            read_only: If True, just read and return the status without pause handling.
                      If False, handle pause behavior by waiting until status changes.
        """
        try:
            status_file = self._get_status_file_path(system_prefix)
            if os.path.exists(status_file):
                with open(status_file, 'r') as f:
                    status = f.read().strip()
                
                # Handle paused status by waiting until status changes (only if not read_only)
                if (not read_only) and ("paused" in status.lower()):
                    self.log(f'{system_prefix} status is Paused, waiting for status change...', level='info', system_prefix=system_prefix)
                    while "paused" in status.lower():
                        time.sleep(1)
                        try:
                            with open(status_file, 'r') as f:
                                status = f.read().strip()
                        except Exception as e:
                            self.log(f'Error reading {system_prefix} status file during pause: {e}', level='warning', system_prefix=system_prefix)
                            time.sleep(1)
                            continue
                    
                    if "running" in status.lower():
                        self.log(f'{system_prefix} status changed from Paused to Running - resuming operation', level='info', system_prefix=system_prefix)
                    else:
                        self.log(f'{system_prefix} status changed from Paused to {status}', level='info', system_prefix=system_prefix)
                
                return status
            else:
                return ""
        except Exception as e:
            self.log(f'Error loading {system_prefix} status: {e}', level='warning', system_prefix=system_prefix)
            return ""
    
    def save_status(self, system_prefix: str, status: str):
        """Generic method to save status to any system's status file."""
        try:
            status_file = self._get_status_file_path(system_prefix)
            with open(status_file, 'w') as f:
                f.write(status)
            self.log(f'{system_prefix} status updated to: {status}', level='info', system_prefix=system_prefix)
        except Exception as e:
            self.log(f'Error saving {system_prefix} status: {e}', level='warning', system_prefix=system_prefix)
    
    def delete_tasks(self, system_prefix: str):
        """Generic method to delete tasks file for any system."""
        try:
            tasks_file = self._get_tasks_file_path(system_prefix)
            if os.path.exists(tasks_file):
                os.remove(tasks_file)
                self.log(f'{system_prefix} tasks file deleted', level='info', system_prefix=system_prefix)
        except Exception as e:
            self.log(f'Error deleting {system_prefix} tasks file: {e}', level='warning', system_prefix=system_prefix)
    
    
    def update_state(self, system_prefix: str, updates: Dict[str, Any]):
        """Generic method to update state for any system by merging new values with existing state."""
        if not isinstance(updates, dict):
            raise ValueError("updates must be a dictionary")
        try:
            current_state = self.get_state(system_prefix)
            current_state.update(updates)
            self.save_state(system_prefix, current_state)
            self.log(f'{system_prefix} state updated: {list(updates.keys())}', level='info', system_prefix=system_prefix)
        except Exception as e:
            self.log(f'Error updating {system_prefix} state: {e}', level='warning', system_prefix=system_prefix)
            raise RuntimeError(f"Failed to update {system_prefix} state: {e}")

    def load_plate_config(self, plate_name: str) -> Dict[str, Any]:
        """
        Loads a plate configuration from a JSON file.
        
        Args:
            plate_name (str): The name of the plate configuration file (without .json extension).
                             The function will look for {plate_name}.json in the Plates directory.
        
        Returns:
            Dict[str, Any]: The plate configuration dictionary
            
        Raises:
            ValueError: If plate_name is invalid or JSON is malformed
            FileNotFoundError: If the plate configuration file doesn't exist
            RuntimeError: If there's an error reading the file
        """
        # Input validation
        if not isinstance(plate_name, str) or not plate_name.strip():
            raise ValueError("plate_name must be a non-empty string")
        
        # Get the directory of the current file (file_handler.py)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        plates_dir = os.path.join(current_dir, "Plates")
        json_file_path = os.path.join(plates_dir, f"{plate_name}.json")
        
        # Check if the file exists
        if not os.path.isfile(json_file_path):
            raise FileNotFoundError(f"Plate configuration file not found: {json_file_path}")
        
        # Load the JSON file
        try:
            with open(json_file_path, 'r') as f:
                plate_config = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format in {json_file_path}: {e}")
        except Exception as e:
            raise RuntimeError(f"Error reading {json_file_path}: {e}")
        
        return plate_config
    
    def save_plate_config(self, plate_name: str, plate_config: Dict[str, Any]) -> None:
        """
        Saves a plate configuration to a JSON file.
        
        Args:
            plate_name (str): The name of the plate configuration file (without .json extension)
            plate_config (Dict[str, Any]): The plate configuration dictionary to save
            
        Raises:
            ValueError: If plate_name is invalid
            RuntimeError: If there's an error writing the file
        """
        # Input validation
        if not isinstance(plate_name, str) or not plate_name.strip():
            raise ValueError("plate_name must be a non-empty string")
        
        if not isinstance(plate_config, dict):
            raise ValueError("plate_config must be a dictionary")
        
        # Get the directory of the current file (file_handler.py)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        plates_dir = os.path.join(current_dir, "Plates")
        
        # Create Plates directory if it doesn't exist
        if not os.path.exists(plates_dir):
            os.makedirs(plates_dir)
        
        json_file_path = os.path.join(plates_dir, f"{plate_name}.json")
        
        # Save the JSON file
        try:
            with open(json_file_path, 'w') as f:
                json.dump(plate_config, f, indent=4)
        except Exception as e:
            raise RuntimeError(f"Error writing {json_file_path}: {e}")
    
    def setup_acquisition(self, chamber_acquisition_name: str,add_counter: bool = True):
        """
        Set up acquisition directories and initialize metadata file.
        
        Args:
            chamber_acquisition_name (str): Name of the chamber acquisition
        """
        if not os.path.exists(self.dataset_path):
            os.makedirs(self.dataset_path, exist_ok=True)
        
        if add_counter:
            existing_acquisitions = [
                d for d in os.listdir(self.dataset_path)
                if os.path.isdir(os.path.join(self.dataset_path, d)) 
                and os.path.exists(os.path.join(self.dataset_path, d, 'Metadata.txt'))
            ]
            counter = len(existing_acquisitions) + 1
            chamber_acquisition_name = f"{chamber_acquisition_name}_{counter}"
        self.acquisition_name = chamber_acquisition_name
        self.acquisition_dir = os.path.join(self.dataset_path, chamber_acquisition_name)
        
        acquisition_dir = self.acquisition_dir
        
        os.makedirs(acquisition_dir, exist_ok=True)
        os.makedirs(os.path.join(acquisition_dir, 'State'), exist_ok=True)
        
        self.log(f'Setting up acquisition {counter}: {chamber_acquisition_name}', level='info', system_prefix='FileHandler')
        
        experiment_state = self.get_state("Experiment")
        experiment_state['current_acquisition_name'] = chamber_acquisition_name
        self.save_state("Experiment", experiment_state)
        
        self._metadata_columns = [
            'Position', 'Channel', 'Exposure', 'PixelSize', 'XY', 'X', 'Y', 'Z', 
            'Zindex', 'Well', 'Group','acq', 'Scope', 'Time', 'TimestampImage','filename'
        ]
        
        metadata_path = os.path.join(acquisition_dir, 'Metadata.txt')
        self._metadata_path = metadata_path
        is_new_file = not os.path.exists(metadata_path) or os.path.getsize(metadata_path) == 0
        
        if is_new_file:
            with open(metadata_path, 'w') as f:
                header = '\t'.join(self._metadata_columns)
                f.write(header + '\n')
        else:
            with open(metadata_path, 'r') as f:
                first_line = f.readline().strip()
                if first_line:
                    self._metadata_columns = first_line.split('\t')
        
        self._acquisition_active = True
        
        log_line_numbers = {}
        for log_file in glob.glob(os.path.join(self.system_state_dir, '*.log')):
            try:
                with open(log_file, 'r') as f:
                    line_count = sum(1 for _ in f)
                log_line_numbers[os.path.basename(log_file)] = line_count
            except Exception as e:
                self.log(f'Error counting lines in {log_file}: {e}', level='warning', system_prefix='FileHandler')
        
        log_info_path = os.path.join(acquisition_dir, 'State', 'log_line_numbers.json')
        with open(log_info_path, 'w') as f:
            json.dump(log_line_numbers, f, indent=4)
    
    def save_image(self, image: Optional[np.ndarray], image_info: Dict[str, Any]):
        """
        Save image and append metadata to Metadata.txt.
        
        Args:
            image (Optional[np.ndarray]): Image array to save, or None
            image_info (Dict[str, Any]): Dictionary containing image metadata
        """
        if not self._acquisition_active:
            self.log("Acquisition not active. Call setup_acquisition first.", level='error', system_prefix='FileHandler')
            raise RuntimeError("Acquisition not active. Call setup_acquisition first.")
        
        # file_name = ''.join([f"{key}--{value}__" for key, value in image_info.items() if key not in ['XY', 'TimestampFrame']])[:-2] + '.tif'
        # file_name = ''.join([f"{key}--{value}__" for key, value in image_info.items() if key not in ['XY', 'TimestampImage','Time','PixelSize','Well']])+ str(int(time.time()))+ '.tif'
        file_name_keys = ['Position','Channel','Zindex','acq']
        image_info['acq'] = self.acquisition_name
        file_name_keys = [i for i in file_name_keys if i in image_info.keys()]
        file_name = ''.join([f"{image_info[key]}__" for key in file_name_keys])
        file_name = file_name + datetime.now().strftime('%Y-%m-%d_%H-%M-%S-%f')+ '.tif'
        image_info['filename'] = file_name
        image_path = os.path.join(self.acquisition_dir, file_name)
        tifffile.imwrite(image_path, image)
        
        values = []
        for key in self._metadata_columns:
            value = image_info.get(key, '')
            if isinstance(value, tuple):
                value = f"({value[0]},{value[1]})"
            else:
                value = str(value)
            values.append(value)
        
        with open(self._metadata_path, 'a') as f:
            f.write('\t'.join(values) + '\n')
        
        self.log(f'Image saved: {file_name}', level='debug', system_prefix='FileHandler')
    
    def finalize_acquisition(self):
        """
        Finalize acquisition by copying relevant log files.
        Uses the current acquisition_dir stored in the FileHandler instance.
        """
        if not self._acquisition_active:
            self.log("Acquisition not active. Call setup_acquisition first.", level='error', system_prefix='FileHandler')
            raise RuntimeError("Acquisition not active. Call setup_acquisition first.")
        
        acquisition_dir = self.acquisition_dir
        acquisition_state_dir = os.path.join(acquisition_dir, 'State')
        log_info_path = os.path.join(acquisition_state_dir, 'log_line_numbers.json')
        
        if os.path.exists(log_info_path):
            with open(log_info_path, 'r') as f:
                log_line_numbers = json.load(f)
            
            for log_filename, start_line in log_line_numbers.items():
                source_log_path = os.path.join(self.system_state_dir, log_filename)
                if os.path.exists(source_log_path):
                    dest_log_path = os.path.join(acquisition_state_dir, log_filename)
                    with open(source_log_path, 'r') as src:
                        lines = src.readlines()
                    if start_line < len(lines):
                        with open(dest_log_path, 'w') as dst:
                            dst.writelines(lines[start_line:])

        for file_type in ['*_state.json', '*_tasks.csv', '*_task_idx.txt', '*_status.txt']:
            state_files = glob.glob(os.path.join(self.system_state_dir, file_type))
            for state_file in state_files:
                dest_path = os.path.join(acquisition_state_dir, os.path.basename(state_file))
                if not os.path.exists(dest_path):
                    shutil.copy2(state_file, dest_path)
        
        self.log(f'Acquisition finalized for {os.path.basename(acquisition_dir)}', level='info', system_prefix='FileHandler')
        
        self._acquisition_active = False
        self._metadata_columns = None
        self._metadata_path = None
    
    def get_available_plate_configs(self) -> List[str]:
        """
        Get a list of available plate configuration files in the Plates directory.
        
        Returns:
            List[str]: List of plate configuration names (without .json extension)
        """
        # Get the directory of the current file
        current_dir = os.path.dirname(os.path.abspath(__file__))
        plates_dir = os.path.join(current_dir, "Plates")
        
        if not os.path.exists(plates_dir):
            return []
        
        # Find all JSON files in the Plates directory
        json_files = glob.glob(os.path.join(plates_dir, "*.json"))
        plate_names = []
        
        for json_file in json_files:
            filename = os.path.basename(json_file)
            name_without_ext = os.path.splitext(filename)[0]
            plate_names.append(name_without_ext)
        
        return sorted(plate_names)
    
    def clear_metadata_cache(self, acquisition_path: str = None):
        """
        Clear cached metadata from memory.
        
        Args:
            acquisition_path (str, optional): Path to clear. If None, clears all cached metadata.
        """
        if acquisition_path is None:
            self._metadata_cache.clear()
            self.log('Cleared all metadata cache', level='debug', system_prefix='FileHandler')
        else:
            if acquisition_path in self._metadata_cache:
                del self._metadata_cache[acquisition_path]
                self.log(f'Cleared metadata cache for {acquisition_path}', level='debug', system_prefix='FileHandler')
    
    def find_latest_acquisition(self, acquisition_name: str, chamber: str) -> Optional[str]:
        """
        Find the path to the most recent complete acquisition for a given acquisition name and chamber.
        An acquisition is considered complete if it has .log files in its State directory.
        
        Args:
            acquisition_name (str): Name of the acquisition (e.g., 'preview')
            chamber (str): Chamber/well identifier (e.g., 'A')
        
        Returns:
            Optional[str]: Path to the most recent complete acquisition, or None if none found
        """
        dataset_path = self.dataset_path
        if not os.path.exists(dataset_path):
            return None
        
        # Pattern matches acquisitions like: acquisition_name_Well-chamber[_counter]
        pattern_prefix = f"{acquisition_name}_Well-{chamber}"
        
        matching_acquisitions = []
        for item in os.listdir(dataset_path):
            acquisition_dir = os.path.join(dataset_path, item)
            if not os.path.isdir(acquisition_dir):
                continue
            
            # Check if this acquisition matches our pattern
            if item == pattern_prefix or item.startswith(f"{pattern_prefix}_"):
                # Check if it has log files in State directory (indicates it imaged fully)
                state_dir = os.path.join(acquisition_dir, 'State')
                if os.path.exists(state_dir):
                    log_files = glob.glob(os.path.join(state_dir, '*.log'))
                    if log_files:
                        matching_acquisitions.append({
                            'path': acquisition_dir,
                            'name': item,
                            'mtime': os.path.getmtime(acquisition_dir)
                        })
        
        if not matching_acquisitions:
            return None
        
        # Sort by modification time (most recent first)
        matching_acquisitions.sort(key=lambda x: x['mtime'], reverse=True)
        return matching_acquisitions[0]['path']
    
    def load_metadata(self, acquisition_path: str = None, fname: str = 'Metadata.txt', delimiter: str = '\t', force_reload: bool = False) -> pd.DataFrame:
        """
        Load metadata from a Metadata.txt file. Results are cached in memory.
        
        Args:
            acquisition_path (str, optional): Path to acquisition directory. If None, uses current acquisition_dir.
            fname (str): Metadata filename, default 'Metadata.txt'
            delimiter (str): Delimiter for the metadata file, default '\t'
            force_reload (bool): Force reload from disk even if cached
        
        Returns:
            pd.DataFrame: DataFrame containing metadata
        """
        if acquisition_path is None:
            if self.acquisition_dir is None:
                self.log("No acquisition directory available", level='error', system_prefix='FileHandler')
                raise RuntimeError("No acquisition directory available")
            acquisition_path = self.acquisition_dir
        
        metadata_path = os.path.join(acquisition_path, fname)
        
        if not force_reload and acquisition_path in self._metadata_cache:
            return self._metadata_cache[acquisition_path]
        
        if not os.path.exists(metadata_path):
            self.log(f'Metadata file not found at {metadata_path}', level='warning', system_prefix='FileHandler')
            return pd.DataFrame()
        
        def convert(val):
            return np.array(list(map(float, val.split())))
        
        try:
            md = pd.read_csv(metadata_path, delimiter=delimiter, converters={'XY': convert})
            md['root_pth'] = md.filename
            md.filename = os.path.join(acquisition_path, md.filename)
            self._metadata_cache[acquisition_path] = md
            self.log(f'Loaded {len(md)} metadata entries', level='debug', system_prefix='FileHandler')
            return md
        except Exception as e:
            self.log(f'Error loading metadata: {e}', level='warning', system_prefix='FileHandler')
            return pd.DataFrame()
    
    def stkread(self, acquisition_path: str = None, groupby: str = 'Position', sortby: str = None,
                fnames_only: bool = False, metadata: bool = False, verbose: bool = False, **kwargs):
        """
        Load images as stacks based on filtering criteria.
        
        Args:
            acquisition_path (str, optional): Path to acquisition directory
            groupby (str): Field to group images by for stacking, default 'Position'
            sortby (str): Field(s) to sort images by
            fnames_only (bool): Return filenames only without loading images
            metadata (bool): Return metadata table along with images
            verbose (bool): Print progress information
            **kwargs: Filtering criteria (Position, Channel, Zindex, acq, exposure, etc.)
        
        Returns:
            Images as stack(s) or filenames, optionally with metadata
        """
        if acquisition_path is None:
            if self.acquisition_dir is None:
                self.log("No acquisition directory available", level='error', system_prefix='FileHandler')
            acquisition_path = self.acquisition_dir
        
        if acquisition_path not in self._metadata_cache:
            self.load_metadata(acquisition_path)
        
        md = self._metadata_cache.get(acquisition_path, pd.DataFrame())
        if md.empty:
            return pd.DataFrame() if metadata else None
        
        # Input coercing
        for key, value in kwargs.items():
            if not isinstance(value, list):
                kwargs[key] = [value]
        
        # Filter images according to criteria
        mask = np.full((md.shape[0],), True, dtype=bool)
        
        # Handle Zindex with range support
        if 'Zindex' in kwargs:
            if 'Zindex' in md.columns:
                zindexes = kwargs['Zindex']
                if len(zindexes) > 0 and zindexes[0] == 'range':
                    _, zmin, zmax = kwargs['Zindex']
                    zindexes = list(range(zmin, zmax))
                mask = np.logical_and(mask, md['Zindex'].isin(zindexes))
            else:
                self.log(f'Warning: Zindex column not found in metadata', level='warning', system_prefix='FileHandler')
            del kwargs['Zindex']
        # Apply filtering for any field that exists in metadata columns
        for key in kwargs:
            if key in md.columns:
                mask = np.logical_and(mask, md[key].isin(kwargs[key]))
            else:
                self.log(f'Warning: Filter key "{key}" not found in metadata columns', level='warning', system_prefix='FileHandler')
        
        image_subset_table = md.loc[mask]
        
        if sortby is not None:
            image_subset_table.sort_values(sortby, inplace=True)
        
        image_groups = image_subset_table.groupby(groupby)
        fnames_output = {}
        mdata = {}
        for posname in image_groups.groups.keys():
            fnames_output[posname] = image_subset_table.loc[image_groups.groups[posname]].filename.values
            mdata[posname] = image_subset_table.loc[image_groups.groups[posname]]
        
        if fnames_only:
            if len(list(fnames_output.keys())) == 1:
                fnames_output = fnames_output[posname]
            if metadata:
                if len(mdata) == 1:
                    mdata = mdata[posname]
                return fnames_output, mdata
            else:
                return fnames_output
        else:
            stk = self._read_local(fnames_output, verbose=verbose)
            if metadata:
                if len(mdata) == 1:
                    mdata = mdata[posname]
                    return stk[posname], mdata
                else:
                    return stk, mdata
            else:
                if len(list(stk.keys())) == 1:
                    return stk[posname]
                else:
                    return stk
    
    def _read_local(self, filename_dict: Dict, verbose: bool = False):
        """
        Load images into dictionary of stacks.
        
        Args:
            filename_dict (Dict): Dictionary of groupby values to filename lists
            verbose (bool): Print progress information
        
        Returns:
            Dict: Dictionary of image stacks
        """
        images_dict = {}
        for key, filenames in filename_dict.items():
            if len(filenames) == 0:
                continue
            img = tifffile.imread(filenames[0])
            imgs = np.ndarray((len(filenames), img.shape[0], img.shape[1]), dtype=img.dtype)
            for img_idx, fname in enumerate(filenames):
                self.log(f'Loading {os.path.basename(fname)}', level='debug', system_prefix='FileHandler')
                imgs[img_idx, :, :] = tifffile.imread(fname)
            images_dict[key] = imgs.transpose([1, 2, 0])
        return images_dict