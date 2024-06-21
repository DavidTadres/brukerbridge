import pathlib
import shutil
import os
import datetime
import time

def oak_transfer(root_path_name, # Will be something like
                 directory_from,
                 oak_target,
                 allowable_extensions,
                 add_to_build_que,
                 copy_SingleImage):

    """
    Rewrote Bella's function which I didn't completely get
    :param root_path_name: str, will be something like 20240613__queue__ and won't change when called recursively!
    :param directory_from: pathlib.Path object
    :param oak_target: pathlib.Path object
    :param extensions_for_oak_transfer: list of extension we want to transfer
    :param add_to_build_que:
    :return:
    """

    for current_file_or_folder in directory_from.iterdir():
        # if we are in a folder, recursively call transfer function
        if current_file_or_folder.is_dir():
            oak_transfer(root_path_name=root_path_name,
                         directory_from=current_file_or_folder,
                         oak_target=oak_target,
                         allowable_extensions=allowable_extensions,
                         add_to_build_que=add_to_build_que,
                         copy_SingleImage=copy_SingleImage)

        else:
            if not copy_SingleImage:
                # DO NOT copy the 'SingleImage' folders that Bruker collects every time
                # one clicks on 'live image'.
                if 'SingleImage' in current_file_or_folder.as_posix():
                    pass
            # Check for allowable extensions (hardcoded in 'main.py'!)
            elif current_file_or_folder.suffix in allowable_extensions:

                # Get the relative path.
                # I.e. 'F:\\brukerbridge\\David\\20240613__queue__\\fly1\\func0\\TSeries-12172018-1322-001\\TSeries-12172018-1322-001_channel_2.nii'
                # becomes '\\fly1\\func0\\TSeries-12172018-1322-001\\TSeries-12172018-1322-001_channel_2.nii'
                #print('oak_target: ' + repr(oak_target))
                relative_path = str(current_file_or_folder).split(root_path_name)[-1]
                # Super strange that the following line doesn't seem to work!
                #current_oak_target = pathlib.Path(oak_target, root_path_name, relative_path)
                # like have an extra / or \ somewhere which confused pathlib!
                str_current_oak_target = oak_target.as_posix() + '/'  +root_path_name + '/' + relative_path
                #print(str_current_oak_target)
                current_oak_target = pathlib.Path(str_current_oak_target)
                #print('current_oak_target.parent ' + repr(current_oak_target.parent))

                # Create parent folder of the file if it doesn't exist yet
                current_oak_target.parent.mkdir(parents=True, exist_ok=True)
                #####################
                ### TRANSFER FILE ###
                #####################

                file_size = os.path.getsize(current_file_or_folder.as_posix())
                file_size_MB = file_size * 10 ** -6
                file_size_GB = file_size * 10 ** -9

                if file_size_GB > 1:
                    now = datetime.datetime.now()
                    current_time = now.strftime("%H:%M:%S")

                    print('{} | Transfering file {}; size = {:.2f} GB'.format(current_time, current_oak_target, file_size_GB),
                          end='')
                    t0 = time.time()

                # FINALLY COPY THE FILE!!!
                shutil.copyfile(current_file_or_folder, current_oak_target)

                if file_size_GB > 1:
                    duration = time.time() - t0
                    duration += 0.1

                    print(' done. duration: {} sec; {} MB/SEC'.format(int(duration), int(file_size_MB / duration)))

                else:
                    print('Copied file ' + relative_path)


def start_oak_transfer(root_path_name, # Will be something like
                       directory_from,
                       oak_target,
                       allowable_extensions,
                       add_to_build_que,
                       copy_SingleImage):
    """
    Function that just calls the actual transfer function which is called recursively!
    :param root_path_name:
    :param directory_from:
    :param oak_target:
    :param allowable_extensions:
    :param add_to_build_que:
    :param copy_SingleImage:
    :return:
    """
    print('*** Starting Oak Upload ***')
    oak_transfer(root_path_name,
                 directory_from,
                 oak_target,
                 allowable_extensions,
                 add_to_build_que,
                 copy_SingleImage)
    print('*** Oak Upload Complete ***')
