import sys
import smtplib
#import re
import os
#import math
import json
from email.mime.text import MIMEText
from time import time
from xml.etree import ElementTree as ET
from time import strftime
from time import sleep
from functools import wraps
import shutil
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
    
    try:
                h5py_file
    except FileNotFoundError:
                print('h5 file not found in fly folder: ' + str(current_target_folder))
    
    subjects = h5py_file['Subjects']

    # Sanity check - do we have the same amount of exp folders as we have subjects defined in the
    # h5 file?
    no_of_exp_folders = 0
    for current_folder in directory.iterdir():
        if 'fly' in current_folder.name:
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
                dict_for_json['functional_channel'] = fly_dict['functional_channel']
                dict_for_json['structural_channel'] = fly_dict['structural_channel']

                # these are all optional
                dict_for_json['Sex'] = fly_dict['sex']
                dict_for_json['circadian_on'] = str(fly_dict['circadian_on'])
                dict_for_json['circadian_off'] = str(fly_dict['circadian_off'])
                dict_for_json['Age'] = str(fly_dict['age'])
                dict_for_json['Temp (inline heater)'] = str(fly_dict['inline_heater_temp'])
                dict_for_json['notes'] = str(fly_dict['notes'])

                save_path = pathlib.Path(current_target_folder, 'fly.json')
                with open(save_path, 'w') as file:
                    json.dump(dict_for_json, file, sort_keys=True, indent=4)

                # Also save the notes done during the experiment

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

def get_fly_json_data_from_h5_one_fly_per_h5(directory):
    """
    Automatically create fly.json required for snake_brainsss from hdf5 from stimpack
    :param directory:
    :return:
    NOTE: Jacob - updated version of get_fly_json_data_from_h5 to work on hdf5 with 
    single fly placed in each fly folder instead of one hdf5 per day in experiment folder
    """

    for current_path in directory.iterdir():
        if 'fly' in current_path.name:
            print('working on folder: ' + str(current_path.name))
            current_target_folder = pathlib.Path(directory, current_path)
            #TODO:current_subject = str(current_target_folder).split('fly')[-1] #extract subject # from fly folder number
            current_subject = 1 #assumes subject number reset to 1 for each fly during experiment
            
            # find hdf5 in fly folder
            for path in current_target_folder.iterdir():
                if '.hdf5' in path.name:
                    print('Found hdf5 file: ' + path.name)
                    h5py_file = h5py.File(path, 'r')
                    break
            try:
                h5py_file
            except FileNotFoundError:
                print('h5 file not found in fly folder: ' + str(current_target_folder))

            # After finding the h5 file (there must only be a single h5 file in the parent folder!)
            # escape the loop and work on the subject
            subject = h5py_file['Subjects']
            # Look for a folder that should be the subjects folder!

            fly_dict = {}
            for current_attrs in subject[str(current_subject)].attrs:
                fly_dict[current_attrs] = subject[str(current_subject)].attrs[current_attrs]

            # Save the dict, can use it to directly write the fly.json file as well!
            # save_path = pathlib.Path(target_path, date, 'fly_' + fly_dict["subject_id"], 'fly.json')

            dict_for_json = {}
            dict_for_json['Genotype'] = fly_dict['genotype_father'] + '_x_' + fly_dict['genotype_mother']
            dict_for_json['functional_channel'] = fly_dict['functional_channel']
            dict_for_json['structural_channel'] = fly_dict['structural_channel']

            # these are all optional
            dict_for_json['Sex'] = fly_dict['sex']
            dict_for_json['circadian_on'] = str(fly_dict['circadian_on'])
            dict_for_json['circadian_off'] = str(fly_dict['circadian_off'])
            dict_for_json['Age'] = str(fly_dict['age'])
            dict_for_json['Temp (inline heater)'] = str(fly_dict['inline_heater_temp'])
            dict_for_json['notes'] = str(fly_dict['notes'])

            save_path = pathlib.Path(current_target_folder, 'fly.json')
            with open(save_path, 'w') as file:
                json.dump(dict_for_json, file, sort_keys=True, indent=4)
            fly_json_made = True
    try:
        fly_json_made
    except FileNotFoundError:
        print('no fly folders found within selected directory: ' + str(directory))


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

def write_h5_metadata_in_stimpack_folder(directory):
    """
    As a preparation to:

        1) checking whether a flyID (such as fly1, fly2 etc.) defined
        by the user on the Bruker PC while imaging fits the metadata entered by the user
        into stimpack (as subject 1, 2 etc.) extract the h5 metadata (situated on the imaging
        computer) and write a json into the the actual stimpack data (such as fictrac/loco data,
        originally situated on the stimpack/fictrac computer).

        2) to compare timestamps of the imaging session with the supposedly attached stimpack
        session

    write a small json file name 'flyID.json' into the stimpack folder

    Original:
    - 2024-06-13.hdf5
    - 2024-06-13
        - 1
            - loco
                - fictrac data
    After function call:
    - 2024-06-13.hdf5
    - 2024-06-13
        - 1
            - flyID.json <<<<<<
            - loco
                - fictrac data

    flyID.json is a dict that looks like:
     {'fly': 'fly1', 'series': '1', 'series_start_time': '1718310030.084193'}

    :param directory: source directory, i.e. F:\brukerbridge\David\20240613__queue__
    :return:
    """
    # read h5 file
    for current_path in directory.iterdir():
        if '.hdf5' in current_path.name:
            print('Found hdf5 file: ' + current_path.name)
            h5py_file = h5py.File(current_path, 'r')
            break
    # After finding the h5 file (there must only be a single h5 file in the parent folder!)
    # escape the loop and work on each defined subject.
    subjects = h5py_file['Subjects']
    # For each series in the h5 file, write a json file directly in the series
    # folder of the data from the stimpack/fictrac computer!

    # Create a dict that combines
    # 1) fly ID from 'current_subject' of h5 file
    # 2) the series that belongs to a given fly as defined by the h5 file
    # 3) the start time of the series

    experiments = {}
    for current_subject in subjects:
        # eries = []
        # start_times = []
        data_for_current_fly = []
        for current_series in subjects[current_subject]['epoch_runs']:
            unix_time = subjects[current_subject]['epoch_runs'][current_series].attrs['run_start_unix_time']
            # We'll have a string such as 'series_001-1718310030.084193' with the number after the '-' indicating
            # unix time when series_001 in our example was started!
            string_to_save = current_series + '-' + str(unix_time)
            data_for_current_fly.append(string_to_save)
            # use unix time as it doesn't depend on timezone!
            # unix_time.append(subjects[current_subject]['epoch_runs'][current_series].attrs['run_start_unix_time'])

        # In this dict, the key (i.e. fly1) defines the subject which has a list (can be more than 1) of series
        # including start times.
        experiments['fly' + str(current_subject)] = data_for_current_fly


    # Now that we have the series ID tied to the fly ID (which is easier to keep track
    # of on Bruker with the imaging folder) write a json file for each series which
    # contains the fly ID.
    # This can easily be checked later on and confirmed to fit the bruker imaging data!
    stimpack_data_folder = pathlib.Path(current_path.as_posix().split('.hdf5')[0])
    # loop through the flies
    for current_fly in experiments:
        # Each fly can have more than one series, loop to return each series
        for current_string in experiments[current_fly]:
            # the folder name of the series by stimpack is '1', '2' etc.
            # The name of the corresponding seires in the h5 file is 'series_001', 'series_002' etc.
            # str(int(current_string.split('-')[0].split('series_')[-1])) converts the string to int
            # so that '001' becomes '1' and '010' becomes '10'.
            current_series = str(int(current_string.split('-')[0].split('series_')[-1]))
            current_series_start_time = current_string.split('-')[-1]
            current_series_path = pathlib.Path(stimpack_data_folder, current_series)

            relevant_metadata = {}
            relevant_metadata['fly'] = current_fly
            relevant_metadata['series'] = current_series
            relevant_metadata['series_start_time'] = current_series_start_time

            # When one does only walking and forgets to tick the 'loco' box, no data is
            # created for that series. This would therefore fail as no folder exists on the
            # brukerbridge computer that would refer to this series. Hence, create the folder
            # and populate it with the fly.json file.
            current_series_path.mkdir(parents=True, exist_ok=True)
            save_path = pathlib.Path(current_series_path, 'flyID.json')
            # Save as json
            with open(save_path, 'w') as file:
                json.dump(relevant_metadata, file, sort_keys=True, indent=4)

def write_h5_metadata_in_stimpack_folder_one_fly_per_h5(directory):
    """
    As a preparation to:

        1) checking whether a flyID (such as fly1, fly2 etc.) defined
        by the user on the Bruker PC while imaging fits the metadata entered by the user
        into stimpack (as subject 1, 2 etc.) extract the h5 metadata (situated on the imaging
        computer) and write a json into the the actual stimpack data (such as fictrac/loco data,
        originally situated on the stimpack/fictrac computer).

        2) to compare timestamps of the imaging session with the supposedly attached stimpack
        session

    write a small json file name 'flyID.json' into the stimpack folder

    Original:
    - 2024-06-13.hdf5
    - 2024-06-13
        - 1
            - loco
                - fictrac data
    After function call:
    - 2024-06-13.hdf5
    - 2024-06-13
        - 1
            - flyID.json <<<<<<
            - loco
                - fictrac data

    flyID.json is a dict that looks like:
     {'fly': 'fly1', 'series': '1', 'series_start_time': '1718310030.084193'}

    :param directory: source directory, i.e. F:\brukerbridge\David\20240613__queue__
    :return:
    NOTE: Jacob - updated version of get_fly_json_data_from_h5 to work on hdf5 with 
    single fly placed in each fly folder instead of one hdf5 per day in experiment folder
    """
    # read h5 file
    for current_path in directory.iterdir():
        if 'fly' in current_path.name:
            print('working on folder: ' + str(current_path.name))
            current_target_folder = pathlib.Path(directory, current_path)
            #TODO:current_subject = str(current_target_folder).split('fly')[-1] #extract subject # from fly folder number
            current_subject = 1 #assumes subject number reset to 1 for each fly during experiment
            fly = str(current_target_folder).split('fly')[-1] #extract subject # from fly folder number
            #TODO: replace fly with current_subject
            # find hdf5 in fly folder
            for path in current_target_folder.iterdir():
                if '.hdf5' in path.name:
                    print('Found hdf5 file: ' + path.name)
                    h5py_file = h5py.File(path, 'r')
                    break
            try:
                h5py_file
            except FileNotFoundError:
                print('h5 file not found in fly folder: ' + str(current_target_folder))


            subject = h5py_file['Subjects']
            # For each series in the h5 file, write a json file directly in the series
            # folder of the data from the stimpack/fictrac computer!

            # Create a dict that combines
            # 1) fly ID from 'current_subject' of h5 file
            # 2) the series that belongs to a given fly as defined by the h5 file
            # 3) the start time of the series

            experiments = {}
            # eries = []
            # start_times = []
            data_for_current_fly = []
            for current_series in subject[str(current_subject)]['epoch_runs']:
                unix_time = subject[str(current_subject)]['epoch_runs'][current_series].attrs['run_start_unix_time']
                # We'll have a string such as 'series_001-1718310030.084193' with the number after the '-' indicating
                # unix time when series_001 in our example was started!
                string_to_save = current_series + '-' + str(unix_time)
                data_for_current_fly.append(string_to_save)
                # use unix time as it doesn't depend on timezone!
                # unix_time.append(subjects[current_subject]['epoch_runs'][current_series].attrs['run_start_unix_time'])

            # In this dict, the key (i.e. fly1) defines the subject which has a list (can be more than 1) of series
            # including start times.
            #TODO:experiments['fly' + str(current_subject)] = data_for_current_fly
            experiments['fly' + fly] = data_for_current_fly


            # Now that we have the series ID tied to the fly ID (which is easier to keep track
            # of on Bruker with the imaging folder) write a json file for each series which
            # contains the fly ID.
            # This can easily be checked later on and confirmed to fit the bruker imaging data!
            date_string = directory.name[0:4] + '-' +  directory.name[4:6] + '-' +  directory.name[6:8]
            #yyyy-mm-dd for fictrac folder
            stimpack_data_folder = pathlib.Path(directory, date_string)
            print('stimpack data folder: ' str(stimpack_data_folder))

            # fly can have more than one series, loop to return each series
            for current_string in experiments['fly' + fly]:
                # the folder name of the series by stimpack is '1', '2' etc.
                # The name of the corresponding seires in the h5 file is 'series_001', 'series_002' etc.
                # str(int(current_string.split('-')[0].split('series_')[-1])) converts the string to int
                # so that '001' becomes '1' and '010' becomes '10'.
                current_series = str(int(current_string.split('-')[0].split('series_')[-1]))
                current_series_start_time = current_string.split('-')[-1]
                current_series_path = pathlib.Path(stimpack_data_folder, current_series)

                relevant_metadata = {}
                relevant_metadata['fly'] = 'fly' + fly
                relevant_metadata['series'] = current_series
                relevant_metadata['series_start_time'] = current_series_start_time

                # When one does only walking and forgets to tick the 'loco' box, no data is
                # created for that series. This would therefore fail as no folder exists on the
                # brukerbridge computer that would refer to this series. Hence, create the folder
                # and populate it with the fly.json file.
                current_series_path.mkdir(parents=True, exist_ok=True)
                save_path = pathlib.Path(current_series_path, 'flyID.json')
                # Save as json
                with open(save_path, 'w') as file:
                    json.dump(relevant_metadata, file, sort_keys=True, indent=4)

def get_datetime_from_xml(xml_file):
    """
    Open imaging xml file and get the date and time of the imaging session!
    :param xml_file:
    :return:
    """
    ##print('Getting datetime from {}'.format(xml_file))
    ##sys.stdout.flush()
    tree = ET.parse(xml_file)
    root = tree.getroot()
    datetime = root.get("date")

    return (datetime)

def add_stimpack_data_to_imaging_folder(directory,
                                        max_diff_imaging_and_stimpack_start_time_second):
    """
    Copy stimpack data from bespoke folder INTO corresponding imaging folder.
    :param directory: source directory, i.e. F:\brukerbridge\David\20240613__queue__
    :return:
    """
    # Dict with error messages
    error_dict = {}

    # Find pathname of stimpack data: Must be the same as the 'hdf5' file without the 'hdf5'
    for current_path in directory.iterdir():
        if '.hdf5' in current_path.name:
            print('Found hdf5 file: ' + current_path.name)
            stimpack_data_folder = pathlib.Path(current_path.as_posix().split('.hdf5')[0])
            print('stimpack_data_folder path is therefore: ' + stimpack_data_folder.as_posix())
            break

    for current_imaging_folder in sorted(directory.iterdir()):
        if 'fly' in current_imaging_folder.name:
            print("current_path: " + repr(current_path))
            # For each folder with a 'fly' in the folder name
            for current_imaging_folder_fly in current_imaging_folder.iterdir():
                if 'func' in current_imaging_folder_fly.name:
                    print("current_imaging_folder_fly: " + repr(current_imaging_folder_fly))
                    # Check if there are more than 1 folder with name TSeries!
                    no_of_TSeries_folders = 0
                    for current_t_series in current_imaging_folder_fly.iterdir():
                        if 'TSeries' in current_t_series.name:
                            no_of_TSeries_folders +=1

                    if no_of_TSeries_folders>1:
                        # Yields i.e. func0_TSeries_error_msg
                        key = current_imaging_folder_fly.name + '_TSeries_error_msg'
                        error_dict[key] = ('More than 1 folder with "TSeries" in folder ' +
                                                   current_imaging_folder_fly.name + '.\nYou can only have'
                                                 'a single folder called TSeries per func folder!')
                        # If there is more than one TSeries folder it's not possible to continue for
                        # that experiment: Since the stimpack or fictrac folder is assigned by 'func' folder
                        # one would need more than one stimpack or fictrac folder per func folder.
                    # elif other errors!
                    else:
                        # for each folder with a 'func' in the folder name
                        for current_t_series in current_imaging_folder_fly.iterdir():
                            #print(current_t_series.name)
                            if 'TSeries' in current_t_series.name:
                                print("current_t_series.name: " + repr(current_t_series.name))
                                # This returns the number of the series without leading zeros
                                imaging_series = str(int(current_t_series.name[-3::]))
                                # For a given imaging folder, check if the loco data has the
                                # correct fly id!
                                current_stimpack_folder = pathlib.Path(stimpack_data_folder, imaging_series)
                                if pathlib.Path(current_stimpack_folder, 'flyID.json').exists():
                                    flyID = get_json_data(pathlib.Path(current_stimpack_folder, 'flyID.json'))
                                    # Will be checked with the first 'if' below.

                                    # Next, want to load the xml file of the imaging data to extract timestamp
                                    imaging_metadata_path = pathlib.Path(current_t_series, current_t_series.name + '.xml')

                                    # This will return i.e. '6/13/2024 04:54:23 PM'
                                    imaging_datetime_string = get_datetime_from_xml(imaging_metadata_path)
                                    # Now it's in this format: datetime.datetime(2024, 6, 13, 4, 54, 23)
                                    imaging_datetime_strf = datetime.strptime(imaging_datetime_string,
                                                                                       '%m/%d/%Y %I:%M:%S %p')
                                    # Get timezone of the local computer (assuming this code is running on same computer
                                    # that created the metadata_xml file)
                                    imaging_timestamp_unix_time = imaging_datetime_strf.timestamp()
                                    # Calculate the absolute difference in seconds between the start of imaging and start of
                                    # stimpack series
                                    delta_imaging_stimpack_start_time = abs(imaging_timestamp_unix_time - float(
                                        flyID['series_start_time']))
                                    # Now we have difference in start time in seconds!
                                    print("current_imaging_folder.name: " + repr(current_imaging_folder.name))
                                    print(" flyID['fly']: "+ repr( flyID['fly']))

                                    if not current_imaging_folder.name == flyID['fly']:
                                        # IF we are here imaging folder defining the fly doesn't match the stimpack.h5 file!
                                        # Cancel and put a __warning__ on the folder!
                                        new_name = pathlib.Path(str(directory).split('__queue__')[0] + '__WARNING__')
                                        os.rename(directory, new_name)
                                        print('>>>>>>>>>>>>>>>>>>>>>>EXITING QUEUE AND WARNING ADDED<<<<<<<<<<<<<<<<<<<')
                                        print('For stimpack/fictrac autotransfer the series number of the stimpack GUI\n')
                                        print('and the series number of the TSeries must be in the same "fly".')
                                        print(
                                            'Instead, the current imaging folder is ' + current_imaging_folder.as_posix() + '\n')
                                        print('with the following h5 metadata: ' + repr(flyID))
                                        sys.exit()
                                    elif not delta_imaging_stimpack_start_time < max_diff_imaging_and_stimpack_start_time_second:  # CHECK TIMESTAMPS!
                                        # IF we are here, the time difference between when the imaging session started
                                        # and the stimpack/fictrac session started is larger than allowed by
                                        # stimpack_imaging_max_allowed_delta!
                                        new_name = pathlib.Path(str(directory).split('__queue__')[0] + '__WARNING__')
                                        os.rename(directory, new_name)
                                        print('--------------------->EXITING QUEUE AND WARNING ADDED<---------------------')
                                        print('For stimpack/fictrac autotransfer the timestamps of the imaging recording\n')
                                        print('session and the stimpack session start time must be smaller than '
                                              + repr(delta_imaging_stimpack_start_time) + 's\n')
                                        print('Calculated delta of: ' + repr(delta_imaging_stimpack_start_time) + '\n')
                                        print('for imaging folder ' + current_t_series.as_posix())
                                        print('h5 metadata contains the following information: ' + repr(flyID))
                                        sys.exit()

                                    else:
                                        # Copy fictrac data into corresponding 'func' folder so that it can easily
                                        # be picked up by the fly_builder later on!
                                        source_path = current_stimpack_folder
                                        target_path = pathlib.Path(current_imaging_folder_fly, 'stimpack')
                                        try:
                                            shutil.copytree(source_path, target_path)
                                        except FileExistsError:
                                            print('\ntarget path ' + target_path.as_posix() + ' already exists! ')
                                            print('Nothing copied\n')
                                else:
                                    print('------------------------>WARNING<-------------------------------------------')
                                    print(pathlib.Path(current_stimpack_folder, 'flyID.json').as_posix() + 'does not exist.\n')
                                    print('It seems that ' + current_t_series.name + 'does not have corresponding fictrac data.')
                                    print('^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^')


    return(error_dict)


def get_bool_from_json(settings_json, input_string):
    try:
        input_string = settings_json[input_string]
        if input_string == 'True' or input_string == 'TRUE' or input_string == 'true':
            output = True
        else:
            output = False
    except KeyError:
        output = False

    return (output)