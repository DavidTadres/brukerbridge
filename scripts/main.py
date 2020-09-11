import sys
import os
import warnings
import subprocess
import json
import brukerbridge as bridge

warnings.filterwarnings("ignore", category=DeprecationWarning)

extensions_for_oak_transfer = ['.nii', '.csv', '.xml', 'json', 'tiff'] # needs to be 4 char
root_directory = "G:/ftp_imports"
users_directory = "C:/Users/User/projects/brukerbridge/users"

def main(args):
    user = args[0]
    directory = args[1]
    full_target = os.path.join(root_directory, user, directory)

    #####################
    ### Setup logging ###
    #####################

    sys.stdout = bridge.Logger_stdout()
    sys.stderr = bridge.Logger_stderr()

    #########################
    ### Get user settings ###
    #########################

    user = "luke" # UPDATE
    if user + '.json' in os.listdir(users_directory):
        json_file = os.path.join(users_directory, user + '.json')
        with open(json_file) as file:
            settings = json.load(file)
    print(settings) # remove
    oak_target = settings['oak_target']
    convert_to = settings['convert_to']
    email = settings['email']

    ######################################
    ### Save email for error reporting ###
    ######################################

    email_file = 'C:/Users/User/projects/brukerbridge/scripts/email.txt'
    with open(email_file, 'w') as f:
        f.write(email)

    #################################
    ### Convert from raw to tiffs ###
    #################################
    
    bridge.convert_raw_to_tiff(full_target)

    #########################################
    ### Convert tiff to nii or tiff stack ###
    #########################################

    if convert_to == 'nii':
        bridge.convert_tiff_collections_to_nii(full_target)
    elif convert_to == 'tiff':
        bridge.convert_tiff_collections_to_stack(full_target)
    else:
        print('{} is an invalid convert_to variable from user metadata.'.format(convert_to))
        print("Must be nii or tiff, with no period")

    #######################
    ### Transfer to Oak ###
    #######################

    bridge.start_oak_transfer(full_target, oak_target, extensions_for_oak_transfer)

    # ### Delete files locally
    # if delete_local:
    #     bridge.delete_local(full_target)

if __name__ == "__main__":
    main(sys.argv[1:])