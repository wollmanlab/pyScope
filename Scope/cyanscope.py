from .scope import *

import importlib
class CyanScope(Scope):
    """
    CyanScope class inherits all methods from Scope class.
    This class can be extended with cyan-specific functionality if needed.
    """
    
    def __init__(self,enable_core: bool = True):
        """
        Initialize the CyanScope class.
        Notes : Need to launch Chrolis Software then Micro-Manager before using this scope.
        Args:
            system_state_dir (str): Directory path for system state files
            enable_core (bool): Whether to initialize Micro-Manager core connection
        """
        super().__init__(enable_core)
        self.config = {}
        self.config['MM_config_path'] = 'C:\GitRepos\pyScope\Configs\CyanScope_config.cfg'
        self.config['tolerance'] = {'X': 0.1, 'Y': 0.1, 'Z': 0.1,'Exposure': 0.1}
        self.config['limits'] = {
            'X': (6500, 92500), 'Y': (113000, 250000), 'Z': (0, 13000), 
            'Exposure': (0, 10000), 'Binning': ['1', '2', '4'], 
            'Channel': ['FarRed', 'DeepBlue', 'Green', 'Orange'], 
            'Time': (0, 1e8)
        }
        self.config['offsets'] = {'X': 0, 'Y': 0, 'Z': 0}
        self.config['axis_mapping'] = {'stage_x': 'plate_x', 'stage_y': 'plate_y'}
        self.config['ImageShape'] = np.array([4096,3000])
        self.config['PixelSize'] = 0.343
        self.tolerance = self.config['tolerance']
        self.limits = self.config['limits']
        self.offsets = self.config['offsets']
        self.axis_mapping = self.config['axis_mapping']
        
        self.log('CyanScope initialization complete')
