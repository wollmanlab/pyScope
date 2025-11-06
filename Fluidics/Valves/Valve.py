import serial
import time
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from file_handler import FileHandler
class Valve:
    """Base class for valve control systems.
    
    Provides interface for selecting valve ports. Subclasses implement
    hardware-specific valve control protocols.
    
    Attributes:
        verbose (bool): Whether to log messages.
        current_port (dict): Dictionary mapping valve IDs to current port numbers.
        file_handler (FileHandler): FileHandler instance for logging.
    """
    
    def __init__(self, gui=False):
        """Initialize Valve base class.
        
        Args:
            gui (bool): Whether GUI mode is enabled. Defaults to False.
        """
        self.verbose=True # When in verbose mode, log() will record the input message to the log.
        self.current_port = {} # A dictionary for storing the currently selected port of each valve.
        sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        from file_handler import FileHandler
        self.file_handler = FileHandler()
        
    def log(self, message, level='info'):
        """Log messages using FileHandler's logging system."""
        if self.verbose:
            self.file_handler.log(message, level=level, system_prefix='Valve')

    def update_user(self,message,level=20):
        self.log(message)
    
    def set_port(self, valve, port):
        """Set port for specified valve.
        
        Args:
            valve (int): Valve ID.
            port (int): Port number to select.
        """
        self.current_port[valve] = port

    def get_port(self, valve):
        """Get currently selected port for specified valve.
        
        Args:
            valve (int): Valve ID.
        
        Returns:
            int: Currently selected port number.
        """
        return self.current_port[valve]


    


    


