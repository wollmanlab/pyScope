# Plate Configurations

Plate configuration files define the geometry of wells on a plate for automated position generation. These JSON files are used by the `Positions` class to automatically generate tiling positions that cover each well with the desired overlap.

## Overview

Plate configuration files specify:
- **Well geometry**: Shape (circle or rectangle), dimensions, and center coordinates
- **Well layout**: Multiple wells can be defined in a single configuration file
- **Coordinate system**: Plate coordinates (before microscope-specific transformations)

The `Positions` class uses these configurations along with scope `fov_info` (Field of View information) to automatically generate a grid of imaging positions that tile each well with the specified overlap.

## JSON Format

### Basic Format (Legacy)

The simplest format is a dictionary where each key is a well name and each value is a well definition:

```json
{
  "well_name": {
    "center": {
      "X": 0.0,
      "Y": 0.0,
      "Z": 0.0
    },
    "shape": "circle",
    "dimensions": {
      "radius": 5000.0
    }
  }
}
```

### Extended Format (with Offset Correction)

The extended format includes metadata for offset correction:

```json
{
  "offset_correction": false,
  "wells": {
    "well_name": {
      "center": {
        "X": 0.0,
        "Y": 0.0,
        "Z": 0.0
      },
      "shape": "circle",
      "dimensions": {
        "radius": 5000.0
      }
    }
  }
}
```

**`offset_correction`**: If `true`, the Positions class will subtract stage offsets from center coordinates before generating positions. This is useful when plate coordinates were measured on a microscope with non-zero offsets.

## Well Definition Structure

Each well definition must contain:

### Required Fields

- **`center`** (dict): Center coordinates of the well in plate coordinate system
  - `X` (float): X coordinate in microns
  - `Y` (float): Y coordinate in microns
  - `Z` (float): Z coordinate in microns (focus level)

- **`shape`** (string): Well shape - either `"circle"` or `"rectangle"` (case-insensitive)

- **`dimensions`** (dict): Shape-specific dimensions
  - For circles: `{"radius": <float>}` - radius in microns
  - For rectangles: `{"width": <float>, "height": <float>}` - width and height in microns

### Optional Fields

- **`rotation`** (float): Rotation angle in degrees (default: 0.0). Only applies to rectangles.

## Shape Examples

### Circle Well

```json
{
  "A1": {
    "center": {
      "X": 0.0,
      "Y": 0.0,
      "Z": 0.0
    },
    "shape": "circle",
    "dimensions": {
      "radius": 5000.0
    }
  }
}
```

### Rectangle Well (No Rotation)

```json
{
  "B1": {
    "center": {
      "X": 10000.0,
      "Y": 10000.0,
      "Z": 0.0
    },
    "shape": "rectangle",
    "dimensions": {
      "width": 8000.0,
      "height": 6000.0
    }
  }
}
```

### Rectangle Well (With Rotation)

```json
{
  "C1": {
    "center": {
      "X": 20000.0,
      "Y": 20000.0,
      "Z": 0.0
    },
    "shape": "rectangle",
    "dimensions": {
      "width": 8000.0,
      "height": 6000.0
    },
    "rotation": 45.0
  }
}
```

## How FOV Info Generates Positions

The `Positions` class uses scope `fov_info` to determine how to tile each well. The `fov_info` dictionary contains:

- **`X`** (float): Field of view width in microns (image width × pixel size)
- **`Y`** (float): Field of view height in microns (image height × pixel size)
- **`Overlap`** (float): Desired overlap between adjacent tiles (0.0 to 1.0, typically 0.1 for 10% overlap)

### Position Generation Process

1. **Calculate Step Size**: 
   ```
   step_x = fov_info['X'] × (1 - fov_info['Overlap'])
   step_y = fov_info['Y'] × (1 - fov_info['Overlap'])
   ```
   This determines the distance between centers of adjacent tiles.

2. **Determine Coverage**: 
   - For circles: Calculate bounding box from radius
   - For rectangles: Calculate bounding box accounting for rotation
   - Determine number of steps needed in X and Y directions

3. **Generate Grid**: 
   - Create a grid of candidate positions covering the bounding box
   - Step size determines spacing between positions

4. **Filter by Shape**: 
   - For circles: Keep positions within the radius
   - For rectangles: Keep positions within the rotated rectangle boundaries

5. **Transform Coordinates**: 
   - Apply axis mapping and offsets to convert plate coordinates to stage coordinates
   - Validate positions against stage limits

### Example Calculation

Given:
- `fov_info = {'X': 200, 'Y': 200, 'Overlap': 0.1}`
- Circle well with `radius = 5000`

Step sizes:
- `step_x = 200 × (1 - 0.1) = 180 microns`
- `step_y = 200 × (1 - 0.1) = 180 microns`

Number of steps needed:
- `num_steps_x = ceil(5000 / 180) = 28 steps`
- `num_steps_y = ceil(5000 / 180) = 28 steps`

This generates approximately `(2 × 28 + 1)² = 3249` candidate positions, which are then filtered to only include those within the circle.

## Usage Examples

### Loading a Plate Configuration

```python
from Scope.positions import Positions

# Initialize Positions with scope fov_info
positions = Positions(
    fov_info={'X': 200, 'Y': 200, 'Overlap': 0.1},
    limits={'X': (0, 100000), 'Y': (0, 100000), 'Z': (0, 10000)}
)

# Load plate configuration
positions.load_plate_from_json('Underwood6')

# Access generated positions
print(f"Total positions: {len(positions.positions)}")
print(f"Wells: {positions.Wells}")
```

### Creating a New Plate Configuration

```python
from Scope.positions import Positions

positions = Positions(
    fov_info={'X': 200, 'Y': 200, 'Overlap': 0.1},
    limits={'X': (0, 100000), 'Y': (0, 100000), 'Z': (0, 10000)}
)

# Add a single well
positions.add_well('A1', {
    'center': {'X': 0, 'Y': 0, 'Z': 0},
    'shape': 'circle',
    'dimensions': {'radius': 5000}
})

# Save as plate configuration
positions.file_handler.save_plate_config('my_plate', {
    'A1': {
        'center': {'X': 0, 'Y': 0, 'Z': 0},
        'shape': 'circle',
        'dimensions': {'radius': 5000}
    }
})
```

### Creating a Grid of Wells

```python
from Scope.positions import Positions

positions = Positions(
    fov_info={'X': 200, 'Y': 200, 'Overlap': 0.1},
    limits={'X': (0, 100000), 'Y': (0, 100000), 'Z': (0, 10000)}
)

# Create a 2x3 grid starting from A1
base_well = {
    'center': {'X': 0, 'Y': 0, 'Z': 0},
    'shape': 'circle',
    'dimensions': {'radius': 5000}
}

positions.add_well_grid(
    base_well_info=base_well,
    rows=2,
    columns=3,
    row_spacing=20000,
    column_spacing=20000,
    save_name='my_grid_plate'
)
```

## Coordinate Systems

### Plate Coordinates

Plate configuration files use **plate coordinates**, which are:
- Measured relative to a plate reference point
- Independent of microscope stage configuration
- Transformed to stage coordinates by the Positions class

### Stage Coordinates

The Positions class transforms plate coordinates to **stage coordinates** using:
- **Axis mapping**: Maps plate X/Y to stage X/Y (with optional sign changes)
- **Offsets**: Adds stage-specific offsets to account for stage zero position

Example transformation:
```python
# Plate coordinate: (1000, 2000)
# With axis_mapping={'stage_x': 'plate_x', 'stage_y': 'plate_y'}
# And offsets={'X': 100000, 'Y': 50000, 'Z': 0}
# Stage coordinate: (101000, 52000)
```

## File Location

Plate configuration files should be saved in the `Plates/` directory with a `.json` extension. The `load_plate_from_json()` method looks for files in this directory.

Example file structure:
```
Plates/
├── example.json
├── Underwood6.json
├── Testing.json
└── my_custom_plate.json
```

## Best Practices

1. **Use descriptive well names**: Use names that match your experimental design (e.g., "A1", "B2", "Control_1")

2. **Consistent units**: All coordinates and dimensions should be in microns

3. **Validate dimensions**: Ensure well dimensions are reasonable for your FOV size
   - Well radius/width should be significantly larger than FOV size
   - Consider overlap when planning coverage

4. **Test configurations**: Load configurations and verify position generation before experiments

5. **Document custom plates**: Add comments or documentation for custom plate configurations

6. **Offset correction**: Use `offset_correction: true` if plate coordinates were measured on a microscope with non-zero offsets

## Troubleshooting

### No positions generated
- Check that well dimensions are larger than FOV size
- Verify `fov_info` values are correct
- Check that well center is within stage limits

### Too many/few positions
- Adjust `Overlap` value in `fov_info` (higher overlap = more positions)
- Verify well dimensions match actual well size
- Check FOV size calculation (image dimensions × pixel size)

### Positions outside stage limits
- Verify stage limits are set correctly
- Check axis mapping and offsets
- Consider using offset correction if coordinates were measured incorrectly

## Related Documentation

- **[Scope Module](../Scope/README.md)**: Detailed documentation on the Positions class and scope integration
- **[FileHandler](../README.md#filehandler-class)**: Information on how plate configurations are stored and loaded

