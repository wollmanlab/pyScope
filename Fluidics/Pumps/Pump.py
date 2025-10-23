import serial
import time
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from file_handler import FileHandler
class Pump:
    """
    Definition of the superclass Pump.
    """
    def __init__(self,gui=False):
        self.verbose=True # When in verbose mode, log() will record the input message to the log. 
        self.direction = 'Forward'
        self.volume = 0 # In the unit of mL
        self.speed = 0 # In the unit of mL/sec
        sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        from file_handler import FileHandler
        self.file_handler = FileHandler()
        
    def log(self, message, level='info'):
        """Log messages using FileHandler's logging system."""
        if self.verbose:
            self.file_handler.log(message, level=level, system_prefix='Pump')
    def update_user(self,message,level=20):
        self.log(message)
    # self.start_flow() starts a 'flow' of liquid from the pump in user specified volume, direction and speed
    def start_flow(self,volume,direction,speed):
        self.set_direction(direction)
        self.set_speed(speed)
        self.flow(volume)
    
    # self.set_direction() is for setting the direction of the pump.
    def set_direction(self,direction):
        self.direction = direction

    # self.set_speed() is for setting the speed of the pump.
    def set_speed(self,speed):
        self.speed = speed
    
    # self.flow() needs to be overwritten (defined) when defining a subclass for specific type of pump
    def flow(self,volume):
        """ OVERWRITE"""

        


    


    


