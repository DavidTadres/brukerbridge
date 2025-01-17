### Brukerbridge computer ###
#host = "171.65.17.84"
# David PC
#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
host_IP = '171.65.16.67'
user_json = 'Jacob'
#<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<

import os
import sys
import shutil
import socket
from tkinter import Tk     # from tkinter import Tk for Python 3.x
from tkinter.filedialog import askdirectory
import pathlib
import json
import pathlib
import ftputil

parent_path = str(pathlib.Path(pathlib.Path(__file__).parent.absolute()).parent.absolute().parent.absolute())
print(parent_path)
sys.path.insert(0, parent_path)
from brukerbridge import utils

CHUNKSIZE = 1_000_000

### Luke testing ###
# host = 'localhost'
# port = 5000
# source_directory = "/Users/luke/Desktop/test_send"

port = 5005

##################################
### WHAT DIRECTORY TO PROCESS? ###
##################################

Tk().withdraw() # we don't want a full GUI, so keep the root window from appearing
source_directory = pathlib.Path(askdirectory(initialdir = "G:/Jacob/")) # show an "Open" dialog box and return the path to the selected file
#source_directory = str(os.sep).join(source_directory.split('/')) # replace slashes with backslashes for windows
print(source_directory)

#calculate # of flies
num_fly = len(os.listdir(source_directory)) # return number of folders in source_directory (ie fly1, fly2...)
print('number of flies: ' + repr(num_fly))
#################################
### LOOK FOR STIMPACK h5 FILE ###
#################################

# Load fictrac_data_path defined in user settings.
# Todo: either make user setting file dynamic
json_path = pathlib.Path(parent_path, 'users\\' + user_json + '.json')
user_settings = utils.get_json_data(json_path)
# The standard way of fictrac to create files is 2024-05-11.
date_folder_to_transfer = source_directory.name
year = date_folder_to_transfer[0:4]
month = date_folder_to_transfer[4:6]
day = date_folder_to_transfer[6:8]
string_to_find_date = year + '-' + month + '-' + day

# Check if stimpack data folder is defined - it's an optional field!
stimpack_h5_path = str(user_settings.get('stimpack_h5_path', "None"))
if stimpack_h5_path != "None":
    stimpack_h5_path = pathlib.Path(stimpack_h5_path)
    # loop through h5 files in stimpack_h5_path
    for fly in range(1,num_fly+1):
        string_to_find = string_to_find_date + '_' + repr(fly) + '.hdf5'
        for folder in stimpack_h5_path.iterdir(): #file is a file/folder name
            if string_to_find in folder.name:
                stimpack_h5_path_fly = folder
                h5_dst_imaging_pc = pathlib.Path(source_directory, 'fly'+repr(fly), stimpack_h5_path_fly.name)
                print('transferring hdf5 file {} to directory {}'.format(stimpack_h5_path_fly, h5_dst_imaging_pc))
                shutil.copyfile(src=stimpack_h5_path_fly, dst=h5_dst_imaging_pc)
    # The easiest way to get this to work is to just copy the h5 file into the imaging folder on the imaging computer!
    # Then I don't have to deal at all with the actual transfer code!

    # currently the autotransfer of fictrac data only works if the h5 file is used!
    if user_settings['autotransfer_stimpack']:
        print('Will attempt to automatically transfer stimpack data')
        stimpack_data_path = user_settings["stimpack_data_path"]

        # If the stimpack file is i.e. 2024-06-13.hdf5 the folder
        # we are looking for is 2024-06-13
        current_stimpack_folder_name = string_to_find_date
        print("current_stimpack_folder_name: " + repr(current_stimpack_folder_name))

        ###################################
        ### Bruker Sr. fictrac computer ###
        ###################################
        ip = '171.65.17.246'
        username = 'clandinin'
        passwd = input('Please enter password for ' + ip + ' for username ' + username + ': ')
        # Please do not hardcode the password here as it'll be publicly available.

        local_target_path = pathlib.Path(source_directory,string_to_find_date)
        utils.DownloadFolderFTP(ip, username, passwd,
                                remote_root_path=stimpack_data_path,
                                folder_to_copy=current_stimpack_folder_name,
                                local_target_path=local_target_path
                                )


#########################
### CONNECT TO SERVER ###
#########################

sock = socket.socket()
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
        #print('CURRENTLY TESTING SO >>>NOT<<< DELETING DATA')
        print('DELETING BRUKER DATA...')
        shutil.rmtree(source_directory)
    else:
        print('!!! Correct number of files but at least one checksum does not match !!!')
else:
    print('!!! Number of files sent and recieve do not match !!!')
    print(F"Sent: {num_files_sent}; Recieved: {num_of_files_recieved}")

print('Done.')