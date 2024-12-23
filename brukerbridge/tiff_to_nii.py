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

    first_frame = sequence.findall('Frame')[0]
    first_frame_file_list = first_frame.findall('File')
    for current_file in first_frame_file_list:
        channels.append(current_file.attrib['channel'])

    return(channels)

def tiff_to_nii(xml_file, brukerbridge_version_info):
    aborted = False
    #data_dir, _ = os.path.split(xml_file)
    data_dir = xml_file.parent
    print("\n\n")
    print('Converting tiffs to nii in directory: {}'.format(data_dir))

    # Check if multipage tiff files
    companion_filepath = pathlib.Path(str(xml_file).split('.')[0] + '.companion.ome')
    if companion_filepath.exists():
        is_multi_page_tiff = True
    else:
        is_multi_page_tiff = False

    print('is_multi_page_tiff is {}'.format(is_multi_page_tiff))

    tree = ET.parse(xml_file)
    root = tree.getroot()

    ##########
    # NEW - get x/y/z size to correctly save nii file #
    # Get rest of data
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
    ###########

    # Get all volumes
    sequences = root.findall('Sequence')
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

    # Get axis dims
    if root.find('Sequence').get('type') == 'TSeries Timed Element': # Plane time series
        num_timepoints = len(sequences[0].findall('Frame'))
        num_z = 1
        is_volume_series = False
    elif root.find('Sequence').get('type') == 'TSeries ZSeries Element': # Volume time series
        num_timepoints = len(sequences)
        num_z = len(sequences[0].findall('Frame'))
        is_volume_series = True
    else: # Default to: Volume time series
        num_timepoints = len(sequences)
        num_z = len(sequences[0].findall('Frame'))
        is_volume_series = True

    print('is_volume_series is {}'.format(is_volume_series))

    #num_channels = get_num_channels(sequences[0])
    # Get existing channels as strings
    channels = get_channel_ids(sequences[0])
    first_tiff = sequences[0].findall('Frame')[0].findall('File')[0].get('filename')
    #first_tiff_path = os.path.join(data_dir, first_tiff)
    first_tiff_path = pathlib.Path(xml_file.parent, first_tiff)

    ### Luke added try except 20221024 because sometimes but rarely a file doesn't exist
    # somthing to do with bruker xml file
    try:
        img = io.imread(first_tiff_path, plugin='pil')
    except FileNotFoundError as e:
        print("!!! FileNotFoundError, passing !!!")

    num_y = np.shape(img)[-2]
    num_x = np.shape(img)[-1]
    print('channels: {}'.format(channels))
    print('num_timepoints: {}'.format(num_timepoints))
    print('num_z: {}'.format(num_z))
    print('num_y: {}'.format(num_y))
    print('num_x: {}'.format(num_x))

    # loop over channels
    for channel_counter, current_channel in enumerate(channels):
        last_num_z = None
        image_array = np.zeros((num_timepoints, num_z, num_y, num_x), dtype=np.uint16)
        print('Created empty array of shape {}'.format(image_array.shape))

        # This might fail as I couldn't test it:
        # originally 'current_channel' was just 0, 1, 2 (int) now it's i.e. only '2' (str)
        if is_multi_page_tiff and (is_volume_series is False):
             # saved as a single big tif for all time steps
            print('is_multi_page_tiff is {} / is_volume_series is {}'.format(is_multi_page_tiff, is_volume_series))
            frames = [sequences[0].findall('Frame')[0]]
            files = frames[0].findall('File')
            filename = files[channel_counter].get('filename')
            first_tiff_path = os.path.join(data_dir, filename)
            img = io.imread(first_tiff_path, plugin='pil')  # shape = t, y, x
            image_array[:,0,:,:] = img
           
        else:
            # loop over time steps to load one tif at a time
            start_time = time.time()
            for i in range(num_timepoints):

                #if i%10 == 0:
                #    print('{}/{}'.format(i+1, num_timepoints))

                if is_volume_series: # For a given volume, get all frames
                    frames = sequences[i].findall('Frame')
                    current_num_z = len(frames)
                    # Handle aborted scans for volumes
                    if last_num_z is not None:
                        if current_num_z != last_num_z:
                            print('Inconsistent number of z-slices (scan aborted).')
                            print('Tossing last volume.')
                            aborted = True
                            break
                    last_num_z = current_num_z

                    # Flip frame order if a bidirectionalZ upstroke (odd i)
                    #if is_bidirectional_z and (i%2 != 0):
                    #    frames = frames[::-1]

                else: # Plane series: Get frame
                    frames = [sequences[0].findall('Frame')[i]]

                if is_multi_page_tiff:
                    files = frames[0].findall('File')
                    filename = files[current_channel].get('filename')
                    first_tiff_path = os.path.join(data_dir, filename)
                    page = int(files[channel_counter].get('page')) - 1  # page number -> array index
                    img = io.imread(first_tiff_path, plugin='pil')  # shape = z, y, x
                    image_array[i,:,:,:] = img
                else:
                    # loop over depth (z-dim)
                    for j, frame in enumerate(frames):
                        # For a given frame, get filename
                        files = frame.findall('File')
                        filename = files[channel_counter].get('filename')
                        #first_tiff_path = os.path.join(data_dir, filename)
                        first_tiff_path = pathlib.Path(data_dir, filename)
                       
                        # Read in file
                        img = io.imread(first_tiff_path, plugin='pil')
                        image_array[i,j,:,:] = img
                                
                ######################
                ### Print Progress ###
                ######################
                memory_usage = int(psutil.Process(os.getpid()).memory_info().rss*10**-9)
                utils.print_progress_table(start_time=start_time,
                                            current_iteration=i,
                                            total_iterations=num_timepoints,
                                            current_mem=memory_usage,
                                            total_mem=32,
                                            mode='tiff_convert')

        if is_volume_series:
            # Will start as t,z,x,y. Want y,x,z,t
            image_array = np.moveaxis(image_array,1,-1) # Now t,x,y,z
            image_array = np.moveaxis(image_array,0,-1) # Now x,y,z,t
            image_array = np.swapaxes(image_array,0,1) # Now y,x,z,t

            # Toss last volume if aborted
            if aborted:
                image_array = image_array[:,:,:,:-1]
        else:
            image_array = np.squeeze(image_array) # t, x, y
            image_array = np.moveaxis(image_array, 0, -1) # x, y, t
            image_array = np.swapaxes(image_array, 0, 1) # y, x, t

        print('Final array shape = {}'.format(image_array.shape))

        aff = np.eye(4)
        #save_name = xml_file[:-4] + '_channel_{}'.format(current_channel+1) + '.nii'
        save_name = pathlib.Path(xml_file.parent, xml_file.name[:-4] + '_channel_{}'.format(current_channel) + '.nii')
        if is_volume_series:
            img = nib.Nifti1Image(image_array, aff) # 32 bit: maxes out at 32767 in any one dimension
        else:
            img = nib.Nifti2Image(image_array, aff) # 64 bit

        ##### NEW
        header_info = img.header # pointer to new header
        # change the voxel dimensions to [2,2,2]
        header_info['pixdim'][1:4] = [x_voxel_size, y_voxel_size, z_voxel_size]  # x,y,z
        ##### NEW END

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
"""
def get_num_channels(sequence):
    frame = sequence.findall('Frame')[0]
    files = frame.findall('File')
    return len(files)
"""


def convert_tiff_collections_to_nii(directory,
                                    brukerbridge_version_info,
                                    fly_json_from_h5,
                                    fly_json_already_created,
                                    autotransfer_stimpack,
                                    max_diff_imaging_and_stimpack_start_time_second):
    #for item in os.listdir(directory):
    # Here we are in the parent directory. By definition (to be documented) this
    # must be a folder like 20240613 which contains subfolders such as 'fly_001'
    # and, optionally, a stimpack produced h5 file!

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

        # Still set this to True as it'll else try to run this many times while the error could be
        # just a manually create fly.json file!
        fly_json_already_created = True


        # option to autotransfer stimpack data (such as fictrac)
        # Note - even though this function is called several times, it should only copy
        # The data once because the variable 'fly_json_already_created' makes sure that
        # we can only be here the first time the function is called!
        if autotransfer_stimpack:
            print('Attempting to automatically assign stimpack/fictrac data to imaging folder')

            # Write flyID.json based on h5 metadata into stimpack data folders!
            # This json file is used below to check whether a given stimpack session can be assumed to
            # belong to a given imaging session

            
            if single_h5 == 'None':
                print('error, no h5 files found')
            elif single_h5:
                utils.write_h5_metadata_in_stimpack_folder(directory)
                print('Wrote h5 metadata in stimpack folder')
            elif not single_h5: 
                utils.write_h5_metadata_in_stimpack_folder_one_fly_per_h5(directory)
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
                                            max_diff_imaging_and_stimpack_start_time_second=max_diff_imaging_and_stimpack_start_time_second)

        # If the item is a file
        else:
            # If the item is an xml file
            if '.xml' in current_path.name:
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
                            break
                    else:
                        #tiff_to_nii(new_path)
                        tiff_to_nii(current_path, brukerbridge_version_info)


