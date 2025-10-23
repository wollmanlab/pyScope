
from Fluidics import *
from Fluidics.fluidics import Fluidics
import importlib

class CyanFluidics(Fluidics):
    def __init__(self,gui=False):
        super().__init__()  # call __init__ method of the super class
        self.verbose = True
        Protocol = getattr(importlib.import_module('SyringeProtocol'), 'SyringeProtocol')
        Pump = getattr(importlib.import_module('SyringePump_v2'), 'SyringePump_v2')
        Valve = getattr(importlib.import_module('ViciValve'), 'ViciValve')
        self.Protocol = Protocol(gui=gui)
        self.Pump = Pump('COM7',gui=gui)
        self.Valve = Valve('COM6',gui=gui)
        self.device = self.__class__.__name__
        self.Protocol.device = self.device
        self.Pump.device = self.device
        self.Valve.device = self.device
        self.Pump.wait_factor = 1/2
        self.Pump.speed_conversion = 1.9*(5/4) #s/mL

        self.Protocol.speed = 0.5#1
        self.Protocol.max_speed = 0.5#1
        self.Protocol.mixes = 0#3

        self.Protocol.closed_speed = 0.25
        self.Protocol.wait_factor = self.Pump.wait_factor
        self.Protocol.speed_conversion = self.Pump.speed_conversion
        self.Protocol.chamber_volume = 4
        self.Protocol.rinse_volume = 2
        self.Protocol.hybe_volume = 2
        self.Protocol.rinse_time = 2.5*60
        self.Protocol.hybe_time = 30*60
        self.Protocol.prime_volume = 3
        self.Protocol.vacume = False
        self.Valve_Commands = { 
                                'A':{'valve':1,'port':1},
                                'B':{'valve':1,'port':2},
                                'C':{'valve':1,'port':3},
                                'D':{'valve':1,'port':4},
                                'E':{'valve':1,'port':5},
                                'F':{'valve':1,'port':6},
                                'TBS':{'valve':1,'port':7},
                                'TCEP':{'valve':1,'port':8},
                                'WBuffer':{'valve':1,'port':9},
                                'Valve2':{'valve':1,'port':10},

                                'Valve3':{'valve':2,'port':1},
                                'Valve4':{'valve':2,'port':2},
                                'Waste':{'valve':2,'port':3},
                                'Air':{'valve':2,'port':4},
                                'Hybe1':{'valve':2,'port':5},
                                'Hybe2':{'valve':2,'port':6},
                                'Hybe3':{'valve':2,'port':7},
                                'Hybe4':{'valve':2,'port':8},
                                'Hybe5':{'valve':2,'port':9},
                                'Hybe6':{'valve':2,'port':10},
                                
                                'Hybe7':{'valve':3,'port':1},
                                'Hybe8':{'valve':3,'port':2},
                                'Hybe9':{'valve':3,'port':3},
                                'Hybe10':{'valve':3,'port':4},
                                'Hybe11':{'valve':3,'port':5},
                                'Hybe12':{'valve':3,'port':6},
                                'Hybe13':{'valve':3,'port':7},
                                'Hybe14':{'valve':3,'port':8},
                                'Hybe15':{'valve':3,'port':9},
                                'Hybe16':{'valve':3,'port':10},

                                'Hybe17':{'valve':4,'port':1},
                                'Hybe18':{'valve':4,'port':2},
                                'Hybe19':{'valve':4,'port':3},
                                'Hybe20':{'valve':4,'port':4},
                                'Hybe21':{'valve':4,'port':5},
                                'Hybe22':{'valve':4,'port':6},
                                'Hybe23':{'valve':4,'port':7},
                                'Hybe24':{'valve':4,'port':8},
                                'Hybe25':{'valve':4,'port':9},
                                '':{'valve':4,'port':10},
                            }