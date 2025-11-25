from .scope import *

import importlib
class BlueScope(Scope):
    """Blue-specific microscope implementation.
    
    Inherits all functionality from Scope base class and configures
    Blue-specific parameters including stage limits, offsets, axis mapping,
    image dimensions, and pixel size.
    """
    
    def __init__(self, enable_core: bool = True):
        """Initialize the BlueScope class.
        
        Configures Blue-specific microscope parameters including stage limits,
        offsets, axis mapping, image shape, and pixel size. Updates channel
        limits from Blue-specific Micro-Manager configuration file.
        
        Note: Need to launch Chrolis Software then Micro-Manager before using this scope.
        
        Args:
            enable_core (bool): Whether to initialize Micro-Manager core connection.
                Defaults to True.
        """
        super().__init__(enable_core)
        self.config = {}
        self.config['MM_config_path'] = 'C:\GitRepos\pyScope\Configs\BlueScope_config.cfg'
        self.config['tolerance'] = {'X': 0.1, 'Y': 0.1, 'Z': 0.1,'Exposure': 0.1}
        self.config['limits'] = {
            'Y': (6500, 92500), 'X': (113000, 250000), 'Z': (0, 13000),
            'Shutter': (False, True),'Autoshutter': (False, True),
            'Exposure': (0, 10000), 'Binning': ['1', '2', '4'], 
            'Channel': ['FarRed', 'DeepBlue', 'Green', 'Orange'], 
            'Time': (0, 1e8)
        }
        # self.config['offsets'] = {'X': 0, 'Y': 0, 'Z': 0}
        self.config['offsets'] = {'X': 186000.0, 'Y': 49500.0, 'Z': 6500.0}
        # for key in self.config['offsets']:
            # self.config['offsets'][key] = (self.config['limits'][key][0] + self.config['limits'][key][1]) / 2
            
        self.config['axis_mapping'] = {'stage_x': 'plate_x', 'stage_y': 'plate_y'}
        self.config['ImageShape'] = np.array([3000,4096])
        self.config['PixelSize'] = 0.343
        self.tolerance = self.config['tolerance']
        self.limits = self.config['limits']
        self.offsets = self.config['offsets']
        self.axis_mapping = self.config['axis_mapping']
        self._update_channel_limits()
        
        self.log('BlueScope initialization complete')
