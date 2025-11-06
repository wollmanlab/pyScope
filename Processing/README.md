# Processing Module

The Processing module provides image processing, stitching, registration, and segmentation functionality for pyScope. It supports both automated processing pipelines and interactive tools for manual curation.

## Overview

The Processing module is responsible for:
- **Image Stitching**: Combining multiple FOV images into large stitched images
- **Image Processing**: Background subtraction, flat-field correction, filtering
- **Image Registration**: Phase correlation-based registration for position correction
- **Interactive Tools**: ROI selection and coordinate selection for manual curation
- **Position Filtering**: Filter positions based on ROI selections

## Architecture

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

## Integration with Scope Module

The Processing module is tightly integrated with the Scope module:

1. **Position Filtering**: Scope uses `stitch_acquisition()` and `interactive_roi_selection()` for filtering positions
2. **Focus Setting**: Scope uses `interactive_coordinate_selection()` for manual focus point selection
3. **Preview Stitching**: Scope uses `stitch_acquisition()` for preview generation and display
4. **Image Processing**: Optional ImageProcessor can be passed to stitching functions

## File Formats

### Metadata Format
Stitching expects a tab-separated metadata file (`Metadata.txt`) with columns:
- `Position`: Position name
- `Channel`: Channel name
- `Zindex`: Z-stack index
- `X`, `Y`: Stage coordinates in microns
- `filename`: Image filename
- `PixelSize`: Pixel size in microns

### Image Formats
- Supports TIFF images via `tifffile`
- 16-bit unsigned integer arrays (uint16)
- Grayscale images (2D arrays)

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

