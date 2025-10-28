import numpy as np
# import torch
import pandas as pd
import os
import tifffile
# from image_processing import ImageProcessor
import math
from tqdm import tqdm

def stitch_acquisition(acquisition_dir, channel,zindex=0,
                       metadata_filename='Metadata.txt',
                       image_processor=None,
                       registration_dict={},
                       border=1000,
                       stitch_rotate=0,
                       stitch_flipud=False,
                       stitch_fliplr=False):
    """
    Stitch acquisition images together based on metadata.
    
    Args:
        acquisition_dir (str): Path to acquisition directory containing metadata and images
        metadata_filename (str): Name of metadata file, default 'Metadata.txt'
        image_processor (ImageProcessor): Optional image processor. If None, uses raw images
        registration_dict (dict): Optional dict with position names as keys, containing 
                                  'X' and 'Y' registration shifts in microns
        border (int): Border pixels to add around stitched image
        stitch_rotate (int): Number of 90-degree rotations to apply
        stitch_flipud (bool): Flip image up/down
        stitch_fliplr (bool): Flip image left/right
        
    Returns:
        torch.Tensor: Stitched image with shape [height, width]
    """
    
    # Load metadata
    metadata = pd.read_csv(os.path.join(acquisition_dir, metadata_filename), delimiter='\t')
    metadata = metadata[metadata['Channel']==channel]
    metadata = metadata[metadata['Zindex']==zindex]
    metadata.index = metadata['Position']
    coordinates = {pos:{'X':row['X'],'Y':row['Y']} for pos,row in metadata.iterrows() if row['Channel']==channel}
    file_names = {pos:os.path.join(acquisition_dir,row['filename']) for pos,row in metadata.iterrows() if row['Channel']==channel}

    # Determine Canvas Size
    test_img = tifffile.imread(metadata['filename'].iloc[0])
    if image_processor is not None:
        test_img = image_processor.process(test_img)
    image_shape_pixels = test_img.shape
    
    # Get min/max coordinates um
    y_values = [coords['Y'] for coords in coordinates.values()]
    x_values = [coords['X'] for coords in coordinates.values()]
    y_min, y_max = min(y_values), max(y_values)
    x_min, x_max = min(x_values), max(x_values)
    # convert to pixels
    pixel_size = metadata['PixelSize'].iloc[0]
    image_size = image_shape_pixels * pixel_size
    y_max = y_max + image_size[0]
    x_max = x_max + image_size[1]
    y_range = y_max - y_min
    x_range = x_max - x_min
    y_range_pixels = math.ceil(y_range / pixel_size) + 2*border
    x_range_pixels = math.ceil(x_range / pixel_size) + 2*border
    canvas_height = y_range_pixels
    canvas_width = x_range_pixels
    canvas = np.zeros((canvas_height, canvas_width), dtype=np.float32)

    for posname,location in tqdm(coordinates.items(),total=len(coordinates),desc='Stitching'):
        img = tifffile.imread(file_names[posname])
        if image_processor is not None:
            img = image_processor.process(img)
        # apply transformations
        # Rotate
        img = np.rot90(img, stitch_rotate)
        
        # Flip
        if stitch_flipud:
            img = np.flipud(img)
        if stitch_fliplr:
            img = np.fliplr(img)

        # determine position on canvas
        position_x = location['X']
        position_y = location['Y']
        if posname in registration_dict:
            position_x = location['X'] + registration_dict[posname]['X']
            position_y = location['Y'] + registration_dict[posname]['Y']
        # convert location to pixels
        position_x_pixels = math.ceil((position_x-x_min) / pixel_size) + border
        position_y_pixels = math.ceil((position_y-y_min) / pixel_size) + border
        # place image on canvas
        x0 = position_x_pixels
        x1 = x0 + img.shape[0]
        y0 = position_y_pixels
        y1 = y0 + img.shape[1]
        canvas[x0:x1, y0:y1] = img #FIXME: in the future do averaging of overlapping pixels
    return canvas
