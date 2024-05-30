"""
Helper module which just checks if raw files still exist. If yes, let the ripper running, else,
kill the program.
Changed code to relative pathnames to work out of the box on other computers.
"""


import os
import sys
from time import sleep
import pathlib
parent_path = str(pathlib.Path(pathlib.Path(__file__).parent.absolute()).parent.absolute())

def main(directory):
    raws_exist = True
    print('RIPPER KILLER IS WATCHING')
    while raws_exist:
        raws_exist = False
        raws_exist = check_for_raw_files(directory, raws_exist)
        print('1 min updates... raws_exist is {}'.format(raws_exist), flush=True)
        if raws_exist:
            sleep(60)

    # Kill bruker converter now that no more raws exist
    #os.system("C:/Users/User/projects/brukerbridge/scripts/ripper_killer.bat")
    path_to_ripper_killer = pathlib.Path(parent_path, 'ripper_killer.bat')
    # os.system("C:/Users/User/projects/brukerbridge/scripts/ripper.bat {}".format('"' + full_target + '"'))
    os.system(str(path_to_ripper_killer))

def check_for_raw_files(directory, raws_exist):
    #for item in os.listdir(directory):
    for item in pathlib.Path(directory).iterdir():
        #new_path = directory + '/' + item

        # Check if item is a directory
        #if os.path.isdir(new_path):
        #    raws_exist = check_for_raw_files(new_path, raws_exist)
        if item.is_dir():
            raws_exist = check_for_raw_files(item, raws_exist)
            
        # If the item is a file
        else:
            if '_RAWDATA_' in item.name:
                raws_exist = True
    return raws_exist

if __name__ == "__main__":
    main(sys.argv[1])