import serial
import time
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from file_handler import FileHandler
class Valve:
    """
    Definition of the superclass Valve.
    """
    def __init__(self,gui=False):
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
    
    # self.set_port() is for selecting the specified port of the specified valve.
    def set_port(self,valve,port):
        self.current_port[valve] = port

    # self.get_port() is for getting the currently selected port of the specified valve. 
    def get_port(self,valve):
        return self.current_port[valve]


    


    


