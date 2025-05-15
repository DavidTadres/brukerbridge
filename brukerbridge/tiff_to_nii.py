import numpy as np
import nibabel as nib
import os
from xml.etree import ElementTree as ET
import sys
#from tqdm import tqdm
import psutil
from skimage import io
import time
import pathlib
import json
import imageio
import h5py
import datetime
parent_path = str(pathlib.Path(pathlib.Path(__file__).parent.absolute()).parent.absolute())
sys.path.insert(0, parent_path)

from brukerbridge import utils

def get_channel_ids(sequence):
    """
    The original code just assigned 'channel 1' to the first
    channel, even if only channel 2 was recorded from.
    To stay faithful to the original channel designation (made
    by the microscope), use this function to define the existing
    channels for a given experiment
    :param sequence:
    :return:
    """
    channels = []
    
    if isinstance(sequence, list):
        sequence = sequence[0]
    first_frame = sequence.findall('Frame')[0]
    first_frame_file_list = first_frame.findall('File')
    for current_file in first_frame_file_list:
        channels.append(current_file.attrib['channel'])

    return(channels)

def tiff_to_nii(xml_file, brukerbridge_version_info):
    
    """
    Notes on extracting data from the xml files:
    
    For volume data
        For singlepage tiffs
            there is a sequence for each volume (ie timepoint)
            each sequence has a frame for each z-slice
            each frame has a file for each channel
        For multipage tiffs
            there is a sequence for each volume (ie timepoint)
            each sequence has a frame for each z-slice
            each sequence has a file for each channel (all frames in one file per channel)

    For single plane data
        For singlepage tiffs
            there is only one sequence
            each timepoint is one frame
            each frame has a file for each channel
        For multipage tiffs
            there is only one sequence
            each timepoint is one frame
            each file contains many (but not all) timepoints for each channel
    """

    aborted = False
    data_dir = xml_file.parent
    print("\n\n")
    print('Converting tiffs to nii in directory: {}'.format(data_dir))

    ### Get general info from xml file about scan (voxel size, multi or singlepage tiff, volume or single plane, )

    # Check if multipage tiff
    companion_filepath = pathlib.Path(str(xml_file).split('.')[0] + '.companion.ome')
    if companion_filepath.exists():
        is_multi_page_tiff = True
    else:
        is_multi_page_tiff = False

    tree = ET.parse(xml_file)
    root = tree.getroot()
    sequences = root.findall('Sequence')
    # get x/y dimensions and x/y/z voxel size
    statevalues = root.findall("PVStateShard")[0].findall("PVStateValue")
    for statevalue in statevalues:
        key = statevalue.get("key")
        if key == "micronsPerPixel":
            indices = statevalue.findall("IndexedValue")
            for index in indices:
                axis = index.get("index")
                if axis == "XAxis":
                    x_voxel_size = float(index.get("value"))
                elif axis == "YAxis":
                    y_voxel_size = float(index.get("value"))
                elif axis == "ZAxis":
                    z_voxel_size = float(index.get("value"))
        # Get y pixel count
        if key == "linesPerFrame":
            num_y = int(statevalue.get("value"))
        # Get x pixel count
        if key == "pixelsPerLine":
            num_x = int(statevalue.get("value"))

    # Identify scan type, get t/z axis dims
    if root.find('Sequence').get('type') == 'TSeries Timed Element': # Plane time series
        num_timepoints = len(sequences[0].findall('Frame'))
        num_z = 1
        is_volume_series = False

    elif root.find('Sequence').get('type') == 'TSeries ZSeries Element': # Volume time series
        num_timepoints = len(sequences)
        num_z = len(sequences[0].findall('Frame'))
        is_volume_series = True
    else:
         TypeError('Could not determine type of sequence, not recognized as "TSeries Timed Element" or a "TSeries ZSeries Element".')

    # Check if bidirectional - will affect loading order
    is_bidirectional_z = sequences[0].get('bidirectionalZ')
    if is_bidirectional_z == 'True':
        is_bidirectional_z = True
    else:
        is_bidirectional_z = False

    #print('BidirectionalZ is {}'.format(is_bidirectional_z))
    if is_bidirectional_z:
        # comment below stolen from brukerbridge:
        # NOTE: berger 2024/08/06
        # Although support for this could be easily cheesed, I have declined to
        # do so for the moment due to some mysteries in the acquisition xml
        # that I am not confident enough to guess at right now. Specifically, the
        # subtrees for the last frame of the downstroke and the first frame of
        # the upstroke do not record the depth at which those frames were
        # acquired. All other frames do.
        #
        # In the example acquisition I was using to develop this, the user set
        # the bottom plane as 100.5um, the top as 340.5 and set the volume to
        # contain 49 planes with 5um increments. Each Sequence subtree indeed
        # contains 49 frames, but (for the downstroke) the 49th does not record
        # z pos. The 48th records a z pos of 335.5. It would not be
        # unreasonable to infer that the 49th plane was at z=340.5um, but that
        # is, ultimately, cowboy shit.
        #
        # In the past, Bella supported bidirectional z scans by simply flipping
        # the order of the frames every other volume. Definitely cowboy shit,
        # but this is what you would want to do to naively support
        # bidirectional scans: take the *sorted* frames and reverse the order
        # the list is traversed by the generator for Sequences with an even
        # cycle attribute
        raise NotImplementedError(
            (
                "Support for bidirectional scans not supported due to Bruker sketchiness. "
                "See the source where this error was thrown for an explanation."
            )
        )

    # Get existing channels as strings
    channels = get_channel_ids(sequences)

    # print scan info
    print('is_multi_page_tiff is {}'.format(is_multi_page_tiff))
    print('is_volume_series is {}'.format(is_volume_series))
    print('channels: {}'.format(channels))
    print('num_timepoints: {}'.format(num_timepoints))
    print('num_z: {}'.format(num_z))
    print('num_y: {}'.format(num_y))
    print('num_x: {}'.format(num_x))
    

    # Note: There's inconsistency in how the ripper provides the data with axes sometimes being swapped...
    # read the first frame to see where each axis is
    first_tiff_filename = sequences[0].findall('Frame')[0].findall('File')[0].get('filename')
    first_tiff_path = pathlib.Path(data_dir, first_tiff_filename)

    ### Luke added try except 20221024 because sometimes but rarely a file doesn't exist
    # somthing to do with bruker xml file
    if first_tiff_path.is_file():
        try:
            img = io.imread(first_tiff_path, plugin='pil')
        except TypeError:
            img = imageio.imread(first_tiff_path)
            '''
            Got this error when I think the ripper messed up:
            img = io.imread(first_tiff_path, plugin='pil')
            ...
            TypeError: int() argument must be a string, a bytes-like object or a number, not 'NoneType'
            '''
    else:
        print("!!! FileNotFoundError, passing !!!")

    if (num_x == num_y) or (num_x == num_z) or (num_y == num_z):
        raise NotImplementedError(
            (
                "Cannot handle identical axis size at the moment because we "
                "don't know what order axes are saved into tiffs by the ripper."
            )
        )

    # Note: this will fail if we have two axis with the identical
    x_axis = np.where(np.array(img.shape) == num_x)[0][0]
    y_axis = np.where(np.array(img.shape) == num_y)[0][0]
    if is_multi_page_tiff:
        if is_volume_series:
            z_axis = np.where(np.array(img.shape) == num_z)[0][0] # only needed for multipage tiff volumetric data where multiple z-planes are in one file
        else:
            t_axis = np.where(np.array(img.shape) != num_x and np.array(img.shape) != num_y) # only needed for multipage tiff single plane data where multiple timepoints are in one file
    ### loop over channels
    for channel_counter, current_channel in enumerate(channels):
        last_num_z = None
        image_array = np.zeros((num_timepoints, num_z, num_y, num_x), dtype=np.uint16)
        print('Created empty array of shape {} for channel {}'.format(image_array.shape, current_channel))
        
        start_time = time.time()

        ### Case1: multipage tiff, single plane ###
        if is_multi_page_tiff and not is_volume_series:

            print('Reading data as multipage tiff, single plane')

            # In this case there is not one file per timepoint
            # First extract all tiff filenames from xml file
            tiff_filenames = []
            temp_tiff_filenames = []

            # loop over all frames in the first sequence and collect filenames
            for current_frame in sequences[0].findall('Frame'):
                if len(temp_tiff_filenames) > 1000:
                    tiff_filenames.append(temp_tiff_filenames)
                    temp_tiff_filenames = []
                current_filename = current_frame.findall('File')[channel_counter].get('filename') # this is where the correct channel is selected based on channel_counter
                if current_filename in tiff_filenames or current_filename in temp_tiff_filenames:
                    continue
                else:
                    temp_tiff_filenames.append(current_filename)
            # After loop, add list bit of temp to tiff_filenames
            tiff_filenames.append(temp_tiff_filenames)
            tiff_filenames = utils.flatten_nested_list(tiff_filenames)

            print(tiff_filenames)

            # We still have to loop if the single plane recording is long enough!
            # loop over time steps to load one tif at a time
            current_start_index = 0
            for current_iteration, current_tiff_filename in enumerate(tiff_filenames):
                current_path_to_tiff = pathlib.Path(data_dir, current_tiff_filename)
                try:
                    img = io.imread(current_path_to_tiff, plugin='pil')
                except TypeError:
                    """
                    Got this error when I think the ripper messed up:
                     img = io.imread(first_tiff_path, plugin='pil')
                     ...
                     xsize = int(self.tag_v2.get(IMAGEWIDTH))
                    TypeError: int() argument must be a string, a bytes-like object or a number, not 'NoneType'
                    """
                    try:
                        img = imageio.imread(current_path_to_tiff)
                    except FileNotFoundError as e:
                        print(e)
                        continue

                image_array[current_start_index:current_start_index+img.shape[0], 0, :, :] = img.transpose(t_axis, y_axis, x_axis)
                #print(time.time() - start_time)
                current_start_index+=img.shape[0]

                ######################
                ### Print Progress ###
                ######################
                memory_usage = int(psutil.Process(os.getpid()).memory_info().rss*10**-9)
                utils.print_progress_table(start_time=start_time,
                                            current_iteration=current_iteration,
                                            total_iterations=len(tiff_filenames),
                                            current_mem=memory_usage,
                                            total_mem=32,
                                            mode='tiff_convert')
           
        ### Case2: singlepage tiff, single plane ###
        elif not is_multi_page_tiff and not is_volume_series:

            print('Reading data as singlepage tiff, single plane')

            # get frames for all timepoints
            frames = sequences[0].findall('Frame')

            # loop over time steps to load one tif at a time
            for current_timepoint in range(num_timepoints):
                #get files for current timepoint
                files = frames[current_timepoint].findall('File')
                current_tiff_filename = files[channel_counter].get('filename') # this is where the correct channel is selected based on channel_counter
                current_path_to_tiff = pathlib.Path(data_dir, current_tiff_filename)

                try:
                    img = io.imread(current_path_to_tiff, plugin='pil')
                except TypeError:
                    """
                    Got this error when I think the ripper messed up:
                     img = io.imread(first_tiff_path, plugin='pil')
                     ...
                     xsize = int(self.tag_v2.get(IMAGEWIDTH))
                    TypeError: int() argument must be a string, a bytes-like object or a number, not 'NoneType'
                    """
                    try:
                        img = imageio.imread(current_path_to_tiff)
                    except FileNotFoundError as e:
                        print(e)
                        continue

                image_array[current_timepoint,0,:,:] = img.transpose(y_axis, x_axis)

                ######################
                ### Print Progress ###
                ######################
                memory_usage = int(psutil.Process(os.getpid()).memory_info().rss*10**-9)
                utils.print_progress_table(start_time=start_time,
                                            current_iteration=current_timepoint,
                                            total_iterations=num_timepoints,
                                            current_mem=memory_usage,
                                            total_mem=32,
                                            mode='tiff_convert')

        ### Case3: multipage tiff, volumetric ###
        elif is_volume_series and is_multi_page_tiff:

            print('Reading data as multipage tiff, volumetric')

            # loop over time steps
            for current_timepoint in range(num_timepoints):
                
                #get frames for current timepoints
                frames = sequences[current_timepoint].findall('Frame')
                #get all channel files for current frames
                files = frames[0].findall('File') #arbitrarily using frame 0 to get filenames because all frames have the same filenames

                #  Handle aborted scans for volumes
                current_num_z = len(frames)
                if last_num_z is not None:
                    if current_num_z != last_num_z:
                        print('Inconsistent number of z-slices (scan aborted).')
                        print('Tossing last volume.')
                        aborted = True
                        break
                last_num_z = current_num_z
                
                current_tiff_filename = files[channel_counter].get('filename') # this is where the correct channel is selected based on channel_counter
                current_tiff_path = pathlib.Path(data_dir, current_tiff_filename)
                try:
                    img = io.imread(current_tiff_path, plugin='pil')  # shape = z, y, x
                except TypeError:
                    """
                    Got this error when I think the ripper messed up:
                     img = io.imread(first_tiff_path, plugin='pil')
                     ...
                     xsize = int(self.tag_v2.get(IMAGEWIDTH))
                    TypeError: int() argument must be a string, a bytes-like object or a number, not 'NoneType'
                    """
                    try:
                        img = imageio.imread(current_tiff_path)

                    except FileNotFoundError as e:
                        print(e)
                        continue

                try:
                    image_array[current_timepoint,:,:,:] = img.transpose(z_axis, y_axis, x_axis)
                except ValueError as e:
                    print(e)
                
                ######################
                ### Print Progress ###
                ######################
                memory_usage = int(psutil.Process(os.getpid()).memory_info().rss*10**-9)
                utils.print_progress_table(start_time=start_time,
                                            current_iteration=current_timepoint,
                                            total_iterations=num_timepoints,
                                            current_mem=memory_usage,
                                            total_mem=32,
                                            mode='tiff_convert')
                
        ### Case4: singlepage tiff, volumetric ###
        elif is_volume_series and not is_multi_page_tiff:
            
            print('Reading data as singlepage tiff, volumetric')

            # loop over time steps
            for current_timepoint in range(num_timepoints):

                #get frames for current timepoint
                frames = sequences[current_timepoint].findall('Frame')

                #  Handle aborted scans for volumes
                current_num_z = len(frames)
                if last_num_z is not None:
                    if current_num_z != last_num_z:
                        print('Inconsistent number of z-slices (scan aborted).')
                        print('Tossing last volume.')
                        aborted = True
                        break
                last_num_z = current_num_z
                
                # loop over depth (z-dim)
                for j, frame in enumerate(frames):
                    # For a given frame, get files
                    files = frame.findall('File')
                    filename = files[channel_counter].get('filename') # this is where the correct channel is selected based on channel_counter
                    current_tiff_path = pathlib.Path(data_dir, filename)

                    # Read in file
                    try:
                        img = io.imread(current_tiff_path, plugin='pil')  # shape = z, y, x
                    except TypeError:
                        """
                        Got this error when I think the ripper messed up:
                        img = io.imread(first_tiff_path, plugin='pil')
                        ...
                        xsize = int(self.tag_v2.get(IMAGEWIDTH))
                        TypeError: int() argument must be a string, a bytes-like object or a number, not 'NoneType'
                        """
                        try:
                            img = imageio.imread(current_tiff_path)

                        except FileNotFoundError as e:
                            print(e)
                            continue
                    
                    image_array[current_timepoint,j,:,:] = img.transpose(y_axis, x_axis)
                                
                ######################
                ### Print Progress ###
                ######################
                memory_usage = int(psutil.Process(os.getpid()).memory_info().rss*10**-9)
                utils.print_progress_table(start_time=start_time,
                                            current_iteration=current_timepoint,
                                            total_iterations=num_timepoints,
                                            current_mem=memory_usage,
                                            total_mem=32,
                                            mode='tiff_convert')

        # restructure data for saving
        if is_volume_series:
            # starts as tzyx, ends as xyzt
            image_array = np.moveaxis(image_array,1,-1) #tyxz
            image_array = np.moveaxis(image_array,0,-1) #yxzt
            image_array = np.swapaxes(image_array,0,1) #xyzt

            aff = np.eye(4)

            # Toss last volume if aborted
            if aborted:
                image_array = image_array[:,:,:,:-1]
        else:
            # starts as tzyx, ends as xyt
            image_array = np.squeeze(image_array) #tyx
            image_array = np.moveaxis(image_array, 0, -1) #yxt
            image_array = np.swapaxes(image_array, 0, 1) #xyt

            aff = np.eye(3)

        print('Final array shape = {}'.format(image_array.shape))

        save_name = pathlib.Path(xml_file.parent, xml_file.name[:-4] + '_channel_{}'.format(current_channel) + '.nii')

        try:
            img = nib.Nifti1Image(image_array, aff) # 32 bit: maxes out at 32767 in any one dimension

        except nib.spatialimages.HeaderDataError:
            img = nib.Nifti2Image(image_array, aff) # 64 bit

        header_info = img.header # pointer to new header

        if is_volume_series:
            header_info['pixdim'][1:4] = [x_voxel_size, y_voxel_size, z_voxel_size]  # x,y,z
        else:
            header_info['pixdim'][1:3] = [x_voxel_size, y_voxel_size] # x,y

        image_array = None # for memory
        print('Saving nii as {}'.format(save_name))
        img.to_filename(save_name)
        img = None # for memory
        print('Saved! sleeping for 2 sec to help memory reconfigure...',end='')
        time.sleep(2)
        print('Sleep over')
        print('\n\n')

    # Save version info after writing the channel info to understand how exactly
    # data was analyzed
    brukerbridge_json = {'brukerbridge version used': brukerbridge_version_info
                         }
    with open(pathlib.Path(xml_file.parent, 'brukerbridge_version.json'), 'w') as file:
        json.dump(brukerbridge_json, file, sort_keys=True, indent=4)


def convert_tiff_collections_to_nii(directory,
                                    brukerbridge_version_info,
                                    fly_json_from_h5,
                                    fly_json_already_created,
                                    autotransfer_stimpack,
                                    autotransfer_jackfish,
                                    max_diff_imaging_and_stimpack_start_time_second):
    #for item in os.listdir(directory):
    # Here we are in the parent directory. By definition (to be documented) this
    # must be a folder like 20240613 which contains subfolders such as 'fly_001'
    # and, optionally, a stimpack produced h5 file!
    #print('called convert_tiff_collections_to_nii with directory ' + repr(directory))

    if fly_json_from_h5 and not fly_json_already_created:
        print('Attempting to create fly.json from stimpack h5 file')
        # First, create fly.json file for each folder based on the h5 file
        # created by stimpack
        single_h5 = 'None'
        try:
            print('first trying to look for one hdf5 in: ' + str(directory))
            utils.get_fly_json_data_from_h5(directory)
            # If able to create all fly.json, set this to True
            fly_json_already_created = True
            single_h5 = True
            print('Successfully created fly.json files from from stimpack h5 file')
        except Exception as e:
            print('******* WARNING ******')
            print('unable to create fly.json files from h5 because:')
            print(e)

        if not fly_json_already_created:
            try:
                print('instead trying to look for one hdf5 in each fly folder in : ' + str(directory))
                utils.get_fly_json_data_from_h5_one_fly_per_h5(directory)
                # If able to create all fly.json, set this to True
                fly_json_already_created = True
                single_h5 = False
                print('Successfully created fly.json files from from stimpack h5 file')
            except Exception as e:
                print('******* WARNING ******')
                print('unable to create fly.json files from h5 because:')
                print(e)
                print('\n')

        # Still set this to True as it'll else try to run this many times while the error could be
        # just a manually create fly.json file!
        fly_json_already_created = True

        # option to autotransfer stimpack data (such as fictrac)
        # Note - even though this function is called several times, it should only copy
        # The data once because the variable 'fly_json_already_created' makes sure that
        # we can only be here the first time the function is called!
        if autotransfer_stimpack:
            try:
                print('Attempting to automatically assign stimpack/fictrac data to imaging folder')

                # Write flyID.json based on h5 metadata into stimpack data folders!
                # This json file is used below to check whether a given stimpack session can be assumed to
                # belong to a given imaging session

                    
                if single_h5 == 'None':
                    print('error, no h5 files found')
                elif single_h5:
                    utils.write_h5_metadata_in_stimpack_folder(directory)
                    print('Wrote h5 metadata in stimpack folder')
                    # Then copy stimpack data from bespoke folder into corresponding imaging folder
                    stimpack_errors = utils.add_stimpack_data_to_imaging_folder(
                       directory, max_diff_imaging_and_stimpack_start_time_second)
                    if bool(stimpack_errors):
                        print('***** ERROR ENCOUNTERD DURING STIMPACK FOLDER ASSIGNMENT *****')
                        for current_error in stimpack_errors:
                            print(current_error)
                            print(':\n')
                            print(stimpack_errors[current_error])
                            print('\n\n')
                    else:
                        print('Successfully copied all stimpack/fictrac data into corresponding imaging folder!')

                elif not single_h5: 
                    utils.write_h5_metadata_in_stimpack_folder_one_fly_per_h5(directory)
                    print('Wrote h5 metadata in stimpack folder')
                
                    # Then copy stimpack data from bespoke folder into corresponding imaging folder
                    #stimpack_errors = utils.add_stimpack_data_to_imaging_folder(
                    #   directory, max_diff_imaging_and_stimpack_start_time_second)
                    # if bool(stimpack_errors):
                    #     print('***** ERROR ENCOUNTERD DURING STIMPACK FOLDER ASSIGNMENT *****')
                    #     for current_error in stimpack_errors:
                    #         print(current_error)
                    #         print(':\n')
                    #         print(stimpack_errors[current_error])
                    #         print('\n\n')
                    # else:
                    #     print('Successfully copied all stimpack/fictrac data into corresponding imaging folder!')
            except UnboundLocalError as e:
                print('********** WARNING **********')
                print('Unable to autotransfer stimpack because:')
                print(e)
                print('\n')

        if autotransfer_jackfish:
            #try:
            print('Attempting to automatically assign jackfish data to imaging folder')
            success_writing_flyID_json_in_jackfish_folder = (
                utils.write_h5_metadata_in_jackfish_folder(directory))
            if success_writing_flyID_json_in_jackfish_folder:
                print('Wrote h5 metadata in jackfish folder'
                      )
                jackfish_erros = utils.add_jackfish_data_to_imaging_folder(
                    directory, max_diff_imaging_and_stimpack_start_time_second
                )
                if bool(jackfish_erros):
                    print('***** ERROR ENCOUNTERED DURING JACKFISH FOLDER ASSIGNMENT *****')
                    for current_error in stimpack_errors:
                        print(current_error)
                        print(':\n')
                        print(jackfish_erros[current_error])
                        print('\n\n')
                else:
                    print('Successfully copied all jackfish data into corresponding imaging folder!')

            else:
                print('>>>>>>>>INFORMATION<<<<<<<<<<')
                print('Unable to transfer any stimpack/jackfish files (post-hoc fictrac recordings).')
                print('This is normal behavior if you have done real-time fictrac recordings instead.')

    for current_path in directory.iterdir():
        #new_path = directory + '/' + item

        # Check if item is a directory
        #if os.path.isdir(new_path):
        #    print(1) #debug
        #    convert_tiff_collections_to_nii(new_path)
        if current_path.is_dir():
            #print(1) # debug
            convert_tiff_collections_to_nii(directory=current_path,
                                            brukerbridge_version_info=brukerbridge_version_info,
                                            fly_json_from_h5=fly_json_from_h5,
                                            fly_json_already_created=fly_json_already_created,
                                            autotransfer_stimpack=autotransfer_stimpack,
                                            autotransfer_jackfish=autotransfer_jackfish,
                                            max_diff_imaging_and_stimpack_start_time_second=max_diff_imaging_and_stimpack_start_time_second)

        # If the item is a file
        else:
            # If the item is a xml file
            if '.xml' in current_path.name:
                create_nii = True
                #print(3) #debug
                #tree = ET.parse(new_path)
                tree = ET.parse(current_path)
                root = tree.getroot()
                # If the item is an xml file with scan info
                if root.tag == 'PVScan':

                    # Also, verify that this folder doesn't already contain any .niis
                    # This is useful if rebooting the pipeline due to some error, and
                    # not wanting to take the time to re-create the already made niis
                    #for item in os.listdir(directory):
                    #    if item.endswith('.nii'):
                    #        print('skipping nii containing folder: {}'.format(directory))
                    #        break
                    for item in directory.iterdir():
                        if '.nii' in item.name:
                            print('skipping nii containing folder: {}'.format(directory))
                            create_nii = False
                            break # breaks the for loop as we have 100s of thousands of items..

                    # Finally, check if it's a singleImage folder
                    if 'SingleImage' in directory.name:
                        print('Single Image folder. Skipping nii creation')
                        create_nii =False
                    # This breaks everything somehow?

                    if create_nii:
                        #tiff_to_nii(new_path)
                        tiff_to_nii(current_path, brukerbridge_version_info)


