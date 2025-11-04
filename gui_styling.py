"""
GUI Styling Configuration

This module contains GUI styling constants and functions that can be imported
without circular dependencies. It's separated from gui.py to avoid circular imports
when Scope modules need to use GUI styling.
"""
import tkinter as tk
from tkinter import ttk

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
    
    # Configure dark style for progress bar with green fill on white background
    style.configure('Dark.Horizontal.TProgressbar',
                   background='#4CAF50',  # Green color for progress fill
                   troughcolor=GUI_COLORS['combobox'],  # White background
                   borderwidth=0,
                   lightcolor='#4CAF50',
                   darkcolor='#4CAF50')
    
    return style

