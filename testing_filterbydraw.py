# C:\Users\wollmanlab\miniconda3\envs\pycro_3.12\python
#C:/Users/wollmanlab/miniconda3/envs/pycro_3.12/python C:\GitRepos\pycro-manager\Testing\Scope\Initialization.py

""" 
Inputs:
Wells: [A,B,C,D,E,F]
Dataset Name: "Dataset"
Channels: ['DeepBlue','FarRed']\
Hybes: 18
"""
from functools import total_ordering
from windows import input_window, initial_focus_window
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

def find_newest_dataset(save_directory, base_name, max_age_minutes=2):
    """
    Find the newest dataset directory that contains NDTiff files.
    
    Args:
        save_directory: Directory to search in
        base_name: Base name pattern to match (e.g., "well_A_acquisition")
        max_age_minutes: Maximum age in minutes for datasets to consider
    
    Returns:
        str: Path to the newest valid dataset, or None if not found
    """
    if not os.path.exists(save_directory):
        return None
    
    # Find the most recent dataset directory
    pattern = os.path.join(save_directory, f"{base_name}*")
    matching_dirs = glob.glob(pattern)
    matching_dirs.sort(key=lambda x: os.path.getmtime(x), reverse=True)
    
    if matching_dirs:
        most_recent_dir = matching_dirs[0]
        print(f"  Found newest dataset: {most_recent_dir}")
        return most_recent_dir
    else:
        print(f"  No datasets found for {base_name}")
        return None



def stitch_images(images, positions, pixel_size, directionality, image_flip=None, stitch_origin=False):
    """
    Stitch images into a composite image based on their positions.
    
    Args:
        images: numpy array of shape (num_positions, height, width) or (height, width, num_positions)
        positions: list of [x, y] position coordinates in microns
        pixel_size: pixel size in microns
        directionality: dict with 'width' and 'height' mapping to 'x' or 'y'
        image_flip: dict with 'width' and 'height' boolean flags for flipping
        stitch_origin: bool, if True, replace each image with its index value
    
    Returns:
        stitched_image: numpy array of the stitched composite image
        stitched_height: height of stitched image in pixels
        stitched_width: width of stitched image in pixels
    """
    
    # Get all position coordinates in microns
    x_coords = [pos[0] for pos in positions]
    y_coords = [pos[1] for pos in positions]
    
    # Find min and max for each axis in microns
    min_x_um, max_x_um = min(x_coords), max(x_coords)
    min_y_um, max_y_um = min(y_coords), max(y_coords)
    
    x_range_um = max_x_um - min_x_um
    y_range_um = max_y_um - min_y_um
    
    # Get image dimensions
    image_height_pixels, image_width_pixels = images.shape[1], images.shape[2]
    
    # Calculate stitched image size
    if directionality['width'] == 'x':
        stitched_width = int(x_range_um / pixel_size) + image_width_pixels
        stitched_height = int(y_range_um / pixel_size) + image_height_pixels
    elif directionality['width'] == 'y':
        stitched_width = int(x_range_um / pixel_size) + image_height_pixels
        stitched_height = int(y_range_um / pixel_size) + image_width_pixels
    
    # Create stitched image template
    stitched_image = np.zeros((stitched_height, stitched_width), dtype=np.uint16)
    
    # Stitch each image into the composite
    for i, pos in enumerate(positions):
        pos_x, pos_y = pos
        image = images[i, :, :]
        
        # If stitch_origin is True, replace image with index value
        if stitch_origin:
            image = np.full_like(image, i, dtype=np.uint16)
        
        # Apply image flipping if specified
        if image_flip is not None:
            if image_flip.get('width', False):
                image = np.fliplr(image)
            if image_flip.get('height', False):
                image = np.flipud(image)
        
        # Calculate pixel offsets
        x_offset_pixels = int((pos_x - min_x_um) / pixel_size)
        y_offset_pixels = int((pos_y - min_y_um) / pixel_size)
        
        # Apply rotation if needed
        if directionality['width'] == 'y':
            image = np.rot90(image, 1)
        
        # Place image in stitched composite
        stitched_image[y_offset_pixels:y_offset_pixels+image.shape[0], 
                      x_offset_pixels:x_offset_pixels+image.shape[1]] = image
    
    return stitched_image

def pixel_to_stage_coordinates(pixel_x, pixel_y, positions, pixel_size, directionality, image_flip=None):
    """
    Convert stitched image pixel coordinates back to stage coordinates.
    
    Args:
        pixel_x, pixel_y: Pixel coordinates in the stitched image
        positions: List of [x, y] stage position coordinates
        pixel_size: Pixel size in microns
        directionality: Dict with 'width' and 'height' mapping to 'x' or 'y'
        image_flip: Dict with 'width' and 'height' boolean flags for flipping
    
    Returns:
        tuple: (stage_x, stage_y) in microns, or None if not found
    """
    # Get all position coordinates in microns
    x_coords = [pos[0] for pos in positions]
    y_coords = [pos[1] for pos in positions]
    
    # Find min and max for each axis in microns
    min_x_um, max_x_um = min(x_coords), max(x_coords)
    min_y_um, max_y_um = min(y_coords), max(y_coords)
    
    # Convert pixel coordinates to microns
    if directionality['width'] == 'x':
        stage_x = min_x_um + pixel_x * pixel_size
        stage_y = min_y_um + pixel_y * pixel_size
    elif directionality['width'] == 'y':
        stage_x = min_x_um + pixel_y * pixel_size
        stage_y = min_y_um + pixel_x * pixel_size
    
    # Apply image flipping if specified
    if image_flip is not None:
        if image_flip.get('width', False):
            stage_x = max_x_um - (stage_x - min_x_um)
        if image_flip.get('height', False):
            stage_y = max_y_um - (stage_y - min_y_um)
    
    return stage_x, stage_y

def interactive_roi_selection(stitched_image):
    """
    Interactive matplotlib interface for ROI selection using freehand drawing.
    
    Args:
        stitched_image: The stitched image to display
    
    Returns:
        numpy.ndarray: Binary mask where 1 = inside ROI, 0 = outside ROI
    """
    fig, ax = plt.subplots(figsize=(15, 10))
    ax.imshow(stitched_image, cmap='gray', interpolation='nearest')
    ax.set_title('ROI Selection - Draw freehand regions of interest\n'
                 'Left click and drag to draw, release to finish\n'
                 'Press "Done" when finished')
    
    roi_polygons = []  # List of polygon coordinate arrays
    current_polygon = None
    is_drawing = False
    
    def on_mouse_press(event):
        nonlocal current_polygon, is_drawing
        
        if event.inaxes != ax:
            return
        
        if event.button == 1:  # Left click - start drawing
            if not is_drawing:
                current_polygon = [event.xdata, event.ydata]
                is_drawing = True
                print(f"Started drawing ROI at ({event.xdata:.1f}, {event.ydata:.1f})")
    
    def on_mouse_move(event):
        nonlocal current_polygon
        
        if event.inaxes == ax and is_drawing and current_polygon is not None:
            # Add point to current polygon
            current_polygon.extend([event.xdata, event.ydata])
            # Redraw the current polygon
            ax.clear()
            ax.imshow(stitched_image, cmap='gray', interpolation='nearest')
            
            # Redraw all completed polygons
            for i, polygon in enumerate(roi_polygons):
                coords = np.array(polygon).reshape(-1, 2)
                ax.plot(coords[:, 0], coords[:, 1], 'r-', linewidth=2, label=f'ROI {i+1}')
                ax.fill(coords[:, 0], coords[:, 1], alpha=0.3, color='red')
            
            # Draw current polygon
            if len(current_polygon) >= 4:  # At least 2 points
                coords = np.array(current_polygon).reshape(-1, 2)
                ax.plot(coords[:, 0], coords[:, 1], 'r-', linewidth=2)
            
            fig.canvas.draw()
    
    def on_mouse_release(event):
        nonlocal current_polygon, is_drawing
        
        if event.inaxes == ax and is_drawing and current_polygon is not None:
            # Finish the current polygon
            current_polygon.extend([event.xdata, event.ydata])
            roi_polygons.append(current_polygon)
            current_polygon = None
            is_drawing = False
            print(f"Finished drawing ROI with {len(roi_polygons)} total ROIs")
    
    def on_key(event):
        nonlocal roi_polygons
        
        if event.key == 'u':  # Undo last ROI
            if roi_polygons:
                removed = roi_polygons.pop()
                print(f"Undid last ROI. {len(roi_polygons)} ROIs remaining.")
                # Redraw
                ax.clear()
                ax.imshow(stitched_image, cmap='gray', interpolation='nearest')
                for i, polygon in enumerate(roi_polygons):
                    coords = np.array(polygon).reshape(-1, 2)
                    ax.plot(coords[:, 0], coords[:, 1], 'r-', linewidth=2)
                    ax.fill(coords[:, 0], coords[:, 1], alpha=0.3, color='red')
                fig.canvas.draw()
        
        elif event.key == 'r':  # Reset all ROIs
            roi_polygons = []
            print("Reset all ROIs.")
            # Redraw
            ax.clear()
            ax.imshow(stitched_image, cmap='gray', interpolation='nearest')
            fig.canvas.draw()
        
        elif event.key == 'd':
            plt.close(fig)
    
    def done_button_clicked(event):
        plt.close(fig)
    
    # Connect events
    fig.canvas.mpl_connect('button_press_event', on_mouse_press)
    fig.canvas.mpl_connect('motion_notify_event', on_mouse_move)
    fig.canvas.mpl_connect('button_release_event', on_mouse_release)
    fig.canvas.mpl_connect('key_press_event', on_key)
    
    # Add done button
    ax_done = plt.axes([0.8, 0.05, 0.1, 0.04])
    btn_done = Button(ax_done, 'Done')
    btn_done.on_clicked(done_button_clicked)
    
    # Add instructions text
    ax.text(0.02, 0.98, 'ROI SELECTION INSTRUCTIONS\n'
            'Left click and drag: Draw freehand ROI\n'
            'U key: Undo last ROI\n'
            'R key: Reset all ROIs\n'
            'Press "Done" when finished', 
            transform=ax.transAxes, fontsize=10, 
            verticalalignment='top',
            bbox=dict(boxstyle="round,pad=0.5", facecolor="white", alpha=0.8))
    
    plt.show()
    
    # Create binary mask from ROI polygons
    mask = np.zeros_like(stitched_image, dtype=np.uint8)
    
    if roi_polygons:
        # Import matplotlib.path for point-in-polygon testing
        from matplotlib.path import Path
        
        # Create coordinate grid for the image
        height, width = stitched_image.shape
        y_coords, x_coords = np.mgrid[0:height, 0:width]
        points = np.column_stack((x_coords.ravel(), y_coords.ravel()))
        
        # For each ROI polygon, mark pixels inside as 1
        for polygon in roi_polygons:
            # Reshape polygon coordinates to (N, 2) format
            coords = np.array(polygon).reshape(-1, 2)
            
            # Create path from polygon coordinates
            path = Path(coords)
            
            # Test which points are inside the polygon
            inside = path.contains_points(points)
            
            # Reshape back to image dimensions and add to mask
            inside_mask = inside.reshape(height, width)
            mask[inside_mask] = 1
    
    return mask

def interactive_coordinate_selection(stitched_image, positions, pixel_size, directionality, image_flip=None):
    """
    Interactive matplotlib interface for coordinate selection and conversion.
    
    Args:
        stitched_image: The stitched image to display
        positions: List of [x, y] stage position coordinates
        pixel_size: Pixel size in microns
        directionality: Dict with 'width' and 'height' mapping to 'x' or 'y'
        image_flip: Dict with 'width' and 'height' boolean flags for flipping
    
    Returns:
        list: List of (pixel_coords, stage_coords) tuples
    """
    fig, ax = plt.subplots(figsize=(15, 10))
    ax.imshow(stitched_image, cmap='gray', interpolation='nearest')
    ax.set_title('Coordinate Selection - Click points to get stage coordinates\n'
                 'Right click anywhere to get stage coordinates\n'
                 'Press "Done" when finished')
    
    clicked_points = []  # List of (pixel_coords, stage_coords) tuples
    
    def on_click(event):
        if event.inaxes == ax:
            if event.button == 3:  # Right click - get coordinates
                pixel_coords = (event.xdata, event.ydata)
                stage_coords = pixel_to_stage_coordinates(
                    pixel_coords[0], pixel_coords[1], 
                    positions, pixel_size, directionality, image_flip
                )
                
                if stage_coords:
                    clicked_points.append((pixel_coords, stage_coords))
                    # Mark the point
                    ax.plot(pixel_coords[0], pixel_coords[1], 'go', markersize=8)
                    ax.text(pixel_coords[0] + 10, pixel_coords[1] + 10, 
                           f'({stage_coords[0]:.1f}, {stage_coords[1]:.1f})', 
                           color='green', fontsize=8, bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.7))
                    fig.canvas.draw()
                    print(f"Clicked point - Pixel: ({pixel_coords[0]:.1f}, {pixel_coords[1]:.1f}), "
                          f"Stage: ({stage_coords[0]:.1f}, {stage_coords[1]:.1f}) um")
    
    def on_key(event):
        if event.key == 'd':
            plt.close(fig)
    
    def done_button_clicked(event):
        plt.close(fig)
    
    # Connect events
    fig.canvas.mpl_connect('button_press_event', on_click)
    fig.canvas.mpl_connect('key_press_event', on_key)
    
    # Add done button
    ax_done = plt.axes([0.8, 0.05, 0.1, 0.04])
    btn_done = Button(ax_done, 'Done')
    btn_done.on_clicked(done_button_clicked)
    
    # Add instructions text
    ax.text(0.02, 0.98, 'COORDINATE SELECTION INSTRUCTIONS\n'
            'Right click: Get stage coordinates\n'
            'Press "Done" when finished', 
            transform=ax.transAxes, fontsize=10, 
            verticalalignment='top',
            bbox=dict(boxstyle="round,pad=0.5", facecolor="white", alpha=0.8))
    
    plt.show()
    
    return clicked_points

if __name__ == "__main__":

    """ Ensure Micro-Manager is running """
    print("Checking if Micro-Manager is running...")
    try:
        from pycromanager import Core
        core = Core()
    except Exception as e:
        print(f"Micro-Manager is not running: {e}")
        raise Exception("Micro-Manager is not running")
    print("Micro-Manager is running")
    # get pixel size and image shape
    core.set_property('Camera', 'Binning', '1')
    camera_binning = int(core.get_property('Camera', 'Binning'))
    raw_pixel_size = 0.343
    pixel_size = raw_pixel_size*camera_binning#core.get_pixel_size_um()
    image_width_pixels = core.get_image_width()
    image_height_pixels = core.get_image_height()
    image_height_um = image_height_pixels * pixel_size
    image_width_um = image_width_pixels * pixel_size
    directionality = {'width':'y','height':'x'}
    image_flip = {'width':False,'height':False}
    print(f"Camera binning: {camera_binning}")
    print(f"Pixel size: {pixel_size} um")
    print(f"Image width: {image_width_pixels} pixels")
    print(f"Image height: {image_height_pixels} pixels")
    print(f"Image height: {image_height_um} um")
    print(f"Image width: {image_width_um} um")
    print(f"Directionality: {directionality}")
    print(f"Image flip: {image_flip}")

    # """ Initial Input Window """
    # print("Starting Initialization")
    # user_input = input_window()
    # user_input = {'dataset_name': 'Test', 'selected_wells': ['A', 'B', 'C', 'D', 'E', 'F'], 'selected_channels': ['DeepBlue', 'FarRed'], 'num_hybes': 18, 'camera_binning': 2}
    user_input = {'dataset_name': 'Test', 'selected_wells': ['A'], 'selected_channels': ['DeepBlue', 'FarRed'], 'num_hybes': 18, 'camera_binning': 2}
    if not user_input:
        raise Exception("No data was collected (GUI was closed without pressing Go)")
    for key, value in user_input.items():
        print(f"{key}: {value}")

    """ Set Coarse Focus """
    print("\nSetting coarse focus...")
    focus_set = initial_focus_window()
    # focus_set = True
    if not focus_set:
        raise Exception("Coarse focus not set")
    print("Coarse focus set")
    # use core to get the x, y, z stage coordinates
    x_stage_coordinate = core.get_x_position()
    y_stage_coordinate = core.get_y_position()
    z_stage_coordinate = core.get_position()
    initial_coarse_focus = z_stage_coordinate
    scan_channel = core.get_current_config('Channel')
    scan_exposure_ms = core.get_exposure()
    print(f"X stage coordinate: {x_stage_coordinate}")
    print(f"Y stage coordinate: {y_stage_coordinate}")
    print(f"Z stage coordinate: {z_stage_coordinate}")
    print(f"Scan channel: {scan_channel}")
    print(f"Scan exposure: {scan_exposure_ms} ms")

    """Set up save directory"""
    save_directory = os.path.join(os.getcwd(), "acquisition_data", user_input['dataset_name'])
    os.makedirs(save_directory, exist_ok=True)

    """ Create Initial Positions """
    spacing = 43000 # 43mm spacing between wells
    well_diameter = 5000 # 30mm diameter of well
    well_radius = well_diameter/2
    overlap_percent = 0.0 # 0% overlap between wells
    A_center = np.array([73000,143000])
    well_centers_XY_stage = {
        'A':A_center + np.array([0,0])*spacing, 
        'B':A_center + np.array([0,1])*spacing, 
        'C':A_center + np.array([0,2])*spacing, 
        'D':A_center + np.array([-1,0])*spacing, 
        'E':A_center + np.array([-1,1])*spacing, 
        'F':A_center + np.array([-1,2])*spacing}
    
    # Create positions for each well
    well_positions = {}
    for well in user_input['selected_wells']:
        well_center = well_center = well_centers_XY_stage[well]
        print(f"Well {well} center: {well_center}")
        
        # Map image dimensions to stage coordinates based on directionality
        if directionality['width'] == 'x':
            step_x = image_width_um * (1 - overlap_percent)
            step_y = image_height_um * (1 - overlap_percent)
        elif directionality['width'] == 'y':
            step_x = image_height_um * (1 - overlap_percent)
            step_y = image_width_um * (1 - overlap_percent)
        else:
            raise ValueError(f"Unknown directionality mapping: {directionality}")
        
        # Calculate grid bounds
        min_x = well_center[0] - well_radius
        max_x = well_center[0] + well_radius
        min_y = well_center[1] - well_radius
        max_y = well_center[1] + well_radius
        
        # Generate grid positions
        x_positions = np.arange(min_x, max_x + step_x, step_x)
        y_positions = np.arange(min_y, max_y + step_y, step_y)
        
        # Filter positions to only include those within the circular well
        valid_positions = []
        for x in x_positions:
            for y in y_positions:
                # Check if position is within the well circle
                distance_from_center = np.sqrt((x - well_center[0])**2 + (y - well_center[1])**2)
                if distance_from_center <= well_radius:
                    valid_positions.append([x, y])
        
        well_positions[well] = valid_positions
        print(f"  Created {len(valid_positions)} positions for well {well}")
        print(f"  Step sizes: X={step_x:.1f} um, Y={step_y:.1f} um")
    
    # Image Wells
    # create a simple loop through positions, snapping images and loading to memor
    # Set exposure and channel
    core.set_exposure(scan_exposure_ms)
    core.set_config('Channel', scan_channel)

    # Four acquisition engine options:
    # 0: Custom (manual) acquisition - direct core.snap_image() calls
    #    - Slowest but most straightforward
    #    - Moves stage, waits, snaps image for each position
    # 1: PycroManager acquisition engine - uses pycromanager.Acquisition
    #    - Medium speed, automatic NDTiff saving
    #    - Uses pycromanager's event-based acquisition system
    # 2: Micro-Manager engine - uses Micro-Manager's native MDA system via JavaBackendAcquisition
    #    - Fastest, uses Micro-Manager's optimized acquisition engine
    #    - Automatic NDTiff saving, same as PycroManager but with native MM backend
    # 3: Micro-Manager Studio engine - creates position list and uses Studio API
    #    - Uses Micro-Manager's Studio API to create position list and trigger acquisition
    #    - Most native Micro-Manager approach
    acquisition_engine = 0
    
    # Uncomment the lines below to test different acquisition modes
    # acquisition_engine = 0  # Custom (manual) acquisition
    # acquisition_engine = 2  # Micro-Manager engine
    
    # Initialize timing variables
    total_acquisition_time = 0
    acquisition_times = {}
    
    print(f"\n{'='*60}")
    engine_names = {0: "Custom (Manual)", 1: "PycroManager", 2: "Micro-Manager (Java Backend)", 3: "Micro-Manager Studio"}
    print(f"Starting acquisition with {engine_names[acquisition_engine]} engine")
    print(f"Total wells to process: {len(user_input['selected_wells'])}")
    print(f"{'='*60}")

    for well in user_input['selected_wells']:
        print(f"\nStarting acquisition for well {well}")        
        print(f"  Number of positions: {len(well_positions[well])}")
        print(f"  Channel: {scan_channel}")
        print(f"  Exposure: {scan_exposure_ms} ms")
        core.set_property('Camera', 'Binning', '4')
        camera_binning = int(core.get_property('Camera', 'Binning'))
        pixel_size = raw_pixel_size*camera_binning#core.get_pixel_size_um()
        image_width_pixels = core.get_image_width()
        image_height_pixels = core.get_image_height()
        image_height_um = image_height_pixels * pixel_size
        image_width_um = image_width_pixels * pixel_size
        
        # Loop through each position and snap images
        all_images = []
        placed_positions = []  # Track which positions were actually placed

        well_start_time = time.time()
        
        if acquisition_engine == 1:  # PycroManager engine
            print(f"  Using PycroManager acquisition engine for well {well}")
            
            # Create acquisition events for all positions in this well
            events = multi_d_acquisition_events(
                num_time_points=1,
                time_interval_s=0,
                channel_group='Channel',
                channels=[scan_channel],
                xy_positions=well_positions[well],
                order='pc'
            )
            
            # Create acquisition
            acq = Acquisition(
                directory=save_directory,
                name=f"well_{well}_acquisition",
                image_process_fn=None,
                show_display=False,
                save_display=False,
                pre_hardware_hook_fn=None,
                post_hardware_hook_fn=None
            )
            
            # Run acquisition and wait for completion
            acq.acquire(events)
            acq.mark_finished()
            # Wait for acquisition to complete properly
            acq.await_completion()
            print(f"  Acquisition completed for well {well}")
            
            # Load images from NDTiff file
            load_start_time = time.time()
            base_name = f"well_{well}_acquisition"
            dataset_path = find_newest_dataset(save_directory, base_name, max_age_minutes=2)
            if dataset_path is None:
                raise Exception(f"No dataset found for well {well}")
            images_fname = os.path.join(dataset_path, f"{base_name}_NDTiffStack.tif")
            images = tifffile.imread(images_fname)
            print(f"  Loaded {images.shape} images from NDTiff dataset")
            
            load_time = time.time() - load_start_time
            print(f"  Image loading time: {load_time:.2f} seconds")
            
        elif acquisition_engine == 2:  # Micro-Manager engine
            print(f"  Using Micro-Manager engine for well {well}")
            
            # Import JavaBackendAcquisition for Micro-Manager's native MDA system
            from pycromanager import JavaBackendAcquisition, multi_d_acquisition_events
            
            # Create acquisition events for all positions in this well
            events = multi_d_acquisition_events(
                num_time_points=1,
                time_interval_s=0,
                channel_group='Channel',
                channels=[scan_channel],
                channel_exposures_ms=[scan_exposure_ms],
                xy_positions=well_positions[well],
                order='pc'
            )
            
            # Create acquisition using Micro-Manager's native system
            acq = JavaBackendAcquisition(
                directory=save_directory,
                name=f"well_{well}_acquisition",
                image_process_fn=None,
                show_display=False,
                pre_hardware_hook_fn=None,
                post_hardware_hook_fn=None
            )
            
            # Run acquisition and wait for completion
            acq.acquire(events)
            acq.mark_finished()
            # Wait for acquisition to complete properly
            acq.await_completion()
            print(f"  Micro-Manager MDA completed for well {well}")
            
            # Load images from NDTiff file
            load_start_time = time.time()
            base_name = f"well_{well}_acquisition"
            dataset_path = find_newest_dataset(save_directory, base_name, max_age_minutes=2)
            if dataset_path is None:
                raise Exception(f"No dataset found for well {well}")
            images_fname = os.path.join(dataset_path, f"{base_name}_NDTiffStack.tif")
            images = tifffile.imread(images_fname)
            print(f"  Loaded {images.shape} images from NDTiff dataset")
            
            load_time = time.time() - load_start_time
            print(f"  Image loading time: {load_time:.2f} seconds")
            
             
        else:  # Custom (manual) acquisition
            print(f"  Using custom (manual) acquisition for well {well}")
            images = np.zeros((len(well_positions[well]),image_height_pixels, image_width_pixels), dtype=np.uint16)
            for i, pos in tqdm(enumerate(well_positions[well]),total=len(well_positions[well]),desc=f"Processing images for well {well}"):
                pos_x, pos_y = pos
                position_label = f"Pos{i}_{scan_channel}_{scan_exposure_ms}ms_{int(pos_x)}X_{int(pos_y)}Y_{int(z_stage_coordinate)}Z"
                core.set_xy_position(pos_x, pos_y)
                core.wait_for_device(core.get_xy_stage_device())
                core.snap_image()
                tagged_image = core.get_tagged_image()
                pixels = np.array(tagged_image.pix, dtype=np.uint16)
                height = tagged_image.tags["Height"]
                width = tagged_image.tags["Width"]
                image = pixels.reshape(height, width)
                images[i,:,:] = image

        # Time the image processing loop
        processing_start_time = time.time()
        
        # Stitch images using the new function
        stitched_image = stitch_images(
            images, well_positions[well], pixel_size, directionality, image_flip
        )
        stitched_image_origin = stitch_images(
            images, well_positions[well], pixel_size, directionality, image_flip, True
        )
        
        # End timing for this well
        processing_time = time.time() - processing_start_time
        well_total_time = time.time() - well_start_time
        acquisition_times[well] = {
            'processing_time': processing_time,
            'total_time': well_total_time,
            'num_positions': len(well_positions[well])
        }
        total_acquisition_time += well_total_time
        
        print(f"  Well {well} timing:")
        print(f"    Processing time: {processing_time:.2f} seconds")
        print(f"    Total well time: {well_total_time:.2f} seconds")
        print(f"    Positions processed: {len(well_positions[well])}")
        if acquisition_engine in [1, 2]:  # PycroManager or Micro-Manager engines
            print(f"    Image loading time: {load_time:.2f} seconds")
        
        # Display final stitched image for this well
        if len(well_positions[well]) > 0:
            plt.figure(figsize=(12, 8))
            plt.imshow(stitched_image, cmap='gray', interpolation='nearest')
            plt.colorbar(label='Intensity')
            plt.xlabel('X (pixels)')
            plt.ylabel('Y (pixels)')
            plt.tight_layout()
            plt.draw()
            plt.show(block=True)  # Keep plots open at the end
            print(f"  Displayed final stitched image for well {well}")
            
            # Interactive ROI and coordinate selection
            print(f"  Starting interactive ROI and coordinate selection for well {well}")
            roi_mask = interactive_roi_selection(stitched_image)
            
            # Get selected positions more efficiently
            if np.sum(roi_mask) > 0:
                # Find indices where mask is True (inside ROIs)
                roi_indices = np.where(roi_mask)
                # Get unique position indices from the origin image
                selected_positions = np.unique(stitched_image_origin[roi_indices])
            else:
                selected_positions = []

            # Print results
            print(f"  ROI Selection Results for well {well}:")
            print(f"    Mask shape: {roi_mask.shape}")
            print(f"    Pixels inside ROIs: {np.sum(roi_mask)}")
            print(f"    Pixels outside ROIs: {np.sum(roi_mask == 0)}")
            print(f"    Percentage of image covered by ROIs: {100 * np.sum(roi_mask) / roi_mask.size:.1f}%")
            print(f"    Selected positions: {selected_positions}")
            
            # Optional: Display the mask
            plt.figure(figsize=(12, 8))
            plt.imshow(roi_mask, cmap='gray', interpolation='nearest')
            plt.colorbar(label='Mask (0=outside, 1=inside ROI)')
            plt.title('ROI Mask')
            plt.xlabel('X (pixels)')
            plt.ylabel('Y (pixels)')
            plt.tight_layout()
            plt.show(block=True)
            print(f"  Displayed ROI mask for well {well}")
            
            # Interactive coordinate selection
            clicked_points = interactive_coordinate_selection(
                stitched_image, well_positions[well], pixel_size, directionality, image_flip
            )
            
            print(f"    Number of clicked points: {len(clicked_points)}")
            for i, (pixel_coords, stage_coords) in enumerate(clicked_points):
                print(f"      Point {i+1}: Pixel=({pixel_coords[0]:.1f}, {pixel_coords[1]:.1f}), "
                      f"Stage=({stage_coords[0]:.1f}, {stage_coords[1]:.1f}) um")
    
    # Print final timing summary
    print(f"\n{'='*60}")
    print(f"ACQUISITION TIMING SUMMARY")
    print(f"{'='*60}")
    print(f"Acquisition engine: {engine_names[acquisition_engine]}")
    print(f"Total acquisition time: {total_acquisition_time:.2f} seconds")
    print(f"Average time per well: {total_acquisition_time/len(user_input['selected_wells']):.2f} seconds")
    
    total_positions = sum(times['num_positions'] for times in acquisition_times.values())
    if total_positions > 0:
        print(f"Total positions processed: {total_positions}")
        print(f"Average time per position: {total_acquisition_time/total_positions:.2f} seconds")
    
    print(f"\nPer-well breakdown:")
    for well, times in acquisition_times.items():
        print(f"  Well {well}: {times['total_time']:.2f}s ({times['num_positions']} positions)")
    
    print(f"{'='*60}")
    
    # Save timing results to file
    timing_file = os.path.join(save_directory, f"timing_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
    with open(timing_file, 'w') as f:
        f.write(f"Acquisition Timing Results\n")
        f.write(f"========================\n")
        f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Acquisition engine: {engine_names[acquisition_engine]}\n")
        f.write(f"Total time: {total_acquisition_time:.2f} seconds\n")
        f.write(f"Total positions: {total_positions}\n")
        f.write(f"Average time per position: {total_acquisition_time/total_positions:.2f} seconds\n\n")
        f.write(f"Per-well breakdown:\n")
        for well, times in acquisition_times.items():
            f.write(f"  Well {well}: {times['total_time']:.2f}s ({times['num_positions']} positions)\n")
    
    print(f"Timing results saved to: {timing_file}")
