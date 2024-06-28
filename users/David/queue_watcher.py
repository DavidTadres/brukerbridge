import time
import subprocess
from time import strftime
import pathlib

parent_path = str(pathlib.Path(pathlib.Path(__file__).parent.absolute()).parent.absolute().parent.absolute())
print(parent_path)

# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
log_folder = pathlib.Path('C:\\Users\\David\\Desktop\\brukerbridge_datalogs')
root_directory = pathlib.Path("F:\\brukerbridge")
# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<

def main():

	#banned_dirs = get_banned_dirs()
	while True:
		queued_folder, stripped_folder = get_queued_folder()
		if queued_folder is not None:
			launch_main_processing(queued_folder, stripped_folder, log_folder)
		time.sleep(0.1)

def get_queued_folder():
	low_queue = None
	stripped_dir = None
	for user_folder in root_directory.iterdir():
		### need to skip this weird file
		if user_folder == 'System Volume Information':
			continue
		#user_folder = os.path.join(root_directory, user_folder)

		#if os.path.isdir(user_folder):
		for potential_queued_folder in user_folder.iterdir():
			#for potential_queued_folder in os.listdir(user_folder):
			#potential_queued_folder = os.path.join(user_folder, potential_queued_folder)

			#if potential_queued_folder.endswith('__queue__'):
			if '__queue__' in potential_queued_folder.name:
				#stripped_dir = potential_queued_folder[:-9] # This returns the path without the '__queue__' string
				stripped_dir = pathlib.Path(str(potential_queued_folder).split('__queue__')[0])
				return(potential_queued_folder, stripped_dir) ### Immediately return any queued folder found

			#if potential_queued_folder.endswith('__lowqueue__'):
			if '__lowqueue__' in potential_queued_folder.name:
				low_queue = potential_queued_folder

	if low_queue is not None:
		stripped_dir = low_queue[:-12]
	return(low_queue, stripped_dir)

"""
def get_banned_dirs():
	banned_dir = 'C:/Users/User/projects/brukerbridge/banned_dirs'
	return os.listdir(banned_dir)
"""

def attempt_rename(source, target):
	print(F'Attemping rename {source} to {target}')
	attempts = 3
	while attempts > 0:
		attempts-=1
		try:
			# works because source is a pathlib.Path object
			source.rename(target)
			#os.rename(source, target)
			print(F'Rename successful {source} to {target}')
			return
		except Exception as e:
			print(F"Rename attempt {attempts} failed")
			print('\n Error message:')
			print(e)
			print('\n\n')
			time.sleep(60)

def launch_main_processing(dir_to_process, stripped_folder, log_folder):
	log_file = 'dataflow_log_' + strftime("%Y%m%d-%H%M%S") + '.txt'
	#full_log_file = os.path.join(log_folder, log_file)
	full_log_file = pathlib.Path(log_folder, log_file)

	# the >> redirects stdout with appending. the 2>&1 does the same with stderr
	# double quotes to accommodates spaces in directory name
	# this command is blocking so this watcher will just wait here until main.py is finished
	print(F"launching {dir_to_process}")
	print(F"log file {full_log_file}")

	f = open(full_log_file, 'w')
	# path to scripts/main.py
	main_py_path = pathlib.Path(parent_path, 'scripts/main.py')
	exit_status = subprocess.call(['python', str(main_py_path), dir_to_process],stdout=f,stderr=f)

	#stderr=subprocess.STDOUT
	if exit_status != 0:
		print("ERROR! Appending __error__ to this folder, then continuing with next in queue.")

		attempt_rename(dir_to_process, pathlib.Path(str(stripped_folder) + "__error__"))
		#raise SystemExit
	else:
		attempt_rename(dir_to_process, pathlib.Path(str(stripped_folder))) # having trouble with removing queue

	#os.system('python C:/Users/User/projects/brukerbridge/scripts/main.py "{}" >> {} 2>&1'.format(dir_to_process, full_log_file))
	#time.sleep(5)

if __name__ == '__main__':
	main()
