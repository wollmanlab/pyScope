
import numpy as np
import itertools

def whiten(img, sigma):
    """Apply Laplacian of Gaussian whitening filter to image.
    
    Converts image to float32 and applies Gaussian Laplacian filter for
    frequency-domain whitening, useful for registration preprocessing.
    
    Args:
        img (np.ndarray): Input image array.
        sigma (float): Gaussian sigma parameter for Laplacian filter.
    
    Returns:
        np.ndarray: Whitened image array (float32).
    """
    from skimage.util import img_as_float32
    img = img_as_float32(img)
    from scipy.ndimage import gaussian_laplace
    output = gaussian_laplace(img, sigma)
    return output

def window(img):
    """Apply Hanning window to image.
    
    Multiplies image by 2D Hanning window to reduce edge artifacts.
    
    Args:
        img (np.ndarray): Input 2D image array.
    
    Returns:
        np.ndarray: Windowed image array.
    
    Raises:
        AssertionError: If image is not 2D.
    """
    assert img.ndim == 2
    return img * get_window(img.shape)

def get_window(shape):
    """Generate 2D Hanning window.
    
    Creates a 2D Hanning window by taking outer product of 1D Hanning windows.
    
    Args:
        shape (tuple): Window shape (height, width).
    
    Returns:
        np.ndarray: 2D Hanning window array (float32).
    """
    wy = np.hanning(shape[0]).astype(np.float32)
    wx = np.hanning(shape[1]).astype(np.float32)
    window = np.outer(wy, wx)
    return window


def register(img1, img2, sigma, upsample=10):
    """Register two images using phase cross-correlation.
    
    Computes optimal translation shift between two images using phase
    cross-correlation on whitened and windowed images. Tests both positive
    and negative shifts to handle wraparound.
    
    Args:
        img1 (np.ndarray): Reference image array.
        img2 (np.ndarray): Image to register to reference.
        sigma (float): Gaussian sigma for whitening filter.
        upsample (int): Upsampling factor for sub-pixel accuracy. Defaults to 10.
    
    Returns:
        tuple: (shift, error) where:
            - shift (np.ndarray): Translation shift vector (y, x).
            - error (float): Registration error metric (-log of normalized correlation).
                Lower values indicate better registration. Returns inf if correlation is 0.
    """
    from skimage.registration import phase_cross_correlation
    from scipy.ndimage import shift as ndimage_shift
    
    img1w = window(whiten(img1, sigma))
    img2w = window(whiten(img2, sigma))

    shift = phase_cross_correlation(
        img1w,
        img2w,
        upsample_factor=upsample,
        normalization=None
    )[0]

    shape = np.array(img1.shape)
    shift_pos = (shift + shape) % shape
    shift_neg = shift_pos - shape
    shifts = list(itertools.product(*zip(shift_pos, shift_neg)))
    correlations = [
        np.abs(np.sum(img1w * ndimage_shift(img2w, s, order=0)))
        for s in shifts
    ]
    idx = np.argmax(correlations)
    shift = shifts[idx]
    correlation = correlations[idx]
    total_amplitude = np.linalg.norm(img1w) * np.linalg.norm(img2w)
    if correlation > 0 and total_amplitude > 0:
        error = -np.log(correlation / total_amplitude)
    else:
        error = np.inf
    return shift, error