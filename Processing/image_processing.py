import numpy as np
# import torch
import tifffile
import pandas as pd
import sys
import json
import itertools
from scipy.ndimage import gaussian_filter, median_filter, minimum_filter, percentile_filter
from scipy import ndimage
from scipy import interpolate
from skimage import restoration
from skimage.measure import block_reduce
from scipy.interpolate import RectBivariateSpline
# from file_handler import FileHandler

# file_handler = FileHandler()

class ImageProcessor:
    """Image processing pipeline for fluorescence microscopy images.
    
    Provides background subtraction, flat-field correction, and various filtering
    operations. Supports configurable processing order and multiple filtering methods.
    
    Attributes:
        FF (np.ndarray or float): Flat-field correction array or scalar.
        constant (float): Constant offset to subtract from images.
        parameters (dict): Processing parameters dictionary.
    """
    
    def __init__(self, FF=None, constant=None, parameters=None):
        """Initialize ImageProcessor with flat-field and processing parameters.
        
        Args:
            FF (np.ndarray or float, optional): Flat-field correction array or scalar.
                If None, defaults to 1. Defaults to None.
            constant (float, optional): Constant offset to subtract. If None, defaults to 0.
                Defaults to None.
            parameters (dict, optional): Processing parameters dictionary. If None,
                uses default parameters. Defaults to None.
        """
        self.FF = FF if FF is not None else 1
        self.constant = constant if constant is not None else 0
        self.parameters = parameters if parameters is not None else self._default_parameters()
    
    def _default_parameters(self):
        """Get default processing parameters.
        
        Returns:
            dict: Default parameters dictionary with keys:
                - bin: Downsampling factor
                - process_img_before_FF: Order of processing steps
                - highpass_sigma: Background subtraction sigma
                - highpass_smooth: Smoothing before background subtraction
                - highpass_function: Background method name
                - highpass_smooth_function: Smoothing method name
        """
        return {
            'bin': 1,
            'process_img_before_FF': True,
            'highpass_sigma': 10,
            'highpass_smooth': 2,
            'highpass_function': 'rolling_ball',
            'highpass_smooth_function': 'median',
        }
    
    def process(self, img):
        """Process an image through the processing pipeline.
        
        Applies background subtraction and flat-field correction according to
        configured parameters.
        
        Args:
            img (np.ndarray or str): Image array or file path to image.
        
        Returns:
            np.ndarray: Processed image array (float32).
        """
        if isinstance(img, str):
            img = tifffile.imread(img)
        img = img.astype(np.float32)
        return self._process_img(img)
    
    def load_image(self, img, FF=None, constant=None):
        """Load image from file and apply processing pipeline.
        
        Args:
            img (str): Image file path.
            FF (str or np.ndarray, optional): Flat-field correction image file path or array.
                If None, defaults to 1. Defaults to None.
            constant (float, optional): Constant offset to subtract. If None, defaults to 0.
                Defaults to None.
        """
        if isinstance(img, str):
            img = load_file(img)
        img = img.astype(self.parameters['numpy_dtype'])
        
        if FF is not None:
            if isinstance(FF, str):
                self.FF = load_file(FF)
            else:
                self.FF = FF
        if constant is not None:
            if isinstance(constant, str):
                self.constant = load_file(constant)
            else:
                self.constant = constant
        
        if self.parameters['bin'] > 1:
            img = self._fast_median_bin(img, bin=self.parameters['bin'])
        
        img = self._process_img(img)
        return img
    
    def _fast_median_bin(self, stk, bin=2):
        """ Downsample image using median binning.
        Reduces image size by binning pixels and taking median value.
        Image dimensions must be divisible by bin factor.
        
        Args:
            stk (np.ndarray): Image array (2D or 3D).
            bin (int): Binning factor. Defaults to 2.
        
        Returns:
            np.ndarray: Downsampled image array.
        
        Raises:
            ValueError: If image dimensions are not divisible by bin.
        """
        if stk.shape[0] % bin != 0 or stk.shape[1] % bin != 0:
            raise ValueError(f"Image dimensions must be divisible by {bin} for downsampling.")
        if len(stk.shape) == 2:
            reshaped = stk.reshape(stk.shape[0] // bin, bin, stk.shape[1] // bin, bin)
            output = np.median(reshaped, axis=(1, 3))
        else:
            output = np.zeros([stk.shape[0]//bin, stk.shape[1]//bin, stk.shape[2]], dtype=stk.dtype)
            for i in range(stk.shape[2]):
                img = stk[:,:,i].copy()
                reshaped = img.reshape(img.shape[0] // bin, bin, img.shape[1] // bin, bin)
                img = np.median(reshaped, axis=(1, 3))
                output[:,:,i] = img
        return output
    
    def _process_img(self, img):
        """Apply processing pipeline to image.
        
        Applies background subtraction and flat-field correction in order
        determined by parameters['process_img_before_FF'].
        
        Args:
            img (np.ndarray): Image array to process.
        
        Returns:
            np.ndarray: Processed image array.
        """
        if self.parameters['process_img_before_FF']:
            img = self._subtract_background(img)
            img = self._correct_optics(img)
        else:
            img = self._correct_optics(img)
            img = self._subtract_background(img)
        return img
    
    def _correct_optics(self, img):
        """Apply flat-field correction and constant offset.
        
        Applies median filter, subtracts constant, and multiplies by flat-field.
        
        Args:
            img (np.ndarray): Image array to correct.
        
        Returns:
            np.ndarray: Corrected image array.
        """
        img = median_filter(img, 2)
        img = img - self.constant
        img = img * self.FF
        return img
    
    def _subtract_background(self, img):
        """Subtract background using high-pass filtering.
        
        Applies smoothing filter (if configured) and high-pass filter to
        estimate and subtract background.
        
        Args:
            img (np.ndarray): Image array to process.
        
        Returns:
            np.ndarray: Background-subtracted image array (clipped to non-negative).
        """
        if self.parameters['highpass_smooth'] > 0:
            img = self._image_filter(img, self.parameters['highpass_smooth_function'], self.parameters['highpass_smooth'])
        if self.parameters['highpass_sigma'] > 0:
            bkg = self._image_filter(img, self.parameters['highpass_function'], self.parameters['highpass_sigma'])
            img = img - bkg
        img = np.clip(img, 0, None)
        return img
    
    def _image_filter(self, img, function, value, dtype=np.float32):
        """Apply various image filtering operations.
        
        Supports multiple filter types: gaussian, median, minimum, percentile,
        rolling_ball, spline interpolation, and polynomial fitting.
        
        Args:
            img (np.ndarray): Image array to filter.
            function (str): Filter function name (e.g., 'gaussian', 'median', 'rolling_ball').
            value: Filter parameter value (sigma, size, etc.).
            dtype: Output data type. Defaults to np.float32.
        
        Returns:
            np.ndarray: Filtered image array.
        """
        if 'robust' in function:
            if '[' in function:
                vmin = int(function.split('[')[-1].split(',')[0])
                vmax = int(function.split(']')[0].split(',')[-1])
            else:
                vmin = 5
                vmax = 95
            vmin, vmax = np.percentile(img.ravel(), [vmin, vmax])
            img = np.clip(img, vmin, vmax)
        if 'gaussian' in function:
            img = gaussian_filter(img, value)
        elif function == 'median':
            img = median_filter(img, value)
        elif function == 'minimum':
            img = minimum_filter(img, size=value)
        elif 'percentile' in function:
            img = percentile_filter(img, int(function.split('_')[-1]), size=value)
        elif 'rolling_ball' in function:
            img = gaussian_filter(restoration.rolling_ball(gaussian_filter(img, value/5), radius=value, num_threads=30), value)
        elif 'spline' in function:
            new_width = int(value.split('|')[0])
            new_height = int(value.split('|')[1])
            original_width, original_height = img.shape
            original_width_posibilites = np.array([i for i in range(1, original_width) if (original_width/i).is_integer()])
            original_height_posibilites = np.array([i for i in range(1, original_height) if (original_height/i).is_integer()])
            new_width = original_width_posibilites[np.argmin(np.abs(original_width_posibilites-new_width))]
            new_height = original_height_posibilites[np.argmin(np.abs(original_height_posibilites-new_height))]
            block_size = np.array([new_width, new_height])

            if 'mean' in function:
                img_sml = block_reduce(img, tuple(block_size), np.mean)
            elif 'median' in function:
                img_sml = block_reduce(img, tuple(block_size), np.median)
            elif 'max' in function:
                img_sml = block_reduce(img, tuple(block_size), np.max)
            elif 'min' in function:
                img_sml = block_reduce(img, tuple(block_size), np.min)
            elif 'percentile' in function:
                percentile = 50
                if 'percentile_' in function:
                    percentile = float(function.split('percentile_')[-1]).split('_')[0]
                img_sml = block_reduce(img, tuple(block_size), np.percentile, func_kwargs={'q': percentile})
            else:
                img_sml = block_reduce(img, tuple(block_size), np.mean)

            if 'smooth' in function:
                img_sml = gaussian_filter(img_sml, 1)
            
            x = np.arange(img.shape[1])
            y = np.arange(img.shape[0])
            x_sml, y_sml = np.meshgrid(np.linspace(0, img.shape[1], img_sml.shape[1]), np.linspace(0, img.shape[0], img_sml.shape[0]))
            x = np.arange(original_height)
            y = np.arange(original_width)
            grid_x, grid_y = np.meshgrid(x, y)
            interpolator = RectBivariateSpline(y_sml[:, 0], x_sml[0], img_sml, kx=1, ky=1)
            img = interpolator.ev(grid_y, grid_x)

        elif 'polyfit' in function:
            function, degrees = function.split('_')
            degrees = int(degrees)
            x = gaussian_filter(np.percentile(img, value, axis=0), 1)
            y = gaussian_filter(np.percentile(img, value, axis=1), 1)
            x = np.poly1d(np.polyfit(range(x.shape[0]), x, degrees))(range(x.shape[0]))
            y = np.poly1d(np.polyfit(range(y.shape[0]), y, degrees))(range(y.shape[0]))
            img = ((np.ones_like(img)*x) + (np.ones_like(img).T*y).T) / 2
        elif 'none' in function:
            img = img.copy()
        else:
            img = 0*img.copy()
        return img.astype(dtype)

def load_file(path):
    """Load file from various formats.
    
    Supports .tif, .npy, .csv, .txt, and .json file formats.
    
    Args:
        path (str): File path to load.
    
    Returns:
        Loaded data (type depends on file format):
            - .tif: np.ndarray (via tifffile)
            - .npy: np.ndarray (via np.load)
            - .csv: pd.DataFrame (via pd.read_csv)
            - .txt: np.ndarray (via np.loadtxt)
            - .json: dict or list (via json.load)
    """
    if '.tif' in path:
        return tifffile.imread(path)
    if '.npy' in path:
        return np.load(path)
    if '.csv' in path:
        return pd.read_csv(path)
    if '.txt' in path:
        return np.loadtxt(path)
    if '.json' in path:
        with open(path, 'r') as f:
            return json.load(f)
