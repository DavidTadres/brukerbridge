"""
called from main, calls 'ripper.bat'
Changed code to relative pathnames to work out of the box on other computers.
"""

import sys
import os
import subprocess
import pathlib
parent_path = str(pathlib.Path(pathlib.Path(__file__).parent.absolute()).parent.absolute())

def convert_raw_to_tiff(full_target):
	# Start ripper watcher, which will kill bruker conversion utility when complete
	print('Starting Ripper Watcher. Will watch {}'.format(full_target))
	#subprocess.Popen([sys.executable, 'C:/Users/User/projects/brukerbridge/scripts/ripper_killer.py', full_target])
	path_to_ripper_killer = pathlib.Path(parent_path, 'scripts/ripper_killer.py')
	subprocess.Popen([sys.executable, path_to_ripper_killer, full_target])

	# Start Bruker conversion utility by calling ripper.bat 
	print('Converting raw to tiff...')
	path_to_ribber_bat = pathlib.Path(parent_path, 'ripper.bat')
	#os.system("C:/Users/User/projects/brukerbridge/scripts/ripper.bat {}".format('"' + full_target + '"'))
	os.system(str(path_to_ribber_bat) + " {}".format('"' + str(full_target) + '"'))
