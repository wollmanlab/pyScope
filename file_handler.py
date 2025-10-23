import os
import json
import pandas as pd
import glob
import time
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List


class FileHandler:
    """
    Centralized file handler for consistent file operations across all classes.
    Manages all State directory file operations.
    """
    
    def __init__(self, system_state_dir: str = None):
        """
        Initialize the FileHandler.
        
        Args:
            system_state_dir (str): Directory path for system state files
        """
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
            log.setLevel(logging.DEBUG)
            
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
        print(f"[{logger_name}] {datetime.now().strftime('%H:%M:%S')} {message}")
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
            
            # Ensure state is serializable (special handling for Scope)
            if system_prefix == "Scope":
                serializable_state = {}
                for key, value in state.items():
                    if value is None:
                        serializable_state[key] = None
                    elif isinstance(value, (str, int, float, bool)):
                        serializable_state[key] = value
                    elif isinstance(value, (list, tuple)):
                        serializable_state[key] = list(value)
                    elif isinstance(value, dict):
                        serializable_state[key] = value
                    else:
                        serializable_state[key] = str(value)
                state = serializable_state
            
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
                if not read_only and status == "Paused":
                    self.log(f'{system_prefix} status is Paused, waiting for status change...', level='info', system_prefix=system_prefix)
                    while status == "Paused":
                        time.sleep(1)
                        try:
                            with open(status_file, 'r') as f:
                                status = f.read().strip()
                        except Exception as e:
                            self.log(f'Error reading {system_prefix} status file during pause: {e}', level='warning', system_prefix=system_prefix)
                            time.sleep(1)
                            continue
                    
                    if status == "Running":
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
