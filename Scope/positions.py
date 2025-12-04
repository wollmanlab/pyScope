"""
A comprehensive tool for planning microscope imaging experiments on well plates.

This script provides a Positions class to manage microscope positions in a pandas DataFrame,
specify microscope-specific configurations (like FOV, stage offsets, and axis mapping), 
and automatically generate tiling positions to cover various well shapes (circles, rectangles) 
with desired overlap.

Key Features:
- `Positions` class to manage all positions in a single pandas DataFrame.
- Support for rotated rectangular wells.
- Automatic generation of grid-based plate layouts (e.g., 96-well plate format).
- Position validation against microscope stage limits to prevent out-of-bounds positions.
- Interactive plotting to manually curate imaging positions.
- Save and load positions to/from CSV files for reproducibility.

The main execution block demonstrates how to use the Positions class to set up different
plate configurations and visualize the resulting stage positions.
"""
import math
import os
from typing import List, Dict, Any, Tuple, Optional
# Matplotlib imports removed - GUI functionality moved to gui.py
import copy
import logging
import pandas as pd
import numpy as np
from file_handler import FileHandler

class Positions:
    """Manages microscope imaging positions for well plates.
    
    Provides tools for generating tiling positions, managing coordinate transformations,
    and loading plate configurations. Supports circular and rectangular wells with
    rotation, automatic tiling with overlap, and position validation.
    
    Attributes:
        fov_info (Dict[str, Any]): Field of view information with keys 'X', 'Y', 'Overlap'.
        offsets (Dict[str, float]): Stage coordinate offsets {'X': float, 'Y': float, 'Z': float}.
        axis_mapping (Dict[str, str]): Mapping between plate and stage coordinate systems.
        limits (Dict[str, tuple]): Stage limits for position validation.
        file_handler (FileHandler): FileHandler instance for file operations.
        positions (pd.DataFrame): DataFrame containing all positions with columns:
            position_name, group, well, autofocus_group, X, Y, Z.
    """
    def __init__(self, 
                fov_info: Dict[str, Any] = None, 
                offsets: Dict[str, float] = {'X': 0, 'Y': 0, 'Z': 0}, 
                axis_mapping: Dict[str, str] = {'stage_x': 'plate_x', 'stage_y': 'plate_y'}, 
                limits: Dict[str, tuple] = None, 
                save_dir: str = None,
                file_handler: FileHandler = None):
                    """
                    Initializes the Positions object with microscope-specific settings.

                    Args:
                        fov_info (Dict[str, Any]): Field of view information including X, Y, and Overlap.
                            Example: {'X': 200, 'Y': 200, 'Overlap': 0.1}
                        offsets (Dict[str, float], optional): Stage offsets for coordinate transformation. 
                            Defaults to {'X': 0, 'Y': 0, 'Z': 0}.
                        axis_mapping (Dict[str, str], optional): Axis mapping for coordinate transformation. 
                            Defaults to {'stage_x': 'plate_x', 'stage_y': 'plate_y'}.
                        limits (Dict[str, tuple], optional): Stage limits for position validation. 
                            Example: {'X': (0, 10000), 'Y': (0, 10000), 'Z': (0, 1000)}. Defaults to None.
                        save_dir (str, optional): Directory path for GUI operations (not used for saving).
                        file_handler (FileHandler, optional): FileHandler instance for JSON operations. 
                            If None, a new FileHandler will be created.
                    """
                    if fov_info is None:
                        raise ValueError("fov_info is required")
                    self.fov_info = fov_info.copy()
                    if not 0 <= self.fov_info.get('Overlap', 0) < 1:
                        raise ValueError("FOV Overlap must be between 0 (inclusive) and 1 (exclusive).")
                    
                    self.offsets = offsets.copy()
                    self.axis_mapping = axis_mapping.copy()
                    
                    if limits is None:
                        raise ValueError("limits are required")
                    self.limits = limits
                    self.file_handler = file_handler if file_handler is not None else FileHandler()
                    self.positions = pd.DataFrame(columns=['position_name', 'group','well','autofocus_group','X', 'Y', 'Z'])
                    

    def log(self, message, level='info'):
        """Log messages using FileHandler's logging system.
        
        Args:
            message (str): Message to log.
            level (str): Log level ('debug', 'info', 'warning', 'error').
                Defaults to 'info'.
        """
        self.file_handler.log(message, level=level, system_prefix='Positions')

    def _transform_plate_to_stage_coords(self, plate_pos: Dict[str, float]) -> Dict[str, float]:
        """
        Applies axis mapping and offsets to convert plate coordinates to stage coordinates.

        Args:
            plate_pos (Dict[str, float]): A position dictionary {'X', 'Y', 'Z'} in the
                                          plate's coordinate system.

        Returns:
            Dict[str, float]: The corresponding position in the microscope stage's
                              coordinate system.
        """
        stage_pos = {}
        
        # Handle Stage X: maps to plate's X, -X, Y, or -Y
        map_x = self.axis_mapping['stage_x']
        sign_x = -1 if '-' in map_x else 1
        stage_pos['X'] = (plate_pos['Y'] if 'y' in map_x else plate_pos['X']) * sign_x

        # Handle Stage Y: maps to plate's Y, -Y, X, or -X
        map_y = self.axis_mapping['stage_y']
        sign_y = -1 if '-' in map_y else 1
        stage_pos['Y'] = (plate_pos['Y'] if 'y' in map_y else plate_pos['X']) * sign_y
            
        stage_pos['Z'] = plate_pos['Z']
        
        # Apply final stage offsets
        stage_pos['X'] += self.offsets['X']
        stage_pos['Y'] += self.offsets['Y']
        stage_pos['Z'] += self.offsets['Z']
        
        return stage_pos

    def _generate_plate_positions(self, name: str, well_info: Dict[str, Any]) -> Dict[str, Dict[str, float]]:
        """
        Generates a grid of FOV positions within the well's shape, using the
        plate's coordinate system (before microscope-specific transformations).

        Args:
            name (str): The name of the well.
            well_info (Dict[str, Any]): Dictionary containing the well's geometry,
                including 'center', 'shape', and 'dimensions'.

        Returns:
            Dict[str, Dict[str, float]]: A dictionary of plate-relative positions,
                                        where keys are tile names (e.g., 'Tile_0_0').
        """
        center = well_info['center']
        shape = well_info['shape'].lower()
        dimensions = well_info['dimensions']
        rotation = well_info.get('rotation', 0.0)
        
        # Calculate the distance to move between the centers of adjacent tiles
        step_x = self.fov_info['X'] * (1 - self.fov_info['Overlap'])
        step_y = self.fov_info['Y'] * (1 - self.fov_info['Overlap'])

        if step_x <= 0 or step_y <= 0:
            raise ValueError("Field of View dimensions and overlap result in a non-positive step size.")

        positions = {}

        # 1. Determine the size of the bounding box needed to contain the (potentially rotated) shape.
        if shape == 'circle':
            radius = dimensions['radius']
            max_dist_x = radius
            max_dist_y = radius
        elif shape == 'rectangle':
            w = dimensions['width'] / 2.0
            h = dimensions['height'] / 2.0
            angle_rad = math.radians(rotation)
            # Project the corners of the rotated rectangle onto the X and Y axes
            # to find the maximum extent. This defines the bounding box.
            max_dist_x = abs(w * math.cos(angle_rad)) + abs(h * math.sin(angle_rad))
            max_dist_y = abs(w * math.sin(angle_rad)) + abs(h * math.cos(angle_rad))
        else:
            raise ValueError(f"Unsupported shape: '{shape}'.")

        # Calculate how many steps in each direction from the center are needed to cover the bounding box.
        num_steps_x = math.ceil(max_dist_x / step_x)
        num_steps_y = math.ceil(max_dist_y / step_y)
        
        self.log(f"Generating positions for well '{name}'", level='debug')
        self.log(f"Center: {center}, Shape: {shape}, Dimensions: {dimensions}", level='debug')
        self.log(f"Step sizes: step_x={step_x}, step_y={step_y}", level='debug')
        self.log(f"Max distances: max_dist_x={max_dist_x}, max_dist_y={max_dist_y}", level='debug')
        self.log(f"Steps needed: num_steps_x={num_steps_x}, num_steps_y={num_steps_y}", level='debug')
        
        # 2. Generate a grid of candidate points covering the bounding box.
        angle_rad_rev = math.radians(-rotation)
        cos_a, sin_a = math.cos(angle_rad_rev), math.sin(angle_rad_rev)
        
        positions_generated = 0
        positions_filtered = 0
        
        for i in range(-num_steps_x, num_steps_x + 1):
            for j in range(-num_steps_y, num_steps_y + 1):
                cand_x = center['X'] + i * step_x
                cand_y = center['Y'] + j * step_y
                # self.log(f"Checking candidate position ({i}, {j}): X={cand_x}, Y={cand_y}", level='debug')
                
                # 3. For each candidate, check if it's inside the actual shape.
                # To do this for a rotated shape, we perform a reverse rotation on the candidate point
                # to bring it back into the shape's original, un-rotated coordinate system.
                dx, dy = cand_x - center['X'], cand_y - center['Y']
                local_x = dx * cos_a - dy * sin_a
                local_y = dx * sin_a + dy * cos_a

                is_inside = False
                if shape == 'circle':
                    # Check if the point is within the radius.
                    distance_squared = local_x**2 + local_y**2
                    radius_squared = dimensions['radius']**2
                    if distance_squared <= radius_squared:
                        is_inside = True
                    # self.log(f"Circle check - distance_squared={distance_squared}, radius_squared={radius_squared}, is_inside={is_inside}", level='debug')
                elif shape == 'rectangle':
                    # Check if the "un-rotated" point is within the simple rectangle boundaries.
                    if (abs(local_x) <= dimensions['width'] / 2.0 and
                        abs(local_y) <= dimensions['height'] / 2.0):
                        is_inside = True
                    # self.log(f"Rectangle check - local_x={local_x}, local_y={local_y}, width/2={dimensions['width']/2.0}, height/2={dimensions['height']/2.0}, is_inside={is_inside}", level='debug')
                
                if is_inside:
                    tile_name = f"Well{name}_Xi{i}_Yi{j}"
                    positions[tile_name] = {'X': cand_x, 'Y': cand_y, 'Z': center['Z']}
                    # self.log(f"Added position {tile_name}: X={cand_x}, Y={cand_y}, Z={center['Z']}", level='debug')
                    positions_generated += 1
                else:
                    positions_filtered += 1
                    # self.log(f"Position outside shape", level='debug')
                    
        self.log(f"Final count - Generated: {positions_generated}, Filtered: {positions_filtered}", level='debug')
        self.log(f"Generated {len(positions)} positions for well '{name}'", level='debug')
        return positions

    def add_well(self, name: str, well_info: Dict[str, Any], apply_offset_correction: bool = False):
        """
        Generates positions for a well and adds them to the positions DataFrame.

        Args:
            name (str): The unique name for the new well.
            well_info (Dict[str, Any]): The geometry definition for the new well.
            apply_offset_correction (bool): If True, subtract offsets from center coordinates 
                                          before generating positions (for positions measured 
                                          on a microscope with non-zero offsets).
        """
        # Input validation
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Well name must be a non-empty string")
        
        if not isinstance(well_info, dict):
            raise ValueError("well_info must be a dictionary")
        
        # Check if well name already exists
        if name in self.positions['well'].values:
            raise ValueError(f"Well '{name}' already exists. Use a different name or remove the existing well first.")
        
        # Validate well_info structure
        required_keys = ['center', 'shape', 'dimensions']
        missing_keys = [key for key in required_keys if key not in well_info]
        if missing_keys:
            raise ValueError(f"well_info missing required keys: {missing_keys}")
        
        # Validate center structure
        center = well_info['center']
        if not isinstance(center, dict):
            raise ValueError("well_info['center'] must be a dictionary")
        
        required_center_keys = ['X', 'Y', 'Z']
        missing_center_keys = [key for key in required_center_keys if key not in center]
        if missing_center_keys:
            raise ValueError(f"well_info['center'] missing required keys: {missing_center_keys}")
        
        # Validate dimensions structure
        dimensions = well_info['dimensions']
        if not isinstance(dimensions, dict):
            raise ValueError("well_info['dimensions'] must be a dictionary")
        
        # Validate shape-specific dimensions
        shape = well_info['shape'].lower()
        if shape == 'circle':
            if 'radius' not in dimensions:
                raise ValueError("Circle shape requires 'radius' in dimensions")
            if not isinstance(dimensions['radius'], (int, float)) or dimensions['radius'] <= 0:
                raise ValueError("Circle radius must be a positive number")
        elif shape == 'rectangle':
            required_rect_keys = ['width', 'height']
            missing_rect_keys = [key for key in required_rect_keys if key not in dimensions]
            if missing_rect_keys:
                raise ValueError(f"Rectangle shape missing required dimensions: {missing_rect_keys}")
            for key in required_rect_keys:
                if not isinstance(dimensions[key], (int, float)) or dimensions[key] <= 0:
                    raise ValueError(f"Rectangle {key} must be a positive number")
        else:
            raise ValueError(f"Unsupported shape: '{shape}'. Supported shapes: 'circle', 'rectangle'")
        
        # 1. Apply offset correction if requested (subtract offsets from center coordinates)
        if apply_offset_correction:
            # Create a copy of well_info to avoid modifying the original
            corrected_well_info = copy.deepcopy(well_info)
            corrected_well_info['center'] = {
                'X': well_info['center']['X'] - self.offsets['X'],
                'Y': well_info['center']['Y'] - self.offsets['Y'],
                'Z': well_info['center']['Z'] - self.offsets['Z']
            }
            self.log(f"Applied offset correction to well '{name}': subtracted offsets {self.offsets}")
        else:
            corrected_well_info = well_info

        # 2. Generate positions in the plate's coordinate system.
        self.log(f"About to generate positions for well '{name}'", level='debug')
        plate_positions = self._generate_plate_positions(name, corrected_well_info)
        self.log(f"Generated {len(plate_positions)} plate positions for well '{name}'", level='debug')

        # 3. Transform each position to the stage's coordinate system and add to DataFrame
        new_rows = []
        for tile_name, pos in plate_positions.items():
            stage_pos = self._transform_plate_to_stage_coords(pos)
            
            # Check if position is within limits (after transformation to stage coordinates)
            position_valid = True
            if self.limits is not None:
                # Validate X position
                if 'X' in self.limits:
                    x_min, x_max = self.limits['X']
                    if stage_pos['X'] < x_min or stage_pos['X'] > x_max:
                        self.log(f"Position filtered out - X {stage_pos['X']} outside limits [{x_min}, {x_max}]", level='debug')
                        position_valid = False
                
                # Validate Y position
                if 'Y' in self.limits and position_valid:
                    y_min, y_max = self.limits['Y']
                    if stage_pos['Y'] < y_min or stage_pos['Y'] > y_max:
                        self.log(f"Position filtered out - Y {stage_pos['Y']} outside limits [{y_min}, {y_max}]", level='debug')
                        position_valid = False
                
                # Validate Z position
                if 'Z' in self.limits and position_valid:
                    z_min, z_max = self.limits['Z']
                    if stage_pos['Z'] < z_min or stage_pos['Z'] > z_max:
                        self.log(f"Position filtered out - Z {stage_pos['Z']} outside limits [{z_min}, {z_max}]", level='debug')
                        position_valid = False
            
            if position_valid:
                # Create row data with only essential position information
                row_data = {
                    'position_name': tile_name,
                    'group': name,
                    'well': name,
                    'autofocus_group': name,
                    'X': stage_pos['X'],
                    'Y': stage_pos['Y'],
                    'Z': stage_pos['Z']
                }
                new_rows.append(row_data)
        
        # Add new rows to DataFrame
        new_df = pd.DataFrame(new_rows)
        self.positions = pd.concat([self.positions, new_df], ignore_index=True)
        
        self.log(f"Added well '{name}' with {len(new_rows)} FOV positions (filtered {len(plate_positions) - len(new_rows)} out-of-bounds positions).")
        self.log(f"Total positions after adding well '{name}': {len(self.positions)}", level='debug')
        self.log(f"Wells in positions DataFrame: {sorted(self.positions['well'].unique().tolist())}", level='debug')
        
        # Log detailed position information for debugging
        if not self.positions.empty:
            for well in self.positions['well'].unique():
                well_positions = self.positions[self.positions['well'] == well]
                self.log(f"Well {well} has {len(well_positions)} positions", level='debug')

    def get_well_positions(self, well_name: str) -> Dict[str, Dict[str, float]]:
        """
        Get positions for a specific well as a dictionary.

        Args:
            well_name (str): The name of the well.

        Returns:
            Dict[str, Dict[str, float]]: Dictionary of positions for the well.
        """
        well_positions = self.positions[self.positions['well'] == well_name]
        if well_positions.empty:
            raise ValueError(f"Well '{well_name}' not found in positions.")
        
        positions = {}
        for _, row in well_positions.iterrows():
            positions[row['position_name']] = {
                'X': row['X'], 
                'Y': row['Y'], 
                'Z': row['Z']
            }
        return positions

    @property
    def Wells(self) -> List[str]: return sorted(self.positions['well'].unique().tolist())
    @Wells.setter
    def Wells(self, well_list: List[str]):
        """
        Filter the positions DataFrame to only include positions from the specified wells.

        Args:
            well_list (List[str]): List of well names to keep. Positions from other wells will be removed.
        """
        if not well_list:
            raise ValueError("well_list must be a non-empty list")
        current_wells = self.positions['well'].unique().tolist()
        # Check which wells from the list actually exist
        existing_wells = [well for well in well_list if well in current_wells]
        missing_wells = [well for well in well_list if well not in current_wells]
        
        if missing_wells:
            raise ValueError(f"Wells not found in positions: {missing_wells}")
        
        if not existing_wells:
            raise ValueError(f"Must have at least one well in the list remaining")
        
        # Filter positions to only include the specified wells
        original_count = len(self.positions)
        self.positions = self.positions[self.positions['well'].isin(existing_wells)].copy()
        new_count = len(self.positions)
        
        self.log(f"Filtered positions: {original_count} -> {new_count} positions")
        self.log(f"Kept wells: {existing_wells}")

    def add_well_grid(self, base_well_info: Dict[str, Any], rows: int, columns: int, row_spacing: float, column_spacing: float, well_names: List[str] = None, save_name: str = None):
        """
        Adds a grid of wells based on a single well's geometry and spacing.
        Optionally saves the plate configuration to a JSON file in the Plates directory.

        Args:
            base_well_info (Dict[str, Any]): The geometry of the first well (e.g., A1),
                                             which serves as a template.
            rows (int): The number of rows in the grid.
            columns (int): The number of columns in the grid.
            row_spacing (float): The distance between the centers of wells in adjacent rows.
            column_spacing (float): The distance between centers of wells in adjacent columns.
            well_names (Optional[List[str]], optional): A custom list of names for the wells.
                If None, defaults to standard 'A1', 'A2'... naming. Defaults to None.
            save_name (Optional[str], optional): Name to save the configuration as. 
                If provided, saves to Plates/{save_name}.json. Defaults to None.
        """
        # Input validation
        if not isinstance(rows, int) or rows <= 0:
            raise ValueError("rows must be a positive integer")
        
        if not isinstance(columns, int) or columns <= 0:
            raise ValueError("columns must be a positive integer")
        
        if not isinstance(row_spacing, (int, float)) or row_spacing <= 0:
            raise ValueError("row_spacing must be a positive number")
        
        if not isinstance(column_spacing, (int, float)) or column_spacing <= 0:
            raise ValueError("column_spacing must be a positive number")
        
        if well_names is not None:
            if not isinstance(well_names, list):
                raise ValueError("well_names must be a list")
            if len(well_names) != rows * columns:
                raise ValueError(f"The number of names provided ({len(well_names)}) does not match the grid size ({rows * columns}).")
            # Check for duplicate names
            if len(well_names) != len(set(well_names)):
                raise ValueError("well_names contains duplicate names")
            # Check if any well names already exist
            existing_wells = set(self.positions['well'].values)
            conflicting_wells = [name for name in well_names if name in existing_wells]
            if conflicting_wells:
                raise ValueError(f"The following well names already exist: {conflicting_wells}")
        
        if save_name is not None and (not isinstance(save_name, str) or not save_name.strip()):
            raise ValueError("save_name must be a non-empty string")

        self.log(f"Generating a {rows}x{columns} well grid...")
        start_center = base_well_info['center']
        
        # Store plate configuration for potential saving
        plate_config = {}
        
        for i, r in enumerate(range(rows)):
            for j, c in enumerate(range(columns)):
                # Determine the well name
                if well_names:
                    well_name = well_names[i * columns + j]
                else:
                    well_name = f"{chr(ord('A') + r)}{c + 1}"

                # Calculate the new well's center based on grid position and spacing
                new_center_x = start_center['X'] + c * column_spacing
                new_center_y = start_center['Y'] + r * row_spacing
                
                new_well_info = copy.deepcopy(base_well_info)
                new_well_info['center'] = {'X': new_center_x, 'Y': new_center_y, 'Z': start_center['Z']}
                
                # Add to positions
                self.add_well(well_name, new_well_info)
                
                # Store in plate configuration for potential saving
                plate_config[well_name] = new_well_info
        
        # Save to file if save_name is provided
        if save_name:
            try:
                self.file_handler.save_plate_config(save_name, plate_config)
                self.log(f"Plate configuration saved as {save_name}.json")
            except Exception as e:
                self.log(f"Failed to save plate configuration: {e}", level='error')
                raise

    def load_plate_from_json(self, plate_name: str):
        """
        Loads a plate configuration from a JSON file and populates self.positions with the wells.

        Args:
            plate_name (str): The name of the plate configuration file (without .json extension).
                             The function will look for {plate_name}.json in the Plates directory.
        """
        # Load the plate configuration using file_handler
        plate_config = self.file_handler.load_plate_config(plate_name)
        
        # Clear existing positions
        self.positions = pd.DataFrame(columns=[
            'position_name', 'group', 'well', 'autofocus_group', 'X', 'Y', 'Z'
        ])
        
        # Handle both old format (direct wells dict) and new format (with offset_correction)
        if isinstance(plate_config, dict) and 'wells' in plate_config:
            # New format with offset correction setting
            wells_config = plate_config['wells']
            apply_offset_correction = plate_config.get('offset_correction', False)
            self.log(f"Loading plate with offset correction: {apply_offset_correction}")
        else:
            # Old format (direct wells dictionary)
            wells_config = plate_config
            apply_offset_correction = False
            self.log("Loading plate with legacy format (no offset correction)")
        
        # Add each well from the configuration
        wells_added = 0
        for well_name, well_info in wells_config.items():
            try:
                self.add_well(well_name, well_info, apply_offset_correction)
                wells_added += 1
            except Exception as e:
                self.log(f"Failed to add well '{well_name}': {e}", level='error')
                continue
        
        self.log(f"Successfully loaded plate '{plate_name}' with {wells_added} wells")
        self.log(f"Total positions generated: {len(self.positions)}")

    def load_positions_from_files(self, well_file_mapping: Dict[str, str]):
        """
        Loads positions from position files (.pos or .csv files) and populates self.positions.
        
        Args:
            well_file_mapping (Dict[str, str]): Dictionary where keys are well names and values are 
                                              file paths to position files (.pos for Micro-Manager files,
                                              .csv for CSV format files).
        """
        import json
        import os
        
        # Input validation
        if not isinstance(well_file_mapping, dict):
            raise ValueError("well_file_mapping must be a dictionary")
        
        if not well_file_mapping:
            raise ValueError("well_file_mapping cannot be empty")
        
        # Check for duplicate well names
        if len(well_file_mapping) != len(set(well_file_mapping.keys())):
            raise ValueError("well_file_mapping contains duplicate well names")
        
        # Check if any well names already exist
        existing_wells = set(self.positions['well'].values)
        conflicting_wells = [name for name in well_file_mapping.keys() if name in existing_wells]
        if conflicting_wells:
            raise ValueError(f"The following well names already exist: {conflicting_wells}")
        
        # Clear existing positions
        self.positions = pd.DataFrame(columns=[
            'position_name', 'group', 'well', 'autofocus_group', 'X', 'Y', 'Z'
        ])
        
        total_positions_loaded = 0
        
        for well_name, file_path in well_file_mapping.items():
            try:
                # Validate file path
                if not isinstance(file_path, str) or not file_path.strip():
                    raise ValueError(f"File path for well '{well_name}' must be a non-empty string")
                
                if not os.path.exists(file_path):
                    raise ValueError(f"File does not exist: {file_path}")
                
                # Determine file type based on extension
                file_extension = os.path.splitext(file_path)[1].lower()
                
                if file_extension == '.pos':
                    # Load and parse the Micro-Manager position file
                    with open(file_path, 'r', encoding='utf-8') as f:
                        mm_data = json.load(f)
                    
                    # Extract positions from the Micro-Manager format
                    positions = self._parse_mm_position_file(mm_data, well_name)
                    
                elif file_extension == '.csv':
                    # Load and parse the CSV position file
                    positions = self._parse_csv_position_file(file_path, well_name)
                    
                else:
                    raise ValueError(f"Unsupported file type: {file_extension}. Supported types: .pos, .csv")
                
                # Add positions to DataFrame
                if positions:
                    new_rows = []
                    for pos_name, coords in positions.items():
                        row_data = {
                            'position_name': pos_name,
                            'group': well_name,
                            'well': well_name,
                            'autofocus_group': well_name,
                            'X': coords['X'],
                            'Y': coords['Y'],
                            'Z': coords['Z']
                        }
                        new_rows.append(row_data)
                    
                    new_df = pd.DataFrame(new_rows)
                    self.positions = pd.concat([self.positions, new_df], ignore_index=True)
                    total_positions_loaded += len(new_rows)
                    
                    self.log(f"Loaded {len(new_rows)} positions from {file_path} for well '{well_name}'")
                else:
                    self.log(f"No positions found in file {file_path} for well '{well_name}'", level='warning')
                    
            except Exception as e:
                self.log(f"Failed to load positions from {file_path} for well '{well_name}': {e}", level='error')
                continue
        
        self.log(f"Successfully loaded {total_positions_loaded} total positions from {len(well_file_mapping)} files")
        self.log(f"Wells loaded: {list(well_file_mapping.keys())}")

    def _parse_mm_position_file(self, mm_data: Dict[str, Any], well_name: str) -> Dict[str, Dict[str, float]]:
        """
        Parses a Micro-Manager position file and extracts position coordinates.
        
        Args:
            mm_data (Dict[str, Any]): The parsed JSON data from the Micro-Manager position file.
            well_name (str): The name of the well these positions belong to.
            
        Returns:
            Dict[str, Dict[str, float]]: Dictionary of positions with coordinates.
        """
        positions = {}
        
        try:
            # Navigate to the StagePositions array
            stage_positions = mm_data.get('map', {}).get('StagePositions', {}).get('array', [])
            
            if not stage_positions:
                self.log(f"No StagePositions found in Micro-Manager file for well '{well_name}'", level='warning')
                return positions
            
            for i, stage_pos in enumerate(stage_positions):
                try:
                    # Get the device names from the position entry itself
                    default_xy_stage = stage_pos.get('DefaultXYStage', {}).get('scalar', '')
                    default_z_stage = stage_pos.get('DefaultZStage', {}).get('scalar', '')
                    device_positions = stage_pos.get('DevicePositions', {}).get('array', [])
                    x_pos = None
                    y_pos = None
                    z_pos = None
                    for device_pos in device_positions:
                        device_name = device_pos.get('Device', {}).get('scalar', '')
                        position_array = device_pos.get('Position_um', {}).get('array', [])
                        if device_name == default_xy_stage and len(position_array) >= 2:
                            x_pos = position_array[0]
                            y_pos = position_array[1]
                        elif device_name == default_z_stage and len(position_array) >= 1:
                            z_pos = position_array[0]
                    
                    # Check if we have valid coordinates
                    if x_pos is not None and y_pos is not None and z_pos is not None:
                        # Use the Label if available, otherwise generate a name
                        label = stage_pos.get('Label', {}).get('scalar', f'Pos_{i}')
                        position_name = f"{well_name}_{label}"
                        
                        positions[position_name] = {
                            'X': float(x_pos),
                            'Y': float(y_pos),
                            'Z': float(z_pos)
                        }
                        
                        self.log(f"Extracted position {position_name}: X={x_pos}, Y={y_pos}, Z={z_pos}", level='debug')
                    else:
                        self.log(f"Position {i} in well '{well_name}' missing required coordinates (X={x_pos}, Y={y_pos}, Z={z_pos})", level='warning')
                        
                except Exception as e:
                    self.log(f"Error parsing position {i} in well '{well_name}': {e}", level='warning')
                    continue
                    
        except Exception as e:
            self.log(f"Error parsing Micro-Manager file for well '{well_name}': {e}", level='error')
        
        return positions

    def _parse_csv_position_file(self, file_path: str, well_name: str) -> Dict[str, Dict[str, float]]:
        """
        Parses a CSV position file and extracts position coordinates.
        
        Args:
            file_path (str): Path to the CSV file.
            well_name (str): The name of the well these positions belong to.
            
        Returns:
            Dict[str, Dict[str, float]]: Dictionary of positions with coordinates.
        """
        positions = {}
        
        try:
            # Read the CSV file
            df = pd.read_csv(file_path)
            
            # Validate required columns
            required_columns = ['position_name', 'X', 'Y', 'Z']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                raise ValueError(f"CSV file missing required columns: {missing_columns}")
            
            # Check if there's a 'well' column and if it matches the expected well name
            if 'well' in df.columns:
                # Filter to only include rows for the specified well
                df_filtered = df[df['well'] == well_name]
                if df_filtered.empty:
                    self.log(f"No positions found for well '{well_name}' in CSV file {file_path}", level='warning')
                    return positions
            else:
                # No 'well' column, assume all positions belong to the specified well
                df_filtered = df
            
            # Extract positions
            for _, row in df_filtered.iterrows():
                try:
                    position_name = str(row['position_name'])
                    x_coord = float(row['X'])
                    y_coord = float(row['Y'])
                    z_coord = float(row['Z'])
                    
                    # Create position name with well prefix if not already present
                    if not position_name.startswith(f"{well_name}_"):
                        position_name = f"{well_name}_{position_name}"
                    
                    pos_dict = {
                        'X': x_coord,
                        'Y': y_coord,
                        'Z': z_coord
                    }
                   
                    positions[position_name] = pos_dict
                    
                    self.log(f"Extracted position {position_name}: X={x_coord}, Y={y_coord}, Z={z_coord}", level='debug')
                    
                except (ValueError, TypeError) as e:
                    self.log(f"Error parsing row in CSV file {file_path}: {e}", level='warning')
                    continue
            
            self.log(f"Successfully parsed {len(positions)} positions from CSV file {file_path} for well '{well_name}'")
            
        except Exception as e:
            self.log(f"Error parsing CSV file {file_path} for well '{well_name}': {e}", level='error')
        
        return positions


