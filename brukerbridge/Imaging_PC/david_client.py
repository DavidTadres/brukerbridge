### Brukerbridge computer ###
#host = "171.65.17.84"
# David PC
#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
host = "171.65.16.149" # < change this to point to your own computer
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
source_directory = pathlib.Path(askdirectory(initialdir = "F:/")) # show an "Open" dialog box and return the path to the selected file
#source_directory = str(os.sep).join(source_directory.split('/')) # replace slashes with backslashes for windows
print(source_directory)

#################################
### LOOK FOR STIMPACK h5 FILE ###
#################################

# Load fictrac_data_path defined in user settings.
# Todo: either make user setting file dynamic
json_path = pathlib.Path(parent_path, 'users\\David.json')
user_settings = utils.get_json_data(json_path)
fictrac_data_path = pathlib.Path(user_settings['fictrac_h5_path'])
# The standard way of fictrac to create files is 2024-05-11.
date_folder_to_transfer = source_directory.name
year = date_folder_to_transfer[0:4]
month = date_folder_to_transfer[4:6]
day = date_folder_to_transfer[6:8]
string_to_find = year + '-' + month + '-' + day

fictrac_h5_path = None

if pathlib.Path(fictrac_data_path, string_to_find).is_dir():
    fictrac_h5_path = pathlib.Path(fictrac_data_path, string_to_find)

#########################
### CONNECT TO SERVER ###
#########################

sock = socket.socket()
sock.connect((host,port))

############################
### SEND FICTRAC H5 DATA ###
############################

if fictrac_data_path is not None:
    print('Sending fictrac data folder ' + str(fictrac_h5_path))

    h5_directory_size = utils.get_dir_size(fictrac_h5_path)
    h5_num_files = utils.get_num_files(fictrac_h5_path)

    sock.sendall(str(h5_directory_size).encode() + b'\n')
    sock.sendall(str(h5_num_files).encode() + b'\n')

    num_files_sent = 0
    for path, dirs, files in os.walk(fictrac_h5_path):
        for file in files:

            filename = os.path.join(path, file)
            relpath = str(os.sep).join(filename.split(os.sep)[1:])
            filesize = os.path.getsize(filename)
            print(f'Sending {relpath}')

            checksum = utils.get_checksum(filename)

            with open(filename, 'rb') as f:
                sock.sendall(relpath.encode() + b'\n')
                sock.sendall(str(filesize).encode() + b'\n')
                sock.sendall(str(checksum).encode() + b'\n')

                # Send the file in chunks so large files can be handled.
                while True:
                    data = f.read(CHUNKSIZE)
                    if not data: break
                    sock.sendall(data)

            num_files_sent += 1

    # Don't delete source data, for now at least - these files are not large anyway!

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
### BEGIN TRASNFER ###
######################

num_files_sent = 0
for path,dirs,files in os.walk(source_directory):
    for file in files:

        filename = os.path.join(path,file)
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