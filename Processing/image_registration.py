


def whiten(img, sigma):
    from skimage.util import img_as_float32
    img = img_as_float32(img)
    from scipy.ndimage import gaussian_laplace
    output = gaussian_laplace(img, sigma)
    return output

def window(img):
    assert img.ndim == 2
    return img * get_window(img.shape)

def get_window(shape):
    wy = np.hanning(shape[0]).astype(np.float32)
    wx = np.hanning(shape[1]).astype(np.float32)
    window = np.outer(wy, wx)
    return window


def register(img1, img2, sigma, upsample=10):
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