import sys
import os
import warnings
import subprocess
import brukerbridge as bridge

warnings.filterwarnings("ignore", category=DeprecationWarning)


def main(args):
    user = args[0]
    directory = args[1]

    sys.stdout = bridge.Logger_stdout()
    sys.stderr = bridge.Logger_stderr()

    extensions_for_oak_transfer = ['.nii', '.csv', '.xml', 'json', 'tiff'] # needs to be 4 char
    ###########################################################################################################
    print("TADA")
    print("main user: {}".format(user))
    print("main directory: {}".format(directory))

    


    
    #################################
    ### Convert from raw to tiffs ###
    #################################



    # bridge.convert_raw_to_tiff(full_target)

    # #########################################
    # ### Convert tiff to nii or tiff stack ###
    # #########################################

    # if convert_to in ['.nii', 'nii', 'nifti']:
    #     bridge.start_convert_tiff_collections(full_target)
    # elif convert_to in ['.tiff', 'tiff', '.tif', 'tif']:
    #     bridge.convert_tiff_collections_to_stack(full_target)
    # else:
    #     print('{} is an invalid convert_to variable from metadata.'.format(convert_to))

    # #######################
    # ### Transfer to Oak ###
    # #######################

    # bridge.start_oak_transfer(full_target, oak_target, extensions_for_oak_transfer)

    # ### Delete files locally
    # if delete_local:
    #     bridge.delete_local(full_target)

if __name__ == "__main__":
    main(sys.argv[1:])