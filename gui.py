"""
Experiment GUI for pyScope

This module contains the main GUI for the Experiment class that displays the current state
and provides controls for fluidics, scope, positions, and experiment management.
All GUI functionality is now consolidated in this file.
"""
import importlib
import tkinter as tk
from tkinter import ttk
import threading
import time
import os
import json
import pandas as pd
from typing import Dict, List, Tuple, Optional, Callable, Any
from Scope.scope import Scope
from Scope.positions import Positions
from experiment import Experiment
# from Fluidics.fluidics import Fluidics
from file_handler import FileHandler

# GUI Configuration - Colors, Fonts, and Styling
# Main color palette
GUI_COLORS = {
    # Primary colors
    'background': '#2b2b2b',           # Dark gray background
    'surface': '#404040',              # Medium gray for surfaces
    'surface_light': '#606060',        # Lighter gray for highlights
    'surface_dark': '#1a1a1a',         # Darker gray for contrast
    
    # Text colors
    'text': '#ffffff',                 # White text
    'text_secondary': '#cccccc',       # Light gray text
    'text_muted': '#999999',           # Muted gray text
    
    # Accent colors
    'primary': '#0078d4',              # Blue accent
    'primary_hover': '#106ebe',        # Darker blue for hover
    'success': '#107c10',              # Green for success
    'warning': '#ff8c00',              # Orange for warnings
    'error': '#d13438',                # Red for errors
    'info': '#0078d4',                 # Blue for info
    
    # Interactive elements
    'button': '#404040',               # Button background
    'button_hover': '#606060',         # Button hover state
    'button_active': '#0078d4',        # Button active state
    'entry': '#404040',                # Entry field background
    'entry_focus': '#0078d4',          # Entry field focus border
    'combobox': '#404040',             # Combobox background
    'combobox_select': '#606060',      # Combobox selection background
    
    # Checkbox and radio button
    'checkbox_bg': '#2b2b2b',          # Checkbox background
    'checkbox_select': '#404040',      # Checkbox selection color
    'checkbox_active': '#2b2b2b',      # Checkbox active background
    
    # Frame and border colors
    'frame': '#2b2b2b',                # Frame background
    'border': '#000000',               # Border color
    'border_light': '#404040',         # Light border
    'border_dark': '#1a1a1a',          # Dark border
    
    # Status colors
    'status_success': '#107c10',       # Success status
    'status_warning': '#ff8c00',       # Warning status
    'status_error': '#d13438',         # Error status
    'status_info': '#0078d4',          # Info status
}

# Font configurations
GUI_FONTS = {
    # Font family
    'family': 'Arial',                 # Default font family
    
    # Font sizes
    'title': ('Arial', 16, 'bold'),    # Main title font
    'subtitle': ('Arial', 14, 'bold'), # Subtitle font
    'heading': ('Arial', 12, 'bold'),  # Section heading font
    'body': ('Arial', 10),             # Body text font
    'small': ('Arial', 9),             # Small text font
    'small_bold': ('Arial', 9, 'bold'), # Small bold text font
    'button': ('Arial', 10),           # Button text font
    'button_bold': ('Arial', 10, 'bold'), # Bold button text font
    'label': ('Arial', 10),            # Label text font
    'entry': ('Arial', 10),            # Entry field font
    'status': ('Arial', 10, 'bold'),   # Status message font
}

def apply_dark_theme(window):
    """
    Apply the dark theme to a tkinter window and all its child widgets.
    
    Args:
        window: The tkinter window or widget to apply the theme to
    """
    # Configure window background
    window.configure(bg=GUI_COLORS['background'])
    
    # Apply theme to all widget types
    window.option_add('*TFrame*background', GUI_COLORS['frame'])
    window.option_add('*TLabel*background', GUI_COLORS['background'])
    window.option_add('*TLabel*foreground', GUI_COLORS['text'])
    window.option_add('*TLabel*font', GUI_FONTS['label'])
    window.option_add('*TButton*background', GUI_COLORS['button'])
    window.option_add('*TButton*foreground', GUI_COLORS['text'])
    window.option_add('*TButton*font', GUI_FONTS['button'])
    window.option_add('*TButton*activebackground', GUI_COLORS['button_hover'])
    window.option_add('*TButton*activeforeground', GUI_COLORS['text'])
    window.option_add('*TEntry*background', GUI_COLORS['entry'])
    window.option_add('*TEntry*foreground', GUI_COLORS['text'])
    window.option_add('*TEntry*font', GUI_FONTS['entry'])
    window.option_add('*TEntry*insertbackground', GUI_COLORS['text'])
    window.option_add('*TCombobox*background', GUI_COLORS['combobox'])
    window.option_add('*TCombobox*foreground', GUI_COLORS['text'])
    window.option_add('*TCombobox*font', GUI_FONTS['entry'])
    window.option_add('*TCombobox*selectbackground', GUI_COLORS['combobox_select'])
    window.option_add('*TCombobox*selectforeground', GUI_COLORS['text'])
    window.option_add('*TCheckbutton*background', GUI_COLORS['checkbox_bg'])
    window.option_add('*TCheckbutton*foreground', GUI_COLORS['text'])
    window.option_add('*TCheckbutton*font', GUI_FONTS['label'])
    window.option_add('*TCheckbutton*selectcolor', GUI_COLORS['checkbox_select'])
    window.option_add('*TCheckbutton*activebackground', GUI_COLORS['checkbox_active'])
    window.option_add('*TCheckbutton*activeforeground', GUI_COLORS['text'])
    window.option_add('*TRadiobutton*background', GUI_COLORS['checkbox_bg'])
    window.option_add('*TRadiobutton*foreground', GUI_COLORS['text'])
    window.option_add('*TRadiobutton*font', GUI_FONTS['label'])
    window.option_add('*TRadiobutton*selectcolor', GUI_COLORS['checkbox_select'])
    window.option_add('*TRadiobutton*activebackground', GUI_COLORS['checkbox_active'])
    window.option_add('*TRadiobutton*activeforeground', GUI_COLORS['text'])
    window.option_add('*TLabelFrame*background', GUI_COLORS['frame'])
    window.option_add('*TLabelFrame*foreground', GUI_COLORS['text'])
    window.option_add('*TLabelFrame*font', GUI_FONTS['heading'])

def create_dark_style():
    """
    Create and configure a dark style for ttk widgets.
    
    Returns:
        ttk.Style: Configured style object
    """
    style = ttk.Style()
    style.theme_use('clam')
    
    # Configure dark style for combobox
    style.configure('Dark.TCombobox',
                   fieldbackground=GUI_COLORS['combobox'],
                   background=GUI_COLORS['combobox'],
                   foreground=GUI_COLORS['text'],
                   selectbackground=GUI_COLORS['combobox_select'],
                   selectforeground=GUI_COLORS['text'],
                   font=GUI_FONTS['entry'],
                   borderwidth=1,
                   relief='solid')
    
    # Configure dark style for button
    style.configure('Dark.TButton',
                   background=GUI_COLORS['button'],
                   foreground=GUI_COLORS['text'],
                   font=GUI_FONTS['button'],
                   borderwidth=1,
                   relief='raised')
    
    style.map('Dark.TButton',
             background=[('active', GUI_COLORS['button_hover']),
                        ('pressed', GUI_COLORS['button_active'])])
    
    return style

def get_status_color(status_type):
    """
    Get the appropriate color for a status message.
    
    Args:
        status_type (str): Type of status ('success', 'warning', 'error', 'info')
    
    Returns:
        str: Color code for the status type
    """
    status_colors = {
        'success': GUI_COLORS['status_success'],
        'warning': GUI_COLORS['status_warning'],
        'error': GUI_COLORS['status_error'],
        'info': GUI_COLORS['status_info']
    }
    return status_colors.get(status_type, GUI_COLORS['text'])

def create_error_label(parent, text="", status_type='error'):
    """
    Create a styled error/status label.
    
    Args:
        parent: Parent widget
        text (str): Text to display
        status_type (str): Type of status ('success', 'warning', 'error', 'info')
    
    Returns:
        tk.Label: Configured label widget
    """
    color = get_status_color(status_type)
    return tk.Label(parent, 
                   text=text, 
                   bg=GUI_COLORS['background'], 
                   fg=color, 
                   font=GUI_FONTS['status'])

def create_title_label(parent, text=""):
    """
    Create a styled title label.
    
    Args:
        parent: Parent widget
        text (str): Text to display
    
    Returns:
        tk.Label: Configured title label widget
    """
    return tk.Label(parent, 
                   text=text, 
                   bg=GUI_COLORS['background'], 
                   fg=GUI_COLORS['text'], 
                   font=GUI_FONTS['title'])

def create_subtitle_label(parent, text=""):
    """
    Create a styled subtitle label.
    
    Args:
        parent: Parent widget
        text (str): Text to display
    
    Returns:
        tk.Label: Configured subtitle label widget
    """
    return tk.Label(parent, 
                   text=text, 
                   bg=GUI_COLORS['background'], 
                   fg=GUI_COLORS['text'], 
                   font=GUI_FONTS['subtitle'])

def create_heading_label(parent, text=""):
    """
    Create a styled heading label.
    
    Args:
        parent: Parent widget
        text (str): Text to display
    
    Returns:
        tk.Label: Configured heading label widget
    """
    return tk.Label(parent, 
                   text=text, 
                   bg=GUI_COLORS['background'], 
                   fg=GUI_COLORS['text'], 
                   font=GUI_FONTS['heading'])

def create_body_label(parent, text=""):
    """
    Create a styled body text label.
    
    Args:
        parent: Parent widget
        text (str): Text to display
    
    Returns:
        tk.Label: Configured body label widget
    """
    return tk.Label(parent, 
                   text=text, 
                   bg=GUI_COLORS['background'], 
                   fg=GUI_COLORS['text'], 
                   font=GUI_FONTS['body'])

def create_button(parent, text="", command=None, bold=False):
    """
    Create a styled button.
    
    Args:
        parent: Parent widget
        text (str): Button text
        command: Command to execute when clicked
        bold (bool): Whether to use bold font
    
    Returns:
        tk.Button: Configured button widget
    """
    font = GUI_FONTS['button_bold'] if bold else GUI_FONTS['button']
    return tk.Button(parent, 
                    text=text, 
                    command=command,
                    bg=GUI_COLORS['button'], 
                    fg=GUI_COLORS['text'],
                    font=font,
                    activebackground=GUI_COLORS['button_hover'], 
                    activeforeground=GUI_COLORS['text'])


class StatePanel:
    """
    Generic state panel that can display state information in configurable column layouts.
    
    Features:
    - Configurable number of columns (1-4)
    - Custom data source functions
    - Automatic widget management
    - Efficient updates (only recreates widgets when structure changes)
    - Customizable column grouping logic
    """
    
    def __init__(self, parent_frame: tk.Frame, num_columns: int = 2, 
                 data_source_func: Optional[Callable] = None,
                 column_grouping_func: Optional[Callable] = None,
                 panel_name: str = "State", create_frame: bool = True):
        """
        Initialize the state panel.
        
        Args:
            parent_frame: The parent tkinter frame to create the panel in
            num_columns: Number of columns to display (1-4)
            data_source_func: Function that returns the state data as a dict
            column_grouping_func: Function that groups items into columns
            panel_name: Name for the panel's LabelFrame
            create_frame: Whether to create a LabelFrame (True) or use parent as frame (False)
        """
        self.parent_frame = parent_frame
        self.num_columns = max(1, min(4, num_columns))  # Clamp between 1-4
        self.data_source_func = data_source_func
        self.column_grouping_func = column_grouping_func
        self.panel_name = panel_name
        self.create_frame = create_frame
        
        # Widget storage
        self.widgets = {}
        self.created = False
        self.last_structure = []
        
        # Create the main state frame
        self.create_state_frame()
        
    def create_state_frame(self):
        """Create the main state frame and column containers."""
        if self.create_frame:
            # Create the state frame
            self.state_frame = tk.LabelFrame(self.parent_frame, text=self.panel_name,
                                           bg='#2b2b2b', fg='#ffffff', 
                                           font=('Arial', 10, 'bold'))
            self.state_frame.pack(fill='x', padx=5, pady=5)
        else:
            # Use parent as the state frame (for embedding)
            self.state_frame = self.parent_frame
        
        # Create the table frame
        self.table_frame = tk.Frame(self.state_frame, bg='#2b2b2b')
        self.table_frame.pack(fill='x', padx=5, pady=5)
        
        # Create column containers
        self.columns = []
        self.column_frames = []
        
        for i in range(self.num_columns):
            col_frame = tk.Frame(self.table_frame, bg='#2b2b2b')
            col_frame.pack(side='left', fill='both', expand=True, 
                          padx=(0, 3) if i < self.num_columns - 1 else (3, 0))
            self.column_frames.append(col_frame)
            self.widgets[f'col_{i}'] = []
    
    def update_display(self, state_data: Optional[Dict[str, Any]] = None):
        """
        Update the state display with new data.
        
        Args:
            state_data: Optional state data dict. If None, uses data_source_func
        """
        try:
            # Get data from source if not provided
            if state_data is None and self.data_source_func:
                state_data = self.data_source_func()
            
            if not state_data:
                self._show_no_data_message()
                return
            
            # Convert to items list
            items = [(k, v) for k, v in state_data.items() if v is not None]
            
            # Group items into columns
            if self.column_grouping_func:
                column_items = self.column_grouping_func(items, self.num_columns)
            else:
                column_items = self._default_grouping(items)
            
            # Check if structure changed
            current_structure = [item[0] for item in items]
            if not self.created or self.last_structure != current_structure:
                self._recreate_widgets(column_items)
                self.created = True
                self.last_structure = current_structure
            else:
                self._update_widget_values(column_items)
                
        except Exception as e:
            print(f"Error updating state display: {e}")
    
    def _default_grouping(self, items: List[Tuple[str, Any]]) -> List[List[Tuple[str, Any]]]:
        """Default grouping: distribute items evenly across columns."""
        items_per_col = len(items) // self.num_columns
        column_items = []
        
        for i in range(self.num_columns):
            start_idx = i * items_per_col
            if i == self.num_columns - 1:  # Last column gets remaining items
                end_idx = len(items)
            else:
                end_idx = (i + 1) * items_per_col
            column_items.append(items[start_idx:end_idx])
        
        return column_items
    
    def _recreate_widgets(self, column_items: List[List[Tuple[str, Any]]]):
        """Recreate all widgets for the new structure."""
        # Clear existing tracked widgets
        for widget_list in self.widgets.values():
            for widget in widget_list:
                widget.destroy()
        
        # Clear any remaining widgets from column frames (including untracked no-data messages)
        for i in range(self.num_columns):
            for widget in self.column_frames[i].winfo_children():
                widget.destroy()
        
        # Reset widget storage
        for i in range(self.num_columns):
            self.widgets[f'col_{i}'] = []
        
        # Reset no-data flag since we're showing actual data
        self.no_data_shown = False
        
        # Create widgets for each column
        for col_idx, items in enumerate(column_items):
            for property_name, value in items:
                self._create_property_widget(col_idx, property_name, value)
    
    def _create_property_widget(self, col_idx: int, property_name: str, value: Any):
        """Create a property widget in the specified column."""
        col_frame = self.column_frames[col_idx]
        
        # Create row frame
        row_frame = tk.Frame(col_frame, bg='#2b2b2b', 
                           relief='solid', bd=1, 
                           highlightthickness=1, highlightbackground='#555555')
        row_frame.pack(fill='x', pady=1)
        
        # Create property label
        property_label = tk.Label(row_frame, text=property_name, 
                                bg='#2b2b2b', fg='#ffffff', 
                                font=('Arial', 8, 'bold'), 
                                anchor='w')
        property_label.pack(side='left', padx=(5, 5))
        
        # Create value label
        value_label = tk.Label(row_frame, text=str(value), 
                             bg='#2b2b2b', fg='#ffffff', 
                             font=('Arial', 8), 
                             anchor='w')
        value_label.pack(side='left', padx=(0, 5))
        
        # Store widgets
        self.widgets[f'col_{col_idx}'].extend([row_frame, property_label, value_label])
    
    def _update_widget_values(self, column_items: List[List[Tuple[str, Any]]]):
        """Update values in existing widgets."""
        # Reset no-data flag since we're updating with actual data
        self.no_data_shown = False
        
        for col_idx, items in enumerate(column_items):
            col_widgets = self.widgets[f'col_{col_idx}']
            
            for item_idx, (property_name, value) in enumerate(items):
                # Find the value label (every 3rd widget starting from index 2)
                value_label_idx = item_idx * 3 + 2
                if value_label_idx < len(col_widgets):
                    value_label = col_widgets[value_label_idx]
                    value_label.config(text=str(value))
    
    def _clear_all_widgets(self):
        """Clear all widgets from all columns."""
        # Clear existing tracked widgets
        for widget_list in self.widgets.values():
            for widget in widget_list:
                try:
                    widget.destroy()
                except:
                    pass  # Widget might already be destroyed
        
        # Clear any remaining widgets from column frames
        for i in range(self.num_columns):
            for widget in self.column_frames[i].winfo_children():
                try:
                    widget.destroy()
                except:
                    pass  # Widget might already be destroyed
        
        # Reset widget storage
        for i in range(self.num_columns):
            self.widgets[f'col_{i}'] = []
        
        # Reset flags
        self.created = False
        self.last_structure = []
        self.no_data_shown = False
    
    def _show_no_data_message(self):
        """Show a no data message."""
        # Clear all existing widgets first
        self._clear_all_widgets()
        
        # Only show if not already shown
        if not hasattr(self, 'no_data_shown') or not self.no_data_shown:
            no_data_frame = tk.Frame(self.column_frames[0], bg='#2b2b2b')
            no_data_frame.pack(fill='x', pady=10)
            
            no_data_label = tk.Label(no_data_frame, text="No state information available",
                                   bg='#2b2b2b', fg='#888888', 
                                   font=('Arial', 8))
            no_data_label.pack()
            
            # Store the no-data widgets so they can be properly cleared
            if 'col_0' not in self.widgets:
                self.widgets['col_0'] = []
            self.widgets['col_0'].extend([no_data_frame, no_data_label])
            
            self.no_data_shown = True


# Predefined grouping functions for common use cases

def scope_grouping(items: List[Tuple[str, Any]], num_columns: int) -> List[List[Tuple[str, Any]]]:
    """Group scope items evenly across columns."""
    mid_point = len(items) // 2
    return [items[:mid_point], items[mid_point:]]


def experiment_grouping(items: List[Tuple[str, Any]], num_columns: int) -> List[List[Tuple[str, Any]]]:
    """Group experiment items evenly across two columns."""
    mid_point = len(items) // 2
    return [items[:mid_point], items[mid_point:]]


def fluidics_grouping(items: List[Tuple[str, Any]], num_columns: int) -> List[List[Tuple[str, Any]]]:
    """Group fluidics items evenly across two columns."""
    mid_point = len(items) // 2
    return [items[:mid_point], items[mid_point:]]


class StatusPanel:
    """
    A reusable status panel that includes a pause button, progress bar, and status label.
    This eliminates code duplication across fluidics, scope, and experiment panels.
    """
    
    def __init__(self, parent, panel_name, system_name, progress_info_type, 
                 pause_callback=None, resume_callback=None, create_frame=True, file_handler=None,
                 launch_callback=None, kill_callback=None,system_prefix=''):
        """
        Initialize the status panel.
        
        Args:
            parent: Parent tkinter widget
            panel_name: Name of the panel (e.g., "Fluidics", "Scope", "Experiment")
            system_name: System name for FileHandler (e.g., "Fluidics", "Scope", "Experiment")
            progress_info_type: Type for progress info retrieval (e.g., "fluidics", "scope")
            pause_callback: Optional custom pause callback function
            resume_callback: Optional custom resume callback function
            create_frame: Whether to create a LabelFrame (True) or use parent as frame (False)
            file_handler: FileHandler instance for reading/writing status files
            launch_callback: Optional custom launch callback function
            kill_callback: Optional custom kill callback function
            system_prefix: Name of system (e.g., "Cyan", "Orange", "Blue")
        """
        self.panel_name = panel_name
        self.system_name = system_name
        self.progress_info_type = progress_info_type
        self.pause_callback = pause_callback
        self.resume_callback = resume_callback
        self.launch_callback = launch_callback
        self.kill_callback = kill_callback
        self.file_handler = file_handler
        self.system_prefix = system_prefix
        
        # Threading support for launched instances
        self.launched_instance = None
        self.launched_thread = None
        self.is_launched = False
        
        # Store previous status for pause/resume functionality
        self.previous_status = None
        
        # Status file name for loading initial status
        self.status_file_name = f"{self.system_name}_status.txt"
        
        if create_frame:
            # Create the main frame
            self.frame = tk.LabelFrame(parent, text=panel_name, 
                                      bg=GUI_COLORS['frame'], fg=GUI_COLORS['text'], 
                                      font=GUI_FONTS['heading'])
            self.frame.grid_propagate(False)  # Prevent frame from expanding beyond allocated space
        else:
            # Use parent as the frame (for embedding)
            self.frame = parent
        
        # Create control frame with launch/kill button, pause button, progress bar, and status
        self.control_frame = tk.Frame(self.frame, bg=GUI_COLORS['frame'])
        self.control_frame.pack(fill='x', padx=10, pady=10)
        
        # Button frame on the left (Launch/Kill and Pause buttons)
        self.button_frame = tk.Frame(self.control_frame, bg=GUI_COLORS['frame'])
        self.button_frame.pack(side='left')
        
        # Launch/Kill button
        self.launch_btn = create_button(self.button_frame, "Launch", 
                                      command=self.launch)
        self.launch_btn.pack(side='left', padx=(0, 5))
        
        # Set initial green styling for Launch button
        self.launch_btn.config(bg=GUI_COLORS['success'], fg='white')
        
        # Pause button
        self.pause_btn = create_button(self.button_frame, "Pause", 
                                      command=self.pause)
        self.pause_btn.pack(side='left', padx=(0, 10))
        
        # Progress bar in the middle
        self.progress_frame = tk.Frame(self.control_frame, bg=GUI_COLORS['frame'])
        self.progress_frame.pack(side='left', fill='x', expand=True, padx=10)
        
        self.progress_bar = ttk.Progressbar(self.progress_frame, mode='determinate', 
                                          style='Dark.Horizontal.TProgressbar')
        self.progress_bar.pack(fill='x', pady=2)
        
        self.progress_info = tk.Label(self.progress_frame, text="No tasks", 
                                    bg=GUI_COLORS['frame'], fg=GUI_COLORS['text_muted'], 
                                    font=GUI_FONTS['small'])
        self.progress_info.pack(anchor='w')
        
        # Status display on the right
        self.status_frame = tk.Frame(self.control_frame, bg=GUI_COLORS['frame'])
        self.status_frame.pack(side='right')
        
        tk.Label(self.status_frame, text="Status:", bg=GUI_COLORS['frame'], 
                fg=GUI_COLORS['text'], font=GUI_FONTS['body']).pack(side='left')
        
        self.status_label = tk.Label(self.status_frame, text="Not Started", 
                                   bg=GUI_COLORS['frame'], fg=GUI_COLORS['warning'],
                                   font=GUI_FONTS['body'])
        self.status_label.pack(side='left', padx=(10, 0))
        
        # Load initial status from file if file_handler is available
        self.load_initial_status()

    def log(self, message, level='info'):
        """Log messages using FileHandler's logging system."""
        self.file_handler.log(f"{self.panel_name}: {message}", level=level, system_prefix='GUI')
    
    def load_initial_status(self):
        """Load the current status from the status file."""
        try:
            # Determine which status property to use based on status_file_name
            if self.status_file_name == "Experiment_status.txt":
                current_status = self.file_handler.get_status("Experiment")
            elif self.status_file_name == "Scope_status.txt":
                current_status = self.file_handler.get_status("Scope")
            elif self.status_file_name == "Fluidics_status.txt":
                current_status = self.file_handler.get_status("Fluidics")
            else:
                return
            
            # Update the status display if we found a valid status
            if current_status and current_status.strip():
                self.set_status(current_status.strip())
                
        except Exception as e:
            print(f"Error loading initial status for {self.panel_name}: {e}")
    
    def pause(self):
        """Pause the system."""
        try:
            paused_status = None  # Initialize paused_status
            
            # Read current status and store it in memory
            current_status = self.file_handler.get_status(self.system_name, read_only=True)
            self.previous_status = current_status
            self.log(f"{self.panel_name} paused - stored previous status: {self.previous_status}")
            
            # Write paused status with previous message info
            paused_status = f"Paused:{self.previous_status.split(':')[-1] if ':' in self.previous_status else self.previous_status}"
            self.file_handler.save_status(self.system_name, paused_status)
            
            # Update status label to match what was written to the file
            self.status_label.config(text=paused_status, fg=GUI_COLORS['warning'])
            self.pause_btn.config(text="Resume", command=self.resume)
            
            # Ensure status label is always in sync with file
            self.refresh_status_from_file()
            
            # Call custom pause callback if provided
            if self.pause_callback:
                self.pause_callback()
            
        except Exception as e:
            print(f"Error pausing {self.panel_name}: {e}")
    
    def resume(self):
        """Resume the system."""
        try:
            # Restore the previous status
            if self.previous_status:
                self.log(f"{self.panel_name} resumed - restoring previous status: {self.previous_status}")
                self.file_handler.save_status(self.system_name, self.previous_status)
                
                # Update the status label to show the restored status
                self.status_label.config(text=self.previous_status, fg=GUI_COLORS['success'])
            else:
                # Fallback if no previous status stored
                self.log(f"{self.panel_name} resumed - no previous status found, setting to Running")
                self.file_handler.save_status(self.system_name, "Running")
                self.status_label.config(text="Running", fg=GUI_COLORS['success'])
            
            self.pause_btn.config(text="Pause", command=self.pause)
            
            # Ensure status label is always in sync with file
            self.refresh_status_from_file()
            
            # Call custom resume callback if provided
            if self.resume_callback:
                self.resume_callback()
            
        except Exception as e:
            print(f"Error resuming {self.panel_name}: {e}")
    
    def launch(self):
        """Launch a threaded instance of the system."""
        if self.is_launched:
            self.kill()
            return
            
        # Reset button to normal state before attempting launch
        self.launch_btn.config(text="Launch", bg=GUI_COLORS['success'], fg='white')
        
        try:
            # Import the appropriate class based on system_name
            if self.system_name == "Experiment":
                from experiment import Experiment
                self.launched_instance = Experiment()
            elif self.system_name == "Scope":
                module = importlib.import_module(f"Scope.{self.system_prefix.lower()}scope")
                class_name = f"{self.system_prefix}Scope"
                scope_class = getattr(module, class_name)
                self.launched_instance = scope_class()
            elif self.system_name == "Fluidics":
                module = importlib.import_module(f"Fluidics.{self.system_prefix.lower()}fluidics")
                class_name = f"{self.system_prefix}Fluidics"
                fluidics_class = getattr(module, class_name)
                self.launched_instance = fluidics_class()
            else:
                print(f"Unknown system: {self.system_name}")
                return
            
            # # Set status to Idle when launching
            # self.launched_instance.status = "Idle"
            
            # Start the continuous_monitoring function in a separate thread
            self.launched_thread = threading.Thread(
                target=self.launched_instance.continuous_monitoring,
                daemon=True
            )
            self.launched_thread.start()
            
            self.is_launched = True
            
            # Update button appearance
            self.launch_btn.config(text="Kill", bg=GUI_COLORS['error'], fg='white')
            
            # Update status
            status = self.launched_instance.status
            self.status_label.config(text=status, fg=GUI_COLORS['success'])
            
            # Ensure status label is always in sync with file
            self.refresh_status_from_file()
            
            # Call custom launch callback if provided
            if self.launch_callback:
                self.launch_callback()
            
            print(f"{self.panel_name} launched successfully")
            
        except Exception as e:
            print(f"Error launching {self.panel_name}: {e}")
            # Set Launch button to orange to indicate error
            self.launch_btn.config(text="Launch", bg=GUI_COLORS['warning'], fg='white')
            # Update status to show error
            self.status_label.config(text="Launch Error", fg=GUI_COLORS['error'])
    
    def kill(self):
        """Kill the launched instance by setting status to Stop."""
        try:
            if not self.is_launched:
                print(f"{self.panel_name} is not launched")
                return
            
            # Set status to Stop to terminate the instance
            self.file_handler.save_status(self.system_name, "Stop")
            
            # Wait for thread to finish (with timeout)
            if self.launched_thread and self.launched_thread.is_alive():
                self.launched_thread.join(timeout=2.0)
            
            # Reset state
            self.is_launched = False
            self.launched_instance = None
            self.launched_thread = None
            
            # Update button appearance
            self.launch_btn.config(text="Launch", bg=GUI_COLORS['success'], fg='white')
            
            # Update status to match what was written to the file
            self.status_label.config(text="Stop", fg=GUI_COLORS['error'])
            
            # Ensure status label is always in sync with file
            self.refresh_status_from_file()
            
            # Call custom kill callback if provided
            if self.kill_callback:
                self.kill_callback()
            
            print(f"{self.panel_name} killed successfully")
            
        except Exception as e:
            print(f"Error killing {self.panel_name}: {e}")
    
    def update_progress(self, progress_info):
        """Update the progress bar display."""
        try:
            if progress_info is None:
                self.progress_bar['value'] = 0
                self.progress_info.config(text="No tasks")
                return
            
            # Update progress bar
            self.progress_bar['value'] = progress_info['progress_percent']
            
            # Update progress info text
            current_task = progress_info['current_task']
            total_tasks = progress_info['total_tasks']
            remaining_time = progress_info['estimated_remaining_time']
            
            if remaining_time > 0:
                minutes = int(remaining_time // 60)
                seconds = int(remaining_time % 60)
                time_text = f"{minutes:02d}:{seconds:02d} remaining"
            else:
                time_text = "Completed"
            
            progress_text = f"Task {current_task}/{total_tasks} - {time_text}"
            self.progress_info.config(text=progress_text)
            
        except Exception as e:
            print(f"Error updating {self.panel_name} progress: {e}")
    
    def set_status(self, status_text, color=None):
        """Set the status label text and color."""
        if color is None:
            color = GUI_COLORS['text']
        self.status_label.config(text=status_text, fg=color)
    
    def refresh_status_from_file(self):
        """Refresh the status label from the status file."""
        try:
            # Get current status using FileHandler
            current_status = self.file_handler.get_status(self.system_name)
            
            # Update the status display if we found a valid status
            if current_status and current_status.strip():
                self.set_status(current_status.strip())
                
        except Exception as e:
            print(f"Error refreshing status for {self.panel_name}: {e}")
    
    def grid(self, **kwargs):
        """Grid the frame (delegates to tkinter Frame.grid)."""
        self.frame.grid(**kwargs)
    
    def pack(self, **kwargs):
        """Pack the frame (delegates to tkinter Frame.pack)."""
        self.frame.pack(**kwargs)

import importlib



class SystemGUI:
    """
    Main GUI class for the System that displays current state and provides controls.
    """
    
    def __init__(self, system: str = ''):
        """
        Initialize the Experiment GUI.
        
        Args:
            experiment_instance: The Experiment instance to control and monitor
        """
        self.file_handler = FileHandler()
        self.system = system
        self.system_prefix = system
        self.experiment = Experiment()

        module_name = f"Scope.{system.lower()}scope"
        module = importlib.import_module(module_name)
        class_name = f"{system}Scope"
        scope_class = getattr(module, class_name)
        self.scope = scope_class(enable_core=False)

        # module_name = f"Fluidics.{system.lower()}Fluidics"
        # module = importlib.import_module(module_name)
        # class_name = f"{system}Fluidics"
        # fluidics_class = getattr(module, class_name)
        # self.fluidics = fluidics_class(gui=False)

        self.update_thread = None #FIXME
        self.running = False #FIXME
        self.available_configs = []  # Initialize available configs
        self.assignments_table_frame = None  # Initialize assignments table frame
        
        # Create main window
        self.root = tk.Tk()
        self.root.title(f"PyScope : {system}")
        self.root.state('zoomed')  # Windows fullscreen
        # For Linux/Mac, use: self.root.attributes('-zoomed', True)
        
        apply_dark_theme(self.root)
        self.style = create_dark_style()
        self.create_main_layout()
        self.start_update_thread() #FIXME
        
        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Bind window resize event to recalculate proportions
        self.root.bind('<Configure>', self.on_window_resize)
    
    def log(self, message, level='info'):
        """Log messages using FileHandler's logging system."""
        self.file_handler.log(message, level=level, system_prefix='GUI')
    
    def on_skip_first_fluidics_changed(self):
        """Handle checkbox state change and save to experiment state."""
        try:
            skip_first = self.skip_first_fluidics_var.get()
            
            # Update experiment state
            updates = {'skip_first_fluidics_task': skip_first}
            self.file_handler.update_state(system_prefix='Experiment', updates=updates)
            
            self.log(f"Skip first fluidics task set to: {skip_first}")
            
        except Exception as e:
            self.log(f"Error updating skip first fluidics task: {e}", level='error')
    
    def create_main_layout(self):
        """Create the main layout with all blocks."""
        # Main container
        main_frame = tk.Frame(self.root, bg=GUI_COLORS['background'])
        main_frame.pack(expand=True, fill='both', padx=20, pady=20)
        
        # Create main content area with left and right panels
        content_frame = tk.Frame(main_frame, bg=GUI_COLORS['background'])
        content_frame.pack(expand=True, fill='both')
        
        # Create grid layout for system control blocks (full width now)
        grid_frame = tk.Frame(content_frame, bg=GUI_COLORS['background'])
        grid_frame.pack(expand=True, fill='both')
        grid_frame.grid_propagate(False)
        self.setup_grid_proportions(grid_frame)
        
        # Create blocks in new layout:
        # Left column: Experiment (top), Scope (middle), Fluidics (bottom)
        # Right column: Dynamic panel (spans full height)
        self.create_experiment_block(grid_frame)
        self.create_experimental_setup_block(grid_frame)
        self.create_scope_block(grid_frame)
        self.create_fluidics_block(grid_frame)
        
        # Store reference to grid_frame for resize handling
        self.grid_frame = grid_frame
    
    def setup_grid_proportions(self, grid_frame):
        """Set up grid proportions with dynamic minimum sizes based on window size."""
        # Get current window size
        self.root.update_idletasks()  # Ensure window is fully rendered
        window_width = self.root.winfo_width()
        window_height = self.root.winfo_height()
        
        # Calculate proportional minimum sizes (as percentages of window size)
        # Left column: 25% of window width, minimum 200px
        left_min_width = max(200, int(window_width * 0.25))
        # Right column: 50% of window width, minimum 400px  
        right_min_width = max(400, int(window_width * 0.5))
        # Each row: 20% of window height, minimum 100px
        row_min_height = max(100, int(window_height * 0.2))
        
        # Configure grid weights and minimum sizes
        grid_frame.grid_columnconfigure(0, weight=1, minsize=left_min_width)
        grid_frame.grid_columnconfigure(1, weight=2, minsize=right_min_width)
        grid_frame.grid_rowconfigure(0, weight=1, minsize=row_min_height)
        grid_frame.grid_rowconfigure(1, weight=1, minsize=row_min_height)
        grid_frame.grid_rowconfigure(2, weight=1, minsize=row_min_height)
    
    def on_window_resize(self, event):
        """Handle window resize events to recalculate grid proportions."""
        # Only handle resize events for the main window
        if event.widget == self.root:
            # Debounce rapid resize events
            if hasattr(self, '_resize_timer'):
                self.root.after_cancel(self._resize_timer)
            self._resize_timer = self.root.after(100, self._update_grid_proportions)
    
    def _update_grid_proportions(self):
        """Update grid proportions after window resize."""
        if hasattr(self, 'grid_frame'):
            self.setup_grid_proportions(self.grid_frame)
    
    def create_embedded_panel(self, parent):
        """Create the embedded GUI panel for hosting other GUIs."""
        # Create main container for embedded content (no title)
        self.embedded_frame = tk.Frame(parent, bg=GUI_COLORS['background'], 
                                      relief='sunken', bd=2)
        self.embedded_frame.pack(expand=True, fill='both')
        self.show_welcome_screen()
    
    def show_welcome_screen(self):
        """Show welcome screen in embedded panel."""
        # Clear existing content
        for widget in self.embedded_frame.winfo_children():
            widget.destroy()
        
        # Create welcome content
        welcome_frame = tk.Frame(self.embedded_frame, bg=GUI_COLORS['background'])
        welcome_frame.pack(expand=True, fill='both', padx=20, pady=20)
        
        welcome_label = create_body_label(welcome_frame, "Welcome")
        welcome_label.pack(pady=20)
        
        info_label = create_body_label(welcome_frame, 
                                     "Use the 'Create' button in the Experiment Control\n"
                                     "section to start setting up your experiment.\n\n"
                                     "This panel will show the experiment setup\n"
                                     "interface when you begin.")
        info_label.pack(pady=10)
    
    def save_experiment_info(self):
        """Save experiment info and proceed to next step."""
        try:
            # Get experiment info from the experimental setup panel
            if hasattr(self, 'exp_entry') and hasattr(self, 'user_entry') and hasattr(self, 'project_entry'):
                exp_name = self.exp_entry.get().strip()
                user_name = self.user_entry.get().strip()
                project_name = self.project_entry.get().strip()
                save_path = getattr(self, 'save_path_entry', None)
                save_path = save_path.get().strip() if save_path else getattr(self.experiment, 'save_path', '')
            else:
                # Fallback to system attributes if entries don't exist
                exp_name = getattr(self.experiment, 'experiment_name', '')
                user_name = getattr(self.experiment, 'user_name', '')
                project_name = getattr(self.experiment, 'project_name', '')
                save_path = getattr(self.experiment, 'save_path', '')
            
            if not exp_name:
                self.log("ERROR: Experiment name cannot be blank!", level='warning')
                return
            if not user_name:
                self.log("ERROR: User name cannot be blank!", level='warning')
                return
            if not project_name:
                self.log("ERROR: Project name cannot be blank!", level='warning')
                return
            
            # Update experiment_state for StatePanel display
            updates = {
                'experiment_name': exp_name,
                'user_name': user_name,
                'project_name': project_name,
                'save_path': save_path,
                'system_name': self.system
            }
            self.file_handler.update_state(system_prefix='Experiment',updates=updates)
            
            self.log(f"Experiment info saved: {exp_name} by {user_name} for project {project_name}")
            
            # Update the experiment state display
            self.update_system_state_display('experiment')
            
        except Exception as e:
            self.log(f"Error saving experiment info: {e}", level='warning')
    
    def on_config_type_change(self, event=None):
        """Handle configuration type selection change."""
        selected_type = self.config_type_var.get()
        self.log(f"Positions GUI: Configuration type changed to: '{selected_type}'")
        
        # Hide well selection frame initially
        self.well_selection_frame.pack_forget()
        self.positions_status_label.config(text="")
        
        # Change button to "Create Positions" for immediate position creation
        self.create_btn.config(text="Create Positions", command=self.create_positions_in_setup)
        
        if selected_type in self.available_configs:
            self.load_plate_config(selected_type)
        elif selected_type == 'Custom Grid':
            self.show_custom_grid_inputs()
        elif selected_type == 'Custom Manual':
            self.show_custom_manual_inputs()
        elif selected_type == 'Load Wells From File':
            self.show_load_wells_from_file_inputs()
        elif selected_type == 'Load Positions From File':
            self.show_load_positions_from_file_inputs()
        else:
            self.log(f"Positions GUI: Unknown configuration type: {selected_type}")
    
    def load_plate_config(self, plate_name: str):
        """Load a plate configuration and prepare for position creation."""
        try:
            self.log(f"Positions GUI: Loading plate config for: {plate_name}")
            # Get the directory of the current file
            current_dir = os.path.dirname(os.path.abspath(__file__))
            plates_dir = os.path.join(current_dir, "Plates")
            json_file_path = os.path.join(plates_dir, f"{plate_name}.json")
            
            self.log(f"Positions GUI: Looking for config file: {json_file_path}")
            
            if not os.path.isfile(json_file_path):
                self.positions_status_label.config(text=f"Configuration file not found: {json_file_path}", 
                                               fg=GUI_COLORS['status_error'])
                self.log(f"Positions GUI: Config file not found: {json_file_path}")
                return
            
            # Load the JSON file
            with open(json_file_path, 'r') as f:
                plate_config = json.load(f)
            
            self.log(f"Positions GUI: Loaded plate config with {len(plate_config)} wells")
            
            # Store plate config for position creation
            self.well_selection_frame.plate_config = plate_config
            self.well_selection_frame.plate_name = plate_name
            
            # Show configuration info instead of well selection
            self.positions_status_label.config(text=f"Loaded {len(plate_config)} wells from {plate_name}.json. Click 'Create Positions' to generate positions for all wells.", 
                                          fg=GUI_COLORS['status_success'])
            self.log(f"Positions GUI: Successfully loaded {len(plate_config)} wells from {plate_name}")
            
        except Exception as e:
            self.positions_status_label.config(text=f"Error loading {plate_name}.json: {str(e)}", 
                                          fg=GUI_COLORS['status_error'])
            self.log(f"Positions GUI: Error loading plate config: {e}")
    
    
    def show_custom_grid_inputs(self):
        """Show input fields for custom grid configuration."""
        # Hide well selection frame initially
        self.well_selection_frame.pack_forget()
        
        # Clear existing widgets in well selection frame
        for widget in self.well_selection_frame.winfo_children():
            widget.destroy()
        
        # Create custom grid input frame
        grid_frame = tk.LabelFrame(self.well_selection_frame, 
                                 text="Custom Grid Configuration", 
                                 bg=GUI_COLORS['frame'], 
                                 fg=GUI_COLORS['text'],
                                 font=GUI_FONTS['heading'])
        grid_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Grid parameters section
        grid_params_frame = tk.LabelFrame(grid_frame, 
                                        text="Grid Parameters", 
                                        bg=GUI_COLORS['frame'], 
                                        fg=GUI_COLORS['text'],
                                        font=GUI_FONTS['body'])
        grid_params_frame.pack(fill='x', padx=5, pady=5)
        
        # Grid parameters in a single row
        tk.Label(grid_params_frame, text="Rows:", bg=GUI_COLORS['frame'], fg=GUI_COLORS['text']).grid(row=0, column=0, sticky='w', padx=5, pady=2)
        rows_var = tk.StringVar(value="2") # Preset
        rows_entry = tk.Entry(grid_params_frame, textvariable=rows_var, bg=GUI_COLORS['entry'], fg=GUI_COLORS['text'], insertbackground=GUI_COLORS['text'], width=6)
        rows_entry.grid(row=0, column=1, padx=5, pady=2)
        
        tk.Label(grid_params_frame, text="Columns:", bg=GUI_COLORS['frame'], fg=GUI_COLORS['text']).grid(row=0, column=2, sticky='w', padx=5, pady=2)
        columns_var = tk.StringVar(value="3") # Preset
        columns_entry = tk.Entry(grid_params_frame, textvariable=columns_var, bg=GUI_COLORS['entry'], fg=GUI_COLORS['text'], insertbackground=GUI_COLORS['text'], width=6)
        columns_entry.grid(row=0, column=3, padx=5, pady=2)
        
        tk.Label(grid_params_frame, text="Row Spacing (μm):", bg=GUI_COLORS['frame'], fg=GUI_COLORS['text']).grid(row=0, column=4, sticky='w', padx=5, pady=2)
        row_spacing_var = tk.StringVar(value="1000") # Preset
        row_spacing_entry = tk.Entry(grid_params_frame, textvariable=row_spacing_var, bg=GUI_COLORS['entry'], fg=GUI_COLORS['text'], insertbackground=GUI_COLORS['text'], width=8)
        row_spacing_entry.grid(row=0, column=5, padx=5, pady=2)
        
        tk.Label(grid_params_frame, text="Column Spacing (μm):", bg=GUI_COLORS['frame'], fg=GUI_COLORS['text']).grid(row=0, column=6, sticky='w', padx=5, pady=2)
        column_spacing_var = tk.StringVar(value="1000") # Preset
        column_spacing_entry = tk.Entry(grid_params_frame, textvariable=column_spacing_var, bg=GUI_COLORS['entry'], fg=GUI_COLORS['text'], insertbackground=GUI_COLORS['text'], width=8)
        column_spacing_entry.grid(row=0, column=7, padx=5, pady=2)
        
        # Well geometry section
        well_geometry_frame = tk.LabelFrame(grid_frame, 
                                          text="Well Geometry", 
                                          bg=GUI_COLORS['frame'], 
                                          fg=GUI_COLORS['text'],
                                          font=GUI_FONTS['body'])
        well_geometry_frame.pack(fill='x', padx=5, pady=5)
        
        # Well geometry section - coordinates and shape on one line
        tk.Label(well_geometry_frame, text="Center X (μm):", bg=GUI_COLORS['frame'], fg=GUI_COLORS['text']).grid(row=0, column=0, sticky='w', padx=5, pady=2)
        center_x_var = tk.StringVar(value="0")
        center_x_entry = tk.Entry(well_geometry_frame, textvariable=center_x_var, bg=GUI_COLORS['entry'], fg=GUI_COLORS['text'], insertbackground=GUI_COLORS['text'], width=8)
        center_x_entry.grid(row=0, column=1, padx=5, pady=2)
        
        tk.Label(well_geometry_frame, text="Center Y (μm):", bg=GUI_COLORS['frame'], fg=GUI_COLORS['text']).grid(row=0, column=2, sticky='w', padx=5, pady=2)
        center_y_var = tk.StringVar(value="0")
        center_y_entry = tk.Entry(well_geometry_frame, textvariable=center_y_var, bg=GUI_COLORS['entry'], fg=GUI_COLORS['text'], insertbackground=GUI_COLORS['text'], width=8)
        center_y_entry.grid(row=0, column=3, padx=5, pady=2)
        
        tk.Label(well_geometry_frame, text="Center Z (μm):", bg=GUI_COLORS['frame'], fg=GUI_COLORS['text']).grid(row=0, column=4, sticky='w', padx=5, pady=2)
        center_z_var = tk.StringVar(value="0")
        center_z_entry = tk.Entry(well_geometry_frame, textvariable=center_z_var, bg=GUI_COLORS['entry'], fg=GUI_COLORS['text'], insertbackground=GUI_COLORS['text'], width=8)
        center_z_entry.grid(row=0, column=5, padx=5, pady=2)
        
        # Second row: Shape and dimensions
        tk.Label(well_geometry_frame, text="Shape:", bg=GUI_COLORS['frame'], fg=GUI_COLORS['text']).grid(row=1, column=0, sticky='w', padx=5, pady=2)
        shape_var = tk.StringVar(value="circle")
        shape_dropdown = ttk.Combobox(well_geometry_frame, textvariable=shape_var, values=["circle", "rectangle"], state="readonly", style='Light.TCombobox',width=8)
        shape_dropdown.grid(row=1, column=1, padx=5, pady=2)
        
        # Dimensions section on the same row
        dimensions_frame = tk.LabelFrame(well_geometry_frame, 
                                       text="", 
                                       bg=GUI_COLORS['frame'], 
                                       fg=GUI_COLORS['text'],
                                       font=GUI_FONTS['small'])
        dimensions_frame.grid(row=1, column=2, columnspan=4, sticky='w', padx=5, pady=2)
        
        # Circle dimensions - compact layout
        self.grid_circle_dims_frame = tk.Frame(dimensions_frame, bg=GUI_COLORS['frame'])
        self.grid_circle_dims_frame.pack(fill='x', padx=2, pady=2)
        
        tk.Label(self.grid_circle_dims_frame, text="Radius (μm):", bg=GUI_COLORS['frame'], fg=GUI_COLORS['text']).grid(row=0, column=0, sticky='w', padx=2)
        radius_var = tk.StringVar(value="500")
        radius_entry = tk.Entry(self.grid_circle_dims_frame, textvariable=radius_var, bg=GUI_COLORS['entry'], fg=GUI_COLORS['text'], insertbackground=GUI_COLORS['text'], width=6)
        radius_entry.grid(row=0, column=1, padx=2)
        
        # Rectangle dimensions - compact layout
        self.grid_rect_dims_frame = tk.Frame(dimensions_frame, bg=GUI_COLORS['frame'])
        
        tk.Label(self.grid_rect_dims_frame, text="Width (μm):", bg=GUI_COLORS['frame'], fg=GUI_COLORS['text']).grid(row=0, column=0, sticky='w', padx=2)
        width_var = tk.StringVar(value="500")
        width_entry = tk.Entry(self.grid_rect_dims_frame, textvariable=width_var, bg=GUI_COLORS['entry'], fg=GUI_COLORS['text'], insertbackground=GUI_COLORS['text'], width=6)
        width_entry.grid(row=0, column=1, padx=2)
        
        tk.Label(self.grid_rect_dims_frame, text="Height (μm):", bg=GUI_COLORS['frame'], fg=GUI_COLORS['text']).grid(row=0, column=2, sticky='w', padx=2)
        height_var = tk.StringVar(value="500")
        height_entry = tk.Entry(self.grid_rect_dims_frame, textvariable=height_var, bg=GUI_COLORS['entry'], fg=GUI_COLORS['text'], insertbackground=GUI_COLORS['text'], width=6)
        height_entry.grid(row=0, column=3, padx=2)
        
        tk.Label(self.grid_rect_dims_frame, text="Rotation (deg):", bg=GUI_COLORS['frame'], fg=GUI_COLORS['text']).grid(row=0, column=4, sticky='w', padx=2)
        rotation_var = tk.StringVar(value="0")
        rotation_entry = tk.Entry(self.grid_rect_dims_frame, textvariable=rotation_var, bg=GUI_COLORS['entry'], fg=GUI_COLORS['text'], insertbackground=GUI_COLORS['text'], width=6)
        rotation_entry.grid(row=0, column=5, padx=2)
        
        # Bind shape change to update dimensions visibility
        shape_var.trace('w', lambda *args: self.on_grid_shape_change(shape_var.get()))
        self.on_grid_shape_change("circle")  # Initial call
        
        # Offset correction and save configuration section on same line
        offset_save_frame = tk.LabelFrame(grid_frame, 
                                        text="", 
                                        bg=GUI_COLORS['frame'], 
                                        fg=GUI_COLORS['text'],
                                        font=GUI_FONTS['body'])
        offset_save_frame.pack(fill='x', padx=5, pady=5)
        
        # Offset correction checkbox
        offset_correction_var = tk.BooleanVar(value=True)  # Checked by default
        offset_correction_checkbox = tk.Checkbutton(offset_save_frame,
                                                  text="Positions already corrected for offsets \n (subtract offsets when creating positions)",
                                                  variable=offset_correction_var,
                                                  bg=GUI_COLORS['checkbox_bg'],
                                                  fg=GUI_COLORS['text'],
                                                  selectcolor=GUI_COLORS['checkbox_select'],
                                                  activebackground=GUI_COLORS['checkbox_active'],
                                                  activeforeground=GUI_COLORS['text'],
                                                  font=GUI_FONTS['small'],
                                                  wraplength=300)
        offset_correction_checkbox.grid(row=0, column=0, columnspan=2, sticky='w', padx=5, pady=2)
        
        # Save configuration on the same line
        tk.Label(offset_save_frame, text="Save as:", bg=GUI_COLORS['frame'], fg=GUI_COLORS['text']).grid(row=0, column=2, sticky='w', padx=5, pady=2)
        save_name_var = tk.StringVar(value="")
        save_name_entry = tk.Entry(offset_save_frame, textvariable=save_name_var, bg=GUI_COLORS['entry'], fg=GUI_COLORS['text'], insertbackground=GUI_COLORS['text'], width=30)
        save_name_entry.grid(row=0, column=3, padx=5, pady=2)
        
        # Store variables for later use
        self.well_selection_frame.grid_vars = {
            'rows': rows_var,
            'columns': columns_var,
            'row_spacing': row_spacing_var,
            'column_spacing': column_spacing_var,
            'center_x': center_x_var,
            'center_y': center_y_var,
            'center_z': center_z_var,
            'shape': shape_var,
            'radius': radius_var,
            'width': width_var,
            'height': height_var,
            'rotation': rotation_var,
            'save_name': save_name_var,
            'offset_correction': offset_correction_var
        }
        
        # Add Create Wells button
        create_wells_frame = tk.Frame(grid_frame, bg=GUI_COLORS['frame'])
        create_wells_frame.pack(fill='x', padx=5, pady=10)
        
        create_wells_btn = create_button(create_wells_frame, "Create Wells", 
                                       command=self.generate_custom_grid_wells, bold=True)
        create_wells_btn.pack(side='left')
        
        # Change button text to "Create Positions" for immediate position creation
        self.create_btn.config(text="Create Positions", command=self.create_positions_in_setup)
        
        # Show the grid frame
        self.well_selection_frame.pack(fill='both', expand=True, pady=(0, 10))
        
        self.positions_status_label.config(text="Custom grid configuration loaded. Fill in the parameters and click 'Create Wells' to generate wells, then 'Create Positions' to create positions.", 
                                      fg=GUI_COLORS['status_info'])
    
    def show_custom_manual_inputs(self):
        """Show input fields for custom manual well configuration."""
        # Clear existing widgets in well selection frame
        for widget in self.well_selection_frame.winfo_children():
            widget.destroy()
        
        # Initialize manual wells storage
        self.well_selection_frame.manual_wells = {}
        
        # Create main manual configuration frame
        manual_frame = tk.LabelFrame(self.well_selection_frame, 
                                   text="Custom Manual Configuration", 
                                   bg=GUI_COLORS['frame'], 
                                   fg=GUI_COLORS['text'],
                                   font=GUI_FONTS['heading'])
        manual_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Configuration name section
        name_frame = tk.Frame(manual_frame, bg=GUI_COLORS['frame'])
        name_frame.pack(fill='x', pady=(0, 10))
        
        tk.Label(name_frame, text="Configuration Name:", bg=GUI_COLORS['frame'], 
                fg=GUI_COLORS['text'], font=GUI_FONTS['small']).pack(side='left')
        self.config_name_var = tk.StringVar()
        self.config_name_entry = tk.Entry(name_frame, textvariable=self.config_name_var,
                                         bg=GUI_COLORS['entry'], fg=GUI_COLORS['text'],
                                         font=GUI_FONTS['entry'])
        self.config_name_entry.pack(side='left', fill='x', expand=True, padx=(10, 0))
        # Leave config name empty by default
        
        # Add well section
        add_well_frame = tk.LabelFrame(manual_frame, text="Add New Well", 
                                     bg=GUI_COLORS['frame'], fg=GUI_COLORS['text'],
                                     font=GUI_FONTS['small'])
        add_well_frame.pack(fill='x', pady=(0, 10))
        
        # Well name and Add Well button on same line
        well_name_frame = tk.Frame(add_well_frame, bg=GUI_COLORS['frame'])
        well_name_frame.pack(fill='x', padx=10, pady=5)
        
        tk.Label(well_name_frame, text="Well Name:", bg=GUI_COLORS['frame'], 
                fg=GUI_COLORS['text'], font=GUI_FONTS['small']).pack(side='left')
        self.well_name_var = tk.StringVar()
        self.well_name_entry = tk.Entry(well_name_frame, textvariable=self.well_name_var,
                                       bg=GUI_COLORS['entry'], fg=GUI_COLORS['text'],
                                       font=GUI_FONTS['entry'])
        self.well_name_entry.pack(side='left', fill='x', expand=True, padx=(10, 10))
        
        # Add Well button on the right
        add_btn = create_button(well_name_frame, "Add Well", command=self.add_manual_well)
        add_btn.pack(side='right')
        
        # Main input frame with all inputs on one line
        main_input_frame = tk.Frame(add_well_frame, bg=GUI_COLORS['frame'])
        main_input_frame.pack(fill='x', padx=10, pady=5)
        
        # Center coordinates
        center_frame = tk.Frame(main_input_frame, bg=GUI_COLORS['frame'])
        center_frame.pack(side='left', fill='x', expand=True, padx=(0, 5))
        
        tk.Label(center_frame, text="Center (X, Y, Z):", bg=GUI_COLORS['frame'], 
                fg=GUI_COLORS['text'], font=GUI_FONTS['small']).pack(anchor='w')
        
        center_inputs_frame = tk.Frame(center_frame, bg=GUI_COLORS['frame'])
        center_inputs_frame.pack(fill='x', pady=(2, 0))
        
        self.center_x_var = tk.StringVar(value="0")
        self.center_y_var = tk.StringVar(value="0")
        self.center_z_var = tk.StringVar(value="0")
        
        tk.Entry(center_inputs_frame, textvariable=self.center_x_var, width=8,
                bg=GUI_COLORS['entry'], fg=GUI_COLORS['text'], font=GUI_FONTS['entry']).pack(side='left', padx=(0, 5))
        tk.Entry(center_inputs_frame, textvariable=self.center_y_var, width=8,
                bg=GUI_COLORS['entry'], fg=GUI_COLORS['text'], font=GUI_FONTS['entry']).pack(side='left', padx=(0, 5))
        tk.Entry(center_inputs_frame, textvariable=self.center_z_var, width=8,
                bg=GUI_COLORS['entry'], fg=GUI_COLORS['text'], font=GUI_FONTS['entry']).pack(side='left')
        
        # Shape selection
        shape_frame = tk.Frame(main_input_frame, bg=GUI_COLORS['frame'])
        shape_frame.pack(side='left', fill='x', expand=True, padx=5)
        
        tk.Label(shape_frame, text="Shape:", bg=GUI_COLORS['frame'], 
                fg=GUI_COLORS['text'], font=GUI_FONTS['small']).pack(anchor='w')
        
        self.shape_var = tk.StringVar(value="circle")
        shape_radio_frame = tk.Frame(shape_frame, bg=GUI_COLORS['frame'])
        shape_radio_frame.pack(fill='x', pady=(2, 0))
        
        tk.Radiobutton(shape_radio_frame, text="Circle", variable=self.shape_var, value="circle",
                      bg=GUI_COLORS['frame'], fg=GUI_COLORS['text'], 
                      selectcolor=GUI_COLORS['checkbox_select'],
                      activebackground=GUI_COLORS['frame'], activeforeground=GUI_COLORS['text'],
                      font=GUI_FONTS['small']).pack(side='left', padx=(0, 10))
        tk.Radiobutton(shape_radio_frame, text="Rectangle", variable=self.shape_var, value="rectangle",
                      bg=GUI_COLORS['frame'], fg=GUI_COLORS['text'], 
                      selectcolor=GUI_COLORS['checkbox_select'],
                      activebackground=GUI_COLORS['frame'], activeforeground=GUI_COLORS['text'],
                      font=GUI_FONTS['small']).pack(side='left')
        
        # Dimensions
        dims_frame = tk.Frame(main_input_frame, bg=GUI_COLORS['frame'])
        dims_frame.pack(side='left', fill='x', expand=True, padx=5)
        
        tk.Label(dims_frame, text="Dimensions:", bg=GUI_COLORS['frame'], 
                fg=GUI_COLORS['text'], font=GUI_FONTS['small']).pack(anchor='w')
        
        # Circle dimensions
        self.circle_dims_frame = tk.Frame(dims_frame, bg=GUI_COLORS['frame'])
        self.circle_dims_frame.pack(fill='x', pady=(2, 0))
        
        tk.Label(self.circle_dims_frame, text="Radius:", bg=GUI_COLORS['frame'], 
                fg=GUI_COLORS['text'], font=GUI_FONTS['small']).pack(side='left')
        self.radius_var = tk.StringVar(value="500")
        tk.Entry(self.circle_dims_frame, textvariable=self.radius_var, width=10,
                bg=GUI_COLORS['entry'], fg=GUI_COLORS['text'], font=GUI_FONTS['entry']).pack(side='left', padx=(5, 0))
        
        # Rectangle dimensions
        self.rect_dims_frame = tk.Frame(dims_frame, bg=GUI_COLORS['frame'])
        
        rect_dims_inner = tk.Frame(self.rect_dims_frame, bg=GUI_COLORS['frame'])
        rect_dims_inner.pack(fill='x')
        
        tk.Label(rect_dims_inner, text="Width:", bg=GUI_COLORS['frame'], 
                fg=GUI_COLORS['text'], font=GUI_FONTS['small']).pack(side='left')
        self.width_var = tk.StringVar(value="1000")
        tk.Entry(rect_dims_inner, textvariable=self.width_var, width=8,
                bg=GUI_COLORS['entry'], fg=GUI_COLORS['text'], font=GUI_FONTS['entry']).pack(side='left', padx=(5, 10))
        
        tk.Label(rect_dims_inner, text="Height:", bg=GUI_COLORS['frame'], 
                fg=GUI_COLORS['text'], font=GUI_FONTS['small']).pack(side='left')
        self.height_var = tk.StringVar(value="800")
        tk.Entry(rect_dims_inner, textvariable=self.height_var, width=8,
                bg=GUI_COLORS['entry'], fg=GUI_COLORS['text'], font=GUI_FONTS['entry']).pack(side='left', padx=(5, 0))
        
        # Rotation (for rectangles)
        rotation_frame = tk.Frame(main_input_frame, bg=GUI_COLORS['frame'])
        rotation_frame.pack(side='right', fill='x', expand=True, padx=(5, 0))
        
        tk.Label(rotation_frame, text="Rotation (degrees):", bg=GUI_COLORS['frame'], 
                fg=GUI_COLORS['text'], font=GUI_FONTS['small']).pack(anchor='w')
        self.rotation_var = tk.StringVar(value="0")
        tk.Entry(rotation_frame, textvariable=self.rotation_var, width=10,
                bg=GUI_COLORS['entry'], fg=GUI_COLORS['text'], font=GUI_FONTS['entry']).pack(anchor='w', pady=(2, 0))
        
        # Offset correction option
        self.offset_correction_var = tk.BooleanVar(value=False)
        offset_correction_checkbox = tk.Checkbutton(main_input_frame,
                                                  text="Apply offset correction",
                                                  variable=self.offset_correction_var,
                                                  bg=GUI_COLORS['checkbox_bg'],
                                                  fg=GUI_COLORS['text'],
                                                  selectcolor=GUI_COLORS['checkbox_select'],
                                                  activebackground=GUI_COLORS['checkbox_active'],
                                                  activeforeground=GUI_COLORS['text'],
                                                  font=GUI_FONTS['small'])
        offset_correction_checkbox.pack(anchor='w', pady=(5, 0))
        
        
        # Bind shape change to update dimensions visibility
        self.shape_var.trace('w', self.on_shape_change)
        self.on_shape_change()  # Initial call
        
        # Wells list frame
        wells_list_frame = tk.LabelFrame(manual_frame, text="Added Wells", 
                                       bg=GUI_COLORS['frame'], fg=GUI_COLORS['text'],
                                       font=GUI_FONTS['small'])
        wells_list_frame.pack(fill='both', expand=True, pady=(10, 0))
        
        # Scrollable frame for wells list
        self.wells_list_canvas = tk.Canvas(wells_list_frame, bg=GUI_COLORS['frame'], height=100)
        self.wells_list_scrollbar = tk.Scrollbar(wells_list_frame, orient="vertical", command=self.wells_list_canvas.yview)
        self.wells_list_scrollable_frame = tk.Frame(self.wells_list_canvas, bg=GUI_COLORS['frame'])
        
        self.wells_list_scrollable_frame.bind(
            "<Configure>",
            lambda e: self.wells_list_canvas.configure(scrollregion=self.wells_list_canvas.bbox("all"))
        )
        
        self.wells_list_canvas.create_window((0, 0), window=self.wells_list_scrollable_frame, anchor="nw")
        self.wells_list_canvas.configure(yscrollcommand=self.wells_list_scrollbar.set)
        
        self.wells_list_canvas.pack(side="left", fill="both", expand=True)
        self.wells_list_scrollbar.pack(side="right", fill="y")
        
        # Add Create Wells button
        create_wells_frame = tk.Frame(manual_frame, bg=GUI_COLORS['frame'])
        create_wells_frame.pack(fill='x', padx=10, pady=10)
        
        create_wells_btn = create_button(create_wells_frame, "Create Wells", 
                                       command=self.generate_manual_wells, bold=True)
        create_wells_btn.pack(side='left')
        
        # Change button text to "Create Positions" for immediate position creation
        self.create_btn.config(text="Create Positions", command=self.create_positions_in_setup)
        
        self.well_selection_frame.pack(fill='both', expand=True, pady=(0, 10))
        self.positions_status_label.config(text="Add wells manually by specifying their properties. Click 'Create Wells' to generate wells, then 'Create Positions' to create positions.", 
                                      fg=GUI_COLORS['status_info'])
    
    def show_load_wells_from_file_inputs(self):
        """Show input fields for loading wells from position files."""
        # Clear existing widgets in well selection frame
        for widget in self.well_selection_frame.winfo_children():
            widget.destroy()
        
        # Initialize file wells storage
        self.well_selection_frame.file_wells = {}
        
        # Create main file configuration frame
        file_frame = tk.LabelFrame(self.well_selection_frame, 
                                 text="Load Wells From Files", 
                                 bg=GUI_COLORS['frame'], 
                                 fg=GUI_COLORS['text'],
                                 font=GUI_FONTS['heading'])
        file_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Instructions
        instructions_frame = tk.Frame(file_frame, bg=GUI_COLORS['frame'])
        instructions_frame.pack(fill='x', pady=(0, 10))
        
        instructions_label = tk.Label(instructions_frame, 
                                    text="Add wells by specifying a well name and the path to a position file (.pos or .csv).\n"
                                         "Each well will load positions from its corresponding file.",
                                    bg=GUI_COLORS['frame'], 
                                    fg=GUI_COLORS['text_secondary'], 
                                    font=GUI_FONTS['small'],
                                    justify='left')
        instructions_label.pack(anchor='w')
        
        # Add well section
        add_well_frame = tk.LabelFrame(file_frame, text="Add New Well", 
                                     bg=GUI_COLORS['frame'], fg=GUI_COLORS['text'],
                                     font=GUI_FONTS['small'])
        add_well_frame.pack(fill='x', pady=(0, 10))
        
        # Well name and Add Well button on same line
        well_name_frame = tk.Frame(add_well_frame, bg=GUI_COLORS['frame'])
        well_name_frame.pack(fill='x', padx=10, pady=5)
        
        tk.Label(well_name_frame, text="Well Name:", bg=GUI_COLORS['frame'], 
                fg=GUI_COLORS['text'], font=GUI_FONTS['small']).pack(side='left')
        self.file_well_name_var = tk.StringVar()
        self.file_well_name_entry = tk.Entry(well_name_frame, textvariable=self.file_well_name_var,
                                           bg=GUI_COLORS['entry'], fg=GUI_COLORS['text'],
                                           font=GUI_FONTS['entry'])
        self.file_well_name_entry.pack(side='left', fill='x', expand=True, padx=(10, 10))
        
        # Add Well button on the right
        add_btn = create_button(well_name_frame, "Add Well", command=self.add_file_well)
        add_btn.pack(side='right')
        
        # File path input frame
        file_path_frame = tk.Frame(add_well_frame, bg=GUI_COLORS['frame'])
        file_path_frame.pack(fill='x', padx=10, pady=5)
        
        tk.Label(file_path_frame, text="File Path:", bg=GUI_COLORS['frame'], 
                fg=GUI_COLORS['text'], font=GUI_FONTS['small']).pack(anchor='w')
        
        path_input_frame = tk.Frame(file_path_frame, bg=GUI_COLORS['frame'])
        path_input_frame.pack(fill='x', pady=(2, 0))
        
        self.file_path_var = tk.StringVar()
        self.file_path_entry = tk.Entry(path_input_frame, textvariable=self.file_path_var,
                                      bg=GUI_COLORS['entry'], fg=GUI_COLORS['text'],
                                      font=GUI_FONTS['entry'])
        self.file_path_entry.pack(side='left', fill='x', expand=True)
        
        browse_btn = create_button(path_input_frame, "Browse", 
                                 command=self.browse_file_path)
        browse_btn.pack(side='right', padx=(5, 0))
        
        # Wells list frame
        wells_list_frame = tk.LabelFrame(file_frame, text="Added Wells", 
                                       bg=GUI_COLORS['frame'], fg=GUI_COLORS['text'],
                                       font=GUI_FONTS['small'])
        wells_list_frame.pack(fill='both', expand=True, pady=(10, 0))
        
        # Scrollable frame for wells list
        self.file_wells_list_canvas = tk.Canvas(wells_list_frame, bg=GUI_COLORS['frame'], height=100)
        self.file_wells_list_scrollbar = tk.Scrollbar(wells_list_frame, orient="vertical", command=self.file_wells_list_canvas.yview)
        self.file_wells_list_scrollable_frame = tk.Frame(self.file_wells_list_canvas, bg=GUI_COLORS['frame'])
        
        self.file_wells_list_scrollable_frame.bind(
            "<Configure>",
            lambda e: self.file_wells_list_canvas.configure(scrollregion=self.file_wells_list_canvas.bbox("all"))
        )
        
        self.file_wells_list_canvas.create_window((0, 0), window=self.file_wells_list_scrollable_frame, anchor="nw")
        self.file_wells_list_canvas.configure(yscrollcommand=self.file_wells_list_scrollbar.set)
        
        self.file_wells_list_canvas.pack(side="left", fill="both", expand=True)
        self.file_wells_list_scrollbar.pack(side="right", fill="y")
        
        # Add Create Wells button
        create_wells_frame = tk.Frame(file_frame, bg=GUI_COLORS['frame'])
        create_wells_frame.pack(fill='x', padx=10, pady=10)
        
        create_wells_btn = create_button(create_wells_frame, "Create Wells", 
                                       command=self.generate_file_wells, bold=True)
        create_wells_btn.pack(side='left')
        
        # Change button text to "Create Positions" for immediate position creation
        self.create_btn.config(text="Create Positions", command=self.create_positions_in_setup)
        
        self.well_selection_frame.pack(fill='both', expand=True, pady=(0, 10))
        self.positions_status_label.config(text="Add wells by specifying well names and file paths. Click 'Create Wells' to generate wells, then 'Create Positions' to create positions.", 
                                      fg=GUI_COLORS['status_info'])
    
    def show_load_positions_from_file_inputs(self):
        """Show input fields for loading positions directly from a CSV file."""
        # Clear existing widgets in well selection frame
        for widget in self.well_selection_frame.winfo_children():
            widget.destroy()
        
        # Create main positions file configuration frame
        positions_file_frame = tk.LabelFrame(self.well_selection_frame, 
                                          text="Load Positions From File", 
                                          bg=GUI_COLORS['frame'], 
                                          fg=GUI_COLORS['text'],
                                          font=GUI_FONTS['heading'])
        positions_file_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Instructions
        instructions_frame = tk.Frame(positions_file_frame, bg=GUI_COLORS['frame'])
        instructions_frame.pack(fill='x', pady=(0, 10))
        
        instructions_label = tk.Label(instructions_frame, 
                                    text="Select a positions.csv file to load positions directly.\n"
                                         "The file should contain columns: position_name, well, X, Y, Z",
                                    bg=GUI_COLORS['frame'], 
                                    fg=GUI_COLORS['text_secondary'], 
                                    font=GUI_FONTS['small'],
                                    justify='left')
        instructions_label.pack(anchor='w')
        
        # File selection section
        file_selection_frame = tk.LabelFrame(positions_file_frame, text="Select Positions File", 
                                           bg=GUI_COLORS['frame'], fg=GUI_COLORS['text'],
                                           font=GUI_FONTS['small'])
        file_selection_frame.pack(fill='x', pady=(0, 10))
        
        # File path input frame
        file_path_frame = tk.Frame(file_selection_frame, bg=GUI_COLORS['frame'])
        file_path_frame.pack(fill='x', padx=10, pady=10)
        
        tk.Label(file_path_frame, text="Positions File:", bg=GUI_COLORS['frame'], 
                fg=GUI_COLORS['text'], font=GUI_FONTS['small']).pack(anchor='w')
        
        path_input_frame = tk.Frame(file_path_frame, bg=GUI_COLORS['frame'])
        path_input_frame.pack(fill='x', pady=(5, 0))
        
        self.positions_file_path_var = tk.StringVar()
        self.positions_file_path_entry = tk.Entry(path_input_frame, textvariable=self.positions_file_path_var,
                                                bg=GUI_COLORS['entry'], fg=GUI_COLORS['text'],
                                                font=GUI_FONTS['entry'])
        self.positions_file_path_entry.pack(side='left', fill='x', expand=True)
        
        browse_positions_btn = create_button(path_input_frame, "Browse", 
                                           command=self.browse_positions_file)
        browse_positions_btn.pack(side='right', padx=(5, 0))
        
        # File info display frame
        self.file_info_frame = tk.Frame(positions_file_frame, bg=GUI_COLORS['frame'])
        self.file_info_frame.pack(fill='x', pady=(0, 10))
        
        # Load button
        load_button_frame = tk.Frame(positions_file_frame, bg=GUI_COLORS['frame'])
        load_button_frame.pack(fill='x', padx=10, pady=10)
        
        load_positions_btn = create_button(load_button_frame, "Load Positions", 
                                         command=self.load_positions_from_file, bold=True)
        load_positions_btn.pack(side='left')
        
        # Change button text to "Create Positions" for immediate position creation
        self.create_btn.config(text="Create Positions", command=self.create_positions_in_setup)
        
        self.well_selection_frame.pack(fill='both', expand=True, pady=(0, 10))
        self.positions_status_label.config(text="Select a positions.csv file and click 'Load Positions' to load positions directly.", 
                                      fg=GUI_COLORS['status_info'])
    
    def on_shape_change(self, *args):
        """Handle shape selection change to show/hide appropriate dimension fields."""
        shape = self.shape_var.get()
        if shape == "circle":
            self.circle_dims_frame.pack(fill='x', pady=(2, 0))
            self.rect_dims_frame.pack_forget()
        else:  # rectangle
            self.circle_dims_frame.pack_forget()
            self.rect_dims_frame.pack(fill='x', pady=(2, 0))
    
    def on_grid_shape_change(self, shape):
        """Handle shape selection change for custom grid to show/hide appropriate dimension fields."""
        if shape == "circle":
            self.grid_circle_dims_frame.pack(fill='x', padx=5, pady=5)
            self.grid_rect_dims_frame.pack_forget()
        else:  # rectangle
            self.grid_circle_dims_frame.pack_forget()
            self.grid_rect_dims_frame.pack(fill='x', padx=5, pady=5)
    
    def add_manual_well(self):
        """Add a manually configured well to the list."""
        try:
            # Get well name
            well_name = self.well_name_var.get().strip()
            if not well_name:
                self.positions_status_label.config(text="Please enter a well name.", 
                                              fg=GUI_COLORS['status_error'])
                return
            
            # Check for duplicate names
            if well_name in self.well_selection_frame.manual_wells:
                self.positions_status_label.config(text=f"Well '{well_name}' already exists.", 
                                              fg=GUI_COLORS['status_error'])
                return
            
            # Get center coordinates
            try:
                center_x = float(self.center_x_var.get())
                center_y = float(self.center_y_var.get())
                center_z = float(self.center_z_var.get())
            except ValueError:
                self.positions_status_label.config(text="Please enter valid numeric values for center coordinates.", 
                                              fg=GUI_COLORS['status_error'])
                return
            
            # Get shape and dimensions
            shape = self.shape_var.get()
            if shape == "circle":
                try:
                    radius = float(self.radius_var.get())
                    if radius <= 0:
                        raise ValueError("Radius must be positive")
                    dimensions = {"radius": radius}
                except ValueError:
                    self.positions_status_label.config(text="Please enter a valid positive radius.", 
                                                  fg=GUI_COLORS['status_error'])
                    return
            else:  # rectangle
                try:
                    width = float(self.width_var.get())
                    height = float(self.height_var.get())
                    rotation = float(self.rotation_var.get())
                    if width <= 0 or height <= 0:
                        raise ValueError("Width and height must be positive")
                    dimensions = {"width": width, "height": height}
                    if rotation != 0:
                        dimensions["rotation"] = rotation
                except ValueError:
                    self.positions_status_label.config(text="Please enter valid numeric values for dimensions.", 
                                                  fg=GUI_COLORS['status_error'])
                    return
            
            # Create well configuration
            well_config = {
                "center": {"X": center_x, "Y": center_y, "Z": center_z},
                "shape": shape,
                "dimensions": dimensions
            }
            
            # Add offset correction flag if enabled
            if self.offset_correction_var.get():
                well_config["apply_offset_correction"] = True
            
            # Add to manual wells
            self.well_selection_frame.manual_wells[well_name] = well_config
            
            # Update wells list display
            self.update_wells_list_display()
            
            # Clear form for next well
            self.well_name_var.set("")
            self.center_x_var.set("0")
            self.center_y_var.set("0")
            self.center_z_var.set("0")
            self.radius_var.set("500")
            self.width_var.set("1000")
            self.height_var.set("800")
            self.rotation_var.set("0")
            
            self.positions_status_label.config(text=f"Added well '{well_name}'. Total wells: {len(self.well_selection_frame.manual_wells)}", 
                                          fg=GUI_COLORS['status_success'])
            
        except Exception as e:
            self.positions_status_label.config(text=f"Error adding well: {str(e)}", 
                                          fg=GUI_COLORS['status_error'])
            self.log(f"Error adding manual well: {e}", level='error')
    
    def update_wells_list_display(self):
        """Update the display of added wells in the scrollable frame."""
        # Clear existing widgets
        for widget in self.wells_list_scrollable_frame.winfo_children():
            widget.destroy()
        
        # Add wells
        for i, (well_name, well_config) in enumerate(self.well_selection_frame.manual_wells.items()):
            well_frame = tk.Frame(self.wells_list_scrollable_frame, bg=GUI_COLORS['frame'])
            well_frame.pack(fill='x', padx=5, pady=2)
            
            # Well name and properties
            info_text = f"{well_name}: {well_config['shape']} at ({well_config['center']['X']:.0f}, {well_config['center']['Y']:.0f}, {well_config['center']['Z']:.0f})"
            if well_config['shape'] == 'circle':
                info_text += f", radius={well_config['dimensions']['radius']:.0f}"
            else:
                info_text += f", {well_config['dimensions']['width']:.0f}x{well_config['dimensions']['height']:.0f}"
                if 'rotation' in well_config['dimensions']:
                    info_text += f", rot={well_config['dimensions']['rotation']:.0f}°"
            
            tk.Label(well_frame, text=info_text, bg=GUI_COLORS['frame'], 
                    fg=GUI_COLORS['text'], font=GUI_FONTS['small']).pack(side='left')
            
            # Remove button
            remove_btn = tk.Button(well_frame, text="Remove", 
                                 command=lambda name=well_name: self.remove_manual_well(name),
                                 bg=GUI_COLORS['button'], fg=GUI_COLORS['text'],
                                 font=GUI_FONTS['small'], relief='flat')
            remove_btn.pack(side='right')
    
    def remove_manual_well(self, well_name):
        """Remove a well from the manual wells list."""
        if well_name in self.well_selection_frame.manual_wells:
            del self.well_selection_frame.manual_wells[well_name]
            self.update_wells_list_display()
            self.positions_status_label.config(text=f"Removed well '{well_name}'. Total wells: {len(self.well_selection_frame.manual_wells)}", 
                                          fg=GUI_COLORS['status_info'])
    
    def generate_manual_wells(self):
        """Generate wells from manual configuration and proceed to well selection."""
        try:
            if not self.well_selection_frame.manual_wells:
                self.positions_status_label.config(text="No wells to generate. Add at least one well first.", 
                                              fg=GUI_COLORS['status_error'])
                return
            
            # Save configuration if name is provided
            config_name = self.config_name_var.get().strip()
            if config_name:
                try:
                    # Create plates directory if it doesn't exist
                    plates_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Plates")
                    os.makedirs(plates_dir, exist_ok=True)
                    
                    # Save configuration
                    config_file = os.path.join(plates_dir, f"{config_name}.json")
                    with open(config_file, 'w') as f:
                        json.dump(self.well_selection_frame.manual_wells, f, indent=2)
                    
                    self.log(f"Manual configuration saved: {config_file}")
                except Exception as e:
                    self.positions_status_label.config(text=f"Error saving configuration: {str(e)}", 
                                                  fg=GUI_COLORS['status_error'])
                    self.log(f"Error saving manual config: {e}", level='error')
                    return
            
            # Create positions from manual wells
            positions_obj = Positions(
                fov_info=self.scope.fov_info,
                offsets=self.scope.offsets,
                axis_mapping=self.scope.axis_mapping,
                limits=self.scope.limits,
                save_dir=self.file_handler.system_state_dir
            )
            
            for well_name, well_config in self.well_selection_frame.manual_wells.items():
                positions_obj.add_well(
                    name=well_name,
                    well_info=well_config,
                    apply_offset_correction=well_config.get('apply_offset_correction', False)
                )
            
            # Store the generated wells for later position creation
            self.well_selection_frame.generated_wells = self.well_selection_frame.manual_wells.copy()
            
            self.positions_status_label.config(text=f"Successfully generated {len(self.well_selection_frame.manual_wells)} wells. Click 'Create Positions' to create positions for all wells.", 
                                          fg=GUI_COLORS['status_success'])
            
        except Exception as e:
            self.positions_status_label.config(text=f"Error generating wells: {str(e)}", 
                                          fg=GUI_COLORS['status_error'])
            self.log(f"Error generating manual wells: {e}", level='error')
    
    def add_file_well(self):
        """Add a well with file path to the list."""
        try:
            # Get well name
            well_name = self.file_well_name_var.get().strip()
            if not well_name:
                self.positions_status_label.config(text="Please enter a well name.", 
                                              fg=GUI_COLORS['status_error'])
                return
            
            # Check for duplicate names
            if well_name in self.well_selection_frame.file_wells:
                self.positions_status_label.config(text=f"Well '{well_name}' already exists.", 
                                              fg=GUI_COLORS['status_error'])
                return
            
            # Get file path
            file_path = self.file_path_var.get().strip()
            if not file_path:
                self.positions_status_label.config(text="Please enter a file path.", 
                                              fg=GUI_COLORS['status_error'])
                return
            
            # Validate file exists
            if not os.path.exists(file_path):
                self.positions_status_label.config(text=f"File does not exist: {file_path}", 
                                              fg=GUI_COLORS['status_error'])
                return
            
            # Validate file extension
            file_extension = os.path.splitext(file_path)[1].lower()
            if file_extension not in ['.pos', '.csv']:
                self.positions_status_label.config(text=f"Unsupported file type: {file_extension}. Supported types: .pos, .csv", 
                                              fg=GUI_COLORS['status_error'])
                return
            
            # Add to file wells
            self.well_selection_frame.file_wells[well_name] = file_path
            
            # Update wells list display
            self.update_file_wells_list_display()
            
            # Clear form for next well
            self.file_well_name_var.set("")
            self.file_path_var.set("")
            
            self.positions_status_label.config(text=f"Added well '{well_name}' with file '{os.path.basename(file_path)}'. Total wells: {len(self.well_selection_frame.file_wells)}", 
                                          fg=GUI_COLORS['status_success'])
            
        except Exception as e:
            self.positions_status_label.config(text=f"Error adding well: {str(e)}", 
                                          fg=GUI_COLORS['status_error'])
            self.log(f"Error adding file well: {e}", level='error')
    
    def update_file_wells_list_display(self):
        """Update the display of added file wells in the scrollable frame."""
        # Clear existing widgets
        for widget in self.file_wells_list_scrollable_frame.winfo_children():
            widget.destroy()
        
        # Add wells
        for i, (well_name, file_path) in enumerate(self.well_selection_frame.file_wells.items()):
            well_frame = tk.Frame(self.file_wells_list_scrollable_frame, bg=GUI_COLORS['frame'])
            well_frame.pack(fill='x', padx=5, pady=2)
            
            # Well name and file info
            file_name = os.path.basename(file_path)
            file_ext = os.path.splitext(file_path)[1].upper()
            info_text = f"{well_name}: {file_name} ({file_ext})"
            
            tk.Label(well_frame, text=info_text, bg=GUI_COLORS['frame'], 
                    fg=GUI_COLORS['text'], font=GUI_FONTS['small']).pack(side='left')
            
            # Remove button
            remove_btn = tk.Button(well_frame, text="Remove", 
                                 command=lambda name=well_name: self.remove_file_well(name),
                                 bg=GUI_COLORS['button'], fg=GUI_COLORS['text'],
                                 font=GUI_FONTS['small'], relief='flat')
            remove_btn.pack(side='right')
    
    def remove_file_well(self, well_name):
        """Remove a well from the file wells list."""
        if well_name in self.well_selection_frame.file_wells:
            del self.well_selection_frame.file_wells[well_name]
            self.update_file_wells_list_display()
            self.positions_status_label.config(text=f"Removed well '{well_name}'. Total wells: {len(self.well_selection_frame.file_wells)}", 
                                          fg=GUI_COLORS['status_info'])
    
    def browse_file_path(self):
        """Open file browser to select position file."""
        from tkinter import filedialog
        file_path = filedialog.askopenfilename(
            title="Select Position File",
            filetypes=[
                ("Position files", "*.pos *.csv"),
                ("Micro-Manager files", "*.pos"),
                ("CSV files", "*.csv"),
                ("All files", "*.*")
            ],
            initialdir=os.getcwd()
        )
        if file_path:
            self.file_path_var.set(file_path)
            self.log(f"Selected file: {file_path}")
    
    def generate_file_wells(self):
        """Generate wells from file configuration and proceed to position creation."""
        try:
            if not self.well_selection_frame.file_wells:
                self.positions_status_label.config(text="No wells to generate. Add at least one well first.", 
                                              fg=GUI_COLORS['status_error'])
                return
            
            # Store the file wells for later position creation
            self.well_selection_frame.generated_file_wells = self.well_selection_frame.file_wells.copy()
            self.well_selection_frame.config_type = 'Load Wells From File'
            
            self.positions_status_label.config(text=f"Successfully prepared {len(self.well_selection_frame.file_wells)} wells for position loading. Click 'Create Positions' to load positions from files.", 
                                          fg=GUI_COLORS['status_success'])
            
        except Exception as e:
            self.positions_status_label.config(text=f"Error preparing wells: {str(e)}", 
                                          fg=GUI_COLORS['status_error'])
            self.log(f"Error generating file wells: {e}", level='error')
    
    def browse_positions_file(self):
        """Open file browser to select positions CSV file."""
        from tkinter import filedialog
        file_path = filedialog.askopenfilename(
            title="Select Positions CSV File",
            filetypes=[
                ("CSV files", "*.csv"),
                ("All files", "*.*")
            ],
            initialdir=os.getcwd()
        )
        if file_path:
            self.positions_file_path_var.set(file_path)
            self.log(f"Selected positions file: {file_path}")
            self.update_positions_file_info(file_path)
    
    def update_positions_file_info(self, file_path):
        """Update the file info display with details about the selected file."""
        try:
            # Clear existing info widgets
            for widget in self.file_info_frame.winfo_children():
                widget.destroy()
            
            if not os.path.exists(file_path):
                return
            
            # Read the CSV file to get info
            df = pd.read_csv(file_path)
            
            # Create info display
            info_text = f"File: {os.path.basename(file_path)}\n"
            info_text += f"Positions: {len(df)}\n"
            
            if 'well' in df.columns:
                unique_wells = df['well'].unique()
                info_text += f"Wells: {len(unique_wells)} ({', '.join(unique_wells[:5])}"
                if len(unique_wells) > 5:
                    info_text += f"..."
                info_text += ")\n"
            
            # Check required columns
            required_columns = ['position_name', 'X', 'Y', 'Z']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                info_text += f"⚠️ Missing columns: {', '.join(missing_columns)}"
            else:
                info_text += "✅ All required columns present"
            
            info_label = tk.Label(self.file_info_frame, text=info_text,
                                bg=GUI_COLORS['frame'], fg=GUI_COLORS['text'],
                                font=GUI_FONTS['small'], justify='left')
            info_label.pack(anchor='w', padx=10, pady=5)
            
        except Exception as e:
            self.log(f"Error reading positions file info: {e}", level='warning')
    
    def load_positions_from_file(self):
        """Load positions directly from the selected CSV file."""
        try:
            file_path = self.positions_file_path_var.get().strip()
            if not file_path:
                self.positions_status_label.config(text="Please select a positions file.", 
                                              fg=GUI_COLORS['status_error'])
                return
            
            if not os.path.exists(file_path):
                self.positions_status_label.config(text=f"File does not exist: {file_path}", 
                                              fg=GUI_COLORS['status_error'])
                return
            
            # Validate file extension
            file_extension = os.path.splitext(file_path)[1].lower()
            if file_extension != '.csv':
                self.positions_status_label.config(text=f"File must be a CSV file (.csv), got: {file_extension}", 
                                              fg=GUI_COLORS['status_error'])
                return
            
            # Read the CSV file
            df = pd.read_csv(file_path)
            
            # Validate required columns
            required_columns = ['position_name', 'X', 'Y', 'Z']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                self.positions_status_label.config(text=f"Missing required columns: {', '.join(missing_columns)}", 
                                              fg=GUI_COLORS['status_error'])
                return
            
            # Validate data types
            try:
                df['X'] = pd.to_numeric(df['X'])
                df['Y'] = pd.to_numeric(df['Y'])
                df['Z'] = pd.to_numeric(df['Z'])
            except ValueError as e:
                self.positions_status_label.config(text=f"Invalid numeric data in position coordinates: {str(e)}", 
                                              fg=GUI_COLORS['status_error'])
                return
            
            # Store the loaded positions for later use
            self.well_selection_frame.loaded_positions_df = df.copy()
            self.well_selection_frame.config_type = 'Load Positions From File'
            
            # Update status
            num_positions = len(df)
            num_wells = len(df['well'].unique()) if 'well' in df.columns else "Unknown"
            self.positions_status_label.config(text=f"Successfully loaded {num_positions} positions from {num_wells} wells. Click 'Create Positions' to use these positions.", 
                                          fg=GUI_COLORS['status_success'])
            
            self.log(f"Loaded {num_positions} positions from {file_path}")
            
        except Exception as e:
            self.positions_status_label.config(text=f"Error loading positions: {str(e)}", 
                                          fg=GUI_COLORS['status_error'])
            self.log(f"Error loading positions from file: {e}", level='error')
    
    def save_manual_config(self):
        """Save the manual configuration as a JSON file."""
        try:
            config_name = self.config_name_var.get().strip()
            if not config_name:
                self.positions_status_label.config(text="Please enter a configuration name.", 
                                              fg=GUI_COLORS['status_error'])
                return
            
            if not self.well_selection_frame.manual_wells:
                self.positions_status_label.config(text="Please add at least one well before saving.", 
                                              fg=GUI_COLORS['status_error'])
                return
            
            # Create plates directory if it doesn't exist
            plates_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Plates")
            os.makedirs(plates_dir, exist_ok=True)
            
            # Save configuration
            config_file = os.path.join(plates_dir, f"{config_name}.json")
            with open(config_file, 'w') as f:
                json.dump(self.well_selection_frame.manual_wells, f, indent=2)
            
            self.positions_status_label.config(text=f"Configuration saved as '{config_name}.json' in Plates directory.", 
                                          fg=GUI_COLORS['status_success'])
            self.log(f"Manual configuration saved: {config_file}")
            
        except Exception as e:
            self.positions_status_label.config(text=f"Error saving configuration: {str(e)}", 
                                          fg=GUI_COLORS['status_error'])
            self.log(f"Error saving manual config: {e}", level='error')
    
    def generate_custom_grid_wells(self):
        """Generate wells from custom grid configuration and show well selection."""
        try:
            grid_vars = self.well_selection_frame.grid_vars
            
            # Get grid parameters
            rows = int(grid_vars['rows'].get())
            columns = int(grid_vars['columns'].get())
            row_spacing = float(grid_vars['row_spacing'].get())
            column_spacing = float(grid_vars['column_spacing'].get())
            center_x = float(grid_vars['center_x'].get())
            center_y = float(grid_vars['center_y'].get())
            center_z = float(grid_vars['center_z'].get())
            shape = grid_vars['shape'].get()
            
            # Get dimensions based on shape
            if shape == 'circle':
                radius = float(grid_vars['radius'].get())
                dimensions = {'radius': radius}
            else:  # rectangle
                width = float(grid_vars['width'].get())
                height = float(grid_vars['height'].get())
                rotation = float(grid_vars['rotation'].get())
                dimensions = {'width': width, 'height': height, 'rotation': rotation}
            
            # Generate well names and positions
            generated_wells = {}
            for row in range(rows):
                for col in range(columns):
                    well_name = f"{chr(65 + row)}{col + 1}"  # A1, A2, B1, B2, etc.
                    well_x = center_x + (col - (columns - 1) / 2) * column_spacing
                    well_y = center_y + (row - (rows - 1) / 2) * row_spacing
                    
                    generated_wells[well_name] = {
                        'center': {'X': well_x, 'Y': well_y, 'Z': center_z},
                        'shape': shape,
                        'dimensions': dimensions
                    }
            
            # Check if save_name is provided and save configuration if so
            save_name = grid_vars['save_name'].get().strip()
            if save_name:
                try:
                    # Create plates directory if it doesn't exist
                    plates_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Plates")
                    os.makedirs(plates_dir, exist_ok=True)
                    
                    # Save configuration
                    config_file = os.path.join(plates_dir, f"{save_name}.json")
                    with open(config_file, 'w') as f:
                        json.dump(generated_wells, f, indent=2)
                    
                    self.log(f"Grid configuration saved: {config_file}")
                    save_message = f"Configuration saved as '{save_name}.json' and "
                except Exception as e:
                    self.log(f"Error saving grid configuration: {e}")
                    save_message = ""
            else:
                save_message = ""
            
            # Store the generated wells
            self.well_selection_frame.generated_wells = generated_wells
            self.well_selection_frame.config_type = 'Custom Grid'
            
            # Add logging for debugging
            self.log(f"Generated {len(generated_wells)} wells for Custom Grid", level='debug')
            self.log(f"Generated well names: {sorted(generated_wells.keys())}", level='debug')
            for well_name, well_config in generated_wells.items():
                self.log(f"Well {well_name}: center={well_config['center']}, shape={well_config['shape']}, dimensions={well_config['dimensions']}", level='debug')
            
            # Update status message to indicate wells are ready
            self.positions_status_label.config(text=f"{save_message}Successfully generated {len(generated_wells)} wells. Click 'Create Positions' to create positions for all wells.", 
                                          fg=GUI_COLORS['status_success'])
            
        except ValueError as e:
            self.positions_status_label.config(text=f"Invalid input: {str(e)}", fg=GUI_COLORS['status_error'])
    
    def show_well_selection_for_custom(self, generated_wells, config_type):
        """Show well selection interface for custom configurations."""
        # Clear existing widgets in well selection frame
        for widget in self.well_selection_frame.winfo_children():
            widget.destroy()
        
        # Change button to "Create Positions" when showing well selection
        self.create_btn.config(text="Create Positions", command=self.create_positions_in_setup)
        
        # Create well selection frame
        well_selection_frame_inner = tk.LabelFrame(self.well_selection_frame, 
                                                 text="Well Selection", 
                                                 bg=GUI_COLORS['frame'], 
                                                 fg=GUI_COLORS['text'],
                                                 font=GUI_FONTS['heading'])
        well_selection_frame_inner.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Create scrollable frame for well checkboxes
        canvas = tk.Canvas(well_selection_frame_inner, bg=GUI_COLORS['frame'])
        scrollbar = tk.Scrollbar(well_selection_frame_inner, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=GUI_COLORS['frame'])
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Create well checkboxes in 3 columns
        well_vars = {}
        well_names = sorted(generated_wells.keys())
        
        # Create 3 columns
        col1 = tk.Frame(scrollable_frame, bg=GUI_COLORS['frame'])
        col1.pack(side='left', fill='both', expand=True, padx=5, pady=5)
        
        col2 = tk.Frame(scrollable_frame, bg=GUI_COLORS['frame'])
        col2.pack(side='left', fill='both', expand=True, padx=5, pady=5)
        
        col3 = tk.Frame(scrollable_frame, bg=GUI_COLORS['frame'])
        col3.pack(side='left', fill='both', expand=True, padx=5, pady=5)
        
        columns = [col1, col2, col3]
        
        # Select all wells by default and distribute across columns
        for i, well_name in enumerate(well_names):
            var = tk.BooleanVar(value=True)
            well_vars[well_name] = var
            
            # Determine which column to use
            col = columns[i % 3]
            
            checkbox = tk.Checkbutton(col,
                                    text=well_name,
                                    variable=var,
                                    bg=GUI_COLORS['checkbox_bg'],
                                    fg=GUI_COLORS['text'],
                                    selectcolor=GUI_COLORS['checkbox_select'],
                                    activebackground=GUI_COLORS['checkbox_active'],
                                    activeforeground=GUI_COLORS['text'],
                                    font=GUI_FONTS['body'])
            checkbox.pack(anchor='w', padx=5, pady=2)
        
        # Store well variables for later use
        self.well_selection_frame.well_vars = well_vars
        self.well_selection_frame.generated_wells = generated_wells
        self.well_selection_frame.config_type = config_type
        
        # Add logging for debugging
        self.log(f"Created well selection interface with {len(well_vars)} wells", level='debug')
        self.log(f"Well variables created: {sorted(well_vars.keys())}", level='debug')
        for well_name, var in well_vars.items():
            self.log(f"Well {well_name} checkbox state: {var.get()}", level='debug')
        
        # Pack scrollable components
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        self.positions_status_label.config(text=f"Generated {len(well_names)} wells from {config_type}. Select wells to include.", 
                                      fg=GUI_COLORS['status_success'])
    
    def cancel_positions(self):
        """Cancel positions creation and return to welcome screen."""
        self.show_welcome_screen()
    
    def show_experiment_config_gui(self):
        """Show experiment configuration GUI in experimental setup panel."""
        # Clear existing content
        for widget in self.experimental_setup_frame.winfo_children():
            widget.destroy()
        
        # Create config GUI content
        config_frame = tk.Frame(self.experimental_setup_frame, bg=GUI_COLORS['background'])
        config_frame.pack(expand=True, fill='both', padx=20, pady=20)
        
        # Create main horizontal container for left and right panels
        main_container = tk.Frame(config_frame, bg=GUI_COLORS['background'])
        main_container.pack(fill='both', expand=True)
        
        # Left panel: Well Assignments
        left_panel = tk.Frame(main_container, bg=GUI_COLORS['background'])
        left_panel.pack(side='left', fill='both', expand=True)
        
        # Combined Group and Fluidics assignments with scrollbar
        assignments_frame = tk.LabelFrame(left_panel, text="Well Assignments", 
                                        bg=GUI_COLORS['frame'], fg=GUI_COLORS['text'], 
                                        font=GUI_FONTS['heading'], padx=0, pady=0)
        assignments_frame.pack(fill='both', expand=True)
        
        # Create scrollable frame for assignments
        assignments_canvas = tk.Canvas(assignments_frame, bg=GUI_COLORS['frame'], height=200)
        assignments_scrollbar = tk.Scrollbar(assignments_frame, orient="vertical", command=assignments_canvas.yview)
        assignments_scrollable_frame = tk.Frame(assignments_canvas, bg=GUI_COLORS['frame'])
        
        assignments_scrollable_frame.bind(
            "<Configure>",
            lambda e: assignments_canvas.configure(scrollregion=assignments_canvas.bbox("all"))
        )
        
        assignments_canvas.create_window((0, 0), window=assignments_scrollable_frame, anchor="nw")
        assignments_canvas.configure(yscrollcommand=assignments_scrollbar.set)
        
        unique_wells = self.experiment.positions['well'].unique() if 'well' in self.experiment.positions.columns else []
        self.group_vars = {}
        self.fluidics_well_entries = {}
        for well in unique_wells:
            self.group_vars[well] = tk.StringVar(value='None')
        
        for i, well in enumerate(unique_wells):
            well_frame = tk.Frame(assignments_scrollable_frame, bg=GUI_COLORS['frame'])
            well_frame.pack(fill='x', padx=10, pady=5)
            
            # Well name
            tk.Label(well_frame, text=f"{well}:", bg=GUI_COLORS['frame'], 
                    fg=GUI_COLORS['text'], width=20, anchor='w').pack(side='left')
            
            # Group assignment
            group_frame = tk.Frame(well_frame, bg=GUI_COLORS['frame'])
            group_frame.pack(side='left', padx=10)
            
            # Only show "Group:" label on the first well
            if i == 0:
                tk.Label(group_frame, text="Group:", bg=GUI_COLORS['frame'], 
                        fg=GUI_COLORS['text'], font=GUI_FONTS['small']).pack(anchor='w')
            
            group_buttons_frame = tk.Frame(group_frame, bg=GUI_COLORS['frame'])
            group_buttons_frame.pack(anchor='w')
            
            tk.Radiobutton(group_buttons_frame, text="None", variable=self.group_vars[well], value='None',
                          bg=GUI_COLORS['checkbox_bg'], fg=GUI_COLORS['text'], 
                          selectcolor=GUI_COLORS['checkbox_select'],
                          activebackground=GUI_COLORS['checkbox_active'], 
                          activeforeground=GUI_COLORS['text'],
                          font=GUI_FONTS['small']).pack(side='left', padx=2)
            
            tk.Radiobutton(group_buttons_frame, text="1", variable=self.group_vars[well], value='Group 1',
                          bg=GUI_COLORS['checkbox_bg'], fg=GUI_COLORS['text'], 
                          selectcolor=GUI_COLORS['checkbox_select'],
                          activebackground=GUI_COLORS['checkbox_active'], 
                          activeforeground=GUI_COLORS['text'],
                          font=GUI_FONTS['small']).pack(side='left', padx=2)
            
            tk.Radiobutton(group_buttons_frame, text="2", variable=self.group_vars[well], value='Group 2',
                          bg=GUI_COLORS['checkbox_bg'], fg=GUI_COLORS['text'], 
                          selectcolor=GUI_COLORS['checkbox_select'],
                          activebackground=GUI_COLORS['checkbox_active'], 
                          activeforeground=GUI_COLORS['text'],
                          font=GUI_FONTS['small']).pack(side='left', padx=2)
            
            # Fluidics assignment
            fluidics_frame = tk.Frame(well_frame, bg=GUI_COLORS['frame'])
            fluidics_frame.pack(side='left', padx=10)
            
            # Only show "Fluidics:" label on the first well
            if i == 0:
                tk.Label(fluidics_frame, text="Fluidics:", bg=GUI_COLORS['frame'], 
                        fg=GUI_COLORS['text'], font=GUI_FONTS['small']).pack(anchor='w')
            
            entry = tk.Entry(fluidics_frame, bg=GUI_COLORS['entry'], 
                           fg=GUI_COLORS['text'], insertbackground=GUI_COLORS['text'], width=5)
            entry.pack(anchor='w')
            entry.insert(0, chr(65 + list(unique_wells).index(well)))  # Default to A, B, C, etc.
            self.fluidics_well_entries[well] = entry
        
        # Pack scrollable components
        assignments_canvas.pack(side="left", fill="both", expand=True)
        assignments_scrollbar.pack(side="right", fill="y")
        
        # Right panel: Controls (Channels, Hybes, Fluidics Protocols)
        right_panel = tk.Frame(main_container, bg=GUI_COLORS['background'])
        right_panel.pack(side='right', fill='both', expand=True, padx=(20, 0))
        
        # Acquisition Data selection
        acquisition_frame = tk.LabelFrame(right_panel, text="Acquisition", 
                                      bg=GUI_COLORS['frame'], fg=GUI_COLORS['text'], 
                                      font=GUI_FONTS['heading'], padx=0, pady=0)
        acquisition_frame.pack(fill='x', pady=(0, 10))
        
        self.channels_vars = []
        self.channel_exposure_vars = []
        self.channel_delay_vars = []
        
        # Get available channels from Scope configuration
        try:
            available_channels = self.scope.available_channels
            self.log(f"Using channels from Scope config: {available_channels}")
        except Exception as e:
            self.log(f"Error getting channels from Scope: {e}, using fallback", level='warning')
            available_channels = ['FarRed', 'DeepBlue', 'Green', 'Orange']
        
        # Create header row
        header_frame = tk.Frame(acquisition_frame, bg=GUI_COLORS['frame'])
        header_frame.pack(fill='x', padx=10, pady=(10, 5))
        
        tk.Label(header_frame, text="Select", bg=GUI_COLORS['frame'], fg=GUI_COLORS['text'],
                font=GUI_FONTS['body'], width=4, anchor='center').pack(side='left', padx=(0, 20))
        tk.Label(header_frame, text="Channel", bg=GUI_COLORS['frame'], fg=GUI_COLORS['text'],
                font=GUI_FONTS['body'], width=10, anchor='center').pack(side='left', padx=(0, 20))
        tk.Label(header_frame, text="Exposure (ms)", bg=GUI_COLORS['frame'], fg=GUI_COLORS['text'],
                font=GUI_FONTS['body'], width=10, anchor='center').pack(side='left', padx=(0, 20))
        tk.Label(header_frame, text="Delay (ms)", bg=GUI_COLORS['frame'], fg=GUI_COLORS['text'],
                font=GUI_FONTS['body'], width=10, anchor='center').pack(side='left')
        
        # Create channel rows
        for channel in available_channels:
            var = tk.BooleanVar()
            var.set(True)
            self.channels_vars.append(var)
            
            exposure_var = tk.StringVar()
            exposure_var.set("500")  # Default value
            self.channel_exposure_vars.append(exposure_var)
            
            delay_var = tk.StringVar()
            delay_var.set("0")  # Default value
            self.channel_delay_vars.append(delay_var)
            
            row_frame = tk.Frame(acquisition_frame, bg=GUI_COLORS['frame'])
            row_frame.pack(fill='x', padx=10, pady=2)
            
            # Checkbox
            cb = tk.Checkbutton(row_frame, variable=var, 
                              bg=GUI_COLORS['checkbox_bg'], fg=GUI_COLORS['text'],
                              selectcolor=GUI_COLORS['checkbox_select'], 
                              activebackground=GUI_COLORS['checkbox_active'], 
                              activeforeground=GUI_COLORS['text'])
            cb.pack(side='left', padx=(0, 20))
            
            # Channel name
            tk.Label(row_frame, text=channel, bg=GUI_COLORS['frame'], fg=GUI_COLORS['text'],
                    font=GUI_FONTS['body'], width=12, anchor='center').pack(side='left', padx=(0, 20))
            
            # Exposure input
            exposure_entry = tk.Entry(row_frame, textvariable=exposure_var, width=12,
                                     bg=GUI_COLORS['entry'], fg=GUI_COLORS['text'],
                                     font=GUI_FONTS['body'], justify='center')
            exposure_entry.pack(side='left', padx=(0, 20))
            
            # Delay input
            delay_entry = tk.Entry(row_frame, textvariable=delay_var, width=12,
                                  bg=GUI_COLORS['entry'], fg=GUI_COLORS['text'],
                                  font=GUI_FONTS['body'], justify='center')
            delay_entry.pack(side='left', padx=(0, 20))
        
        # Steps section
        steps_frame = tk.Frame(acquisition_frame, bg=GUI_COLORS['frame'])
        steps_frame.pack(fill='x', padx=10, pady=(10, 10))
        
        tk.Label(steps_frame, text="Steps:", bg=GUI_COLORS['frame'], 
                fg=GUI_COLORS['text'], font=GUI_FONTS['heading'], width=8, anchor='w').pack(side='left')
        
        # Start input
        tk.Label(steps_frame, text="Start:", bg=GUI_COLORS['frame'], 
                fg=GUI_COLORS['text'], font=GUI_FONTS['body'], width=6, anchor='w').pack(side='left', padx=(5, 5))
        
        self.steps_start_var = tk.StringVar()
        self.steps_start_var.set("0")
        steps_start_entry = tk.Entry(steps_frame, textvariable=self.steps_start_var, width=8,
                                     bg=GUI_COLORS['entry'], fg=GUI_COLORS['text'],
                                     font=GUI_FONTS['body'], justify='center')
        steps_start_entry.pack(side='left', padx=(0, 10))
        
        # End input
        tk.Label(steps_frame, text="End:", bg=GUI_COLORS['frame'], 
                fg=GUI_COLORS['text'], font=GUI_FONTS['body'], width=6, anchor='w').pack(side='left', padx=(0, 5))
        
        self.steps_end_var = tk.StringVar()
        self.steps_end_var.set("0")
        steps_end_entry = tk.Entry(steps_frame, textvariable=self.steps_end_var, width=8,
                                  bg=GUI_COLORS['entry'], fg=GUI_COLORS['text'],
                                  font=GUI_FONTS['body'], justify='center')
        steps_end_entry.pack(side='left', padx=(0, 10))
        
        # dZ input
        tk.Label(steps_frame, text="dZ (um):", bg=GUI_COLORS['frame'], 
                fg=GUI_COLORS['text'], font=GUI_FONTS['body'], width=6, anchor='w').pack(side='left', padx=(0, 5))
        
        self.steps_dz_var = tk.StringVar()
        self.steps_dz_var.set("0")
        steps_dz_entry = tk.Entry(steps_frame, textvariable=self.steps_dz_var, width=8,
                                 bg=GUI_COLORS['entry'], fg=GUI_COLORS['text'],
                                 font=GUI_FONTS['body'], justify='center')
        steps_dz_entry.pack(side='left')
        
        # Fluidics
        fluidics_frame = tk.LabelFrame(right_panel, text="Fluidics", 
                                      bg=GUI_COLORS['frame'], fg=GUI_COLORS['text'], 
                                      font=GUI_FONTS['heading'], padx=0, pady=0)
        fluidics_frame.pack(fill='x', pady=(0, 10))
        
        fluidics_content = tk.Frame(fluidics_frame, bg=GUI_COLORS['frame'])
        fluidics_content.pack(fill='x', padx=10, pady=10)
        
        # Number of hybes section
        hybes_section = tk.Frame(fluidics_content, bg=GUI_COLORS['frame'])
        hybes_section.pack(fill='x', pady=(0, 10))
        
        tk.Label(hybes_section, text="Number of Hybes:", bg=GUI_COLORS['frame'], 
                fg=GUI_COLORS['text'], font=GUI_FONTS['body'], width=15, anchor='w').pack(side='left')
        
        self.hybes_var = tk.StringVar()
        self.hybes_dropdown = ttk.Combobox(hybes_section, textvariable=self.hybes_var, 
                                          style='Dark.TCombobox', width=10)
        self.hybes_dropdown['values'] = list(range(1, 51))
        self.hybes_dropdown.set(18)
        self.hybes_dropdown.pack(side='left', padx=(10, 0))
        
        # Protocols section
        protocols_section = tk.Frame(fluidics_content, bg=GUI_COLORS['frame'])
        protocols_section.pack(fill='x')
        
        tk.Label(protocols_section, text="Protocols:", bg=GUI_COLORS['frame'], 
                fg=GUI_COLORS['text'], font=GUI_FONTS['body'], width=15, anchor='w').pack(side='left')
        
        protocols_frame = tk.Frame(protocols_section, bg=GUI_COLORS['frame'])
        protocols_frame.pack(side='left', padx=(10, 0))
        
        self.hybe_var = tk.BooleanVar()
        self.strip_var = tk.BooleanVar()
        self.hybe_var.set(True)
        self.strip_var.set(True)
        
        protocol_1_frame = tk.Frame(protocols_frame, bg=GUI_COLORS['frame'])
        protocol_1_frame.pack(side='left', padx=10)
        
        protocol_2_frame = tk.Frame(protocols_frame, bg=GUI_COLORS['frame'])
        protocol_2_frame.pack(side='left', padx=10)
        
        tk.Checkbutton(protocol_1_frame, variable=self.hybe_var, 
                      bg=GUI_COLORS['checkbox_bg'], fg=GUI_COLORS['text'],
                      selectcolor=GUI_COLORS['checkbox_select'], 
                      activebackground=GUI_COLORS['checkbox_active'], 
                      activeforeground=GUI_COLORS['text']).pack(side='left')
        
        # Get available protocols from Protocol class
        from Fluidics.Protocols.Protocol import Protocol
        protocol_instance = Protocol()
        available_protocols = list(protocol_instance.protocols.keys())
        
        self.protocol_1_var = tk.StringVar()
        self.protocol_1_dropdown = ttk.Combobox(protocol_1_frame, 
                                               textvariable=self.protocol_1_var,
                                               values=available_protocols,
                                               style='Dark.TCombobox', width=15)
        self.protocol_1_dropdown.pack(side='left', padx=(5, 0))
        self.protocol_1_dropdown.set("Strip")
        
        tk.Checkbutton(protocol_2_frame, variable=self.strip_var, 
                      bg=GUI_COLORS['checkbox_bg'], fg=GUI_COLORS['text'],
                      selectcolor=GUI_COLORS['checkbox_select'], 
                      activebackground=GUI_COLORS['checkbox_active'], 
                      activeforeground=GUI_COLORS['text']).pack(side='left')
        
        self.protocol_2_var = tk.StringVar()
        self.protocol_2_dropdown = ttk.Combobox(protocol_2_frame, 
                                               textvariable=self.protocol_2_var,
                                               values=available_protocols,
                                               style='Dark.TCombobox', width=15)
        self.protocol_2_dropdown.pack(side='left', padx=(5, 0))
        self.protocol_2_dropdown.set("Hybe")
        
        # Skip first fluidics task checkbox
        skip_first_frame = tk.Frame(protocols_section, bg=GUI_COLORS['frame'])
        skip_first_frame.pack(fill='x', pady=(5, 0))
        
        self.skip_first_fluidics_var = tk.BooleanVar()
        
        # Load initial state from experiment state
        try:
            experiment_state = self.file_handler.get_state('Experiment')
            skip_first = experiment_state.get('skip_first_fluidics_task', False)
            self.skip_first_fluidics_var.set(skip_first)
        except:
            self.skip_first_fluidics_var.set(False)
        
        tk.Checkbutton(skip_first_frame, text="Skip first fluidics task", 
                      variable=self.skip_first_fluidics_var,
                      command=self.on_skip_first_fluidics_changed,
                      bg=GUI_COLORS['checkbox_bg'], fg=GUI_COLORS['text'],
                      selectcolor=GUI_COLORS['checkbox_select'], 
                      activebackground=GUI_COLORS['checkbox_active'], 
                      activeforeground=GUI_COLORS['text'],
                      font=GUI_FONTS['body']).pack(side='left')
        
        # Position Refinement
        position_refinement_frame = tk.LabelFrame(right_panel, text="Position Refinement", 
                                                bg=GUI_COLORS['frame'], fg=GUI_COLORS['text'], 
                                                font=GUI_FONTS['heading'], padx=0, pady=0)
        position_refinement_frame.pack(fill='x', pady=(0, 10))
        
        position_refinement_content = tk.Frame(position_refinement_frame, bg=GUI_COLORS['frame'])
        position_refinement_content.pack(fill='x', padx=10, pady=10)
        
        # Position Filtering
        position_filtering_frame = tk.Frame(position_refinement_content, bg=GUI_COLORS['frame'])
        position_filtering_frame.pack(fill='x', pady=2)
        
        tk.Label(position_filtering_frame, text="Position Filtering:", bg=GUI_COLORS['frame'], 
                fg=GUI_COLORS['text'], font=GUI_FONTS['body'], width=15, anchor='w').pack(side='left')
        
        self.position_filtering_var = tk.StringVar()
        self.position_filtering_dropdown = ttk.Combobox(position_filtering_frame, 
                                                       textvariable=self.position_filtering_var, 
                                                       style='Dark.TCombobox', width=15)
        self.position_filtering_dropdown['values'] = ['None', 'Draw']
        self.position_filtering_dropdown.set('None')
        self.position_filtering_dropdown.pack(side='left', padx=(10, 0))
        
        # Focus
        focus_frame = tk.LabelFrame(right_panel, text="Focus", 
                                  bg=GUI_COLORS['frame'], fg=GUI_COLORS['text'], 
                                  font=GUI_FONTS['heading'], padx=0, pady=0)
        focus_frame.pack(fill='x', pady=(0, 10))
        
        focus_content = tk.Frame(focus_frame, bg=GUI_COLORS['frame'])
        focus_content.pack(fill='x', padx=10, pady=10)
        
        # Preview Focus
        preview_focus_frame = tk.Frame(focus_content, bg=GUI_COLORS['frame'])
        preview_focus_frame.pack(fill='x', pady=2)
        
        tk.Label(preview_focus_frame, text="Preview Focus Method:", bg=GUI_COLORS['frame'], 
                fg=GUI_COLORS['text'], font=GUI_FONTS['body'], width=20, anchor='w').pack(side='left')
        
        self.preview_focus_var = tk.StringVar()
        self.preview_focus_dropdown = ttk.Combobox(preview_focus_frame, 
                                                 textvariable=self.preview_focus_var, 
                                                 style='Dark.TCombobox', width=15)
        self.preview_focus_dropdown['values'] = ['None', 'Manual Plate', 'Manual Well']
        self.preview_focus_dropdown.set('None')
        self.preview_focus_dropdown.pack(side='left', padx=(10, 0))
        
        # Acquisition Focus
        acquisition_focus_frame = tk.Frame(focus_content, bg=GUI_COLORS['frame'])
        acquisition_focus_frame.pack(fill='x', pady=2)
        
        tk.Label(acquisition_focus_frame, text="Acquisition Focus Method:", bg=GUI_COLORS['frame'], 
                fg=GUI_COLORS['text'], font=GUI_FONTS['body'], width=20, anchor='w').pack(side='left')
        
        self.acquisition_focus_var = tk.StringVar()
        self.acquisition_focus_dropdown = ttk.Combobox(acquisition_focus_frame, 
                                                     textvariable=self.acquisition_focus_var, 
                                                     style='Dark.TCombobox', width=15)
        self.acquisition_focus_dropdown['values'] = ['None', 'Plane']
        self.acquisition_focus_dropdown.set('None')
        self.acquisition_focus_dropdown.pack(side='left', padx=(10, 0))
        
        # AutoFocus Method
        autofocus_method_frame = tk.Frame(focus_content, bg=GUI_COLORS['frame'])
        autofocus_method_frame.pack(fill='x', pady=2)
        
        tk.Label(autofocus_method_frame, text="AutoFocus Method:", bg=GUI_COLORS['frame'], 
                fg=GUI_COLORS['text'], font=GUI_FONTS['body'], width=20, anchor='w').pack(side='left')
        
        self.autofocus_method_var = tk.StringVar()
        self.autofocus_method_dropdown = ttk.Combobox(autofocus_method_frame, 
                                                     textvariable=self.autofocus_method_var, 
                                                     style='Dark.TCombobox', width=15)
        self.autofocus_method_dropdown['values'] = ['None', 'Relative']
        self.autofocus_method_dropdown.set('None')
        self.autofocus_method_dropdown.pack(side='left', padx=(10, 0))
        
        # Error label
        self.config_error_label = create_error_label(config_frame, "")
        self.config_error_label.pack(pady=10)
        
        # Buttons
        button_frame = tk.Frame(config_frame, bg=GUI_COLORS['background'])
        button_frame.pack(fill='x', pady=10)
        
        cancel_btn = create_button(button_frame, "Cancel", 
                                 command=self.cancel_experiment_config)
        cancel_btn.pack(side='right', padx=(10, 0))
        
        save_btn = create_button(button_frame, "Save Configuration", 
                               command=self.save_experiment_config, bold=True)
        save_btn.pack(side='right')
    
    def save_experiment_config(self):
        """Save experiment configuration and complete setup."""
        try:
            self.config_error_label.config(text="")
            
            # Get group assignments from GUI
            group_assignments = {}
            for well, var in self.group_vars.items():
                group_assignments[well] = var.get()
            
            # Get fluidics well assignments from GUI
            fluidics_well_assignments = {}
            for well, entry in self.fluidics_well_entries.items():
                fluidics_well_name = entry.get().strip()
                if fluidics_well_name:
                    fluidics_well_assignments[well] = fluidics_well_name
            
            # Get selected channels from GUI
            try:
                available_channels = self.scope.available_channels
            except Exception as e:
                self.log(f"Error getting channels from Scope: {e}, using fallback", level='warning')
                available_channels = ['FarRed', 'DeepBlue', 'Green', 'Orange']
            
            selected_channels = [channel for channel, var in zip(available_channels, self.channels_vars) if var.get()]
            
            # Get channel exposure values from GUI
            channel_exposure = {}
            for i, channel in enumerate(available_channels):
                try:
                    exposure_value = int(self.channel_exposure_vars[i].get())
                    channel_exposure[channel] = exposure_value
                except ValueError:
                    # If invalid input, use default value
                    channel_exposure[channel] = 500
            
            # Get channel delay values from GUI with validation
            channel_delay = {}
            for i, channel in enumerate(available_channels):
                try:
                    delay_value = float(self.channel_delay_vars[i].get())
                    
                    # Validate delay is between 0 and 1000
                    if delay_value < 0 or delay_value > 1000:
                        self.config_error_label.config(text=f"ERROR: Delay for {channel} must be between 0 and 1000!")
                        return
                    
                    channel_delay[channel] = delay_value
                except ValueError:
                    self.config_error_label.config(text=f"ERROR: Delay for {channel} must be a valid number!")
                    return
            
            if not selected_channels:
                self.config_error_label.config(text="ERROR: Please select at least one channel!")
                return
            
            # Validate fluidics well assignments
            unique_wells = self.experiment.positions['well'].unique() if 'well' in self.experiment.positions.columns else []
            if len(fluidics_well_assignments) != len(unique_wells):
                self.config_error_label.config(text="ERROR: Please assign fluidics wells to all plate wells!")
                return
            
            # Get fluidics protocols from GUI
            selected_fluidics = []
            if self.hybe_var.get():
                protocol_1_name = self.protocol_1_var.get()
                if protocol_1_name:
                    selected_fluidics.append(protocol_1_name.lower())
            if self.strip_var.get():
                protocol_2_name = self.protocol_2_var.get()
                if protocol_2_name:
                    selected_fluidics.append(protocol_2_name.lower())
            
            if not selected_fluidics:
                selected_fluidics = ['none']
            
            # Get number of hybes
            num_hybes = int(self.hybes_var.get())
            
            # Get parameters settings from GUI
            position_filtering = self.position_filtering_var.get()
            preview_focus = self.preview_focus_var.get()
            acquisition_focus = self.acquisition_focus_var.get()
            autofocus_method = self.autofocus_method_var.get()
            
            # Get steps settings from GUI with validation
            try:
                steps_start = float(self.steps_start_var.get())
                steps_end = float(self.steps_end_var.get())
                steps_dz = float(self.steps_dz_var.get())
                
                # Validate dZ is positive (except when start equals end, then dZ can be 0)
                if steps_dz < 0 or (steps_dz <= 0 and steps_start != steps_end):
                    self.config_error_label.config(text="ERROR: dZ must be positive! (or 0 when start equals end)")
                    return
                
                # Validate dZ is smaller than or equal to the difference between start and end
                if steps_dz > abs(steps_end - steps_start):
                    self.config_error_label.config(text="ERROR: dZ must be smaller than or equal to the difference between start and end!")
                    return
                
                steps_settings = {
                    'start': steps_start,
                    'end': steps_end,
                    'dz': steps_dz
                }
                
            except ValueError:
                self.config_error_label.config(text="ERROR: Steps values must be valid numbers!")
                return
            
            # Filter positions to only include wells with group assignments (not "None")
            wells_with_groups = {well for well, group in group_assignments.items() if group != 'None'}
            if hasattr(self.experiment, 'positions') and not self.experiment.positions.empty:
                original_position_count = len(self.experiment.positions)
                self.experiment.positions = self.experiment.positions[self.experiment.positions['well'].isin(wells_with_groups)].copy()
                filtered_position_count = len(self.experiment.positions)
                self.log(f"Filtered positions: {original_position_count} -> {filtered_position_count} (removed {original_position_count - filtered_position_count} positions from wells without groups)")
                self.file_handler.save_positions(self.experiment.positions)
            
            # Update experiment state using the new method
            updates = {
                'group_assignments': group_assignments,
                'groups': list(set(group_assignments.values())),
                'fluidics_well_assignments': fluidics_well_assignments,
                'selected_channels': selected_channels,
                'channel_exposure': channel_exposure,
                'channel_delay': channel_delay,
                'fluidics_protocols': selected_fluidics,
                'num_hybes': num_hybes,
                'position_filtering': position_filtering,
                'preview_focus': preview_focus,
                'acquisition_focus': acquisition_focus,
                'autofocus_method': autofocus_method,
                'steps': steps_settings
            }
            self.file_handler.update_state(system_prefix='Experiment',updates=updates)
            
            self.log(f"Group assignments: {group_assignments}")
            self.log(f"Fluidics well assignments: {fluidics_well_assignments}")
            self.log(f"Selected channels: {selected_channels}")
            self.log(f"Channel exposure: {channel_exposure}")
            self.log(f"Channel delay: {channel_delay}")
            self.log(f"Fluidics protocols: {selected_fluidics}")
            self.log(f"Number of hybes: {num_hybes}")
            self.log(f"Position filtering: {position_filtering}")
            self.log(f"Preview focus: {preview_focus}")
            self.log(f"Acquisition focus: {acquisition_focus}")
            self.log(f"Autofocus method: {autofocus_method}")
            self.log(f"Steps: {steps_settings}")
            self.log("Configuration saved successfully!")
            
            # Create tasks (without GUI)
            self.experiment.create_tasks()
            
            self.log("Experiment setup completed successfully!")
            
            # Show completion message
            for widget in self.experimental_setup_frame.winfo_children():
                widget.destroy()

            self.update_experiment_info()
            
        except Exception as e:
            self.config_error_label.config(text=f"ERROR: {str(e)}")
            self.log(f"Error saving experiment configuration: {e}", level='error')
    
    def cancel_experiment_config(self):
        """Cancel experiment configuration and return to welcome screen."""
        self.show_experimental_setup_welcome()

    def update_experiment_control_display(self):
        """Update the experiment control buttons and status based on experiment state."""
        try:
            exp_state = self.file_handler.get_state("Experiment")
            exp_name = exp_state.get('experiment_name')
            user_name = exp_state.get('user_name')
            project_name = exp_state.get('project_name')
            
            if exp_name and user_name and project_name:
                # Enable experiment control buttons
                self.start_btn.config(state='normal')
                self.stop_btn.config(state='normal')
                self.reset_btn.config(state='normal')
                
                # Update status
                self.experiment_status_panel.set_status("Ready", GUI_COLORS['success'])
                
            else:
                # No experiment defined - disable buttons
                self.start_btn.config(state='disabled')
                self.stop_btn.config(state='disabled')
                self.reset_btn.config(state='disabled')
                
                # Update status
                self.experiment_status_panel.set_status("Idle", GUI_COLORS['text_muted'])
                
        except Exception as e:
            self.log(f"Error updating experiment control display: {e}", level='warning')


    def create_fluidics_block(self, parent):
        """Create the fluidics control block."""
        # Create StatusPanel for fluidics control
        self.fluidics_status_panel = StatusPanel(
            parent=parent,
            panel_name="Fluidics",
            system_name="Fluidics",
            progress_info_type="fluidics",
            pause_callback=lambda: self.pause_system_callback('fluidics'),
            resume_callback=lambda: self.resume_system_callback('fluidics'),
            launch_callback=lambda: self.launch_system_callback('fluidics'),
            kill_callback=lambda: self.kill_system_callback('fluidics'),
            file_handler=self.file_handler,
            system_prefix=self.system_prefix
        )
        self.fluidics_status_panel.grid(row=2, column=0, sticky='nsew', padx=10, pady=10)
        
        # Create StatePanel for fluidics state display directly in the StatusPanel frame
        self.fluidics_state_panel = StatePanel(
            parent_frame=self.fluidics_status_panel.frame,
            num_columns=2,
            data_source_func=lambda: self.get_system_state_data('fluidics'),
            column_grouping_func=fluidics_grouping,
            panel_name="",
            create_frame=False
        )
    
    def create_scope_block(self, parent):
        """Create the scope control block."""
        # Create StatusPanel for scope control
        self.scope_status_panel = StatusPanel(
            parent=parent,
            panel_name="Scope",
            system_name="Scope",
            progress_info_type="scope",
            pause_callback=lambda: self.pause_system_callback('scope'),
            resume_callback=lambda: self.resume_system_callback('scope'),
            launch_callback=lambda: self.launch_system_callback('scope'),
            kill_callback=lambda: self.kill_system_callback('scope'),
            file_handler=self.file_handler,
            system_prefix=self.system_prefix
        )
        self.scope_status_panel.grid(row=1, column=0, sticky='nsew', padx=10, pady=10)
        
        # Create StatePanel for scope state display directly in the StatusPanel frame
        self.scope_state_panel = StatePanel(
            parent_frame=self.scope_status_panel.frame,
            num_columns=2,
            data_source_func=lambda: self.get_system_state_data('scope'),
            column_grouping_func=scope_grouping,
            panel_name="",
            create_frame=False
        )
    
    def create_experimental_setup_block(self, parent):
        """Create the experimental setup block."""
        frame = tk.LabelFrame(parent, text="Dynamic", 
                             bg=GUI_COLORS['frame'], fg=GUI_COLORS['text'], 
                             font=GUI_FONTS['heading'])
        frame.grid(row=0, column=1, rowspan=3, sticky='nsew', padx=10, pady=10)
        frame.grid_propagate(False)  # Prevent frame from expanding beyond allocated space
        
        # Create main container for embedded content
        self.experimental_setup_frame = tk.Frame(frame, bg=GUI_COLORS['background'], 
                                                relief='sunken', bd=2)
        self.experimental_setup_frame.pack(expand=True, fill='both', padx=5, pady=5)
        
        # Initial state - show welcome message
        self.show_experimental_setup_welcome()
    
    def show_experimental_setup_welcome(self):
        """Show welcome screen in experimental setup panel."""
        # Clear existing content
        for widget in self.experimental_setup_frame.winfo_children():
            widget.destroy()
        
        # Create welcome content
        welcome_frame = tk.Frame(self.experimental_setup_frame, bg=GUI_COLORS['background'])
        welcome_frame.pack(expand=True, fill='both', padx=20, pady=20)
        
        welcome_label = create_body_label(welcome_frame, "Experimental Setup")
        welcome_label.pack(pady=20)
        
        instructions_label = create_body_label(welcome_frame, "Use the Create button to start setting up your experiment")
        instructions_label.pack(pady=10)
    
    def show_startup_gui_in_setup(self):
        """Show startup GUI in experimental setup panel."""
        # Clear existing content
        for widget in self.experimental_setup_frame.winfo_children():
            widget.destroy()
        
        # Create startup GUI content
        startup_frame = tk.Frame(self.experimental_setup_frame, bg=GUI_COLORS['background'])
        startup_frame.pack(expand=True, fill='both', padx=20, pady=20)
        
        # Title
        title_label = create_heading_label(startup_frame, "Setup Experiment")
        title_label.pack(pady=(0, 20))
        
        # Experiment name
        exp_frame = tk.Frame(startup_frame, bg=GUI_COLORS['background'])
        exp_frame.pack(fill='x', pady=5)
        
        tk.Label(exp_frame, text="Experiment Name:", bg=GUI_COLORS['background'], 
                fg=GUI_COLORS['text']).pack(anchor='w')
        self.exp_entry = tk.Entry(exp_frame, bg=GUI_COLORS['entry'],
                                 fg=GUI_COLORS['text'], font=GUI_FONTS['entry'])
        self.exp_entry.pack(fill='x', pady=(5, 0))
        self.exp_entry.insert(0, "New_Experiment") #Preset
        
        # User name
        user_frame = tk.Frame(startup_frame, bg=GUI_COLORS['background'])
        user_frame.pack(fill='x', pady=5)
        
        tk.Label(user_frame, text="User Name:", bg=GUI_COLORS['background'], 
                fg=GUI_COLORS['text']).pack(anchor='w')
        self.user_entry = tk.Entry(user_frame, bg=GUI_COLORS['entry'],
                                  fg=GUI_COLORS['text'], font=GUI_FONTS['entry'])
        self.user_entry.pack(fill='x', pady=(5, 0))
        self.user_entry.insert(0, "User") #Preset
        
        # Project name
        project_frame = tk.Frame(startup_frame, bg=GUI_COLORS['background'])
        project_frame.pack(fill='x', pady=5)
        
        tk.Label(project_frame, text="Project Name:", bg=GUI_COLORS['background'], 
                fg=GUI_COLORS['text']).pack(anchor='w')
        self.project_entry = tk.Entry(project_frame, bg=GUI_COLORS['entry'],
                                     fg=GUI_COLORS['text'], font=GUI_FONTS['entry'])
        self.project_entry.pack(fill='x', pady=(5, 0))
        self.project_entry.insert(0, "New_Project") #Preset
        
        # Save path
        save_path_frame = tk.Frame(startup_frame, bg=GUI_COLORS['background'])
        save_path_frame.pack(fill='x', pady=5)
        
        tk.Label(save_path_frame, text="Save Path:", bg=GUI_COLORS['background'], 
                fg=GUI_COLORS['text']).pack(anchor='w')
        
        path_input_frame = tk.Frame(save_path_frame, bg=GUI_COLORS['background'])
        path_input_frame.pack(fill='x', pady=(5, 0))
        
        self.save_path_entry = tk.Entry(path_input_frame, bg=GUI_COLORS['entry'],
                                       fg=GUI_COLORS['text'], font=GUI_FONTS['entry'])
        self.save_path_entry.pack(side='left', fill='x', expand=True)
        
        # Set default save path to 'D:/Images' if it exists, otherwise empty
        default_save_path = 'D:/Images'
        if os.path.exists(default_save_path):
            self.save_path_entry.insert(0, default_save_path)
            self.log(f"Set default save path to: {default_save_path}")
        else:
            self.save_path_entry.insert(0, "")  # Empty if path doesn't exist
            self.log(f"Default save path '{default_save_path}' does not exist, leaving empty")
        
        browse_btn = create_button(path_input_frame, "Browse", 
                                 command=self.browse_save_path)
        browse_btn.pack(side='right', padx=(5, 0))
        
        # Buttons
        button_frame = tk.Frame(startup_frame, bg=GUI_COLORS['background'])
        button_frame.pack(fill='x', pady=10)
        
        cancel_btn = create_button(button_frame, "Cancel", 
                                 command=self.cancel_startup)
        cancel_btn.pack(side='right', padx=(10, 0))
        
        continue_btn = create_button(button_frame, "Continue", 
                                   command=self.continue_startup, bold=True)
        continue_btn.pack(side='right')
    
    def continue_startup(self):
        """Continue from startup to positions creation."""
        # Get experiment info
        exp_name = self.exp_entry.get().strip()
        user_name = self.user_entry.get().strip()
        project_name = self.project_entry.get().strip()
        save_path = self.save_path_entry.get().strip()
        
        if not exp_name or not user_name or not project_name:
            self.log("Please enter experiment name, user name, and project name", level='warning')
            return
        
        # Save experiment info
        self.experiment.experiment_name = exp_name
        self.experiment.user_name = user_name
        self.experiment.project_name = project_name
        self.experiment.save_path = save_path
        self.save_experiment_info()
        self.show_positions_gui_in_setup()
    
    def browse_save_path(self):
        """Open file browser to select save path."""
        from tkinter import filedialog
        directory = filedialog.askdirectory(
            title="Select Save Directory",
            initialdir=os.getcwd()
        )
        if directory:
            self.save_path_entry.delete(0, tk.END)
            self.save_path_entry.insert(0, directory)
            self.log(f"Selected save path: {directory}")
    
    def cancel_startup(self):
        """Cancel startup and return to welcome screen."""
        self.show_experimental_setup_welcome()
    
    def show_positions_gui_in_setup(self):
        """Show positions GUI in experimental setup panel."""
        # Clear existing content
        for widget in self.experimental_setup_frame.winfo_children():
            widget.destroy()
        
        # Create positions GUI content
        positions_frame = tk.Frame(self.experimental_setup_frame, bg=GUI_COLORS['background'])
        positions_frame.pack(expand=True, fill='both', padx=10, pady=10)
        
        # Configuration type selection
        config_frame = tk.Frame(positions_frame, bg=GUI_COLORS['background'])
        config_frame.pack(fill='x', pady=5)
        
        # Configuration type dropdown and buttons on same line
        dropdown_frame = tk.Frame(config_frame, bg=GUI_COLORS['background'])
        dropdown_frame.pack(fill='x', pady=5)
        
        # Add "Methods" label to the left of the dropdown
        methods_label = tk.Label(dropdown_frame, text="Create Positions Methods:", bg=GUI_COLORS['background'], 
                                fg=GUI_COLORS['text'], font=('Arial', 10))
        methods_label.pack(side='left', padx=(0, 10))
        
        self.config_type_var = tk.StringVar()
        self.config_type_dropdown = ttk.Combobox(dropdown_frame, textvariable=self.config_type_var, 
                                                style='Light.TCombobox', state='readonly')
        self.config_type_dropdown.pack(side='left', fill='x', expand=True, padx=(0, 10))
        
        # Populate dropdown with available options
        self.log("Attempting to get available plate configs...")
        available_configs = self.file_handler.get_available_plate_configs()
        self.log(f"Found available configs: {available_configs}")
        dropdown_options = available_configs + ['Custom Grid', 'Custom Manual', 'Load Wells From File', 'Load Positions From File']
        # FIXME This is really burried in here maybe it should be more accessible
        
        self.config_type_dropdown['values'] = dropdown_options
        self.available_configs = available_configs
        self.config_type_dropdown.bind('<<ComboboxSelected>>', self.on_config_type_change)
        
        # Buttons on same line as dropdown
        self.create_btn = create_button(dropdown_frame, "Create Wells", 
                                      command=self.create_positions_in_setup, bold=True)
        self.create_btn.pack(side='right', padx=(5, 0))
        
        cancel_btn = create_button(dropdown_frame, "Cancel", 
                                 command=self.cancel_positions_in_setup)
        cancel_btn.pack(side='right', padx=(5, 0))
        
        # Status label above well selection
        self.positions_status_label = create_error_label(positions_frame, "")
        self.positions_status_label.pack(pady=5)
        
        # Well selection frame (initially hidden)
        self.well_selection_frame = tk.LabelFrame(positions_frame, 
                                                text="Well Selection", 
                                                bg=GUI_COLORS['frame'], 
                                                fg=GUI_COLORS['text'],
                                                font=GUI_FONTS['heading'])
    
    def cancel_positions_in_setup(self):
        """Cancel positions creation and return to welcome screen."""
        self.show_experimental_setup_welcome()
    
    def create_positions_in_setup(self):
        """Create positions and continue to experiment configuration."""
        self.log("Positions GUI: Create positions button clicked")
        selected_type = self.config_type_var.get()
        self.log(f"Positions GUI: Selected configuration type: {selected_type}")
        
        if not selected_type:
            self.positions_status_label.config(text="Please select a configuration type.", 
                                          fg=GUI_COLORS['status_error'])
            self.log("Positions GUI: No configuration type selected")
            return

        # Create positions object
        positions_obj = Positions(
            fov_info=self.scope.fov_info,
            offsets=self.scope.offsets,
            axis_mapping=self.scope.axis_mapping,
            limits=self.scope.limits,
            save_dir=self.file_handler.system_state_dir #FIXME should be the save path defined early on in the experiment
        )
        
        if selected_type in self.available_configs:
            # Handle existing plate configuration
            if not hasattr(self.well_selection_frame, 'plate_config'):
                self.positions_status_label.config(text="Please wait for the configuration to load.", 
                                              fg=GUI_COLORS['status_error'])
                return
            try:
                # Add ALL wells from plate config
                plate_config = self.well_selection_frame.plate_config
                for well_name, well_config in plate_config.items():
                    positions_obj.add_well(well_name, well_config)
                
                # Save positions to system
                self.experiment.positions = positions_obj.positions.copy()
                self.file_handler.save_positions(self.experiment.positions)
                
                self.log(f"Positions created successfully: {len(self.experiment.positions)} positions")
                
                self.positions_status_label.config(text=f"Successfully created {len(self.experiment.positions)} positions for {len(plate_config)} wells.", 
                                              fg=GUI_COLORS['status_success'])
                self.show_experiment_config_gui()
                
            except Exception as e:
                self.positions_status_label.config(text=f"Error creating positions: {str(e)}", 
                                              fg=GUI_COLORS['status_error'])
                self.log(f"Error creating positions: {e}", level='error')
        
        elif selected_type == 'Custom Grid':
            # Handle custom grid configuration
            if not hasattr(self.well_selection_frame, 'generated_wells'):
                self.positions_status_label.config(text="Please create wells first by clicking 'Create Wells'.", 
                                              fg=GUI_COLORS['status_error'])
                return
            try:
                # Add selected wells
                generated_wells = self.well_selection_frame.generated_wells
                apply_offset_correction = self.well_selection_frame.grid_vars['offset_correction'].get()
                
                self.log(f"Starting position creation for Custom Grid", level='debug')
                self.log(f"Generated wells available: {list(generated_wells.keys())}", level='debug')
                self.log(f"Apply offset correction: {apply_offset_correction}", level='debug')
                
                wells_added = 0
                positions_before = len(positions_obj.positions)
                for well_name, well_config in generated_wells.items():
                    self.log(f"Processing well: {well_name}", level='debug')
                    self.log(f"Well {well_name} config: {well_config}", level='debug')
                    
                    positions_before_well = len(positions_obj.positions)
                    positions_obj.add_well(well_name, well_config, apply_offset_correction)
                    positions_after_well = len(positions_obj.positions)
                    positions_added = positions_after_well - positions_before_well
                    
                    self.log(f"Well {well_name} added {positions_added} positions", level='debug')
                    wells_added += 1
                
                total_positions_added = len(positions_obj.positions) - positions_before
                self.log(f"Total wells added: {wells_added}", level='debug')
                self.log(f"Total positions added: {total_positions_added}", level='debug')
                self.log(f"Final positions DataFrame shape: {positions_obj.positions.shape}", level='debug')
                
                # Log detailed position information
                if not positions_obj.positions.empty:
                    self.log(f"Position details:", level='debug')
                    for well in positions_obj.positions['well'].unique():
                        well_positions = positions_obj.positions[positions_obj.positions['well'] == well]
                        self.log(f"Well {well}: {len(well_positions)} positions", level='debug')
                        self.log(f"Well {well} position names: {well_positions['position_name'].tolist()}", level='debug')
                
                # Save positions to system
                self.experiment.positions = positions_obj.positions.copy()
                self.file_handler.save_positions(self.experiment.positions)
                
                self.log(f"Positions created successfully: {len(self.experiment.positions)} positions")
                
                self.positions_status_label.config(text=f"Successfully created {len(self.experiment.positions)} positions for {len(generated_wells)} wells.", 
                                              fg=GUI_COLORS['status_success'])
                
                # Proceed to experiment configuration
                self.show_experiment_config_gui()
                
            except Exception as e:
                self.positions_status_label.config(text=f"Error creating positions: {str(e)}", 
                                              fg=GUI_COLORS['status_error'])
                self.log(f"Error creating positions: {e}", level='error')
        
        elif selected_type == 'Custom Manual':
            # Handle custom manual configuration
            if not hasattr(self.well_selection_frame, 'generated_wells'):
                self.positions_status_label.config(text="Please create wells first by clicking 'Create Wells'.", 
                                              fg=GUI_COLORS['status_error'])
                return
            
            try:
                # Add ALL generated wells
                generated_wells = self.well_selection_frame.generated_wells
                for well_name, well_config in generated_wells.items():
                    apply_offset_correction = well_config.get("apply_offset_correction", False)
                    # Remove the flag from config before passing to add_well
                    clean_config = {k: v for k, v in well_config.items() if k != "apply_offset_correction"}
                    positions_obj.add_well(well_name, clean_config, apply_offset_correction)
                
                # Save positions to system
                self.experiment.positions = positions_obj.positions.copy()
                self.file_handler.save_positions(self.experiment.positions)
                
                self.log(f"Positions created successfully: {len(self.experiment.positions)} positions")
                
                self.positions_status_label.config(text=f"Successfully created {len(self.experiment.positions)} positions for {len(generated_wells)} wells.", 
                                              fg=GUI_COLORS['status_success'])
                
                
                # Proceed to experiment configuration
                self.show_experiment_config_gui()
                
            except Exception as e:
                self.positions_status_label.config(text=f"Error creating positions: {str(e)}", 
                                              fg=GUI_COLORS['status_error'])
                self.log(f"Error creating positions: {e}", level='error')
        
        elif selected_type == 'Load Wells From File':
            # Handle load wells from file configuration
            if not hasattr(self.well_selection_frame, 'generated_file_wells'):
                self.positions_status_label.config(text="Please create wells first by clicking 'Create Wells'.", 
                                              fg=GUI_COLORS['status_error'])
                return
            
            try:
                # Load positions from files using the new method
                file_wells = self.well_selection_frame.generated_file_wells
                positions_obj.load_positions_from_files(file_wells)
                
                # Save positions to system
                self.experiment.positions = positions_obj.positions.copy()
                self.file_handler.save_positions(self.experiment.positions)
                
                self.log(f"Positions loaded successfully: {len(self.experiment.positions)} positions")
                
                self.positions_status_label.config(text=f"Successfully loaded {len(self.experiment.positions)} positions from {len(file_wells)} files.", 
                                              fg=GUI_COLORS['status_success'])
                
                # Proceed to experiment configuration
                self.show_experiment_config_gui()
                
            except Exception as e:
                self.positions_status_label.config(text=f"Error loading positions: {str(e)}", 
                                              fg=GUI_COLORS['status_error'])
                self.log(f"Error loading positions: {e}", level='error')
        
        elif selected_type == 'Load Positions From File':
            # Handle load positions from file configuration
            if not hasattr(self.well_selection_frame, 'loaded_positions_df'):
                self.positions_status_label.config(text="Please load positions first by clicking 'Load Positions'.", 
                                              fg=GUI_COLORS['status_error'])
                return
            
            try:
                # Use the loaded positions DataFrame directly
                loaded_positions_df = self.well_selection_frame.loaded_positions_df
                
                # Save positions to system
                self.experiment.positions = loaded_positions_df.copy()
                self.file_handler.save_positions(self.experiment.positions)
                
                self.log(f"Positions loaded successfully: {len(self.experiment.positions)} positions")
                
                num_positions = len(loaded_positions_df)
                num_wells = len(loaded_positions_df['well'].unique()) if 'well' in loaded_positions_df.columns else "Unknown"
                self.positions_status_label.config(text=f"Successfully loaded {num_positions} positions from {num_wells} wells.", 
                                              fg=GUI_COLORS['status_success'])
                
                # Proceed to experiment configuration
                self.show_experiment_config_gui()
                
            except Exception as e:
                self.positions_status_label.config(text=f"Error using loaded positions: {str(e)}", 
                                              fg=GUI_COLORS['status_error'])
                self.log(f"Error using loaded positions: {e}", level='error')
    
    def create_experiment_block(self, parent):
        """Create the experiment control block."""
        frame = tk.LabelFrame(parent, text="Experiment", 
                             bg=GUI_COLORS['frame'], fg=GUI_COLORS['text'], 
                             font=GUI_FONTS['heading'])
        frame.grid(row=0, column=0, sticky='nsew', padx=10, pady=10)
        frame.grid_propagate(False)  # Prevent frame from expanding beyond allocated space
        
        # Create main content area
        main_content_frame = tk.Frame(frame, bg=GUI_COLORS['frame'])
        
        # Control buttons (Create, Start, Stop, Reset) - separate from StatusPanel
        control_frame = tk.Frame(main_content_frame, bg=GUI_COLORS['frame'])
        control_frame.pack(fill='x', padx=5, pady=5)
        
        button_frame = tk.Frame(control_frame, bg=GUI_COLORS['frame'])
        button_frame.pack(side='left')
        
        self.create_btn = create_button(button_frame, "Create", 
                                      command=self.create_experiment)
        self.create_btn.pack(side='left', padx=(0, 10))
        
        self.start_btn = create_button(button_frame, "Start", 
                                     command=self.start_experiment)
        self.start_btn.pack(side='left', padx=(0, 10))
        self.start_btn.config(state='disabled')
        
        self.stop_btn = create_button(button_frame, "Stop", 
                                    command=self.stop_experiment)
        self.stop_btn.pack(side='left', padx=(0, 10))
        self.stop_btn.config(state='disabled')
        
        self.reset_btn = create_button(button_frame, "Reset", 
                                     command=self.reset_experiment)
        self.reset_btn.pack(side='left', padx=(0, 10))
        self.reset_btn.config(state='disabled')
        
        # Create StatusPanel for experiment status (pause button, progress bar, status)
        self.experiment_status_panel = StatusPanel(
            parent=main_content_frame,
            panel_name="",  # Empty name since we already have the main frame title
            system_name="Experiment",
            progress_info_type="experiment",
            pause_callback=lambda: self.pause_system_callback('experiment'),
            resume_callback=lambda: self.resume_system_callback('experiment'),
            launch_callback=lambda: self.launch_system_callback('experiment'),
            kill_callback=lambda: self.kill_system_callback('experiment'),
            create_frame=False, 
            file_handler=self.file_handler
        )
        self.experiment_status_panel.pack(fill='x', padx=5, pady=5)
        
        # Create StatePanel for experiment state display directly in the main content frame
        self.experiment_state_panel = StatePanel(
            parent_frame=main_content_frame,
            num_columns=2,
            data_source_func=lambda: self.get_system_state_data('experiment'),
            column_grouping_func=experiment_grouping,
            panel_name="",
            create_frame=False
        )
        
        main_content_frame.pack(fill='both', expand=True, padx=5, pady=5)
        self.update_experiment_info()
    
    def pause_system_callback(self, system_type):
        """Unified callback for system pause buttons."""
        self.log(f"{system_type.title()} paused")
    
    def resume_system_callback(self, system_type):
        """Unified callback for system resume buttons."""
        self.log(f"{system_type.title()} resumed")
    
    def launch_system_callback(self, system_type):
        """Unified callback for system launch buttons."""
        self.log(f"{system_type.title()} launched")
    
    def kill_system_callback(self, system_type):
        """Unified callback for system kill buttons."""
        self.log(f"{system_type.title()} killed")
    
    def start_update_thread(self): #FIXME
        """Start the background update thread."""
        self.running = True
        self.update_thread = threading.Thread(target=self.update_loop, daemon=True)
        self.update_thread.start()
    
    def update_loop(self):
        """Background loop to update GUI information."""
        while self.running:
            try:
                self.update_system_state_display('scope')
                self.update_system_state_display('fluidics')
                self.update_system_state_display('experiment')
                # self.update_experiment_info()
                self.update_progress_bars()
                self.update_status_labels()
                time.sleep(5)
                
            except Exception as e:
                self.log(f"Error in update loop: {e}", level='warning')
                time.sleep(5)
    
    def get_system_state_data(self, system_type):
        """Get state data for a specific system (fluidics, scope, or experiment)."""
        try:
            if system_type == 'fluidics':
                # Try to load from fluidics state file
                import os
                import json
                
                fluidics_state_file = os.path.join(self.file_handler.system_state_dir, "Fluidics_state.json")
                if os.path.exists(fluidics_state_file):
                    with open(fluidics_state_file, 'r') as f:
                        fluidics_state = json.load(f)
                    
                    # Convert to display format
                    display_data = {}
                    for key, value in fluidics_state.items():
                        if value is not None:
                            display_key = key.replace('_', ' ').title()
                            display_data[display_key] = str(value)
                    
                    if display_data:
                        return display_data
                
                # Return empty dict when no data is available
                return {}
                
            elif system_type == 'scope':
                # Use the new Scope_state property
                return self.file_handler.get_state("Scope")
                
            elif system_type == 'experiment':
                # Use the new Experiment_state property
                state = self.file_handler.get_state("Experiment")
                
                # Prepare display data from experiment state
                info_data = {}
                
                # Basic experiment info
                if 'experiment_name' in state:
                    info_data['Experiment'] = state['experiment_name']
                if 'user_name' in state:
                    info_data['User'] = state['user_name']
                if 'project_name' in state:
                    info_data['Project'] = state['project_name']
                # if 'save_path' in state:
                #     info_data['Save Path'] = state['save_path']
                if 'system_name' in state:
                    info_data['System'] = state['system_name']
                
                # Calculate derived values
                if 'group_assignments' in state:
                    num_wells = len(state['group_assignments'])
                    info_data['Wells'] = str(num_wells)
                
                # Add positions count if available from system
                positions_df = self.file_handler.Positions
                num_positions = len(positions_df) if not positions_df.empty else 0
                info_data['Positions'] = str(num_positions)
                
                # Add tasks count if available from system
                num_tasks = len(self.file_handler.get_tasks("Experiment")) if not self.file_handler.get_tasks("Experiment").empty else 0
                info_data['Tasks'] = str(num_tasks)
                
                # Add channels info
                if 'selected_channels' in state and state['selected_channels']:
                    channels_text = ", ".join(state['selected_channels'])
                    info_data['Channels'] = channels_text
                
                # Add protocols info
                if 'fluidics_protocols' in state and state['fluidics_protocols']:
                    protocols_text = ", ".join(state['fluidics_protocols'])
                    info_data['Protocols'] = protocols_text
                
                # Add number of hybes
                if 'num_hybes' in state:
                    info_data['Hybes'] = str(state['num_hybes'])
                
                return info_data
            else:
                self.log(f"Unknown system type: {system_type}", level='error')
                return {}
                
        except Exception as e:
            self.log(f"Error getting {system_type} state data: {e}", level='warning')
            return {}
    
    
    def update_system_state_display(self, system_type, state_data=None):
        """Update the state display for a specific system (scope, fluidics, or experiment)."""
        try:
            if system_type == 'scope':
                if hasattr(self, 'scope_state_panel'):
                    self.scope_state_panel.update_display()
            elif system_type == 'fluidics':
                if hasattr(self, 'fluidics_state_panel'):
                    self.fluidics_state_panel.update_display()
            elif system_type == 'experiment':
                if hasattr(self, 'experiment_state_panel'):
                    self.experiment_state_panel.update_display()
            else:
                self.log(f"Unknown system type: {system_type}", level='error')
                
        except Exception as e:
            self.log(f"Error updating {system_type} state display: {e}", level='warning')
    
    
    def update_experiment_info(self):
        """Update the experiment information display."""
        try:
            current_exp_name = getattr(self.experiment, 'experiment_name', None)
            current_user_name = getattr(self.experiment, 'user_name', None)
            current_project_name = getattr(self.experiment, 'project_name', None)
            
            if hasattr(self, '_last_exp_name') and hasattr(self, '_last_user_name') and hasattr(self, '_last_project_name'):
                if (self._last_exp_name == current_exp_name and 
                    self._last_user_name == current_user_name and
                    self._last_project_name == current_project_name):
                    return
            
            self._last_exp_name = current_exp_name
            self._last_user_name = current_user_name
            self._last_project_name = current_project_name
            
            self.root.after(0, self.update_experiment_control_display)
                
        except Exception as e:
            self.log(f"Error updating experiment info: {e}", level='warning')
    
    def get_progress_info(self, task_type):
        """Get progress information for fluidics, scope, or experiment tasks using FileHandler directly."""
        try:
            if task_type == 'fluidics':
                tasks_df = self.file_handler.get_tasks("Fluidics")
                current_idx = self.file_handler.get_task_idx("Fluidics")
            elif task_type == 'scope':
                tasks_df = self.file_handler.get_tasks("Scope")
                current_idx = self.file_handler.get_task_idx("Scope")
            elif task_type == 'experiment':
                tasks_df = self.file_handler.get_tasks("Experiment")
                current_idx = self.file_handler.get_task_idx("Experiment")
            else:
                return None
            
            # Check if task files exist and have content
            if tasks_df.empty:
                return None
            
            total_tasks = len(tasks_df)
            # Handle 1-based indexing: current_idx 1 means we're on task 1 of total_tasks
            # Progress should be (current_idx - 1) / total_tasks for 1-based indexing
            if current_idx == 0:
                # 0 means "waiting to start" - no progress
                progress_percent = 0
                remaining_tasks = total_tasks
            else:
                # 1-based indexing: current_idx 1 = task 1, current_idx 2 = task 2, etc.
                progress_percent = ((current_idx - 1) / total_tasks) * 100 if total_tasks > 0 else 0
                remaining_tasks = total_tasks - (current_idx - 1)
            
            # Calculate expected completion time based on elapsed time
            if current_idx > 0:
                # Estimate time per task based on current progress
                # This is a simple estimation - in practice you might want more sophisticated timing
                estimated_time_per_task = 30  # seconds (placeholder)
                estimated_remaining_time = remaining_tasks * estimated_time_per_task
            else:
                estimated_remaining_time = 0
            
            return {
                'current_task': current_idx,
                'total_tasks': total_tasks,
                'progress_percent': progress_percent,
                'estimated_remaining_time': estimated_remaining_time,
                'has_tasks': True
            }
            
        except Exception as e:
            print(f"Error getting progress info for {task_type}: {e}")
            return None

    def update_progress_bars(self):
        """Update progress bars for fluidics and scope tasks."""
        try:
            # Update fluidics progress
            fluidics_progress = self.get_progress_info('fluidics')
            if fluidics_progress and fluidics_progress['has_tasks']:
                self.root.after(0, lambda: self.fluidics_status_panel.update_progress(fluidics_progress))
            else:
                self.root.after(0, lambda: self.fluidics_status_panel.update_progress(None))
            
            # Update scope progress
            scope_progress = self.get_progress_info('scope')
            if scope_progress and scope_progress['has_tasks']:
                self.root.after(0, lambda: self.scope_status_panel.update_progress(scope_progress))
            else:
                self.root.after(0, lambda: self.scope_status_panel.update_progress(None))
            
            # Update experiment progress
            experiment_progress = self.get_progress_info('experiment')
            if experiment_progress and experiment_progress['has_tasks']:
                self.root.after(0, lambda: self.experiment_status_panel.update_progress(experiment_progress))
            else:
                self.root.after(0, lambda: self.experiment_status_panel.update_progress(None))
                
        except Exception as e:
            self.log(f"Error updating progress bars: {e}", level='warning')
    
    def update_status_labels(self):
        """Update status labels from file_handler for all panels."""
        try:
            # Update fluidics status
            self.root.after(0, lambda: self.fluidics_status_panel.refresh_status_from_file())
            # Update scope status
            self.root.after(0, lambda: self.scope_status_panel.refresh_status_from_file())
            # Update experiment status
            self.root.after(0, lambda: self.experiment_status_panel.refresh_status_from_file())
                
        except Exception as e:
            self.log(f"Error updating status labels: {e}", level='warning')
    
    def pause_system(self, system_type):
        """Pause a system (fluidics, scope, or experiment)."""
        try:
            # Map system types to their corresponding panels
            system_mapping = {
                'fluidics': self.fluidics_status_panel,
                'scope': self.scope_status_panel,
                'experiment': self.experiment_status_panel
            }
            
            if system_type not in system_mapping:
                self.log(f"Unknown system type: {system_type}", level='error')
                return
            
            status_panel = system_mapping[system_type]
            
            # Use the StatusPanel's pause method which handles previous status storage
            status_panel.pause()
            self.log(f"{system_type.title()} paused")
            
        except Exception as e:
            self.log(f"Error pausing {system_type}: {e}", level='error')
    
    def resume_system(self, system_type):
        """Resume a system (fluidics, scope, or experiment)."""
        try:
            # Map system types to their corresponding panels
            system_mapping = {
                'fluidics': self.fluidics_status_panel,
                'scope': self.scope_status_panel,
                'experiment': self.experiment_status_panel
            }
            
            if system_type not in system_mapping:
                self.log(f"Unknown system type: {system_type}", level='error')
                return
            
            status_panel = system_mapping[system_type]
            
            # Use the StatusPanel's resume method which restores previous status
            status_panel.resume()
            self.log(f"{system_type.title()} resumed")
            
        except Exception as e:
            self.log(f"Error resuming {system_type}: {e}", level='error')
    
    
    def create_experiment(self):
        """Create a new experiment."""
        try:
            self.log("GUI: Starting experiment creation...")
            self.experiment_status_panel.set_status("Creating...", GUI_COLORS['info'])
            self.root.update()
            
            # Show startup GUI in experimental setup panel
            self.show_startup_gui_in_setup()
            self.experiment_status_panel.set_status("Ready", GUI_COLORS['success'])
            self.log("GUI: Experiment creation started - use experimental setup panel to continue")
                
        except Exception as e:
            self.experiment_status_panel.set_status("Error", GUI_COLORS['error'])
            self.log(f"GUI: Error creating experiment: {e}", level='error')
    
    def start_experiment(self): #FIXME
        """Start the experiment."""
        try:
            self.experiment_status_panel.set_status("Starting...", GUI_COLORS['info'])
            self.root.update()
            
            # Set experiment task index to 1 when experiment starts (0 = waiting to start)
            self.file_handler.save_task_idx("Experiment", 1) #(0 = waiting to start)
            
            # Set status to Running
            self.file_handler.save_status("Experiment", "Running")
            
            self.experiment_status_panel.set_status("Running", GUI_COLORS['success'])
            self.log("Experiment started - task index set to 1")
            
        except Exception as e:
            self.experiment_status_panel.set_status("Start Error", GUI_COLORS['error'])
            self.log(f"Error starting experiment: {e}", level='error')
    
    def stop_experiment(self):
        """Stop the experiment."""
        self.experiment_status_panel.set_status("Not Implemented", GUI_COLORS['warning'])
        self.log("Stop experiment not implemented yet")
    
    def reset_experiment(self):
        """Reset the experiment and clear all system variables."""
        try:
            self.log("GUI: Resetting experiment...")
            self.experiment_status_panel.set_status("Resetting...", GUI_COLORS['info'])
            self.root.update()
            self.experiment = Experiment()
            self.clear_system_variables()
            self.reset_gui_to_startup()
            self.experiment_status_panel.set_status("Reset Complete", GUI_COLORS['success'])
            self.log("GUI: Experiment reset completed successfully")
            
        except Exception as e:
            self.experiment_status_panel.set_status("Reset Error", GUI_COLORS['error'])
            self.log(f"GUI: Error resetting experiment: {e}", level='error')
    
    def clear_system_variables(self):
        """Clear all experiment-related system variables."""
        try:
            self.clear_saved_files()
            self.update_system_state_display('experiment')
            
            
            # Update scope and fluidics state displays to show empty state
            self.update_system_state_display('scope')
            self.update_system_state_display('fluidics')
            
            self.log("System variables cleared successfully")
            
        except Exception as e:
            self.log(f"Error clearing system variables: {e}", level='error')
    
    def clear_saved_files(self):
        """Clear all saved system files."""
        try:
            import os
            #FUTURE : remove based on file type maybe with system prefix
            # Files to remove - all system state files
            #FIXME : remove based on file type maybe with system prefix
            files_to_remove = [
                'Experiment_state.json',
                'Positions.csv', 
                'Experiment_tasks.csv',
                'Experiment_task_idx.txt',
                'Experiment_status.txt',
                'Scope_state.json',
                'Scope_tasks.csv',
                'Scope_task_idx.txt', 
                'Scope_status.txt',
                'Fluidics_state.json',
                'Fluidics_tasks.csv',
                'Fluidics_task_idx.txt',
                'Fluidics_status.txt',
                'scope_task.txt'  # Scope task trigger file
            ]
            
            for filename in files_to_remove:
                filepath = os.path.join(self.file_handler.system_state_dir, filename)
                if os.path.exists(filepath):
                    os.remove(filepath)
                    self.log(f"Removed file: {filename}")
            
            # Reset status files to initial state
            self.file_handler.save_status("Experiment", "Idle")
            self.file_handler.save_status("Scope", "Idle") 
            self.file_handler.save_status("Fluidics", "Idle")
            
            self.log("All system files cleared and status reset to Idle")
            
        except Exception as e:
            self.log(f"Error clearing saved files: {e}", level='warning')
    
    def reset_gui_to_startup(self):
        """Reset GUI to startup state."""
        try:
            self.start_btn.config(state='disabled')
            self.stop_btn.config(state='disabled')
            self.reset_btn.config(state='disabled')
        
            self.show_experimental_setup_welcome()
            self.experiment_status_panel.set_status("Idle", GUI_COLORS['text_muted'])
            
            self.log("GUI reset to startup state")
            
        except Exception as e:
            self.log(f"Error resetting GUI: {e}", level='error')
    
    def on_closing(self):
        """Handle window closing."""
        try:
            self.running = False
            
            
            # Kill all launched instances
            if hasattr(self, 'scope_status_panel') and self.scope_status_panel.is_launched:
                self.scope_status_panel.kill()
            if hasattr(self, 'fluidics_status_panel') and self.fluidics_status_panel.is_launched:
                self.fluidics_status_panel.kill()
            if hasattr(self, 'experiment_status_panel') and self.experiment_status_panel.is_launched:
                self.experiment_status_panel.kill()
            
            self.root.destroy()
        except Exception as e:
            self.log(f"Error closing GUI: {e}", level='warning')
    
    def run(self):
        """Start the GUI main loop."""
        self.root.mainloop()


def create_experiment_gui(system='Cyan'):
    gui = SystemGUI(system=system)
    gui.run()


if __name__ == '__main__':
    create_experiment_gui(system='Cyan')
