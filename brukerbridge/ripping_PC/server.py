import socket
import os
import sys
import time
from time import strftime
import pathlib

parent_path = str(pathlib.Path(pathlib.Path(__file__).parent.absolute()).parent.absolute().parent.absolute())
print(parent_path)
sys.path.insert(0, parent_path)
# This just imports '*.py' files from the folder 'brainsss'.
from brukerbridge import utils

verbose = False
CHUNKSIZE = 1_000_000
SERVER_HOST = "0.0.0.0"
SERVER_PORT = 5005
target_directory = pathlib.Path("F:/brukerbridge")

####
# SERVER_HOST = ""
# SERVER_PORT = 5000
# target_directory = "/Users/luke/Desktop/test_recieve"
####

sock = socket.socket()
sock.bind((SERVER_HOST, SERVER_PORT))
sock.listen(1)

# this while loop handles the server being ready for the next set of transfers
while True:

	print(f"[*] Listening as {SERVER_HOST}:{SERVER_PORT}", flush=True)
	print("[*] Ready to receive files from Bruker client", flush=True)
	print(strftime("%Y%m%d-%H%M%S"))

	client,address = sock.accept()
	print(f"[+] {address} is connected.", flush=True)
	print(strftime("%Y%m%d-%H%M%S"))

	do_checksums_match = []
	num_files_transfered = 0
	total_gb_transfered = 0
	with client,client.makefile('rb') as clientfile:

		# this while loop handles looping over files
		while True:

			if num_files_transfered == 0:
				source_directory_size = int(float(clientfile.readline().strip().decode()))
				total_num_files = int(clientfile.readline().strip().decode())
				start_time = time.time()
				print(F"FIRST LOOP START TIME: {start_time}",flush=True)

			raw = clientfile.readline()

			### This is what will finally break the loop when this message is received ###
			if raw.strip().decode() == "ALL_FILES_TRANSFERED":

				print('ALL_FILES_TRANSFERED', flush=True)
				all_checksums_true = False not in do_checksums_match
				message = str(len(do_checksums_match)) + "." + str(all_checksums_true)
				client.sendall(message.encode())
				break

			filename = raw.strip().decode()
			length = int(clientfile.readline()) # don't need to decode because casting as int
			size_in_gb = length*10**-9
			checksum_original = str(clientfile.readline().strip().decode())

			if verbose: print(f'Downloading {filename}...\n  Expecting {length:,} bytes...',end='',flush=True)

			path = pathlib.Path(target_directory, filename)
			path.parent.mkdir(parents=True, exist_ok=True)
			## Original ##
			#path = os.path.join(target_directory,filename)
			#os.makedirs(os.path.dirname(path),exist_ok=True)

			# Read the data in chunks so it can handle large files.
			with open(path,'wb') as f:
				while length:
					chunk = min(length,CHUNKSIZE)
					data = clientfile.read(chunk)
					if not data:
						break
					f.write(data)
					length -= len(data)
				else: # only runs if while doesn't break and length==0
					if verbose: print('Complete', end='', flush=True)

			checksum_copy = utils.get_checksum(path)

			if checksum_original == checksum_copy:
				if verbose: print(' [CHECKSUMS MATCH]', flush=True)
				do_checksums_match.append(True)

			else:
				print('!!!!!! WARNING CHECKSUMS DO NOT MATCH - ABORTING !!!!!!', flush=True)
				do_checksums_match.append(False)
				raise SystemExit

			num_files_transfered += 1
			total_gb_transfered += size_in_gb

			######################
			### Print Progress ###
			######################
			utils.print_progress_table(start_time=start_time,
										current_iteration=num_files_transfered,
										total_iterations=total_num_files,
										current_mem=int(total_gb_transfered),
										total_mem=source_directory_size,
                                        mode='server')

			continue

	print(F'all_checksums_true is {all_checksums_true}', flush=True)

	try:
		print('{} min duration, with average transfer speed {:2f} MB/sec'.format(int((time.time()-start_time)/60), source_directory_size * 1000 / (time.time() - start_time)))
	except ZeroDivisionError:
		print('zero error... ?', flush=True)
		print(F"start time: {start_time}", flush=True)
		current_time = time.time()
		print(F"current time: {current_time}", flush=True)
		print(F"time minus start time: {current_time-start_time}", flush=True)

	# This is not correct anymore!
	#dir_to_flag = '\\'.join(path.split('\\')[:2])

	# pathlib.Path(path).relative_to(target_directory)
	# if path = WindowsPath('F:/brukerbridge/David/20240404__queue__/fly3/anat0/TSeries-12172018-1322-002')
	# and target_directory = WindowsPath('F:/brukerbridge')
	# pathlib.Path(path).relative_to(target_directory)
	# would yield i.e. WindowsPath('David/20240404__queue__/fly3/anat0/TSeries-12172018-1322-002')
	dir_to_flag = pathlib.Path(path).relative_to(target_directory).parts[1]

	full_path = pathlib.Path(target_directory, dir_to_flag)

	#print(dir_to_flag, flush=True)
	#os.rename(dir_to_flag, dir_to_flag + '__queue__')
	print(full_path, flush=True)
	os.rename(full_path, pathlib.Path(str(full_path) + '__queue__'))

	# close the client socket
	client.close()
	# Now the server will return to the beginning of the while loop and is ready for next transfer



	# # Launch main file processing
	# filename = os.path.normpath(filename)
	# user, directory = filename.split(os.sep)[0], filename.split(os.sep)[1]

	# # make sure there is no email file left from aborted or failed processing rounds
	# try:
	#     email_file = 'C:/Users/User/projects/brukerbridge/scripts/email.txt'
	#     os.remove(email_file)
	# except:
	#     pass

	# print("USER: {}".format(user), flush=True)
	# print("DIRECTORY: {}".format(directory), flush=True)
	# #print("LOGFILE: {}".format(full_log_file), flush=True)
	# sys.stdout.flush()
	# os.system('python C:/Users/User/projects/brukerbridge/scripts/main.py "{}" "{}"'.format(user, directory))
	# # added double quotes to accomidate spaces in directory name

	# # email user informing of success or failure, and send relevant log file info
	# os.system("python C:/Users/User/projects/brukerbridge/scripts/final_email.py")

	# close the server socket
	#sock.close()
