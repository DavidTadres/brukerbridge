__project__ = 'brukerbridge'
__version__ = '0.0.1'
__date__ = '2nd of June, 2024'

import sys
import warnings
import subprocess
import json
import time
import pathlib
from xml.etree import ElementTree as ET

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

extensions_for_oak_transfer = ['.nii',
							   '.csv',
							   '.xml', # Bruker xml files
							   '.json', # Snake_brainsss json files
							   #'.tiff', # Bruker images - seems to be unecessary (small images are .tif)
							   '.hdf5', # stimpack created h5 file
							   '.dat', # Fictrac data
							   '.log', # fictrac log
							   '.txt', # another fictrac log
							   '.avi', # fictrac video file
							   '.png', # fictrac_template.png
							   '.mp4', # fictrac video (if it exists)
							   #'.gz', # compressed files, for now (2025/05/25) that's nii.gz
							   # pathlib.Path.suffix, includes '.'
							   ]
print('Uploading files with these extensions to oak: ' + repr(extensions_for_oak_transfer))
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

	user_json_path = pathlib.Path(users_directory, user + '.json')
	print("user_json_path" + str(user_json_path))
	with open(user_json_path) as file:
		settings = json.load(file)

	oak_target = pathlib.Path(settings['oak_target'])
	print('oak_target ' + repr(oak_target))
	convert_to = settings['convert_to']
	#email = settings.get('email', False)

	add_to_build_que = utils.get_bool_from_json(settings, 'add_to_build_qeue')
	transfer_fictrac_bool = utils.get_bool_from_json(settings, "transfer_fictrac_bool") # Currently not used by David & Jacob, from Bella
	#split = settings.get('split', False)
	fly_json_from_h5 = utils.get_bool_from_json(settings, 'fly_json_from_h5')
	print("fly_json_from_h5" + repr(fly_json_from_h5))
	fly_json_already_created = False
	if fly_json_from_h5:

		# If there is a h5 file, it is possible to auto-assign loco data to
		# each experiment
		autotransfer_stimpack = utils.get_bool_from_json(settings,'autotransfer_stimpack')
		autotransfer_jackfish = utils.get_bool_from_json(settings, 'autotransfer_jackfish')
		if autotransfer_stimpack or autotransfer_jackfish:
			# User can define the 'slack' they want to have between start of stimpack
			# series and imaging series.
			max_diff_imaging_and_stimpack_start_time_second = float(
				settings.get('max_diff_imaging_and_stimpack_start_time_second', "60"))
		else:
			print('autotransfer_stimpack: ' + repr(autotransfer_stimpack))
			print('autotransfer_jackfish ' + repr(autotransfer_jackfish))
			max_diff_imaging_and_stimpack_start_time_second = None
	# If no h5 file, not possible to do autotransfer of stimpack data. Just define
	# variables as False and None
	else:
		autotransfer_stimpack = False
		autotransfer_jackfish = False
		max_diff_imaging_and_stimpack_start_time_second = None
	copy_SingleImage = utils.get_bool_from_json(settings,'copy_SingleImage')

	#################################
	### Convert from raw to tiffs ###
	#################################
	# New 2025/04/29:
	# Automatically detects what PVScan Version was used for recording
	# and calls that version

	
	t0 = time.time()
	# Find out what version of PV was used for the recording
	xml_paths = []
	def recursive_search(path):
		"""
		Recursive function to find xml file with identical name
		as the folder defining the large xml file Bruker writes which
		contains the PVScan version
		:param path:
		:return:
		"""
		for current_file in path.iterdir():
			if current_file.is_dir():
				recursive_search(current_file)
			else:
				# Check if the file/folder has xml extension
				if ('xml' in current_file.suffix and
						not 'Voltage' in current_file.name): # Might be necessary to add more if in the future
					# have the xml file, read it
					xml_paths.append(current_file)
					return()
	# Run recursive function, use list to keep track of xml_paths
	recursive_search(dir_to_process)
	tree = ET.parse(xml_paths[0])
	root = tree.getroot()
	PVScan_version = root.get('version') # i.e. '5.8.64.800'

	if PVScan_version == '5.8.64.800':
		print('DANGER WITH PV5.8!!!!')
		print('DONT PERFORM RIPPING ON THIS COMPUTER!')
		print('skipping ripping')
	elif PVScan_version == "5.8.64.814":
		print('DANGER WITH PV5.8!!!!')
		print('DONT PERFORM RIPPING ON THIS COMPUTER!')
		print('skipping ripping')
	else:
		raw_to_tiff.convert_raw_to_tiff(dir_to_process, PVScan_version)
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
													autotransfer_jackfish=autotransfer_jackfish,
													max_diff_imaging_and_stimpack_start_time_second=max_diff_imaging_and_stimpack_start_time_second,
													save_suffix='.nii')
	elif convert_to == 'nii.gz':
		tiff_to_nii.convert_tiff_collections_to_nii(directory=dir_to_process,
													brukerbridge_version_info=VERSION_INFO,
													fly_json_from_h5=fly_json_from_h5,
													fly_json_already_created=fly_json_already_created,
													autotransfer_stimpack=autotransfer_stimpack,
													autotransfer_jackfish=autotransfer_jackfish,
													max_diff_imaging_and_stimpack_start_time_second=max_diff_imaging_and_stimpack_start_time_second,
													save_suffix='.nii.gz')
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