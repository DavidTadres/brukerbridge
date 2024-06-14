#import pathlib
#parent_path = str(pathlib.Path(pathlib.Path(__file__).parent.absolute()).parent.absolute())
#print(parent_path)


# Get data from fictrac computer.
# While this could be done at a later stage, i.e. by the server after data has been received it
# is possible that one would then interfere with the next experimenter!
# Hence, I'll integrate it on the client side (i.e. when user is moving imaging data).
import ftputil
import shutil
import pathlib

###################################
### Bruker Sr. fictrac computer ###
###################################
ip = '171.65.17.246'
username='clandinin'
passwd=input('Please enter password for ' + ip + ' for username ' + username)
fictrac_source = '../../data/david/stimpack_data/fictrac' # Unix style

source_folder = fictrac_source +'/' + '2024-06-10'
# Unable to use pathlib because we are accessing a remote that is/can be different than
# the computer this code is run!

####################################


######################
### Local computer ###
######################
target_folder = pathlib.Path('F:/temp/2024-06-10')

relevant_folder = '2024-06-10'
def iterdir_until_file(folder):
    """
    clumsy attempt of writing a function that allows me to find all
    folders in a folder
    :param folder:
    :return:
    """
    print('folder: ' + folder)

    # Check if this is a file
    if ftp_host.path.isfile(folder):
        # If yes, download!
        # Start by grabbing the relative path, i.e. the part AFTER the 'relevant' folder
        relative_path = folder.split(relevant_folder)[-1]

        current_target_folder = pathlib.Path(target_folder, relative_path)
        print("current_target_folder " + repr(current_target_folder))
        current_target_folder.parent.mkdir(exist_ok=True, parents=True)
        ftp_host.download(folder, current_target_folder)  # remote, local
    else:
        # Else loop and recursively call self to go one folder deeper!
        for current_folder in ftp_host.listdir(folder):
            print("current_folder: " + current_folder)
            current_full_folder = folder + '/' + current_folder

            iterdir_until_file(current_full_folder)


# Download some files from the login directory.
with ftputil.FTPHost(ip, username, passwd) as ftp_host:
    #all_fictrac_folders = ftp_host.listdir(fictrac_source) # needs to be string, not pathlib!

    for current_folder in ftp_host.listdir(fictrac_source):
        if relevant_folder == current_folder:
            print(relevant_folder)
            relevant_folder_path = fictrac_source + '/' + relevant_folder

            iterdir_until_file(relevant_folder_path)

    #        for current_folder in ftp_host.listdir(relevant_folder_path):
    #            print(current_folder)
    #ftp_host.download(source_folder, target_folder)
    #shutil.copytree(source_folder, target_folder)



    #names = ftp_host.listdir(ftp_host.curdir)
    #for name in names:
    #    if ftp_host.path.isfile(name):
    #        ftp_host.download(name, name)  # remote, local