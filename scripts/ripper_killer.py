"""
Helper module which just checks if raw files still exist. If yes, let the ripper running, else,
kill the program.
Changed code to relative pathnames to work out of the box on other computers.
"""


import os
import sys
from time import sleep
import pathlib
from glob import glob
parent_path = str(pathlib.Path(pathlib.Path(__file__).parent.absolute()).parent.absolute())

def main(directory):
    ripping_incomplete = True
    print('RIPPER KILLER IS WATCHING')
    while ripping_incomplete:
        ripping_incomplete = False
        ripping_incomplete = ripping_incomplete_func(directory, ripping_incomplete)
        print('1 min updates... raws_exist is {}'.format(ripping_incomplete), flush=True)
        if ripping_incomplete:
            sleep(60)
    # Kill bruker converter now that no more raws exist
    #os.system("C:/Users/User/projects/brukerbridge/scripts/ripper_killer.bat")
    path_to_ripper_killer = pathlib.Path(parent_path, 'ripper_killer.bat')
    # os.system("C:/Users/User/projects/brukerbridge/scripts/ripper.bat {}".format('"' + full_target + '"'))
    os.system(str(path_to_ripper_killer))
'''
    # Note 241119 - MC told me that the cause of missing voltage data in Andrew's fork
    # was that the ripper was killed to early.
    # We might have the same problem.
    ripping_incomplete = True
    print('calling ripping_incomplete')
    while ripping_incomplete:
        ripping_incomplete = ripping_incomplete_func(directory)
        #if ripping_incomplete:
        # Always wait a 60 seconds before killing the ripper
        if ripping_incomplete:
            print('1 min updates... ripping incomplete: {}'.format(ripping_incomplete), flush=True)
        else:
            print('Ripping complete. Waiting 1 minute before killing ripper')
        sleep(60)

'''
'''
def ripping_incomplete_func(directory):
    """
    By Minseung - checks if both rawdata image file and any voltage recordings exist.
    :param directory:
    :return:
    """
    # For Voltage Recording, the VRFilelist.txt gets deleted, while the voltage raw data is not reliably deleted (not on current BrukerBridge). MC 20241118
    #if len(glob(f"{directory}/*_RAWDATA_*")) + len(glob(f"{directory}/*_VoltageRecording_[0-9][0-9][0-9]_VRFilelist.txt")) == 0:
    #    return(False)
    #else:
    #    return(True)
    # The above can't work because we have undetermined file structure from directory!
    # need to build a recursive function instead
    directory = pathlib.Path(directory) # easier filepath handling
    print(directory)
    folders_incomplete = []

    def one_folder_deeper(directory):
        for current_folder in directory.iterdir():
            #print("current_folder of one_folder_deeper: " + repr(current_folder))
            if current_folder.is_dir():
                one_folder_deeper(current_folder)
            else:
                #print("current_folder of one_folder_deeper: " + repr(current_folder))
                if len(glob(f"{directory}/*_RAWDATA_*")) + len(
                        glob(f"{directory}/*_VoltageRecording_[0-9][0-9][0-9]_VRFilelist.txt")) == 0:
                    folders_incomplete.append(False)

                else:
                    folders_incomplete.append(True)
                return()

    for current_folder in directory.iterdir():
        if current_folder.is_dir():
            print("current_folder: " + repr(current_folder))
            one_folder_deeper(current_folder)
        else:
            if len(glob(f"{directory}/*_RAWDATA_*")) + len(
                glob(f"{directory}/*_VoltageRecording_[0-9][0-9][0-9]_VRFilelist.txt")) == 0:
                folders_incomplete.append(False)
            else:
                folders_incomplete.append(True)
    print("folders_incomplete: " + repr(folders_incomplete))
    if any(folders_incomplete):
        return(True)
    else:
        return(False)'''


def ripping_incomplete_func(directory, ripping_incomplete):
    #for item in os.listdir(directory):
    for item in pathlib.Path(directory).iterdir():
        #new_path = directory + '/' + item

        # Check if item is a directory
        #if os.path.isdir(new_path):
        #    raws_exist = ripping_incomplete_func(new_path, raws_exist)
        if item.is_dir():
            ripping_incomplete = ripping_incomplete_func(item, ripping_incomplete)
            
        # If the item is a file
        else:
            # This check whether we have any image files that are not yet ripped
            #if '_RAWDATA_' in item.name:
            # WE want to keep the raw files now as there are errors with the ripper...
            if 'Filelist.txt' in item.name:
                ripping_incomplete = True
            # This should address the bug Minseung discovered:
            # Ripping of the voltage trace also happens here and if we only check
            # for raw files to be gone, we might kill the ripper before voltage
            # traces are ripped!
            elif '_VoltageRecording_' in item.name and '_VRFilelist.txt' in item.name:
                ripping_incomplete

    return ripping_incomplete


if __name__ == "__main__":
    main(sys.argv[1])