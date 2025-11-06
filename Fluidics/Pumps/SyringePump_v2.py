from Fluidics.Pumps.Pump import *
from fractions import Fraction
import numpy as np
import time
class SyringePump_v2(Pump):
    """Syringe pump v2 implementation using Arduino serial communication.
    
    Improved version with duty cycle-based speed control. Sends formatted
    serial messages to Arduino for pump control. Uses pin 5 for forward,
    pin 4 for reverse.
    
    Attributes:
        forward (int): Digital pin number for forward direction. Defaults to 5.
        reverse (int): Digital pin number for reverse direction. Defaults to 4.
        com_port (str): Serial COM port for Arduino communication.
        speed_conversion (float): Conversion factor from volume to time (sec/mL).
        wait_factor (float): Additional wait time factor after flow completes.
        serial (serial.Serial): Serial connection to Arduino.
    """
    
    def __init__(self, com_port, forward=5, reverse=4, gui=False):
        """Initialize SyringePump_v2 with Arduino connection.
        
        Args:
            com_port (str): Serial COM port (e.g., 'COM7').
            forward (int): Digital pin for forward direction. Defaults to 5.
            reverse (int): Digital pin for reverse direction. Defaults to 4.
            gui (bool): Whether GUI mode is enabled. If True, skips serial connection.
                Defaults to False.
        """
        super().__init__()
        self.forward = 5
        self.reverse = 4
        self.com_port = com_port
        # speed_conversion is mesaured by recording the time (seconds) the syringe pump takes to withdraw 1mL of water.
        # This value varies from pump to pump and must be mesaured for each new syringe pump.
        self.speed_conversion = 1.9*(5/4) # in the unit of sec/mL
        # wait_factor is for determining the extra amount of time to wait in addition to the theoretical duration.
        # The formual is: total_waiting = theoretical_duration+wait_factor*(volume*speed_conversion)
        self.wait_factor = 1/3
        if not gui:
            self.serial = serial.Serial(com_port, 9600, timeout=2)
    
    def flow(self, volume):
        """Execute pump flow using Arduino serial commands.
        
        Sends formatted serial message to Arduino with direction, speed (duty cycle),
        and duration. Waits for completion with buffer time.
        
        Args:
            volume (float): Volume to pump in mL.
        """
        # Abbreviate direction to minimize RAM usage on Arduino
        if self.direction=='Forward':
            direction = 'F'
        elif self.direction=='Reverse':
            direction = 'R'
        else:
            direction = 'U' 
            
        # Calculate the theoretical duration for the syringe pump to finish pumping.
        # Note that the speed here is actually duty cycle.
        duration = (float(volume)/float(self.speed))*self.speed_conversion

        # Translate user specification in to formatted message for Arduino. The format is @{direction}%{speed}_{duration}$!
        message = bytes("@{direction}%{speed}_{duration}$!".format(direction=direction, speed=self.speed,duration=duration), 'utf-8')
        # print(message)
        try:
            self.serial.write(message)
            self.serial.flush()
        except Exception as e:
            self.update_user(e)
            self.update_user('Failed to set pin.')
            pass
        
        time.sleep(1)

        # Send another message following the first message for stopping the syringe pump after finishing the job specified in the first message.
        message = bytes("@{direction}%{speed}_{duration}$!".format(direction='U', speed=self.speed,duration=duration), 'utf-8')
        print(message)
        try:
            self.serial.write(message)
            self.serial.flush()
        except Exception as e:
            self.update_user(e)
            self.update_user('Failed to set pin.')
            pass

        # Sleep for the theoretical duration plus some extra amount of buffer to ensure no further action before the syringe pump finishes the current job.
        time.sleep(duration+(float(volume)*self.speed_conversion)*self.wait_factor)


