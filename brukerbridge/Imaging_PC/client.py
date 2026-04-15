"""
Unified Bruker imaging PC client.

Usage:
    python client.py <username>

Where <username> matches a JSON file in the users/ directory (e.g. "David" -> users/David.json).
The user's JSON must contain at minimum:
    - host_IP: IP address of the ripping PC
    - initial_browse_dir: starting directory for the file browser dialog
"""

import os
import sys
import shutil
import socket
from tkinter import Tk
from tkinter.filedialog import askdirectory
import pathlib
import json

parent_path = str(pathlib.Path(pathlib.Path(__file__).parent.absolute()).parent.absolute().parent.absolute())
sys.path.insert(0, parent_path)
from brukerbridge import utils

CHUNKSIZE = 1_000_000
port = 5005

##########################
### Parse user argument ###
##########################

if len(sys.argv) < 2:
    print("Usage: python client.py <username>")
    print("Example: python client.py David")
    sys.exit(1)

user_name = sys.argv[1]
json_path = pathlib.Path(parent_path, 'users', user_name + '.json')
if not json_path.exists():
    print(f"User config not found: {json_path}")
    sys.exit(1)

user_settings = utils.get_json_data(json_path)
host_IP = user_settings['host_IP']
initial_browse_dir = user_settings.get('initial_browse_dir', 'F:/')

##################################
### WHAT DIRECTORY TO PROCESS? ###
##################################

Tk().withdraw()
source_directory = pathlib.Path(askdirectory(initialdir=initial_browse_dir))
print(source_directory)

# Safety check: don't accidentally select a folder inside this repository
if source_directory.name in pathlib.Path(__file__).as_posix():
    print('You seem to have selected a folder inside this repository instead of an experimental folder.')
    print('Please try again.')
    sys.exit(1)

#################################
### LOOK FOR STIMPACK h5 FILE ###
#################################

# The standard way of fictrac to create files is 2024-05-11.
date_folder_to_transfer = source_directory.name
year = date_folder_to_transfer[0:4]
month = date_folder_to_transfer[4:6]
day = date_folder_to_transfer[6:8]
string_to_find = year + '-' + month + '-' + day

stimpack_h5_path = None

# Check if stimpack data folder is defined - it's an optional field!
stimpack_data_path = str(user_settings.get('stimpack_h5_path', "None"))
if stimpack_data_path != "None":
    stimpack_data_path = pathlib.Path(stimpack_data_path)
else:
    stimpack_data_path = None
if stimpack_data_path is not None:
    for folder in stimpack_data_path.iterdir():
        if string_to_find in folder.name:
            stimpack_h5_path = folder
            break

# The easiest way to get this to work is to just copy the h5 file into the imaging folder on the imaging computer!
# Then I don't have to deal at all with the actual transfer code!

if stimpack_h5_path is not None:
    h5_dst_imaging_pc = pathlib.Path(source_directory, stimpack_h5_path.name)
    shutil.copyfile(src=stimpack_h5_path, dst=h5_dst_imaging_pc)

    # currently the autotransfer of fictrac data only works if the h5 file is used!
    if user_settings['autotransfer_stimpack']:
        print('Will attempt to automatically transfer stimpack data')
        stimpack_data_path = user_settings["stimpack_data_path"]

        # If the stimpack file is i.e. 2024-06-13.hdf5 the folder
        # we are looking for is 2024-06-13
        current_stimpack_folder_name = stimpack_h5_path.name.split('.hdf5')[0]
        print("current_stimpack_folder_name: " + repr(current_stimpack_folder_name))

        ###################################
        ### Bruker Sr. fictrac computer ###
        ###################################
        ip = '171.65.17.246'
        username = 'clandinin'
        passwd = input('Please enter password for ' + ip + ' for username ' + username + ': ')
        # Please do not hardcode the password here as it'll be publicly available.

        local_target_path = pathlib.Path(str(h5_dst_imaging_pc).split('.hdf5')[0])
        utils.DownloadFolderFTP(ip, username, passwd,
                                remote_root_path=stimpack_data_path,
                                folder_to_copy=current_stimpack_folder_name,
                                local_target_path=local_target_path
                                )

        # Jackfish video transfer (gated by user setting)
        if utils.get_bool_from_json(settings_json=user_settings, input_string='autotransfer_jackfish'):
            print('Will attempt to automatically transfer videos created by Jackfish')
            jackfish_data_path = user_settings["jackfish_data_path"]

            current_jackfish_folder_name = stimpack_h5_path.name.split('.hdf5')[0]
            current_jackfish_folder_name = current_jackfish_folder_name.replace('-', '')

            local_target_path_jackfish_data = pathlib.Path(source_directory, current_jackfish_folder_name + '_jackfish')
            local_target_path_jackfish_data.mkdir(exist_ok=True, parents=True)

            utils.DownloadFolderFTP(ip, username, passwd,
                                    remote_root_path=jackfish_data_path,
                                    folder_to_copy=current_jackfish_folder_name,
                                    local_target_path=local_target_path_jackfish_data
                                    )


#########################
### CONNECT TO SERVER ###
#########################

sock = socket.socket()
print(f"Connecting to host_IP={host_IP!r} on port={port}")
sock.connect((host_IP, port))

##########################
### GET DIRECTORY SIZE ###
##########################

print('Calculating directory size... ', end='')
source_directory_size = utils.get_dir_size(source_directory)
num_files = utils.get_num_files(source_directory)
print('Done   |  {} GB   |   {} Files'.format(source_directory_size, num_files))

sock.sendall(str(source_directory_size).encode() + b'\n')
sock.sendall(str(num_files).encode() + b'\n')

######################
### BEGIN TRANSFER ###
######################

num_files_sent = 0
for path,dirs,files in os.walk(source_directory):
    for file in files:

        # for example ''C:\\Users\\David\\brukerbridge\\launch_server.bat'
        filename = os.path.join(path,file)
        # Becomes 'Users\\David\\brukerbridge\\launch_server.bat'
        relpath = str(os.sep).join(filename.split(os.sep)[1:])
        filesize = os.path.getsize(filename)
        print(f'Sending {relpath}')

        checksum = utils.get_checksum(filename)

        with open(filename,'rb') as f:
            sock.sendall(relpath.encode() + b'\n')
            sock.sendall(str(filesize).encode() + b'\n')
            sock.sendall(str(checksum).encode() + b'\n')

            # Send the file in chunks so large files can be handled.
            while True:
                data = f.read(CHUNKSIZE)
                if not data: break
                sock.sendall(data)

        num_files_sent += 1

#########################
### TRANSFER COMPLETE ###
#########################

sock.sendall("ALL_FILES_TRANSFERED".encode() + b'\n')
message = sock.recv(1024).decode()
num_of_files_recieved = int(message.split('.')[0])
all_checksums_true = bool(message.split('.')[1])

#############################
### FINAL CLIENT PRINTING ###
#############################

if num_files_sent == num_of_files_recieved:
    if all_checksums_true:
        print('Confirmed correct number of files recieved and all checksums match.')
        print('DELETING BRUKER DATA...')
        shutil.rmtree(source_directory)
    else:
        print('!!! Correct number of files but at least one checksum does not match !!!')
else:
    print('!!! Number of files sent and recieve do not match !!!')
    print(F"Sent: {num_files_sent}; Recieved: {num_of_files_recieved}")

print('Done.')
