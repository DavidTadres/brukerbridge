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
from anatomical_orientation import make_direction_for_nifty
from bruker_ultima_utils import parse_xml
import datetime
parent_path = str(pathlib.Path(pathlib.Path(__file__).parent.absolute()).parent.absolute())
sys.path.insert(0, parent_path)

from brukerbridge import utils


def tiff_to_nii(xml_file,
                brukerbridge_version_info,
                imaging_orientation,
                save_suffix = 'nii'):

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

    ##########################################################################################################
    #### Get info from xml file about scan (voxel size, multi or singlepage tiff, volume or single plane) ####
    ##########################################################################################################


    # Parse xml file using bruker_ultima_utils (single source of truth for
    # Bruker metadata extraction, including the Sequence-level ZAxis fix)
    md = parse_xml(xml_file)

    # We still need raw XML elements for iterating frames/files downstream
    tree = ET.parse(xml_file)
    root = tree.getroot()
    sequences = root.findall('Sequence')

    # Unpack metadata into local variables used by the rest of this function
    is_multi_page_tiff = md.is_multi_page_tiff
    num_x = md.x_dim
    num_y = md.y_dim
    num_z = md.z_dim
    num_timepoints = md.num_timepoints
    x_voxel_size = md.x_voxel_size
    y_voxel_size = md.y_voxel_size
    z_voxel_size = md.z_voxel_size
    is_volume_series = md.is_volume_series
    is_bidirectional_z = md.is_bidirectional_z
    channels = md.channel_ids

    # print scan info
    print('is_multi_page_tiff is {}'.format(is_multi_page_tiff))
    print('is_volume_series is {}'.format(is_volume_series))
    print('channels: {}'.format(channels))
    print('num_timepoints: {}'.format(num_timepoints))
    print('num_z: {}'.format(num_z))
    print('num_y: {}'.format(num_y))
    print('num_x: {}'.format(num_x))

    ###############################################################
    #### load first tiff and double check axes order/dimension ####
    ###############################################################

    # Note: We should define all axis through the xml file, not by reading the image file!
    # HOWEVER: There's inconsistency in how the ripper provides the data with axes sometimes being swapped...
    # Hence, read the first frame to see where each axis is
    first_tiff_filename = sequences[0].findall('Frame')[0].findall('File')[0].get('filename')
    first_tiff_path = pathlib.Path(data_dir, first_tiff_filename)

    if first_tiff_path.is_file():
        try:
            img = io.imread(first_tiff_path)
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

    print('first tiff shape = {}'.format(img.shape))

    ### check axes order/dimension ###
    # based on previous testing (JCS, 5/16/2025) we expect the tiff to be in the order of:
        #multipage tiff, single plane: t, y, x
        #multipage tiff, volumetric: z, y, x
        #singlepage tiff, single plane: y, x
        #singlepage tiff, volumetric: y, x

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
            for dim in range(len(img.shape)):
                if dim not in [x_axis, y_axis]:
                    t_axis = dim # only needed for multipage tiff single plane data where multiple timepoints are in one file
                    break

    #################################################
    #### extract data from tiffs and save to nii ####
    #################################################

    # loop over channels
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
                    img = io.imread(current_path_to_tiff)
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

                if is_bidirectional_z:
                    raise NotImplementedError('This needs to be carefully tested, no idea what happens in this situation')
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
                    img = io.imread(current_path_to_tiff)
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
                if is_bidirectional_z:
                    raise NotImplementedError('This needs to be carefully tested, no idea what happens in this situation')
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
                    img = io.imread(current_tiff_path)  # shape = z, y, x
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
                    if is_bidirectional_z:
                        # Invert every second volum z-order!
                        if current_timepoint%2 != 0:
                            image_array[current_timepoint, :, :, :] = img.transpose(z_axis, y_axis, x_axis)[::-1]
                        else:
                            image_array[current_timepoint, :, :, :] = img.transpose(z_axis, y_axis, x_axis)
                    else:
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
                        img = io.imread(current_tiff_path)  # shape = z, y, x
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
        ##########################
        #### Save nii to file ####
        ##########################

        # restructure data for saving
        if is_volume_series:
            # starts as tzyx, ends as xyzt
            image_array = np.moveaxis(image_array,1,-1) #tyxz
            image_array = np.moveaxis(image_array,0,-1) #yxzt
            image_array = np.swapaxes(image_array,0,1) #xyzt

            # Toss last volume if aborted
            if aborted:
                image_array = image_array[:,:,:,:-1]
        else:
            # starts as tzyx, ends as xyt
            image_array = np.squeeze(image_array) #tyx
            image_array = np.moveaxis(image_array, 0, -1) #yxt
            image_array = np.swapaxes(image_array, 0, 1) #xyt

        print('Final array shape = {}'.format(image_array.shape))

        # This is mostly a copy of snakebrainsss/workflow/modules_io_utils.save_nifty!
        # Keep track of how this is done to make sure the logic stays the same
        if is_volume_series:
            # 3D volume
            affine = make_direction_for_nifty(orientation=imaging_orientation,
                                               spacing=(x_voxel_size, y_voxel_size, z_voxel_size),
                                               origin=None)
            # dir_3x3 = make_direction_3d_f(imaging_orientation)
            # affine = np.eye(4)
            # affine[:3, :3] = dir_3x3.T @ np.diag((x_voxel_size, y_voxel_size, z_voxel_size))
        else:
            affine = make_direction_for_nifty(orientation=imaging_orientation,
                                               spacing=(x_voxel_size, y_voxel_size, 1),
                                               origin=None)
            # # 2D image: derive out-of-plane axis automatically from cross product
            # dir_3x3 = make_direction_2d(imaging_orientation)
            # affine = np.eye(4)
            # affine[:3, :3] = dir_3x3.T @ np.diag((x_voxel_size, y_voxel_size, 1))

        # aff = np.eye(4)
        #save_name = xml_file[:-4] + '_channel_{}'.format(current_channel+1) + '.nii'
        save_name = pathlib.Path(xml_file.parent, xml_file.name[:-4] + '_channel_{}'.format(current_channel) + save_suffix)
        try:
            img = nib.Nifti1Image(image_array, affine) #aff) # 32 bit: maxes out at 32767 in any one dimension
        except nib.spatialimages.HeaderDataError:
            img = nib.Nifti2Image(image_array, affine) #aff) # 64 bit

        # header_info = img.header # pointer to new header

        # if is_volume_series:
        #     header_info['pixdim'][1:4] = [x_voxel_size, y_voxel_size, z_voxel_size]  # x,y,z
        # else:
        #     header_info['pixdim'][1:3] = [x_voxel_size, y_voxel_size] # x,y

        image_array = None # for memory
        print('Saving nii as {}'.format(save_name))
        img.to_filename(save_name)
        img = None # for memory
        print('Saved! sleeping for 2 sec to help memory reconfigure...',end='')
        time.sleep(2)
        print('Sleep over')
        print('\n\n')

    #####################################################
    #### save brukerbridge version info to json file ####
    #####################################################

    brukerbridge_json = {'brukerbridge version used': brukerbridge_version_info
                         }
    with open(pathlib.Path(xml_file.parent, 'brukerbridge_version.json'), 'w') as file:
        json.dump(brukerbridge_json, file, sort_keys=True, indent=4)


def convert_tiff_collections_to_nii(directory,
                                    brukerbridge_version_info,
                                    fly_json_from_h5,
                                    fly_json_already_created,
                                    autotransfer_stimpack,
                                    max_diff_imaging_and_stimpack_start_time_second,
                                    imaging_orientation,
                                    save_suffix):
    """Recursively find PVScan XML files and convert their TIFF data to NIfTI.

    Also handles fly.json creation from stimpack h5 and stimpack/loco data
    assignment to imaging folders (when autotransfer_stimpack is True).

    Note: jackfish/fictrac assignment was moved to main.py (runs after
    wait_for_fictrac to avoid race conditions with WSL FicTrac processes).

    TODO: move autotransfer_stimpack, fly_json_from_h5, and related logic
    out of this function into main.py to make tiff-to-nii purely about
    file conversion.

    :param directory: root directory containing fly folders and optionally h5
    :param brukerbridge_version_info: version string saved alongside NIfTIs
    :param fly_json_from_h5: bool, create fly.json from stimpack h5
    :param fly_json_already_created: bool, skip fly.json if already done
    :param autotransfer_stimpack: bool, assign stimpack/loco data to imaging dirs
    :param max_diff_imaging_and_stimpack_start_time_second: float or None
    :param imaging_orientation: str, anatomical orientation code (e.g. 'LSP')
    :param save_suffix: str, '.nii' or '.nii.gz'
    """

    if fly_json_from_h5 and not fly_json_already_created:
        print('Attempting to create fly.json from stimpack h5 file')
        # First, create fly.json file for each folder based on the h5 file
        # created by stimpack

        # This bool keeps track of the two ways h5 files can be used:
        # 1) David has one h5 per day. It contains all
        #    all metadata for a given fly. This file is located
        #    in the root folder (directory).
        # 2) Jacob has one h5 per experiment. These files are located
        #    in the experimental folder
        # Start by setting the bool to None
        single_h5 = None
        try:
            print('first trying to look for one hdf5 in: ' + str(directory))
            utils.get_fly_json_data_from_h5(directory)
            # If able to create all fly.json, set this to True
            fly_json_already_created = True
            # Found h5 file, hence we have a single h5 file for this directory
            single_h5 = True
            print('Successfully created fly.json files from from stimpack h5 file')
        except Exception as e:
            print('******* WARNING ******')
            print('unable to create fly.json files from h5 because:')
            print(e)

        # This catches Jacob's case: If fly json couldn't be created it
        # then looks for h5 files in each experimental folder.
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

                # No h5 file written
                if single_h5 is None:
                    print('error, no h5 files found')
                # This is David's case, single h5 file
                elif single_h5:
                    # Try writing h5 metadate in stimpack folder
                    success_writing_flyID_json_in_stimpack_loco_folder = (
                        utils.write_h5_metadata_in_stimpack_folder(directory))
                    # Report success
                    if success_writing_flyID_json_in_stimpack_loco_folder:
                        print('Wrote h5 metadata in stimpack folder')
                        # Then copy stimpack data from bespoke folder into corresponding imaging folder
                        stimpack_errors = utils.add_stimpack_data_to_imaging_folder(
                            directory, max_diff_imaging_and_stimpack_start_time_second)
                        if bool(stimpack_errors):
                            print('***** ERROR ENCOUNTERED DURING STIMPACK FOLDER ASSIGNMENT *****')
                            for current_error in stimpack_errors:
                                print(current_error)
                                print(':\n')
                                print(stimpack_errors[current_error])
                                print('\n\n')
                        else:
                            print('Successfully copied all stimpack/fictrac data into corresponding imaging folder!')
                    # Or failure
                    else:
                        print('>>>>>>>>INFORMATION<<<<<<<<<<')
                        print('Unable to transfer any stimpack/loco files (real-time fictrac recordings).')
                        print('This is normal behavior if you have recorded videos with jackfish instead.')
                elif not single_h5:
                    #utils.write_h5_metadata_in_stimpack_folder_one_fly_per_h5(directory)
                    print('skipped writing h5 metadata in stimpack folder, not yet implemented for one h5 per fly')

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

    for current_path in directory.iterdir():
        #new_path = directory + '/' + item

        # Check if item is a directory
        #if os.path.isdir(new_path):
        #    print(1) #debug
        #    convert_tiff_collections_to_nii(new_path)
        if current_path.is_dir():
            # Skip MarkPoints (photostimulation) folders — their XML has root tag
            # 'PVScan' but no PVStateShard, which breaks parse_xml.
            if current_path.name.startswith('MarkPoints'):
                print('Skipping MarkPoints folder: {}'.format(current_path.name))
                continue
            #print(1) # debug
            convert_tiff_collections_to_nii(directory=current_path,
                                            brukerbridge_version_info=brukerbridge_version_info,
                                            fly_json_from_h5=fly_json_from_h5,
                                            fly_json_already_created=fly_json_already_created,
                                            autotransfer_stimpack=autotransfer_stimpack,
                                            max_diff_imaging_and_stimpack_start_time_second=max_diff_imaging_and_stimpack_start_time_second,
                                            imaging_orientation=imaging_orientation,
                                            save_suffix=save_suffix)

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

                    # Guard: some PVScan-rooted XMLs (e.g., MarkPoints) have no
                    # PVStateShard, which would crash parse_xml. Skip those.
                    if not root.findall("PVStateShard"):
                        print('Skipping PVScan XML without PVStateShard: {}'.format(current_path))
                        continue

                    # Guard: aborted/empty scans have Sequences but no Frame
                    # elements, which crashes parse_xml's get_channel_ids.
                    first_seq = root.find("Sequence")
                    if first_seq is not None and not first_seq.findall("Frame"):
                        print('Skipping {} because its Sequence contains no Frame elements (empty/aborted scan)'.format(current_path))
                        continue

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
                        tiff_to_nii(current_path,
                                    brukerbridge_version_info,
                                    imaging_orientation,
                                    save_suffix)


