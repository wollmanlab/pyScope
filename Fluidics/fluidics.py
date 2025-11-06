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
    def __init__(self,gui=False):
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
        """Log messages using FileHandler's logging system."""
        self.file_handler.log(message, level=level, system_prefix='Fluidics')

    def update_user(self,message,level='info',logger='Fluidics'):
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
    
    # decode_message() is for interpreting(spliting) the formated message read from XXXX_Staus.txt file into protocol, chambers, other
    def decode_message(self,message): #FIXME
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

    # execute_protocol() is for executing a protocol based on the protocol, chambers, other.
    # protocol: name of the protocol to execute.
    # chambers: the chambers where the protocol should be executed.
    # other: other necessary arguments to specify the protocol
    def execute_protocol(self,protocol,chambers,other):
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

    # flow() is for executing the most basic step of a protocol (one row of the Protocol dataframe) based on the column values.
    def flow(self,port,volume,speed,pause,direction):
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

    # set_port() is for selecting the port of a specific valve based on the port ID.
    # command: the port ID of the port to set (e.g. TBS, Hybe10, Hybe25,...)
    def set_port(self,command):
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

    # start_flow() is Pump class's start_flow with a sanity check of volume>0
    def start_flow(self,volume,direction,speed):
        if volume>0:
            self.update_state({
                'pump_direction': direction,
                'pump_volume': volume,
                'pump_speed': speed
            })
            self.Pump.start_flow(volume,direction,speed)
            self.update_state({'pump_direction': 'idle'})

    # sleep() is for waiting for t amount of time and updating user every 10sec.
    # t: amount of time to wait in the unit of sec.
    def sleep(self,t):
        if t>0:
            self.update_state({'pause': t})
            self.log('Wait '+str(round(t))+'s')
            for i in range(10):
                time.sleep(t/10)
                if t>0:
                    self.log(str(round((i+1)*10))+'% Complete')
            self.update_state({'pause': 0})

    # summarize_protocol() is for generating a summary of the steps by calculating total volume for each port and total estimated time.
    # steps: a dataframe to summarize where each row is one step
    def summarize_protocol(self,steps):
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


    
