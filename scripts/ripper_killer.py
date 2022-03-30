import os
import sys
from time import sleep

def main(directory):
    raws_exist = True
    print('RIPPER KILLER IS WATCHING')
    while raws_exist:
        raws_exist = False
        raws_exist = check_for_raw_files(directory, raws_exist)
        print('1 min updates... raws_exist is {}'.format(raws_exist), flush=True)
        sleep(60)

    # Kill bruker converter now that no more raws exist
    os.system("C:/Users/User/projects/brukerbridge/scripts/ripper_killer.bat")

def check_for_raw_files(directory, raws_exist):
    for item in os.listdir(directory):
        new_path = directory + '/' + item

        # Check if item is a directory
        if os.path.isdir(new_path):
            raws_exist = check_for_raw_files(new_path, raws_exist)
            
        # If the item is a file
        else:
            if '_RAWDATA_' in item:
                raws_exist = True
    return raws_exist

if __name__ == "__main__":
    main(sys.argv[1])