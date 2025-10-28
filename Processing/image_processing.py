import numpy as np
import torch
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
from file_handler import FileHandler

file_handler = FileHandler()

class ImageProcessor:
    def __init__(self, FF=None, constant=None, parameters=None):
        self.FF = FF if FF is not None else 1
        self.constant = constant if constant is not None else 0
        self.parameters = parameters if parameters is not None else self._default_parameters()
    
    def _default_parameters(self):
        return {
            'bin': 1,
            'process_img_before_FF': True,
            'highpass_sigma': 10,
            'highpass_smooth': 2,
            'highpass_function': 'rolling_ball',
            'highpass_smooth_function': 'median',
        }
    
    def process(self, img):
        if isinstance(img, str):
            img = tifffile.imread(img)
        img = img.astype(np.float32)
        return self._process_img(img)
    
    def load_image(self, img, FF=None, constant=None):
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
        if self.parameters['process_img_before_FF']:
            img = self._subtract_background(img)
            img = self._correct_optics(img)
        else:
            img = self._correct_optics(img)
            img = self._subtract_background(img)
        return img
    
    def _correct_optics(self, img):
        img = median_filter(img, 2)
        img = img - self.constant
        img = img * self.FF
        return img
    
    def _subtract_background(self, img):
        if self.parameters['highpass_smooth'] > 0:
            img = self._image_filter(img, self.parameters['highpass_smooth_function'], self.parameters['highpass_smooth'])
        if self.parameters['highpass_sigma'] > 0:
            bkg = self._image_filter(img, self.parameters['highpass_function'], self.parameters['highpass_sigma'])
            img = img - bkg
        img = np.clip(img, 0, None)
        return img
    
    def _image_filter(self, img, function, value, dtype=np.float32):
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
        else:
            img = 0*img.copy()
        return img.astype(dtype)

def load_file(path):
    if '.tif' in path:
        return tifffile.imread(path)
    if '.pt' in path:
        return torch.load(path)
    if '.npy' in path:
        return np.load(path)
    if '.csv' in path:
        return pd.read_csv(path)
    if '.txt' in path:
        return np.loadtxt(path)
    if '.json' in path:
        with open(path, 'r') as f:
            return json.load(f)
