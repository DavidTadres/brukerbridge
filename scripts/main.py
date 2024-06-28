__project__ = 'brukerbridge'
__version__ = '0.0.1'
__date__ = '2nd of June, 2024'

import sys
import warnings
import subprocess
import json
import time
import pathlib
parent_path = str(pathlib.Path(pathlib.Path(__file__).parent.absolute()).parent.absolute())
sys.path.insert(0, parent_path)
# This just imports '*.py' files from the folder 'brainsss'.
from brukerbridge import raw_to_tiff
from brukerbridge import tiff_to_nii
from brukerbridge.not_used import tiffs_to_tiff_stack
from brukerbridge import transfer_fictrac
from brukerbridge import transfer_to_oak
from brukerbridge import utils

### Save version of brukerbridge used for running this repo ###
CURRENT_GIT_BRANCH = subprocess.check_output(["git", "branch", "--show-current"]).strip().decode()
CURRENT_GIT_HASH = subprocess.check_output(["git", "rev-parse", "HEAD"]).strip().decode()
# Create one string containing all the information
VERSION_INFO = 'v' + __version__ + \
                  ', git branch: ' +  CURRENT_GIT_BRANCH + \
                  ', git hash: ' + CURRENT_GIT_HASH
### Use variable VERSION_INFO to track version ###

warnings.filterwarnings("ignore", category=DeprecationWarning)

extensions_for_oak_transfer = ['.nii', '.csv', '.xml', '.json', '.tiff', '.hdf5',
							   '.dat', '.log', '.txt',
							   ]
users_directory = pathlib.Path(parent_path, 'users')

def main(args):

	############################
	### Get target directory ###
	############################

	# user = args[0].lower().strip('"')
	# directory = args[1].strip('"')
	# full_target = os.path.join(root_directory, user, directory)
	# print("full target: {}".format(full_target))

	dir_to_process = args[0].lower().strip('"')
	#dir_to_process = os.path.normpath(dir_to_process)
	dir_to_process = pathlib.Path(dir_to_process)
	#user, directory = dir_to_process.split(os.sep)[1], dir_to_process.split(os.sep)[2]
	user, directory = dir_to_process.parts[-2], dir_to_process.parts[-1]
	print("Directory to process: {}".format(dir_to_process))

	#########################
	### Get user settings ###
	#########################

	#if user + '.json' in [x.lower() for x in os.listdir(users_directory)]:
	#	json_file = os.path.join(users_directory, user + '.json')
	#	with open(json_file) as file:
	#		settings = json.load(file)
	user_json_path = pathlib.Path(users_directory, user + '.json')
	print("user_json_path" + str(user_json_path))
	with open(user_json_path) as file:
		settings = json.load(file)

	oak_target = pathlib.Path(settings['oak_target'])
	print('oak_target ' + repr(oak_target))
	convert_to = settings['convert_to']
	#email = settings.get('email', False)


	add_to_build_que = utils.get_bool_from_json(settings, 'add_to_build_qeue')
	transfer_fictrac_bool = utils.get_bool_from_json(settings, "transfer_fictrac_bool")
	#split = settings.get('split', False)
	fly_json_from_h5 = utils.get_bool_from_json(settings, 'fly_json_from_h5')
	if fly_json_from_h5:
		fly_json_already_created = False
		# If there is a h5 file, it is possible to auto-assign loco data to
		# each experiment
		autotransfer_stimpack = utils.get_bool_from_json(settings,'autotransfer_stimpack')
		if autotransfer_stimpack:
			# User can define the 'slack' they want to have between start of stimpack
			# series and imaging series.
			max_diff_imaging_and_stimpack_start_time_second = float(
				settings.get('max_diff_imaging_and_stimpack_start_time_second', "60"))
	# If no h5 file, not possible to do autotransfer of stimpack data. Just define
	# variables as False and None
	else:
		autotransfer_stimpack = False
		max_diff_imaging_and_stimpack_start_time_second = None
	copy_SingleImage = utils.get_bool_from_json(settings,'copy_SingleImage')

	#################################
	### Convert from raw to tiffs ###
	#################################
	
	t0 = time.time()
	raw_to_tiff.convert_raw_to_tiff(dir_to_process)
	print("RAW TO TIFF DURATION: {} MIN".format(int((time.time()-t0)/60)))

	#########################################
	### Convert tiff to nii or tiff stack ###
	#########################################

	if convert_to == 'nii':
		tiff_to_nii.convert_tiff_collections_to_nii(directory=dir_to_process,
													brukerbridge_version_info=VERSION_INFO,
													fly_json_from_h5=fly_json_from_h5,
													fly_json_already_created=fly_json_already_created,
													autotransfer_stimpack=autotransfer_stimpack,
													max_diff_imaging_and_stimpack_start_time_second=max_diff_imaging_and_stimpack_start_time_second)
	elif convert_to == 'tiff':
		# NOT TESTED! LIKELY WONT WORK!
		tiffs_to_tiff_stack.convert_tiff_collections_to_stack(dir_to_process)
	else:
		print('{} is an invalid convert_to variable from user metadata.'.format(convert_to))
		print("Must be nii or tiff, with no period")

	#######################
	### Transfer to Oak ###
	#######################
	start_time = time.time()
	#size_transfered = transfer_to_oak.start_oak_transfer(directory_from=str(dir_to_process),
	#													 oak_target=oak_target,
	#													 allowable_extensions=extensions_for_oak_transfer,
	#													 add_to_build_que=add_to_build_que)

	transfer_to_oak.start_oak_transfer(root_path_name=dir_to_process.name,
													directory_from=dir_to_process,
													oak_target=oak_target,
													allowable_extensions=extensions_for_oak_transfer,
													add_to_build_que=add_to_build_que,
									   				copy_SingleImage=copy_SingleImage)
	print('OAK TRANSFER DURATION: {} MIN'.format(int((time.time()-start_time) / 60)))

	##############################
	### Transfer fictrac files ###
	##############################
	if transfer_fictrac_bool:
		try:
			transfer_fictrac.transfer_fictrac(user)
		except:
			print("-----------> FICTRAC TRANSFER FAILED <-----------")

	# ### Delete files locally
	# if delete_local:
	#     bridge.delete_local(full_target)

if __name__ == "__main__":
	main(sys.argv[1:])