import numpy as np
# import torch
import pandas as pd
import os
from pandas.core.indexes.base import np_can_hold_element
import tifffile
# from image_processing import ImageProcessor
import math
from tqdm import tqdm

def stitch_acquisition(acquisition_dir, channel, zindex=0,
                       metadata_filename='Metadata.txt',
                       image_processor=None,
                       registration_dict={},
                       border=1000,
                       stitch_rotate=0,
                       stitch_flipud=False,
                       stitch_fliplr=False,
                       bin=1,
                       idx_stitch=False,
                       output_pixel_size=None,
                       position_names=None,
                       verbose=True):
    """Stitch acquisition images together based on metadata.
    
    Combines multiple FOV images into a single stitched image based on stage
    coordinates from metadata. Supports image transformations, registration
    corrections, and optional position indexing for ROI-based filtering.
    
    Args:
        acquisition_dir (str): Path to acquisition directory containing metadata and images.
        channel (str): Channel name to stitch.
        zindex (int): Z-stack index to stitch. Defaults to 0.
        metadata_filename (str): Name of metadata file. Defaults to 'Metadata.txt'.
        image_processor (ImageProcessor, optional): Optional image processor for preprocessing.
            If None, uses raw images. Defaults to None.
        registration_dict (dict): Dictionary mapping position names to registration shifts.
            Format: {position_name: {'X': float, 'Y': float}}. Defaults to {}.
        border (int): Border pixels to add around stitched image. Defaults to 1000.
        stitch_rotate (int): Number of 90-degree rotations to apply. Defaults to 0.
        stitch_flipud (bool): Flip image up/down. Defaults to False.
        stitch_fliplr (bool): Flip image left/right. Defaults to False.
        bin (int): Downsampling factor (ignored if output_pixel_size is provided).
            Defaults to 1.
        idx_stitch (bool): If True, returns additional outputs for position indexing.
            Defaults to False.
        output_pixel_size (float, optional): Target output pixel size in microns.
            If provided, bin is calculated automatically. Defaults to None.
        position_names (list, optional): List of position names to include.
            If None, includes all positions. Defaults to None.
        verbose (bool): Show progress bar. Defaults to True.
    
    Returns:
        tuple: Returns depend on idx_stitch:
            - If idx_stitch=False: (canvas, pixel2stage)
                - canvas (np.ndarray): Stitched image array [height, width]
                - pixel2stage (callable): Function mapping pixel (x, y) to stage (X, Y)
            - If idx_stitch=True: (canvas, pixel2stage, idx_canvas, posname_idx_mapper)
                - idx_canvas (np.ndarray): Array mapping pixels to position indices
                - posname_idx_mapper (dict): Dictionary mapping position names to indices
    """
    
    # Load metadata
    metadata = pd.read_csv(os.path.join(acquisition_dir, metadata_filename), delimiter='\t')
    metadata = metadata[metadata['Channel']==channel]
    metadata = metadata[metadata['Zindex']==zindex]
    metadata.index = metadata['Position']
    if position_names is not None:
        metadata = metadata[metadata['Position'].isin(position_names)]
    coordinates = {pos:{'X':row['X'],'Y':row['Y']} for pos,row in metadata.iterrows() if row['Channel']==channel}
    file_names = {pos:os.path.join(acquisition_dir,row['filename']) for pos,row in metadata.iterrows() if row['Channel']==channel}
    posname_idx_mapper = {pos:idx for idx,pos in enumerate(metadata['Position'].unique())}
    # Calculate bin from output_pixel_size if provided
    pixel_size = metadata['PixelSize'].iloc[0]
    if output_pixel_size is not None:
        bin = int(max(1, round(output_pixel_size / pixel_size)))
    else:
        bin = int(bin)
    # Determine Canvas Size
    img = tifffile.imread(os.path.join(acquisition_dir,metadata['filename'].iloc[0]))
    if bin>1:
        # Trim image to be multiple of bin for consistent binning
        h, w = img.shape[:2]
        h_trimmed = (h // bin) * bin
        w_trimmed = (w // bin) * bin
        img = img[:h_trimmed, :w_trimmed]
        img = img[::bin,::bin]
    print(img.shape)
    if image_processor is not None:
        img = image_processor.process(img)

    # apply transformations
    # Rotate
    img = np.rot90(img, int(stitch_rotate/90))
    # Flip
    if stitch_flipud:
        img = np.flipud(img)
    if stitch_fliplr:
        img = np.fliplr(img)
    image_shape_pixels = img.shape
    del img
    
    # Get min/max coordinates um
    y_values = [coords['Y'] for coords in coordinates.values()]
    x_values = [coords['X'] for coords in coordinates.values()]
    y_min, y_max = min(y_values), max(y_values)
    x_min, x_max = min(x_values), max(x_values)
    # convert to pixels (pixel_size already loaded above, adjust for bin)
    if bin>1:
        pixel_size = pixel_size * bin
    # image_size = image_shape_pixels * pixel_size
    y_max = y_max + image_shape_pixels[0]* pixel_size
    x_max = x_max + image_shape_pixels[1]* pixel_size
    y_range = y_max - y_min
    x_range = x_max - x_min
    y_range_pixels = math.ceil(y_range / pixel_size) + 2*border
    x_range_pixels = math.ceil(x_range / pixel_size) + 2*border
    canvas_height = y_range_pixels
    canvas_width = x_range_pixels
    canvas = np.zeros((canvas_height, canvas_width), dtype=np.float32)
    if idx_stitch:
        idx_canvas = np.zeros((canvas_height, canvas_width), dtype=np.int32)
    for posname,location in tqdm(coordinates.items(),total=len(coordinates),desc='Stitching',disable=not verbose):
        img = tifffile.imread(file_names[posname])
        if bin>1:
            # Trim image to be multiple of bin for consistent binning
            h, w = img.shape[:2]
            h_trimmed = (h // bin) * bin
            w_trimmed = (w // bin) * bin
            img = img[:h_trimmed, :w_trimmed]
            img = img[::bin,::bin]
        if image_processor is not None:
            img = image_processor.process(img)
        # apply transformations
        # Rotate
        img = np.rot90(img, int(stitch_rotate/90))
        
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
        # place image on canvas center on position
        x0 = position_x_pixels - int(img.shape[1]/2)
        x1 = x0 + img.shape[1]
        y0 = position_y_pixels - int(img.shape[0]/2)
        y1 = y0 + img.shape[0]
        try:
            canvas[y0:y1,x0:x1] = img #FIXME: in the future do averaging of overlapping pixels
            if idx_stitch:
                idx_canvas[y0:y1,x0:x1] = posname_idx_mapper[posname]
        except:
            print(f"Error placing image {posname} on canvas")
            print(x0,x1,y0,y1)
            print(img.shape)
            print(canvas.shape)
            # raise
    
    def pixel2stage(x, y):
        """Convert pixel coordinates (x, y) to stage coordinates (X, Y) in microns."""
        X = x_min + (x - border) * pixel_size
        Y = y_min + (y - border) * pixel_size
        return X, Y
    
    if idx_stitch:
        return canvas, pixel2stage, idx_canvas, posname_idx_mapper
    return canvas, pixel2stage

from functools import total_ordering
from pycromanager import Core, Acquisition, multi_d_acquisition_events
import numpy as np
import time
import os
import matplotlib.pyplot as plt
from tqdm import tqdm
from datetime import datetime
import tifffile
import glob
from matplotlib.patches import Circle
from matplotlib.widgets import Button
import matplotlib.patches as patches

def interactive_roi_selection(stitched_image, message=None):
    """Interactive matplotlib interface for ROI selection using freehand drawing.
    
    Displays stitched image and allows user to draw multiple ROI polygons by
    clicking and dragging. Supports undo, reset, and multiple ROI selection.
    
    Args:
        stitched_image (np.ndarray): The stitched image array to display.
        message (str, optional): Optional message to display below the plot.
            Defaults to None.
    
    Returns:
        tuple: (mask, canvas_rgb) where:
            - mask (np.ndarray): Labeled mask array where 0 = outside ROI,
                and values 1, 2, 3, ... correspond to ROI indices
            - canvas_rgb (np.ndarray): RGB visualization of mask overlaid on image
    
    Controls:
        - Left click and drag: Draw ROI polygon
        - U key: Undo last ROI
        - R key: Reset all ROIs
        - D key: Done (close window)
        - "Done" button: Finish selection
    """
    fig, ax = plt.subplots(figsize=(15, 10))
    # Maximize window to fullscreen
    try:
        mngr = fig.canvas.manager
        mngr.window.state('zoomed')  # Windows
    except:
        try:
            mngr.full_screen_toggle()
        except:
            pass
    vmin = stitched_image.min()
    # vmax = np.percentile(stitched_image[stitched_image>0],99) #FIXME: Sticker is really bright, so we need to adjust the vmax
    vmax = np.percentile(stitched_image[stitched_image>0],75)
    im = ax.imshow(stitched_image, cmap='gray', interpolation='nearest', vmin=vmin, vmax=vmax)
    ax.invert_yaxis() ##FIXME: this is a hack to make the image look correct
    
    # Color cycle for different ROIs
    colors = ['red', 'blue', 'green', 'yellow', 'cyan', 'magenta', 'orange', 'purple', 'pink', 'brown']
    
    # Calculate bounding box of non-zero pixels for faster rendering
    non_zero_mask = stitched_image > 0
    if np.any(non_zero_mask):
        y_sum = np.sum(non_zero_mask, axis=1)
        x_sum = np.sum(non_zero_mask, axis=0)
        y_nonzero = np.where(y_sum > 0)[0]
        x_nonzero = np.where(x_sum > 0)[0]
        if len(y_nonzero) > 0 and len(x_nonzero) > 0:
            y_min, y_max = y_nonzero[0], y_nonzero[-1]
            x_min, x_max = x_nonzero[0], x_nonzero[-1]
            # Add small padding
            padding = 50
            y_min = max(0, y_min - padding)
            y_max = min(stitched_image.shape[0], y_max + padding)
            x_min = max(0, x_min - padding)
            x_max = min(stitched_image.shape[1], x_max + padding)
            ax.set_xlim(x_min, x_max)
            ax.set_ylim(y_min, y_max)

    if max((y_max-y_min),(x_max-x_min))>2000:
        ax.set_title('ROI Selection \n (Lower output pixel size for faster rendering)')
    else:
        ax.set_title('ROI Selection')
    roi_polygons = []  # List of polygon coordinate arrays
    polygon_artists = []  # List of matplotlib artists for completed polygons
    current_line = None  # Line2D artist for current polygon being drawn
    current_polygon = None
    is_drawing = False
    update_counter = 0  # Counter for throttling display updates
    
    def update_display(force=False):
        """Update the display without clearing everything"""
        nonlocal current_line, update_counter
        update_counter += 1
        
        # Only update display every 3rd point or when forced, to speed up drawing
        if not force and update_counter % 3 != 0:
            return
        
        if current_polygon is not None and len(current_polygon) >= 4:
            coords = np.array(current_polygon).reshape(-1, 2)
            roi_index = len(roi_polygons)  # Index of ROI being drawn (0-based)
            color = colors[roi_index % len(colors)]
            
            if current_line is None:
                # Create line on first update
                current_line, = ax.plot(coords[:, 0], coords[:, 1], color=color, linewidth=2)
            else:
                # Update existing line data (much faster than recreating)
                current_line.set_data(coords[:, 0], coords[:, 1])
        
        fig.canvas.draw_idle()
    
    def on_mouse_press(event):
        nonlocal current_polygon, is_drawing, current_line, update_counter
        
        if event.inaxes != ax:
            return
        
        if event.button == 1:  # Left click - start drawing
            if not is_drawing:
                current_polygon = [event.xdata, event.ydata]
                is_drawing = True
                update_counter = 0  # Reset counter for new drawing
                if current_line is not None:
                    current_line.remove()
                    current_line = None
                print(f"Started drawing ROI at ({event.xdata:.1f}, {event.ydata:.1f})")
    
    def on_mouse_move(event):
        nonlocal current_polygon
        
        if event.inaxes == ax and is_drawing and current_polygon is not None:
            if event.xdata is None or event.ydata is None:
                return
            
            current_polygon.extend([event.xdata, event.ydata])
            update_display()
    
    def on_mouse_release(event):
        nonlocal current_polygon, is_drawing, current_line
        
        if event.inaxes == ax and is_drawing and current_polygon is not None:
            # Finish the current polygon
            if event.xdata is not None and event.ydata is not None:
                current_polygon.extend([event.xdata, event.ydata])
            
            # Force final update to show complete line
            if len(current_polygon) >= 4:
                update_display(force=True)
                coords = np.array(current_polygon).reshape(-1, 2)
                roi_index = len(roi_polygons)  # Index of this ROI (0-based)
                color = colors[roi_index % len(colors)]
                line, = ax.plot(coords[:, 0], coords[:, 1], color=color, linewidth=2)
                fill = ax.fill(coords[:, 0], coords[:, 1], alpha=0.3, color=color)[0]
                roi_polygons.append(current_polygon)
                polygon_artists.append((line, fill))
            
            if current_line is not None:
                current_line.remove()
                current_line = None
            current_polygon = None
            is_drawing = False
            print(f"Finished drawing ROI with {len(roi_polygons)} total ROIs")
            fig.canvas.draw_idle()
    
    def on_key(event):
        nonlocal roi_polygons, polygon_artists, current_line
        
        if event.key == 'u':  # Undo last ROI
            if roi_polygons:
                removed = roi_polygons.pop()
                if polygon_artists:
                    line, fill = polygon_artists.pop()
                    line.remove()
                    fill.remove()
                print(f"Undid last ROI. {len(roi_polygons)} ROIs remaining.")
                fig.canvas.draw_idle()
        
        elif event.key == 'r':  # Reset all ROIs
            roi_polygons = []
            for line, fill in polygon_artists:
                line.remove()
                fill.remove()
            polygon_artists = []
            if current_line is not None:
                current_line.remove()
                current_line = None
            print("Reset all ROIs.")
            fig.canvas.draw_idle()
        
        elif event.key == 'd':
            plt.close(fig)
    
    def done_button_clicked(event):
        plt.close(fig)
    
    # Connect events
    fig.canvas.mpl_connect('button_press_event', on_mouse_press)
    fig.canvas.mpl_connect('motion_notify_event', on_mouse_move)
    fig.canvas.mpl_connect('button_release_event', on_mouse_release)
    fig.canvas.mpl_connect('key_press_event', on_key)
    
    # Add optional message above the instructions
    if message is not None:
        fig.text(0.8, 0.28, message, fontsize=9, 
                 horizontalalignment='left', verticalalignment='top',
                 bbox=dict(boxstyle="round,pad=0.5", facecolor="yellow", alpha=0.7))
    
    # Add instructions text above the done button - store reference so it persists
    instructions_text = fig.text(0.8, 0.12, 'INSTRUCTIONS\n'
            'Left click and drag: Draw\n'
            'U key: Undo last ROI\n'
            'R key: Reset all ROIs\n'
            'Press "Done" when finished', 
            fontsize=10, 
            horizontalalignment='left',
            verticalalignment='bottom',
            bbox=dict(boxstyle="round,pad=0.5", facecolor="white", alpha=0.8))
    
    # Add done button
    ax_done = plt.axes([0.8, 0.05, 0.1, 0.04])
    btn_done = Button(ax_done, 'Done')
    btn_done.on_clicked(done_button_clicked)
    
    plt.show()
    
    # Create labeled mask from ROI polygons (0 = outside, 1, 2, 3, ... = ROI index)
    mask = np.zeros_like(stitched_image, dtype=np.uint8)
    
    if roi_polygons:
        # Import matplotlib.path for point-in-polygon testing
        from matplotlib.path import Path
        
        # Create coordinate grid for the image
        height, width = stitched_image.shape
        y_coords, x_coords = np.mgrid[0:height, 0:width]
        points = np.column_stack((x_coords.ravel(), y_coords.ravel()))
        
        # For each ROI polygon, mark pixels inside with ROI index (1, 2, 3, ...)
        for roi_idx, polygon in enumerate(roi_polygons, start=1):
            # Reshape polygon coordinates to (N, 2) format
            coords = np.array(polygon).reshape(-1, 2)
            
            # Create path from polygon coordinates
            path = Path(coords)
            
            # Test which points are inside the polygon
            inside = path.contains_points(points)
            
            # Reshape back to image dimensions and add to mask with ROI index
            inside_mask = inside.reshape(height, width)
            mask[inside_mask] = roi_idx
    colors = ['red', 'blue', 'green', 'yellow', 'cyan', 'magenta', 'orange', 'purple', 'pink', 'brown']
    color_mapper = {'red': (255, 0, 0), 'blue': (0, 0, 255), 'green': (0, 255, 0), 'yellow': (255, 255, 0), 'cyan': (0, 255, 255), 'magenta': (255, 0, 255), 'orange': (255, 165, 0), 'purple': (128, 0, 128), 'pink': (255, 192, 203), 'brown': (165, 42, 42)}
    rgb_mask = 255*np.ones((mask.shape[0], mask.shape[1], 3),dtype=np.int16)
    for roi_idx in np.unique(mask[mask>0]):
        color = colors[(roi_idx-1) % len(colors)]
        color_rgb = color_mapper[color]
        rgb_mask[mask==roi_idx] = color_rgb
    canvas = stitched_image
    vmax = np.percentile(canvas[canvas>0],99)
    canvas_rgb = rgb_mask * canvas[:,:,None].copy()/vmax
    canvas_rgb = canvas_rgb/canvas_rgb.max()
    return mask, canvas_rgb

def interactive_coordinate_selection(stitched_image, message=None):
    """Interactive matplotlib interface for coordinate selection.
    
    Displays stitched image and allows user to click points to select coordinates.
    Useful for selecting focus points or reference positions.
    
    Args:
        stitched_image (np.ndarray): The stitched image array to display.
            Can be 2D (grayscale) or 3D (RGB).
        message (str, optional): Optional message to display below the plot.
            Defaults to None.
    
    Returns:
        list: List of (x, y) pixel coordinate tuples in the order they were clicked.
    
    Controls:
        - Left click: Select point
        - U key: Undo last point
        - R key: Reset all points
        - D key: Done (close window)
        - "Done" button: Finish selection
    """
    fig, ax = plt.subplots(figsize=(15, 10))
    # Maximize window to fullscreen
    try:
        mngr = fig.canvas.manager
        mngr.window.state('zoomed')  # Windows
    except:
        try:
            mngr.full_screen_toggle()
        except:
            pass
    if len(stitched_image.shape)==3:
        im = ax.imshow(stitched_image, interpolation='nearest')
    else:
        vmin = stitched_image.min()
        vmax = np.percentile(stitched_image[stitched_image>0],99)
        im = ax.imshow(stitched_image, cmap='gray', interpolation='nearest', vmin=vmin, vmax=vmax)
    ax.invert_yaxis() ##FIXME: this is a hack to make the image look correct
    
    # Calculate bounding box of non-zero pixels for faster rendering
    non_zero_mask = stitched_image > 0
    if np.any(non_zero_mask):
        y_sum = np.sum(non_zero_mask, axis=1)
        x_sum = np.sum(non_zero_mask, axis=0)
        y_nonzero = np.where(y_sum > 0)[0]
        x_nonzero = np.where(x_sum > 0)[0]
        if len(y_nonzero) > 0 and len(x_nonzero) > 0:
            y_min, y_max = y_nonzero[0], y_nonzero[-1]
            x_min, x_max = x_nonzero[0], x_nonzero[-1]
            # Add small padding
            padding = 50
            y_min = max(0, y_min - padding)
            y_max = min(stitched_image.shape[0], y_max + padding)
            x_min = max(0, x_min - padding)
            x_max = min(stitched_image.shape[1], x_max + padding)
            ax.set_xlim(x_min, x_max)
            ax.set_ylim(y_min, y_max)
    if max((y_max-y_min),(x_max-x_min))>2000:
        ax.set_title('Coordinate Selection \n (Lower output pixel size for faster rendering)')
    else:
        ax.set_title('Coordinate Selection')
    clicked_points = []  # List of (x, y) pixel coordinate tuples
    point_markers = []  # List of plot artists for points
    
    def on_click(event):
        nonlocal clicked_points, point_markers
        if event.inaxes == ax:
            if event.button == 1:  # Left click - select point
                if event.xdata is not None and event.ydata is not None:
                    pixel_coords = (event.xdata, event.ydata)
                    clicked_points.append(pixel_coords)
                    point_num = len(clicked_points)
                    # Mark the point with a black dot and white outline
                    marker, = ax.plot(pixel_coords[0], pixel_coords[1], 'o', 
                                     markersize=8, markerfacecolor='black', 
                                     markeredgecolor='white', markeredgewidth=2)
                    point_markers.append(marker)
                    fig.canvas.draw_idle()
                    print(f"Point {point_num} - Pixel: ({pixel_coords[0]:.1f}, {pixel_coords[1]:.1f})")
                else:
                    print("Warning: Clicked outside image bounds or coordinates are None")
    
    def on_key(event):
        nonlocal clicked_points, point_markers
        if event.key == 'u':  # Undo last point
            if clicked_points:
                clicked_points.pop()
                if point_markers:
                    marker = point_markers.pop()
                    marker.remove()
                print(f"Undid last point. {len(clicked_points)} points remaining.")
                fig.canvas.draw_idle()
        elif event.key == 'r':  # Reset all points
            clicked_points = []
            for marker in point_markers:
                marker.remove()
            point_markers = []
            print("Reset all points.")
            fig.canvas.draw_idle()
        elif event.key == 'd':
            plt.close(fig)
    
    def done_button_clicked(event):
        plt.close(fig)
    
    # Connect events
    fig.canvas.mpl_connect('button_press_event', on_click)
    fig.canvas.mpl_connect('key_press_event', on_key)
    
    # Add optional message above the instructions
    if message is not None:
        fig.text(0.8, 0.28, message, fontsize=9, 
                 horizontalalignment='left', verticalalignment='top',
                 bbox=dict(boxstyle="round,pad=0.5", facecolor="yellow", alpha=0.7))
    
    # Add instructions text above the done button
    instructions_text = fig.text(0.8, 0.12, 'INSTRUCTIONS\n'
            'Left click: Select point\n'
            'U key: Undo last point\n'
            'R key: Reset all points\n'
            'Press "Done" when finished', 
            fontsize=10, 
            horizontalalignment='left',
            verticalalignment='bottom',
            bbox=dict(boxstyle="round,pad=0.5", facecolor="white", alpha=0.8))
    
    # Add done button
    ax_done = plt.axes([0.8, 0.05, 0.1, 0.04])
    btn_done = Button(ax_done, 'Done')
    btn_done.on_clicked(done_button_clicked)
    
    plt.show()
    
    return clicked_points

def filter_positions(idx_canvas, mask, posname_idx_mapper):
    """Filter positions based on which ones fall within selected ROIs.
    
    Determines which positions (represented by indices in idx_canvas) overlap
    with selected ROIs (represented by non-zero values in mask). Returns
    dictionary mapping position names to their ROI group assignments.
    
    Args:
        idx_canvas (np.ndarray): Canvas array where each pixel value corresponds
            to a position index (from idx_stitch=True in stitch_acquisition).
        mask (np.ndarray): Labeled mask array where 0 = outside ROI, and values
            1, 2, 3, ... correspond to ROI indices (from interactive_roi_selection).
        posname_idx_mapper (dict): Dictionary mapping position names to their
            indices in idx_canvas.
    
    Returns:
        dict: Dictionary mapping position names to ROI group numbers (1, 2, 3, ...).
            Only includes positions that overlap with selected ROIs.
    """
    positions_to_keep = {}
    selected_idxs = np.unique(idx_canvas[mask>0])
    for posname,idx in posname_idx_mapper.items():
        if not idx in selected_idxs:
            continue
        m = idx_canvas==idx
        rois = mask[m]
        unique_rois = np.unique(rois)
        unique_rois = unique_rois[unique_rois>0]
        if unique_rois.shape[0]==0:
            continue
        # if len(unique_rois)==1:
        group = int(unique_rois[0])
        positions_to_keep[posname] = group
    print(f"Keeping {len(positions_to_keep)} positions")
    print(positions_to_keep)
    return positions_to_keep

if __name__ == '__main__':
    from stitching import stitch_acquisition
    from image_processing import ImageProcessor
    # acquisition_dir = 'D:/Images/User/New_Project/New_Experiment/preview_Well-A_20'
    acquisition_dir = 'D:/Images/User/New_Project/New_Experiment/preview_Well-A_30'
    channel='DeepBlue'

    image_processor = ImageProcessor()
    image_processor.parameters['highpass_sigma'] = 10
    image_processor.parameters['highpass_function'] = 'gaussian'
    image_processor.parameters['highpass_smooth'] = 2
    image_processor.parameters['highpass_smooth_function'] = 'median'

    canvas, pixel2stage, idx_canvas, posname_idx_mapper = stitch_acquisition(
        acquisition_dir, 
        channel,
        zindex=0,
        metadata_filename='Metadata.txt',
        image_processor=None,
        registration_dict={},
        border=2000,
        stitch_rotate=0,
        stitch_flipud=False,
        stitch_fliplr=False,
        output_pixel_size=50,
        idx_stitch=True
    )

    mask,canvas_rgb = interactive_roi_selection(canvas,message = 'Select areas that you want \n to image one region at a time')

    positions_to_keep = filter_positions(idx_canvas, mask, posname_idx_mapper)


    clicked_points = interactive_coordinate_selection(canvas_rgb, message = 'Select a few areas for each region \n where you want to set focus')

    stage_coordinates = [pixel2stage(point[0], point[1]) for point in clicked_points]
    print(stage_coordinates)
