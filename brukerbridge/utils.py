import sys
import smtplib
#import re
import os
#import math
import json
from email.mime.text import MIMEText
from time import time
from time import strftime
from time import sleep
from functools import wraps
import numpy as np
#import nibabel as nib
#from xml.etree import ElementTree as ET
#import subprocess
import h5py
import pathlib
import hashlib
from datetime import datetime
import ftputil

# only imports on linux, which is fine since only needed for sherlock
try:
    import fcntl
except ImportError:
    pass

def sec_to_hms(t):
    secs=F"{np.floor(t%60):02.0f}"
    mins=F"{np.floor((t/60)%60):02.0f}"
    hrs=F"{np.floor((t/3600)%60):02.0f}"
    return ':'.join([hrs, mins, secs])

def print_progress_table(start_time, current_iteration, total_iterations, current_mem, total_mem, mode):
    if mode == 'server':
        print_iters = [1,2,4,8,16,32,50,75,100,125,150,175,200,225,250,275,300,325,350,375,400,500,600,700,800,900,1000,5000,10000,10000]
    if mode == 'tiff_convert':
        print_iters = [1,2,4,8,16,32,64,128,256,512,1064,2128,4256,8512,17024,34048,68096]
    

    fraction_complete = current_iteration/total_iterations
    elapsed = time()-start_time
    elapsed_hms = sec_to_hms(elapsed)
    try:
        remaining = elapsed/fraction_complete - elapsed
    except ZeroDivisionError:
        remaining = 0
    remaining_hms = sec_to_hms(remaining)
    
    ### PRINT TABLE TITLE ###
    if current_iteration == 1:
        title_string = "| Current Time |  Print Frequency  |     Num / Total   |         GB / Total      | Elapsed Time / Remaining   |"
        # if mode == 'server':
        #     title_string += "  MB / SEC  |"
        print(title_string, flush=True)
    
    now = datetime.now()
    current_time_string = "   {}   ".format(now.strftime("%H:%M:%S"))
    print_freq_string = "       {:05d}       ".format(current_iteration)
    iteration_string = "   {:05d} / {:05d}   ".format(current_iteration, total_iterations)
    memory_string = "        {:03d} / {:03d}        ".format(current_mem, total_mem)
    time_string = F"     {elapsed_hms} / {remaining_hms}    "
    full_string = '|'.join(['', current_time_string, print_freq_string, iteration_string, memory_string, time_string, ''])
    # if mode == 'server':
    #     speed = 
    #     full_string =+ '{}'.format()
    
    if current_iteration in print_iters:
        print(full_string, flush=True)
        
    if current_iteration == total_iterations:
        print(full_string, flush=True)

def progress_bar(iteration, total, length, fill = '#'):
    if total == 0:
        total = 1        
    filledLength = int(length * iteration // total)
    bar = fill * filledLength + '-' * (length - filledLength)
    fraction = F"{str(iteration):^4}" + '/' + F"{str(total):^4}"
    bar_string = f"{bar}"
    return bar_string

def get_num_files(directory):
    num_files = 0
    for path, dirs,files in os.walk(directory):
        num_files += len(files)
    return num_files

def get_dir_size(directory):
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(directory):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            # skip if it is symbolic link
            if not os.path.islink(fp):
                total_size += os.path.getsize(fp)
    return total_size*10**-9 #report in GB

def get_checksum(filename):
    with open(filename, "rb") as f:
        bytes = f.read()  # read file as bytes
        readable_hash = hashlib.md5(bytes).hexdigest()
    return readable_hash

def get_json_data(file_path):
    with open(file_path) as f:  
        data = json.load(f)
    return data

def send_email(subject='', message='', recipient="brezovec@stanford.edu"):
    """ Sends emails!

    Parameters
    ----------
    subject: email subject heading (str)
    message: body of text (str)

    Returns
    -------
    Nothing. """
    print('Sending email to {} ({})'.format(recipient, subject))
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login("python.notific@gmail.com", "uxnglqrswphwtdsf")

    msg = MIMEText(message)
    msg['Subject'] = subject

    server.sendmail(recipient, recipient, msg.as_string())
    server.quit()

def timing(f):
    """ Wrapper function to time how long functions take (and print function name). """

    @wraps(f)
    def wrapper(*args, **kwargs):
        start = time()
        print('\nFUNCTION CALL: {}'.format(f.__name__))
        sys.stdout.flush()
        result = f(*args, **kwargs)
        end = time()
        duration = end-start

        # Make units nice (originally in seconds)
        if duration < 1:
            duration = duration * 1000
            suffix = 'ms'
        elif duration < 60:
            duration = duration
            suffix = 'sec'
        elif duration < 3600:
            duration = duration / 60
            suffix = 'min'
        else:
            duration = duration / 3600
            suffix = 'hr'

        print('FUNCTION {} done. DURATION: {:.2f} {}'.format(f.__name__,duration,suffix))
        sys.stdout.flush()
        return result
    return wrapper

class Logger_stdout(object):
    def __init__(self, full_log_file):
        # self.terminal = sys.stdout
        # log_folder = 'C:/Users/User/Desktop/dataflow_logs'
        # log_file = 'dataflow_log_' + strftime("%Y%m%d-%H%M%S") + '.txt'
        # self.full_log_file = os.path.join(log_folder, log_file)
        self.log = open(full_log_file, "a")
        self.log = sys.stdout

    def write(self, message):
        #  self.terminal.write(message)
        #self.terminal.write('boo')
        #self.log.write('boo2')
        self.log.write(message)  

    def flush(self):
        #this flush method is needed for python 3 compatibility.
        #this handles the flush command by doing nothing.
        #you might want to specify some extra behavior here.
        pass 

# class Logger_stdout(object):
#     def __init__(self, full_log_file):
#         self.terminal = sys.stdout
#         # log_folder = 'C:/Users/User/Desktop/dataflow_logs'
#         # log_file = 'dataflow_log_' + strftime("%Y%m%d-%H%M%S") + '.txt'
#         # self.full_log_file = os.path.join(log_folder, log_file)
#         self.log = open(full_log_file, "a")

#     def write(self, message):
#         self.terminal.write(message)
#         #self.terminal.write('boo')
#         #self.log.write('boo2')
#         self.log.write(message)  

#     def flush(self):
#         #this flush method is needed for python 3 compatibility.
#         #this handles the flush command by doing nothing.
#         #you might want to specify some extra behavior here.
#         pass 

class Logger_stderr(object):
    def __init__(self, full_log_file):
        self.terminal = sys.stderr
        # log_folder = 'C:/Users/User/Desktop/dataflow_error'
        # log_file = 'dataflow_log_' + strftime("%Y%m%d-%H%M%S") + '.txt'
        # self.full_log_file = os.path.join(log_folder, log_file)
        self.log = open(full_log_file, "a")

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)  

    def flush(self):
        #this flush method is needed for python 3 compatibility.
        #this handles the flush command by doing nothing.
        #you might want to specify some extra behavior here.
        pass

def get_fly_json_data_from_h5(directory):
    """
    Automatically create fly.json required for snake_brainsss from hdf5 from stimpack
    :param directory:
    :return:
    """
    for current_path in directory.iterdir():
        if '.hdf5' in current_path.name:
            print('Found hdf5 file: ' + current_path.name)
            h5py_file = h5py.File(current_path, 'r')
            break
    # After finding the h5 file (there must only be a single h5 file in the parent folder!)
    # escape the loop and work on each defined subject.
    subjects = h5py_file['Subjects']

    # Sanity check - do we have the same amount of exp folders as we have subjects defined in the
    # h5 file?
    no_of_exp_folders = 0
    for current_folder in directory.iterdir():
        if current_folder.is_dir():
            no_of_exp_folders += 1

    # Only continue if # of subjects matches # of foldres
    if len(subjects) == no_of_exp_folders:
        for current_subject in subjects:
            # Look for a folder that should be the subjects folder!
            current_target_folder = pathlib.Path(directory, 'fly' + current_subject)

            if current_target_folder.exists():
                fly_dict = {}

                for current_attrs in subjects[str(current_subject)].attrs:
                    fly_dict[current_attrs] = subjects[str(current_subject)].attrs[current_attrs]

                # Save the dict, can use it to directly write the fly.json file as well!
                # save_path = pathlib.Path(target_path, date, 'fly_' + fly_dict["subject_id"], 'fly.json')

                dict_for_json = {}
                dict_for_json['Genotype'] = fly_dict['genotype_father'] + '_x_' + fly_dict['genotype_mother']
                #dict_for_json['functional_channel'] = fly_dict['functional_channel']
                #dict_for_json['structural_channel'] = fly_dict['structural_channel']

                # these are all optional
                dict_for_json['Sex'] = fly_dict['sex']
                #dict_for_json['circadian_on'] = str(fly_dict['circadian_on'])
                #dict_for_json['circadian_off'] = str(fly_dict['circadian_off'])
                dict_for_json['Age'] = str(fly_dict['age'])
                #dict_for_json['Temp (inline heater)'] = str(fly_dict['Temp (inline heater)'])

                save_path = pathlib.Path(current_target_folder, 'fly.json')
                with open(save_path, 'w') as file:
                    json.dump(dict_for_json, file, sort_keys=True, indent=4)

            else:
                print('>>>>>>ERROR<<<<<')
                print(current_path.name + ' indicates experiments were done with a folder called ' +
                      pathlib.Path(directory, 'fly' + current_subject).name)
                print('However, that folder does not seem to exist')
                print('Could therefore not create fly.json files from h5!')
                print('>>>>>>ERROR<<<<<')


    else:
        print('>>>>>>ERROR<<<<<')
        print('Number of subjects in h5: ' + repr(len(subjects)))
        print('Number of folders in ' + directory.name + ':' + repr(no_of_exp_folders))
        print('Could not create fly.json files from h5 as the number of subjects and folders should match!')
        print('>>>>>>ERROR<<<<<<<')

class DownloadFolderFTP():
    """
    TO BE TESTED
    This class connects to a remote computer using ip, username and password.
    It then downloads all files in a folder while keeping the folder structure
    intact.
    Note that the remote_root_path should be strings with the correct separator for the
    REMOTE computer!
    """
    def __init__(self, ip, username, passwd,
                 remote_root_path, folder_to_copy,
                 local_target_path):

        # Define class wide variables:
        self.folder_to_copy = folder_to_copy
        self.local_target_path = local_target_path
        self.remote_root_path = remote_root_path

        ######################################
        ### Connect to Stimpack/fictrac PC ###
        ######################################
        with ftputil.FTPHost(ip, username, passwd) as self.ftp_host:
            # will iterate through each of the folders, i.e. in 'fictrac source'
            for current_folder in self.ftp_host.listdir(remote_root_path):
                if self.folder_to_copy == current_folder:
                    #print(relevant_folder)
                    relevant_folder_path = remote_root_path + '/' + self.folder_to_copy
                    print('relevant_folder_path: ' + repr(relevant_folder_path))
                    # call function which will iterate through file structure until
                    # it hits a file
                    self.iterdir_until_file_ftphost(relevant_folder_path)

    def iterdir_until_file_ftphost(self, folder):
        """
        Since we don't have access to pathlib nor os, I wrote this
        function to walk through all folders until a file is found. Once
        a file is found, copy it (with the full path).
        :param folder:
        :return:
        """
        #print('folder: ' + folder)

        # Check if the current path in 'folder' is a file
        if self.ftp_host.path.isfile(folder):
            # If yes, download!
            # Start by grabbing the relative path, i.e. the part AFTER the
            # folder name we are copying.
            # For example, if we want to copy a folder called '20240611' we
            # might have folder = '/../../David/stimpack/fictrac/20240611/1/loco/data.dat'
            # the next line will return /1.loc/data.data
            relative_path = folder.split(self.folder_to_copy)[-1]
            # Next, combine it with the desired target folder on the local computer
            current_target_folder = pathlib.Path(self.local_target_path,
                                                 #self.folder_to_copy,
                                                 relative_path[1::]) # w/o 1:: there's a leading /!
            print('local_target_path ' + repr(self.local_target_path))
            print('relative_path ' + repr(relative_path))
            print("current_target_folder " + repr(current_target_folder))
            # Make sure the folder structure (i.e. C:/brukerbridge/David/20240611/1/loco)
            # exists
            current_target_folder.parent.mkdir(exist_ok=True, parents=True)
            # Then download the file into that folder
            self.ftp_host.download(folder, current_target_folder)  # remote, local
        else:
            # Else loop recursively: Call self to go one folder deeper!
            for current_folder in self.ftp_host.listdir(folder):
                #print("current_folder: " + current_folder)
                current_full_folder = folder + '/' + current_folder

                self.iterdir_until_file_ftphost(current_full_folder)