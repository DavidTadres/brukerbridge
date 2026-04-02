"""
Unified Bruker ripping PC server.

Usage:
    python server.py <username>

Where <username> matches a JSON file in the users/ directory (e.g. "David" -> users/David.json).
The user's JSON must contain:
    - server_target_directory: path where received files are written on the ripping PC
"""

import socket
import os
import sys
import time
from time import strftime
import pathlib
import json

parent_path = str(pathlib.Path(pathlib.Path(__file__).parent.absolute()).parent.absolute().parent.absolute())
sys.path.insert(0, parent_path)
from brukerbridge import utils

##########################
### Parse user argument ###
##########################

if len(sys.argv) < 2:
    print("Usage: python server.py <username>")
    print("Example: python server.py David")
    sys.exit(1)

user_name = sys.argv[1]
json_path = pathlib.Path(parent_path, 'users', user_name + '.json')
if not json_path.exists():
    print(f"User config not found: {json_path}")
    sys.exit(1)

with open(json_path) as f:
    user_settings = json.load(f)

target_directory = pathlib.Path(user_settings['server_target_directory'])

verbose = False
CHUNKSIZE = 1_000_000
SERVER_HOST = "0.0.0.0"
SERVER_PORT = 5005

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

			if verbose:
				print(f'Downloading {filename}...\n  Expecting {length:,} bytes...',end='',flush=True)

			path = pathlib.Path(target_directory, filename)
			path.parent.mkdir(parents=True, exist_ok=True)

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

	# Extract user folder and date directory from received file path
	# e.g. path = 'B:/brukerbridge/David/20240404/fly3/anat0/TSeries-...'
	# relative to target_directory gives 'David/20240404/fly3/...'
	user_folder = pathlib.Path(path).relative_to(target_directory).parts[0]
	dir_to_flag = pathlib.Path(path).relative_to(target_directory).parts[1]

	full_path = pathlib.Path(target_directory, user_folder, dir_to_flag)

	print(full_path, flush=True)
	os.rename(full_path, pathlib.Path(str(full_path) + '__queue__'))

	# close the client socket
	client.close()
	# Now the server will return to the beginning of the while loop and is ready for next transfer
