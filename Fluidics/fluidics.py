import serial
import time
import pandas as pd
import numpy as np
import argparse
import importlib
import threading
import sys
import os
import ast
from math import floor,ceil
import json
# Adding all subdirectories in the directory of fluidics.py to the path of python.
dir = os.path.dirname(os.path.abspath(__file__))
for file in os.listdir(dir):
    if os.path.isdir(os.path.join(dir,file)):
        sys.path.append(os.path.join(dir,file))
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from Fluidics.Pumps.Pump import Pump as Pump
from Fluidics.Protocols.Protocol import Protocol as Protocol
from Fluidics.Valves.ViciValve import Valve as Valve
from file_handler import FileHandler

"""
    Definition of the superclass Fluidics
"""
class Fluidics(object):
    """Base class for fluidics control systems.
    
    Provides protocol execution, valve control, pump control, and file-based
    communication with other systems. Subclasses implement system-specific
    valve and pump configurations.
    
    Attributes:
        simulate (bool): Whether to run in simulation mode (no hardware control).
        file_handler (FileHandler): FileHandler instance for state management.
        device (str): Device name (class name).
        last_message (str): Last status message received.
        Valve_Commands (dict): Dictionary mapping port IDs to valve/port numbers.
        busy (bool): Whether system is currently executing a protocol.
        state (dict): Current system state (ports, pump status, etc.).
    """
    
    def __init__(self, gui=False):
        """Initialize Fluidics base class.
        
        Args:
            gui (bool): Whether to enable GUI (not used in base class).
                Defaults to False.
        """
        self.simulate = False
        self.file_handler = FileHandler()
        self.device = self.__class__.__name__
        self.last_message = "" # The latest message from other software
        self.Valve_Commands = {} # A dictionary for mapping port ID to specific port, see any subclass of Fluidics for examples.
        self.busy=False # Whether the fluidics is busy with running a protocol
        self.state = {
            'current_port': None,
            'pump_direction': 'idle',  # 'forward', 'reverse', 'idle'
            'pump_volume': None,
            'pump_speed': None
        }

    def log(self, message, level='info'):
        """Log messages using FileHandler's logging system.
        
        Args:
            message (str): Message to log.
            level (str): Log level ('debug', 'info', 'warning', 'error').
                Defaults to 'info'.
        """
        self.file_handler.log(message, level=level, system_prefix='Fluidics')

    def update_user(self,message,level='info',logger='Fluidics'):
        """Update user with log message (supports numeric or string log levels).
        
        Converts numeric log levels (10, 20, 30, 40, 50) to string levels
        if logger parameter is an integer.
        
        Args:
            message (str): Message to log.
            level (str or int): Log level. If logger is int, level is converted
                from numeric (10=debug, 20=info, 30=warning, 40=error, 50=critical).
                Defaults to 'info'.
            logger (str or int): Logger name or numeric level. If int, level
                parameter is treated as logger name. Defaults to 'Fluidics'.
        """
        level_mapper = {
            10: 'debug',
            20: 'info',
            30: 'warning',
            40: 'error',
            50: 'critical'
        }
        if isinstance(logger,int):
            level = level_mapper[level]
        else:
            level = level
        self.file_handler.log(message, level=level, system_prefix=logger)

    def continuous_monitoring(self):
        """Continuous monitoring of fluidics system status.
        
        Polls system status every second and logs changes. Stops when user
        initiates 'Stop' command.
        """
        self.last_message = ''
        self.log('Continuous monitoring started')
        try:
            while True:
                status = self.status
                if self.last_message!=status:
                    self.last_message = status
                    self.log(f"New Message: {status}")
                if status == "Stop":
                    self.log('Continuous monitoring stopped by user')
                    break
                elif "Command" in status:
                    self.interpret_command(status)
                time.sleep(1)
        finally:
            self.status = "offline"
            self.log('Continuous monitoring terminated - status set to offline')

    def interpret_command(self, current_message):
        """Interpret message from other software.
        
        Args:
            current_message (str): Message to interpret.
        """
        """Interpret message from other software."""
        self.log(f"Interpreting Command: {current_message}")
        self.busy = True
        # interpret message
        message = current_message.split(':')[-1]
        self.status = "Running:"+message
        protocol,chambers,other = self.decode_message(message)
        self.execute_protocol(protocol,chambers,other)
        self.status = "Finished:"+message
        self.busy = False

    @property
    def status(self):
        """Get fluidics status from file handler."""
        return self.file_handler.get_status("Fluidics", read_only=False)

    @status.setter
    def status(self, value):
        """Set fluidics status and save to file handler."""
        self.file_handler.save_status("Fluidics", value)

    def update_state(self, state_updates=None):
        """Update the fluidics state dictionary."""
        try:
            if state_updates is not None:
                self.state.update(state_updates)
                # Check if current_port was updated and add well/solution keys
                if 'current_port' in state_updates:
                    port = state_updates['current_port']
                    if len(port) == 1:
                        self.state['well'] = port
                    else:
                        self.state['solution'] = port
            self.file_handler.save_state("Fluidics",self.state)     
            # self.file_handler.save_state("Fluidics", self._reorder_state_for_saving())()
        except Exception as e:
            self.log(f'Error updating state: {e}', level='warning')
    
    def _reorder_state_for_saving(self):
        """Reorder state dictionary to ensure pump keys are first, valve keys are last."""
        all_keys = list(self.state.keys())
        ordered_keys = []
        for key in all_keys:
            if 'pump' in str(key).lower():
                ordered_keys.append(key)
        for key in all_keys:
            if key in ordered_keys:
                continue
            if 'valve' in str(key).lower():
                ordered_keys.append(key)
        for key in all_keys:
            if key in ordered_keys:
                continue
            ordered_keys.append(key)
        ordered_state = {key: self.state[key] for key in ordered_keys}
        return ordered_keys
        # Separate keys into three categories
        pump_keys = {}
        valve_keys = {}
        other_keys = {}
        
        for key, value in self.state.items():
            if 'pump' in key.lower():
                pump_keys[key] = value
            elif key.startswith('Valve'):
                valve_keys[key] = value
            else:
                other_keys[key] = value
        
        # Create ordered dictionary: pump keys first, other keys middle, valve keys last
        ordered_state = {}
        ordered_state.update(pump_keys)
        ordered_state.update(other_keys)
        ordered_state.update(valve_keys)
        
        return ordered_state
    
    def decode_message(self, message):
        """Decode command message into protocol, chambers, and other parameters.
        
        Parses formatted message string into components. Handles simulation mode
        flag ('!') and special protocols (Flush, Prime, Clean).
        
        Args:
            message (str): Formatted message string.
                Format: "Protocol*[Chambers]*Other" or "Protocol*[Chambers]*Other!"
                '!' suffix enables simulation mode.
        
        Returns:
            tuple: (protocol, chambers, other) where:
                - protocol (str): Protocol name
                - chambers (list or dict): Chamber list or Valve_Commands dict
                - other (str): Additional parameters
        """
        protocol,chambers,other = message.split('*')
        if '!' in other:
            other = other.split('!')[0]
            self.simulate = True
            self.Protocol.simulate = True
        if '+' in other:
            if other.split('+')[-1] =='':
                other = other.split('+')[0]
        # chambers = chambers[1:-1].split(',')
        chambers = ast.literal_eval(chambers)
        if 'Flush' in protocol:
            chambers = self.Valve_Commands
        if 'Prime' in protocol:
            chambers = self.Valve_Commands
        if 'Clean' in protocol:
            chambers = self.Valve_Commands
        return protocol,chambers,other

    def execute_protocol(self, protocol, chambers, other):
        """Execute a fluidics protocol.
        
        Retrieves protocol steps, saves tasks, executes each step, and cleans up
        task files upon completion. Supports simulation mode for testing.
        
        Args:
            protocol (str): Name of the protocol to execute.
            chambers (list or dict): Chambers where protocol should be executed.
            other (str): Additional protocol parameters.
        """
        steps = self.Protocol.get_steps(protocol,chambers,other) # Same as Tasks 
        if not isinstance(steps,pd.DataFrame):
            self.log('Unknown Protocol: '+str(protocol))
        else:
            # Set status to Running when protocol starts
            # self.status = "Running"
            self.file_handler.save_tasks("Fluidics", steps)
            
            self.summarize_protocol(steps)
            if not self.simulate:
                for idx,step in steps.iterrows():
                    # Update task index for progress tracking
                    self.file_handler.save_task_idx("Fluidics", idx)
                    # self._update_task_index(idx)
                    self.log(f"step {idx}")
                    self.log(pd.DataFrame(step).T)
                    if step.direction == 'Wait':
                        if step.pause<100:
                            time.sleep(step.pause)
                        else:
                            t = step.pause
                            self.log('Wait '+str(round(t))+'s')
                            for i in range(10):
                                time.sleep(t/10)
                                if t>0:
                                    self.log(str(round((i+1)*10))+'% Complete')
                    else:
                        if not self.flow(step.port,step.volume,step.speed,step.pause,step.direction):
                            self.log('Flow stopped due to status check')
                            break
            else:
                time.sleep(1) # wait 0.5 minutes
        
        # Clean up task files after protocol completion (both real and simulated)
        self.file_handler.save_task_idx("Fluidics", 0)
        self.file_handler.delete_tasks("Fluidics")
        self.status = "Idle"

        self.simulate = False
        self.Protocol.simulate = False

    def flow(self, port, volume, speed, pause, direction):
        """Execute a single flow step (basic protocol operation).
        
        Sets valve port, starts pump flow, and waits for specified pause time.
        Checks status before each operation and can be interrupted by 'Stop' status.
        
        Args:
            port (str): Port ID to set valve to.
            volume (float): Volume to pump in mL.
            speed (float): Pump speed parameter.
            pause (float): Pause time after flow in seconds.
            direction (str): Flow direction ('forward', 'reverse', 'Wait').
        
        Returns:
            bool: True if flow completed successfully, False if stopped by status check.
        """
        self.log(f"FLOW :::flow {port} {volume} {speed} {pause} {direction}")
        self.update_state({'current_port': port})
        
        # Check status before each operation
        if self.status == "Stop":
            self.log('Status is Stop - skipping flow step')
            return False
            
        self.set_port(port)
        
        if self.status == "Stop":
            self.log('Status is Stop - skipping start_flow')
            return False
            
        self.start_flow(volume,direction,speed)
        
        if self.status == "Stop":
            self.log('Status is Stop - skipping sleep')
            return False
            
        self.sleep(pause)
        
        return True

    def set_port(self, command):
        """Set valve port based on port ID command.
        
        Looks up valve and port number from Valve_Commands dictionary and sets
        valve position. Handles cascading valve selection for special port IDs
        like "ValveN" that trigger multiple valve changes.
        
        Args:
            command (str): Port ID (e.g., 'TBS', 'Hybe10', 'Valve2').
                Special IDs like 'Valve2' can trigger cascading valve changes.
        """
        if not command in self.Valve_Commands.keys():
            self.log('Unknown Tube: '+command)
        else:
            # self.log('Tube: '+command)
            # Look up and select the valve and port number corresponding to the input port ID
            valve_num = int(self.Valve_Commands[command]['valve'])
            port_num = int(self.Valve_Commands[command]['port'])
            self.Valve.set_port(valve_num-1, port_num-1)
            self.update_state({f'Valve{valve_num}': f'Port{port_num}'})
            # This while loop to be a trick for selecting a series of valves based on special port ID naming "ValveN".
            # See NinjaFluidics.py, RonageFLuidics.py, and PurpleFluidics.py for an example where the command Valve2 can select both Valve2 and Valve3
            command = 'Valve'+str(valve_num)
            while command in self.Valve_Commands.keys():
                valve_num = int(self.Valve_Commands[command]['valve'])
                port_num = int(self.Valve_Commands[command]['port'])
                self.Valve.set_port(valve_num-1, port_num-1)
                self.update_state({f'Valve{valve_num}': f'Port{port_num}'})
                command = 'Valve'+str(valve_num)

    def start_flow(self, volume, direction, speed):
        """Start pump flow with volume and speed parameters.
        
        Updates state and calls Pump.start_flow() if volume > 0.
        Sets pump_direction back to 'idle' after flow completes.
        
        Args:
            volume (float): Volume to pump in mL. Must be > 0.
            direction (str): Flow direction ('forward', 'reverse').
            speed (float): Pump speed parameter.
        """
        if volume>0:
            self.update_state({
                'pump_direction': direction,
                'pump_volume': volume,
                'pump_speed': speed
            })
            self.Pump.start_flow(volume,direction,speed)
            self.update_state({'pump_direction': 'idle'})

    def sleep(self, t):
        """Wait for specified time with progress updates.
        
        Updates user every 10% of wait time. Updates state with pause duration.
        
        Args:
            t (float): Time to wait in seconds.
        """
        if t>0:
            self.update_state({'pause': t})
            self.log('Wait '+str(round(t))+'s')
            for i in range(10):
                time.sleep(t/10)
                if t>0:
                    self.log(str(round((i+1)*10))+'% Complete')
            self.update_state({'pause': 0})

    def summarize_protocol(self, steps):
        """Generate summary of protocol steps.
        
        Calculates total volume per port and estimated total time.
        Logs summary information in human-readable format.
        
        Args:
            steps (pd.DataFrame): Protocol steps DataFrame with columns:
                port, volume, direction, time_estimate.
        """
        self.log('Protocol Summary')
        ports = np.unique(steps['port'])
        for port in ports:
            if len(port)>1:
                total_volume = np.sum([float(i) for i in steps[(steps['port']==port)&(steps['direction']=='Reverse')]['volume']])
                if total_volume>0:
                    self.log('Port: '+str(port)+'  Total Volume: '+str(total_volume)+'mL')
        total_time= np.sum([float(i) for i in steps['time_estimate'] if i!=''])
        if total_time<60:
            self.log('Estimated Total Time: '+str(int(total_time))+'s')
        elif total_time<60*60:
            minutes = floor(total_time/60)
            total_time = total_time-(minutes*60)
            self.log('Estimated Total Time: '+str(int(minutes))+'m'+str(int(total_time))+'s')
        else:
            hours = floor(total_time/(60*60))
            total_time = total_time-(hours*60*60)
            minutes = floor(total_time/60)
            total_time = total_time-(minutes*60)
            self.log('Estimated Total Time: '+str(int(hours))+'h'+str(int(minutes))+'m'+str(int(total_time))+'s')

# Load the subclass selected by user.
if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--fluidics_class", type=str, dest="fluidics_class", default="Fluidics", action='store', help="Which Fluidics Class to use")
    args = parser.parse_args()

    fluidics_class = args.fluidics_class
    system_prefix = fluidics_class.lower().split('fluidics')[0].capitalize()
    module = importlib.import_module(f"{system_prefix.lower()}fluidics")
    class_name = f"{system_prefix}Fluidics"
    fluidics_class = getattr(module, class_name)
    self = fluidics_class(gui=False)
    while True:
        self.continuous_monitoring()


    
