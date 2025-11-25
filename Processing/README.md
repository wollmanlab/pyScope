# Processing Module

The Processing module provides image processing, stitching, registration, and segmentation functionality for pyScope. It supports both automated processing pipelines and interactive tools for manual curation. The module includes an autonomous `Processing` class that operates independently with continuous monitoring for automated experiment execution.

## Overview

The Processing module is responsible for:
- **Image Stitching**: Combining multiple FOV images into large stitched images
- **Image Processing**: Background subtraction, flat-field correction, filtering
- **Image Registration**: Phase correlation-based registration for position correction
- **Interactive Tools**: ROI selection and coordinate selection for manual curation
- **Position Filtering**: Filter positions based on ROI selections
- **Autonomous Processing**: Independent operation with file-based communication for automated stitching workflows

## Architecture

### Core Classes

#### `Processing` (`processing.py`)
The main processing orchestrator class that provides:
- File-based communication with Experiment system
- Continuous monitoring for autonomous task execution
- Automated stitching workflows with flat-field correction
- Integration with experiment task scheduling

**Key Features:**
- Autonomous operation via continuous monitoring loop
- Automatic flat-field (FF) and constant correction calculation
- Group-based stitching with position indexing support
- Status management and progress tracking
- Command interpretation and protocol execution

**Protocols:**
- **Stitch**: Automated stitching protocol that:
  1. Finds latest acquisition directories for specified chambers
  2. Calculates flat-field and constant corrections for each channel
  3. Saves corrections as TIF files
  4. Stitches images per group with corrections applied
  5. Saves stitched images and optional indexing outputs

**Command Format:**
```
Stitch*['A','B']*hybe1
Stitch*['A','B']*hybe1+idx_stitch
```

**Output Files:**
- `FF_{channel}.tif`: Flat-field correction image
- `constant_{channel}.tif`: Constant offset image
- `stitched_{channel}_{group}.tif`: Stitched image (uint16)
- `pixel2stage_{channel}_{group}.pkl`: Coordinate transformation function (if idx_stitch)
- `idx_canvas_{channel}_{group}.tif`: Position indexing array (if idx_stitch)
- `posname_idx_mapper_{channel}_{group}.json`: Position name to index mapping (if idx_stitch)

**Usage:**
```python
from Processing.processing import Processing

# Initialize and start continuous monitoring
processing = Processing()
processing.continuous_monitoring()
```

### Core Modules

#### `stitching.py`
Main stitching functionality for combining acquisition images:

**`stitch_acquisition()`**
- Stitches images from an acquisition directory based on metadata
- Supports configurable pixel size, binning, and transformations
- Returns stitched canvas and coordinate transformation function
- Optional position indexing for ROI-based filtering

**Key Features:**
- Metadata-driven stitching (reads from `Metadata.txt`)
- Configurable output pixel size (automatic binning calculation)
- Image transformations (rotation, flipping)
- Registration dictionary support for position correction
- Border padding for edge handling
- Position name filtering

**Interactive Tools:**
- `interactive_roi_selection()`: Freehand drawing interface for ROI selection
- `interactive_coordinate_selection()`: Point-and-click coordinate selection
- `filter_positions()`: Filter positions based on ROI selections

#### `image_processing.py`
Image processing pipeline for preprocessing images:

**`ImageProcessor` Class**
- Configurable image processing pipeline
- Flat-field correction (FF) and constant offset subtraction
- Background subtraction with multiple methods
- Image filtering and smoothing

**Processing Pipeline:**
1. **Binning**: Optional downsampling via median binning
2. **Background Subtraction**: Multiple methods (Gaussian, rolling ball, spline, polyfit)
3. **Optics Correction**: Flat-field correction and constant offset
4. **Filtering**: Median filtering for noise reduction

**Supported Background Methods:**
- `gaussian`: Gaussian blur-based background
- `rolling_ball`: Rolling ball algorithm
- `spline`: Spline interpolation on downsampled image
- `polyfit`: Polynomial fitting
- `median`: Median filtering
- `percentile`: Percentile filtering
- `minimum`: Minimum filtering

#### `image_registration.py`
Image registration for position correction:

**`register()`**
- Phase cross-correlation based registration
- Whitening and windowing for robust registration
- Returns shift vector and error metric

**Key Features:**
- Sub-pixel accuracy via upsampling
- Windowed images to reduce edge effects
- Whitening for illumination correction
- Correlation-based shift selection

#### `segmentation.py`
Segmentation functionality (currently minimal implementation):
- Placeholder for future segmentation algorithms

## Key Functions

### Stitching

#### `stitch_acquisition()`

```python
canvas, pixel2stage = stitch_acquisition(
    acquisition_dir='path/to/acquisition',
    channel='FarRed',
    zindex=0,
    metadata_filename='Metadata.txt',
    image_processor=None,
    registration_dict={},
    border=1000,
    stitch_rotate=0,
    stitch_flipud=False,
    stitch_fliplr=False,
    output_pixel_size=5.0,
    idx_stitch=False,
    position_names=None,
    verbose=True
)
```

**Parameters:**
- `acquisition_dir`: Path to acquisition directory containing images and metadata
- `channel`: Channel name to stitch
- `zindex`: Z-stack index (default: 0)
- `metadata_filename`: Name of metadata file (default: 'Metadata.txt')
- `image_processor`: Optional ImageProcessor instance for preprocessing
- `registration_dict`: Dictionary mapping position names to registration shifts
- `border`: Border pixels to add around stitched image
- `stitch_rotate`: Number of 90-degree rotations to apply
- `stitch_flipud`: Flip image up/down
- `stitch_fliplr`: Flip image left/right
- `output_pixel_size`: Target output pixel size in microns (auto-calculates binning)
- `idx_stitch`: If True, returns position indexing arrays
- `position_names`: Optional list of position names to include
- `verbose`: Show progress bar

**Returns:**
- `canvas`: Stitched image array [height, width]
- `pixel2stage`: Function mapping pixel coordinates (x, y) to stage coordinates (X, Y)
- `idx_canvas` (if `idx_stitch=True`): Array mapping pixels to position indices
- `posname_idx_mapper` (if `idx_stitch=True`): Dictionary mapping position names to indices

### Image Processing

#### `ImageProcessor`

```python
from Processing.image_processing import ImageProcessor

# Initialize with default parameters
processor = ImageProcessor()

# Initialize with custom parameters
processor = ImageProcessor(
    FF=flat_field_image,  # Flat-field correction image
    constant=100.0,        # Constant offset
    parameters={
        'bin': 1,
        'process_img_before_FF': True,
        'highpass_sigma': 10,
        'highpass_smooth': 2,
        'highpass_function': 'rolling_ball',
        'highpass_smooth_function': 'median'
    }
)

# Process an image
processed_image = processor.process(image_path_or_array)
```

**Processing Parameters:**
- `bin`: Downsampling factor (must divide image dimensions)
- `process_img_before_FF`: Order of processing steps
- `highpass_sigma`: Background subtraction sigma (0 to disable)
- `highpass_smooth`: Smoothing before background subtraction
- `highpass_function`: Background method ('gaussian', 'rolling_ball', 'spline', etc.)
- `highpass_smooth_function`: Smoothing method ('median', 'gaussian', etc.)

### Image Registration

#### `register()`

```python
from Processing.image_registration import register

shift, error = register(
    img1=reference_image,
    img2=target_image,
    sigma=10.0,      # Whitening sigma
    upsample=10      # Upsampling factor for sub-pixel accuracy
)
```

**Returns:**
- `shift`: (dy, dx) shift vector in pixels
- `error`: Registration error metric (lower is better)

### Interactive Tools

#### `interactive_roi_selection()`

```python
from Processing.stitching import interactive_roi_selection

mask, canvas_rgb = interactive_roi_selection(
    stitched_image=canvas,
    message='Select areas to image'
)
```

**Returns:**
- `mask`: Labeled mask array (0 = outside ROI, 1, 2, 3, ... = ROI indices)
- `canvas_rgb`: RGB visualization of mask overlaid on image

**Controls:**
- Left click and drag: Draw ROI polygon
- `U` key: Undo last ROI
- `R` key: Reset all ROIs
- `D` key: Done (close window)
- "Done" button: Finish selection

#### `interactive_coordinate_selection()`

```python
from Processing.stitching import interactive_coordinate_selection

points = interactive_coordinate_selection(
    stitched_image=canvas,
    message='Select focus points'
)
```

**Returns:**
- `points`: List of (x, y) pixel coordinate tuples

**Controls:**
- Left click: Select point
- `U` key: Undo last point
- `R` key: Reset all points
- `D` key: Done (close window)
- "Done" button: Finish selection

#### `filter_positions()`

```python
from Processing.stitching import filter_positions

positions_to_keep = filter_positions(
    idx_canvas=idx_canvas,
    mask=mask,
    posname_idx_mapper=posname_idx_mapper
)
```

**Returns:**
- Dictionary mapping position names to ROI group numbers

## Usage Examples

### Autonomous Processing Operation

```python
from Processing.processing import Processing

# Initialize Processing class
processing = Processing()

# Start continuous monitoring (runs indefinitely)
processing.continuous_monitoring()
```

The Processing class will:
1. Monitor `Processing_status.txt` for commands
2. Execute stitching protocols automatically
3. Calculate flat-field corrections
4. Stitch images per group
5. Save outputs to acquisition directories

### Experiment Integration

Processing tasks are automatically created by the Experiment class:

```python
# Experiment automatically creates tasks like:
# Stitch*['A','B']*hybe1
# Stitch*['A','B']*Strip1+idx_stitch  # First stitch includes indexing

# Processing executes these tasks independently:
# 1. Finds latest acquisition matching 'hybe1' for wells A and B
# 2. Calculates FF and constant for each channel
# 3. Stitches images per group
# 4. Saves stitched images and optional indexing outputs
```

### Basic Stitching

```python
from Processing.stitching import stitch_acquisition

# Stitch a preview acquisition
canvas, pixel2stage = stitch_acquisition(
    acquisition_dir='path/to/preview_Well-A1',
    channel='FarRed',
    output_pixel_size=5.0,
    verbose=True
)

# Convert pixel coordinates to stage coordinates
X, Y = pixel2stage(1000, 2000)
```

### Stitching with Image Processing

```python
from Processing.stitching import stitch_acquisition
from Processing.image_processing import ImageProcessor

# Create image processor
processor = ImageProcessor(
    FF=flat_field_image,
    parameters={
        'highpass_sigma': 10,
        'highpass_function': 'rolling_ball'
    }
)

# Stitch with processing
canvas, pixel2stage = stitch_acquisition(
    acquisition_dir='path/to/acquisition',
    channel='FarRed',
    image_processor=processor,
    output_pixel_size=5.0
)
```

### Position Filtering Workflow

```python
from Processing.stitching import (
    stitch_acquisition, 
    interactive_roi_selection, 
    filter_positions
)

# Stitch preview with position indexing
canvas, pixel2stage, idx_canvas, posname_idx_mapper = stitch_acquisition(
    acquisition_dir='path/to/preview',
    channel='FarRed',
    output_pixel_size=50.0,
    idx_stitch=True
)

# Interactive ROI selection
mask, canvas_rgb = interactive_roi_selection(
    canvas,
    message='Select areas to image'
)

# Filter positions based on ROIs
positions_to_keep = filter_positions(
    idx_canvas,
    mask,
    posname_idx_mapper
)

# positions_to_keep maps position names to ROI group numbers
# Use this to filter the positions DataFrame
```

### Focus Point Selection

```python
from Processing.stitching import (
    stitch_acquisition,
    interactive_coordinate_selection
)

# Stitch preview
canvas, pixel2stage = stitch_acquisition(
    acquisition_dir='path/to/preview',
    channel='FarRed',
    output_pixel_size=50.0
)

# Select focus points interactively
points = interactive_coordinate_selection(
    canvas,
    message='Select at least 4 focus points'
)

# Convert to stage coordinates
focus_positions = [pixel2stage(x, y) for x, y in points]
```

### Image Registration

```python
from Processing.image_registration import register
import tifffile

# Load reference and target images
ref_img = tifffile.imread('reference.tif')
target_img = tifffile.imread('target.tif')

# Register images
shift, error = register(ref_img, target_img, sigma=10.0, upsample=10)

print(f"Shift: {shift}, Error: {error}")

# Apply shift to registration dictionary
registration_dict = {
    'position_name': {
        'X': shift[1] * pixel_size,  # Convert pixels to microns
        'Y': shift[0] * pixel_size
    }
}
```

## Integration with Experiment Workflow

The Processing module is integrated into the experiment workflow:

1. **Task Scheduling**: Experiment automatically creates Processing tasks after each Scope Acquire command
2. **Autonomous Operation**: Processing runs independently, monitoring for tasks via file-based communication
3. **Automatic Stitching**: After each acquisition, Processing automatically:
   - Calculates flat-field corrections
   - Stitches images per group
   - Saves outputs to acquisition directories
4. **Position Indexing**: First stitch for each group includes position indexing for ROI-based analysis

**Task Integration:**
- Processing tasks are automatically added to `Experiment_tasks.csv` after each Scope Acquire task
- First stitch command for each group includes `+idx_stitch` flag for position indexing
- Processing executes tasks independently, coordinating with Experiment via status files

## Integration with Scope Module

The Processing module is tightly integrated with the Scope module:

1. **Position Filtering**: Scope uses `stitch_acquisition()` and `interactive_roi_selection()` for filtering positions
2. **Focus Setting**: Scope uses `interactive_coordinate_selection()` for manual focus point selection
3. **Preview Stitching**: Scope uses `stitch_acquisition()` for preview generation and display
4. **Image Processing**: Optional ImageProcessor can be passed to stitching functions
5. **Automated Workflow**: Processing automatically stitches acquisitions created by Scope

## File-Based Communication

The Processing class communicates with the Experiment system through files in the `State` directory:

### Input Files
- **`Processing_status.txt`**: Task trigger file with protocol commands
- **`Metadata.txt`**: Image metadata in acquisition directories
- **Acquisition directories**: Image files and metadata from Scope acquisitions

### Output Files
- **`Processing_status.txt`**: Current processing status (Idle, Running, Finished, Error)
- **`Processing_task_idx.txt`**: Current task index for progress tracking
- **`Processing.log`**: Logging output
- **Acquisition directories**: Stitched images and correction files

### Status Values
- `Idle`: Ready for new tasks
- `Running:<protocol>`: Currently executing a protocol
- `Finished:<protocol>`: Protocol completed successfully
- `Error:<message>`: Error occurred during execution
- `Offline`: Processing monitoring stopped

### Command Format
Commands are sent via status file in the format:
```
Command:Stitch*['A','B']*hybe1
Command:Stitch*['A','B']*hybe1+idx_stitch
```

Where:
- `Stitch`: Protocol name
- `['A','B']`: List of chamber/well names
- `hybe1`: Acquisition name
- `+idx_stitch`: Optional flag for position indexing (first stitch per group)

## File Formats

### Metadata Format
Stitching expects a tab-separated metadata file (`Metadata.txt`) with columns:
- `Position`: Position name
- `Channel`: Channel name
- `Zindex`: Z-stack index
- `X`, `Y`: Stage coordinates in microns
- `filename`: Image filename
- `PixelSize`: Pixel size in microns
- `Group`: Group assignment for position (optional)

### Image Formats
- Supports TIFF images via `tifffile`
- 16-bit unsigned integer arrays (uint16)
- Grayscale images (2D arrays)
- 3D arrays for position indexing (height × width × 3)

## Dependencies

- `numpy`: Array operations
- `pandas`: Metadata handling
- `scipy`: Image filtering and registration
- `scikit-image`: Image processing algorithms
- `tifffile`: TIFF image I/O
- `matplotlib`: Interactive visualization
- `tqdm`: Progress bars

## Performance Considerations

- **Large Images**: Use `output_pixel_size` to reduce memory usage for large acquisitions
- **Binning**: Pre-binning images reduces processing time
- **ROI Selection**: Lower `output_pixel_size` improves interactive performance
- **Registration**: Higher `upsample` improves accuracy but increases computation time

## Future Enhancements

- Advanced segmentation algorithms
- Multi-scale registration
- GPU acceleration for large images
- Additional background subtraction methods
- Real-time stitching preview
- Support for additional image formats

