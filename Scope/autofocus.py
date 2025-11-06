import numpy as np
import pandas as pd
import sys
import os
import socket
import importlib
import tkinter as tk
from tkinter import ttk
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from file_handler import FileHandler
from Processing.stitching import stitch_acquisition, interactive_coordinate_selection
from scipy.ndimage import gaussian_filter, median_filter, minimum_filter, percentile_filter
from scipy import ndimage
# Import GUI styling from gui_styling.py (separated to avoid circular imports)
from gui_styling import GUI_COLORS, GUI_FONTS, apply_dark_theme, create_dark_style

class Autofocus:
    def __init__(self):
        self.file_handler = FileHandler()
    def log(self,message,level='info'):
        self.file_handler.log(message,level=level,system_prefix=self.__class__.__name__)
    def setup(self,scope):
        self.log('No Setup Needed',level='warning')
    def update_focus(self,scope,autofocus_group):
        self.log(f'No Update Needed for {autofocus_group}',level='warning')
    def focus(self,scope,X=None,Y=None,position_name=None,goto=False):
        self.log('No Autofocus used',level='warning')
        return scope.Z

class ImageScanAutofocus(Autofocus):
    def __init__(self,
            channel='FarRed',
            exposure=25,
            coarse_window=(200,20),
            medium_window=(20,2),
            fine_window=(5,0.5),
            bkg_sigma=25,
            median_filter_size=2,binning=2):
        super().__init__()
        self.channel = channel
        self.exposure = exposure
        self.coarse_window = coarse_window
        self.medium_window = medium_window
        self.fine_window = fine_window
        self.bkg_sigma = bkg_sigma
        self.median_filter_size = median_filter_size
        self.binning = binning

    def scan_find_focus(self,scope,windows=['coarse','medium','fine']):
        self.log('ImageScanAutofocus find focus',level='debug')
        previous_channel = scope.Channel
        previous_exposure = scope.Exposure
        previous_binning = scope.Binning
        scope.Channel = self.channel
        scope.Exposure = self.exposure
        scope.Binning = self.binning
        selected_windows = []
        if 'coarse' in windows:
            selected_windows.append(self.coarse_window)
        if 'medium' in windows:
            selected_windows.append(self.medium_window)
        if 'fine' in windows:
            selected_windows.append(self.fine_window)
        for window_width,window_stepsize in selected_windows:
            starting_Z = scope.Z
            steps = np.arange(starting_Z - window_width,starting_Z + window_width,window_stepsize)
            metrics = np.zeros(len(steps))
            for i, step in enumerate(steps):
                if not scope.is_valid('Z', step):
                    self.log(f"ImageScanAutofocus Invalid Z: { step}",level='warning')
                    continue
                scope.Z =  step
                metrics[i] = self.calculate_metric(scope.snapImage())
            best_step = steps[np.argmax(metrics)]
            self.log(f"Best step: {best_step} with metric: {metrics[np.argmax(metrics)]}",level='info')
            self.log(f"info {zip(steps,metrics)}",level='info')
            scope.Z = best_step
        scope.Channel = previous_channel
        scope.Exposure = previous_exposure
        scope.Binning = previous_binning
        return scope.Z

    def calculate_metric(self,image):
        self.log('ImageScanAutofocus calculate metric',level='debug')
        # Convert to float32 for processing
        image = image.astype(np.float32)
        # Step 1: Background subtraction with Gaussian filter
        if self.bkg_sigma > 0:
            image = image - gaussian_filter(image, self.bkg_sigma)
        # Step 2: Median filtering (2x2)
        if self.median_filter_size > 0:
            image = median_filter(image, size=self.median_filter_size)
        # Step 3: Sobel edge detection
        # image = np.sqrt(ndimage.sobel(image, axis=1)**2)
        # Step 4: Sum of edge magnitudes
        focus_metric = np.mean(np.abs(image))
        return focus_metric

    def focus(self,scope,X=None,Y=None,position_name=None,goto=False):
        self.scan_find_focus(scope,windows=['fine'])
        return scope.Z
    
    def user_input_gui(self, scope):
        """Simple popup GUI for configuring ImageScanAutofocus parameters."""
        root = tk.Tk()
        root.title("ImageScanAutofocus Configuration")
        root.geometry("400x550")
        root.resizable(False, False)
        root.attributes('-topmost', True)
        apply_dark_theme(root)
        style = create_dark_style()
        
        result = [None]
        
        frame = tk.Frame(root, bg=GUI_COLORS['background'], padx=20, pady=20)
        frame.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(frame, text="ImageScanAutofocus Configuration", 
                bg=GUI_COLORS['background'], fg=GUI_COLORS['text'], 
                font=GUI_FONTS['heading']).pack(pady=(0, 15))
        
        channel_frame = tk.Frame(frame, bg=GUI_COLORS['background'])
        channel_frame.pack(fill=tk.X, pady=5)
        tk.Label(channel_frame, text="Channel:", bg=GUI_COLORS['background'], 
                fg=GUI_COLORS['text'], width=12, anchor='w', font=GUI_FONTS['body']).pack(side=tk.LEFT)
        channel_var = tk.StringVar()
        channel_var.set('FarRed')
        channel_combo = ttk.Combobox(channel_frame, textvariable=channel_var, 
                                     values=scope.available_channels, state='readonly', 
                                     width=20, style='Dark.TCombobox')
        channel_combo.set('FarRed')
        channel_combo.pack(side=tk.LEFT)
        
        exposure_frame = tk.Frame(frame, bg=GUI_COLORS['background'])
        exposure_frame.pack(fill=tk.X, pady=5)
        tk.Label(exposure_frame, text="Exposure:", bg=GUI_COLORS['background'], 
                fg=GUI_COLORS['text'], width=12, anchor='w', font=GUI_FONTS['body']).pack(side=tk.LEFT)
        exposure_var = tk.StringVar(value='5')
        exposure_entry = tk.Entry(exposure_frame, textvariable=exposure_var, 
                                 bg=GUI_COLORS['entry'], fg=GUI_COLORS['text'],
                                 insertbackground=GUI_COLORS['text'], width=22, font=GUI_FONTS['entry'])
        exposure_entry.pack(side=tk.LEFT)
        
        bkg_sigma_frame = tk.Frame(frame, bg=GUI_COLORS['background'])
        bkg_sigma_frame.pack(fill=tk.X, pady=5)
        tk.Label(bkg_sigma_frame, text="Bkg Sigma:", bg=GUI_COLORS['background'], 
                fg=GUI_COLORS['text'], width=12, anchor='w', font=GUI_FONTS['body']).pack(side=tk.LEFT)
        bkg_sigma_var = tk.StringVar(value='10')
        bkg_sigma_entry = tk.Entry(bkg_sigma_frame, textvariable=bkg_sigma_var, 
                                 bg=GUI_COLORS['entry'], fg=GUI_COLORS['text'],
                                 insertbackground=GUI_COLORS['text'], width=22, font=GUI_FONTS['entry'])
        bkg_sigma_entry.pack(side=tk.LEFT)
        
        median_filter_size_frame = tk.Frame(frame, bg=GUI_COLORS['background'])
        median_filter_size_frame.pack(fill=tk.X, pady=5)
        tk.Label(median_filter_size_frame, text="Median Filter:", bg=GUI_COLORS['background'], 
                fg=GUI_COLORS['text'], width=12, anchor='w', font=GUI_FONTS['body']).pack(side=tk.LEFT)
        median_filter_size_var = tk.StringVar(value='0')
        median_filter_size_entry = tk.Entry(median_filter_size_frame, textvariable=median_filter_size_var, 
                                 bg=GUI_COLORS['entry'], fg=GUI_COLORS['text'],
                                 insertbackground=GUI_COLORS['text'], width=22, font=GUI_FONTS['entry'])
        median_filter_size_entry.pack(side=tk.LEFT)
        
        windows = [
            ('Coarse', 'coarse', (200, 20)),
            ('Medium', 'medium', (20, 2)),
            ('Fine', 'fine', (5, 0.5))
        ]
        
        window_vars = {}
        for window_name, window_key, (range_val, step_val) in windows:
            window_frame = tk.LabelFrame(frame, text=f"{window_name} Window", 
                                        bg=GUI_COLORS['background'], fg=GUI_COLORS['text'],
                                        font=GUI_FONTS['body'], padx=10, pady=5)
            window_frame.pack(fill=tk.X, pady=5)
            
            range_frame = tk.Frame(window_frame, bg=GUI_COLORS['background'])
            range_frame.pack(fill=tk.X, pady=2)
            tk.Label(range_frame, text="Range (±):", bg=GUI_COLORS['background'], 
                    fg=GUI_COLORS['text'], width=10, anchor='w', font=GUI_FONTS['small']).pack(side=tk.LEFT)
            range_var = tk.StringVar(value=str(range_val))
            window_vars[f'{window_key}_range'] = range_var
            tk.Entry(range_frame, textvariable=range_var, bg=GUI_COLORS['entry'], 
                    fg=GUI_COLORS['text'], insertbackground=GUI_COLORS['text'], 
                    width=15, font=GUI_FONTS['small']).pack(side=tk.LEFT, padx=(0, 5))
            tk.Label(range_frame, text="μm", bg=GUI_COLORS['background'], 
                    fg=GUI_COLORS['text_secondary'], font=GUI_FONTS['small']).pack(side=tk.LEFT)
            
            step_frame = tk.Frame(window_frame, bg=GUI_COLORS['background'])
            step_frame.pack(fill=tk.X, pady=2)
            tk.Label(step_frame, text="Step:", bg=GUI_COLORS['background'], 
                    fg=GUI_COLORS['text'], width=10, anchor='w', font=GUI_FONTS['small']).pack(side=tk.LEFT)
            step_var = tk.StringVar(value=str(step_val))
            window_vars[f'{window_key}_step'] = step_var
            tk.Entry(step_frame, textvariable=step_var, bg=GUI_COLORS['entry'], 
                    fg=GUI_COLORS['text'], insertbackground=GUI_COLORS['text'], 
                    width=15, font=GUI_FONTS['small']).pack(side=tk.LEFT, padx=(0, 5))
            tk.Label(step_frame, text="μm", bg=GUI_COLORS['background'], 
                    fg=GUI_COLORS['text_secondary'], font=GUI_FONTS['small']).pack(side=tk.LEFT)
        
        def on_ok():
            try:
                channel = channel_var.get()
                exposure = float(exposure_var.get())
                if exposure <= 0:
                    raise ValueError("Exposure must be positive")
                
                bkg_sigma = float(bkg_sigma_var.get())
                if bkg_sigma < 0:
                    raise ValueError("Bkg Sigma must be non-negative")
                
                median_filter_size = float(median_filter_size_var.get())
                if median_filter_size < 0:
                    raise ValueError("Median Filter Size must be non-negative")
                
                coarse_range = float(window_vars['coarse_range'].get())
                coarse_step = float(window_vars['coarse_step'].get())
                medium_range = float(window_vars['medium_range'].get())
                medium_step = float(window_vars['medium_step'].get())
                fine_range = float(window_vars['fine_range'].get())
                fine_step = float(window_vars['fine_step'].get())
                
                if any(x <= 0 for x in [coarse_range, coarse_step, medium_range, medium_step, fine_range, fine_step]):
                    raise ValueError("All values must be positive")
                
                self.channel = channel
                self.exposure = exposure
                self.bkg_sigma = bkg_sigma
                self.median_filter_size = int(median_filter_size) if median_filter_size > 0 else 0
                self.coarse_window = (coarse_range, coarse_step)
                self.medium_window = (medium_range, medium_step)
                self.fine_window = (fine_range, fine_step)
                result[0] = True
                root.quit()
            except ValueError as e:
                error_label = tk.Label(frame, text=f"Error: {str(e)}", 
                                      fg=GUI_COLORS['error'], bg=GUI_COLORS['background'], 
                                      font=GUI_FONTS['small'])
                error_label.pack(pady=5)
                root.after(3000, error_label.destroy)
        
        def on_cancel():
            result[0] = False
            root.quit()
        
        button_frame = tk.Frame(frame, bg=GUI_COLORS['background'])
        button_frame.pack(fill=tk.X, pady=(15, 0))
        tk.Button(button_frame, text="Cancel", command=on_cancel, 
                 bg=GUI_COLORS['button'], fg=GUI_COLORS['text'],
                 activebackground=GUI_COLORS['button_hover'], activeforeground=GUI_COLORS['text'],
                 width=10, padx=10, pady=5, font=GUI_FONTS['button']).pack(side=tk.RIGHT, padx=(10, 0))
        tk.Button(button_frame, text="OK", command=on_ok, 
                 bg=GUI_COLORS['primary'], fg=GUI_COLORS['text'],
                 activebackground=GUI_COLORS['primary_hover'], activeforeground=GUI_COLORS['text'],
                 width=10, padx=10, pady=5, font=GUI_FONTS['button_bold']).pack(side=tk.RIGHT)
        
        root.mainloop()
        root.destroy()
        return result[0]

class RelativeAutofocus(ImageScanAutofocus):
    """
        RelativeAutofocus sets all positions within a autofocus group relative to a reference point.
        Setup will include selecting a reference point for each group 
        After all the points have been set the class will go to each point and find focus
        calling update focus will go back to the reference point and find focus and assign a rigid transformation to the group
        calling focus will determine which transformation to use for each region of space and return the updated coordinates

    """
    def __init__(self,level='well',setup_method='stitched'):
        super().__init__()
        optional_levels = ['plate','well','group']
        # If group selected assumed that positions has a column called group
        if not level in optional_levels:
            self.log(f'Invalid level: {level}. Valid levels are: {optional_levels}',level='error')
        self.level = level 

        if level =='plate':
            optional_setup_methods = ['manual']
        else:
            optional_setup_methods = ['stitched','manual']
        if setup_method not in optional_setup_methods:
            self.log(f'Invalid setup method: {setup_method}. Valid methods are: {optional_setup_methods}',level='warning')
        self.setup_method = setup_method if setup_method in optional_setup_methods else optional_setup_methods[0]
        self.reference_points_filename = os.path.join(self.file_handler.system_state_dir,f'autofocus_reference_points.csv')

    def setup(self,scope):
        positions = scope.file_handler.Positions
        if self.level == 'plate':
            positions['autofocus_group'] = 'plate'
        else:
            positions['autofocus_group'] = positions[self.level]
        self.positions = positions
        scope.file_handler.save_positions(positions)

        """ Gui for selecting Channel and Exposure and window sizes"""
        # self.user_input_gui(scope)
        

        unique_groups = positions['autofocus_group'].unique()
        setup_complete = False
        self.reference_points = pd.DataFrame(index=unique_groups,columns=['autofocus_group','X','Y','Z','X_shift','Y_shift','Z_shift'])
        if os.path.exists(self.reference_points_filename):
            # print(f"Loading reference points from {self.reference_points_filename}")
            loaded_reference_points = pd.read_csv(self.reference_points_filename,index_col='autofocus_group')
            loaded_reference_points['autofocus_group'] = loaded_reference_points.index
            # check if index is the same as unique_groups
            if len([i for i in unique_groups if not i in loaded_reference_points.index])==0:
                # print(f"Reference points match unique groups")
                self.log(f"Loaded reference points from {self.reference_points_filename}",level='info')
                self.reference_points = loaded_reference_points
                setup_complete = True
            else:
                # print(f"Reference points do not match unique groups")
                self.log(f"Reference points in {self.reference_points_filename} do not match unique groups",level='warning')
                # self.log(f"Loaded reference points from {self.reference_points_filename}",level='info')


        if not setup_complete:
            if self.setup_method == 'stitched':
                self.stitched_setup(scope)
            elif self.setup_method == 'manual':
                self.manual_setup(scope)

            # Now find focus for each group
            for autofocus_group,reference_point in self.reference_points.iterrows():
                self.log(f"Moving to {autofocus_group} reference point (X,Y,Z): {scope.XYZ}",level='info')
                scope.Z = scope.limits['Z'][0] # move to bottom of the plate
                scope.XY = (reference_point['X'],reference_point['Y'])
                scope.Z = reference_point['Z'] # move back to the original z position
                self.log(f"Finding focus for {autofocus_group}",level='info')
                new_focus = self.scan_find_focus(scope)
                self.reference_points.loc[autofocus_group,'Z'] = new_focus
            self.reference_points.to_csv(self.reference_points_filename,index=False)

    def manual_setup(self,scope):
        positions = self.positions
        total_groups = len(positions['autofocus_group'].unique())
        i = 0
        for autofocus_group in positions['autofocus_group'].unique():
            group_positions = positions[positions['autofocus_group'] == autofocus_group]
            Z = scope.Z
            scope.Z = self.limits['Z'][0] # move to bottom of the plate
            scope.XY = (group_positions['X'].median(), group_positions['Y'].median())
            scope.Z = Z # move back to the original z position
            scope._show_focus_popup("Please manually move the stage to \n select a reference point for {autofocus_group} (X,Y,Z) \n {i+1} of {total_groups}")
            self.reference_points.loc[autofocus_group,'X'] = scope.X
            self.reference_points.loc[autofocus_group,'Y'] = scope.Y
            self.reference_points.loc[autofocus_group,'Z'] = scope.Z
            self.reference_points.loc[autofocus_group,'X_shift'] = 0
            self.reference_points.loc[autofocus_group,'Y_shift'] = 0
            self.reference_points.loc[autofocus_group,'Z_shift'] = 0
            self.reference_points.loc[autofocus_group,'autofocus_group'] = autofocus_group
            i+=1


    def stitched_setup(self,scope):
        positions = self.positions
        unique_groups = positions['autofocus_group'].unique()
        i = 0
        self.reference_points = pd.DataFrame(index=unique_groups,columns=['autofocus_group','X','Y','Z','X_shift','Y_shift','Z_shift'])
        wells = positions['well'].unique()
        for well in wells:
            well_positions = positions[positions['well'] == well]
            if len(well_positions) == 0:
                continue
            # Load preview and stitch it for entire well
            acquisition_dir = self.file_handler.find_latest_acquisition('preview',well)
            if acquisition_dir is None:
                self.log(f"No acquisition found for {well}",level='error')
                continue
            channel = self.file_handler.get_state('Experiment')['preview_channels'][0]
            if channel is None:
                self.log(f"No channel found for {well}",level='error')
                continue
            # Stitch acquisition
            stitched, pixel2stage, idx_canvas, posname_idx_mapper = stitch_acquisition(
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
                
            groups = well_positions['autofocus_group'].unique()
            for autofocus_group in groups:
                group_positions = well_positions[well_positions['autofocus_group'] == autofocus_group]
                group_idxes = [posname_idx_mapper[pos] for pos in group_positions['position_name']]
                group_mask = np.zeros_like(idx_canvas)
                for idx in group_idxes:
                    group_mask[idx_canvas==idx] = 1
                group_mask = group_mask.astype(bool)
                stitched_rgb = np.ones([stitched.shape[0],stitched.shape[1],3])
                stitched_rgb[group_mask,1:2] = 0 # MAKE RED

                points = []
                message = ""
                while len(points) != 1:
                    points = interactive_coordinate_selection(stitched, message = f"Select a single point for the {autofocus_group} \n {i+1} of {len(unique_groups)} \n {message}")
                    if len(points) == 0:
                        message = f"No points selected for {autofocus_group} Try again"
                    if len(points) > 1:
                        message = f"Multiple points selected for {autofocus_group} Please select only one point"
                point = points[0]
                i+=1
                stage_coordinates = pixel2stage(point[0], point[1])
                if not scope.is_valid('X',stage_coordinates[0]):
                    self.log(f"{autofocus_group} Invalid X: {stage_coordinates[0]}",level='error')
                if not scope.is_valid('Y',stage_coordinates[1]):
                    self.log(f"{autofocus_group} Invalid Y: {stage_coordinates[1]}",level='error')
                if not scope.is_valid('Z',group_positions['Z'].median()):
                    self.log(f"{autofocus_group} Invalid Z: {group_positions['Z'].median()}",level='error')
                self.reference_points.loc[autofocus_group,'X'] = stage_coordinates[0]
                self.reference_points.loc[autofocus_group,'Y'] = stage_coordinates[1]
                self.reference_points.loc[autofocus_group,'Z'] = group_positions['Z'].median()
                self.reference_points.loc[autofocus_group,'X_shift'] = 0.0
                self.reference_points.loc[autofocus_group,'Y_shift'] = 0.0
                self.reference_points.loc[autofocus_group,'Z_shift'] = 0.0
                self.reference_points.loc[autofocus_group,'autofocus_group'] = autofocus_group


    def update_focus(self,scope,autofocus_group):
        self.positions = self.file_handler.Positions
        # reference_points = self.file_handler.reference_points
        self.reference_points = pd.read_csv(self.reference_points_filename,index_col='autofocus_group')
        self.reference_points['autofocus_group'] = self.reference_points.index
        reference_points = self.reference_points
        scope.XYZ = (reference_points.loc[autofocus_group,'X'],reference_points.loc[autofocus_group,'Y'],reference_points.loc[autofocus_group,'Z'])
        self.log(f"Moving to {autofocus_group} reference point (X,Y,Z): {scope.XYZ}",level='info')
        self.log(f"Finding focus for {autofocus_group}",level='info')
        starting_focus = scope.Z
        new_focus = self.scan_find_focus(scope)
        translation = new_focus - starting_focus
        reference_points.loc[autofocus_group,'Z_shift'] = translation
        self.log(f"Updating reference points for {autofocus_group} (X,Y,Z): {scope.XYZ} (shift: {translation})",level='info')
        self.reference_points = reference_points
        self.reference_points.to_csv(self.reference_points_filename,index=False)
        # self.file_handler.save_reference_points(reference_points)

    def focus(self,scope,X=None,Y=None,position_name=None,goto=True):
        if X is None:
            X = scope.X
        if Y is None:
            Y = scope.Y
        Z = scope.Z
        if not str(position_name) in self.positions['position_name'].unique():
            self.log(f"Position name {position_name} not found in positions",level='warning')
            position_name = None
        if position_name is None:
            positions_xy = np.array([self.positions['X'],self.positions['Y']])
            closest_index = np.argmin(np.linalg.norm(positions_xy - np.array([X,Y]),axis=1))
            closest_position = self.positions.iloc[closest_index]
        else:
            closest_position = self.positions[self.positions['position_name'] == position_name].iloc[0]
        autofocus_group = closest_position['autofocus_group']
        translation = float(self.reference_points.loc[autofocus_group,'Z_shift'])
        new_z = float(Z + translation)
        if not scope.is_valid('Z',new_z):
            self.log(f"Invalid Z: X={X},Y={Y} (Z): {new_z} (shift: {translation})",level='error')
        if goto:
            scope.Z = new_z
        self.log(f"Focusing on X={X},Y={Y} (Z): {new_z} (shift: {translation})",level='debug')
        return new_z

if __name__ == "__main__":
    # Test the user_input_gui
    print("Testing ImageScanAutofocus user_input_gui...")
    
    # Create scope instance using PC name to determine system type
    pc_name = socket.gethostname()
    system = pc_name.split('Scope')[0].capitalize()
    module_name = f"Scope.{system.lower()}scope"
    module = importlib.import_module(module_name)
    class_name = f"{system}Scope"
    scope_class = getattr(module, class_name)
    scope = scope_class(enable_core=True)
    print(f"Using {system}Scope instance with channels: {scope.available_channels}")
    
    # # Create ImageScanAutofocus instance
    # autofocus = ImageScanAutofocus(
    #     channel='FarRed',
    #     exposure=5,
    #     coarse_window=(200, 20),
    #     medium_window=(20, 2),
    #     fine_window=(5, 0.5)
    # )\
    
    autofocus = RelativeAutofocus(level='well',setup_method='stitched')
    
    print(f"Initial configuration:")
    print(f"  Channel: {autofocus.channel}")
    print(f"  Exposure: {autofocus.exposure}")
    print(f"  Coarse Window: {autofocus.coarse_window}")
    print(f"  Medium Window: {autofocus.medium_window}")
    print(f"  Fine Window: {autofocus.fine_window}")
    print("\nOpening GUI...")
    
    # Show the GUI
    result = autofocus.user_input_gui(scope)
    
    if result:
        print("\nConfiguration updated:")
        print(f"  Channel: {autofocus.channel}")
        print(f"  Exposure: {autofocus.exposure}")
        print(f"  Coarse Window: {autofocus.coarse_window}")
        print(f"  Medium Window: {autofocus.medium_window}")
        print(f"  Fine Window: {autofocus.fine_window}")
    else:
        print("\nConfiguration cancelled or failed.")