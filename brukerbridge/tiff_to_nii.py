import numpy as np
import nibabel as nib
import os
from matplotlib.pyplot import imread
from xml.etree import ElementTree as ET
import sys
from tqdm import tqdm
import psutil
from PIL import Image
import time

def tiff_to_nii(xml_file):
    aborted = False
    data_dir, _ = os.path.split(xml_file)
    print('Converting tiffs to nii in directory: \n{}'.format(data_dir))

    tree = ET.parse(xml_file)
    root = tree.getroot()
    # Get all volumes
    sequences = root.findall('Sequence')

     # Check if bidirectional - will affect loading order
    isBidirectionalZ = sequences[0].get('bidirectionalZ')
    if isBidirectionalZ == 'True':
        isBidirectionalZ = True
    else:
        isBidirectionalZ = False
    print('BidirectionalZ is {}'.format(isBidirectionalZ))

    # Get axis dims
    if root.find('Sequence').get('type') == 'TSeries Timed Element': # Plane time series
        num_timepoints = len(sequences[0].findall('Frame'))
        num_z = 1
        isVolumeSeries = False
    elif root.find('Sequence').get('type') == 'TSeries ZSeries Element': # Volume time series
        num_timepoints = len(sequences)
        num_z = len(sequences[0].findall('Frame'))
        isVolumeSeries = True
    else: # Default to: Volume time series
        num_timepoints = len(sequences)
        num_z = len(sequences[0].findall('Frame'))
        isVolumeSeries = True

    print('isVolumeSeries is {}'.format(isVolumeSeries))
    print('num_timepoints {}'.format(num_timepoints))
    print('num_z {}'.format(num_z))

    num_channels = get_num_channels(sequences[0])
    test_file = sequences[0].findall('Frame')[0].findall('File')[0].get('filename')
    fullfile = os.path.join(data_dir, test_file)
    img = imread(fullfile)
    num_y = np.shape(img)[0]
    num_x = np.shape(img)[1]
    print('num_channels: {}'.format(num_channels))
    print('num_timepoints: {}'.format(num_timepoints))
    print('num_z: {}'.format(num_z))
    print('num_y: {}'.format(num_y))
    print('num_x: {}'.format(num_x))

    # loop over channels
    for channel in range(num_channels):
        last_num_z = None
        image_array = np.zeros((num_timepoints, num_z, num_y, num_x), dtype=np.uint16)
        print('Created empty array of shape {}'.format(image_array.shape))
        # loop over time
        for i in range(num_timepoints):
            if i%10 == 0:
                print('{}/{}'.format(i+1, num_timepoints))

            if isVolumeSeries: # For a given volume, get all frames
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
                if isBidirectionalZ and (i%2 != 0):
                    frames = frames[::-1]

            else: # Plane series: Get frame
                frames = [sequences[0].findall('Frame')[i]]

            # loop over depth (z-dim)
            for j, frame in enumerate(frames):
                # For a given frame, get filename
                files = frame.findall('File')
                filename = files[channel].get('filename')
                fullfile = os.path.join(data_dir, filename)

                # Read in file
                img = imread(fullfile)
                image_array[i,j,:,:] = img

            # print memory info periodically
            if i%10 == 0:
                memory_usage = psutil.Process(os.getpid()).memory_info().rss*10**-9
                print('Current memory usage: {:.2f}GB'.format(memory_usage))
                sys.stdout.flush()

        if isVolumeSeries:
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

        memory_usage = psutil.Process(os.getpid()).memory_info().rss*10**-9
        print('Current memory usage: {:.2f}GB'.format(memory_usage))
        sys.stdout.flush()

        aff = np.eye(4)
        save_name = xml_file[:-4] + '_channel_{}'.format(channel+1) + '.nii'
        if isVolumeSeries:
            img = nib.Nifti1Image(image_array, aff) # 32 bit: maxes out at 32767 in any one dimension
        else:
            img = nib.Nifti2Image(image_array, aff) # 64 bit
        image_array = None # for memory
        print('Saving nii as {}'.format(save_name))
        img.to_filename(save_name)
        img = None # for memory
        print('Saved! sleeping for 10 sec to help memory reconfigure...')
        time.sleep(10)
        print('Sleep over')

def get_num_channels(sequence):
    frame = sequence.findall('Frame')[0]
    files = frame.findall('File')
    return len(files)

def convert_tiff_collections_to_nii(directory):
    for item in os.listdir(directory):
        new_path = directory + '/' + item

        # Check if item is a directory
        if os.path.isdir(new_path):
            convert_tiff_collections_to_nii(new_path)

        # If the item is a file
        else:
            # If the item is an xml file
            if '.xml' in item:
                tree = ET.parse(new_path)
                root = tree.getroot()
                # If the item is an xml file with scan info
                if root.tag == 'PVScan':

                    # Also, verify that this folder doesn't already contain any .niis
                    # This is useful if rebooting the pipeline due to some error, and
                    # not wanting to take the time to re-create the already made niis
                    for item in os.listdir(directory):
                        if item.endswith('.nii'):
                            print('skipping nii containing folder: {}'.format(directory))
                            break
                    else:
                        tiff_to_nii(new_path)
