from socket import *
import os
import sys
import subprocess
import brukerbridge as bridge
import time
from time import strftime

verbose = False
CHUNKSIZE = 1_000_000
SERVER_HOST = "0.0.0.0"
SERVER_PORT = 5001
target_directory = "H:/"

####
# SERVER_HOST = ""
# SERVER_PORT = 5000
# target_directory = "/Users/luke/Desktop/test_recieve"
####

sock = socket()
sock.bind((SERVER_HOST, SERVER_PORT))
sock.listen(1)

while True:

	print(f"[*] Listening as {SERVER_HOST}:{SERVER_PORT}", flush=True)
	print("[*] Ready to receive files from Bruker client", flush=True)
	client,address = sock.accept()

	log_folder = 'C:/Users/User/Desktop/dataflow_logs'
	log_file = 'dataflow_log_' + strftime("%Y%m%d-%H%M%S") + '.txt'
	full_log_file = os.path.join(log_folder, log_file)
	# sys.stdout = open(full_log_file, 'a')
	# sys.stderr = open(full_log_file, 'a')

	print(f"[+] {address} is connected.", flush=True)

	do_checksums_match = []

	first_loop = True
	num_files_transfered = 0 
	total_gb_transfered = 0
	with client,client.makefile('rb') as clientfile:

	    while True:

	        if first_loop:
	            source_directory_size = int(float(clientfile.readline().strip().decode()))
	            total_num_files = clientfile.readline().strip().decode()

	        raw = clientfile.readline()

	        ### This is what will finally break the loop when this message is recieved ###
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

	        path = os.path.join(target_directory,filename)
	        os.makedirs(os.path.dirname(path),exist_ok=True)

	        # Read the data in chunks so it can handle large files.
	        with open(path,'wb') as f:
	            while length:
	                chunk = min(length,CHUNKSIZE)
	                data = clientfile.read(chunk)
	                if not data: break
	                f.write(data)
	                length -= len(data)
	            else: # only runs if while doesn't break and length==0
	                if verbose: print('Complete', end='', flush=True)

	        checksum_copy = bridge.get_checksum(path)

	        if checksum_original == checksum_copy:
	            if verbose: print(' [CHECKSUMS MATCH]', flush=True)
	            do_checksums_match.append(True)

	        else:
	            print('!!!!!! WARNING CHECKSUMS DO NOT MATCH - ABORTING !!!!!!', flush=True)
	            do_checksums_match.append(False)
	            raise SystemExit

	        num_files_transfered += 1
	        total_gb_transfered += size_in_gb

	        ##########################
	        ### Print Progress Bar ###
	        ##########################

	        bar_length = 80
	        if not first_loop:
	            #print('\r', end='', flush=True) # Carriage return
	           	print("\r", flush=True) # Carriage return

	        bar_string = bridge.progress_bar(int(total_gb_transfered), source_directory_size, bar_length)
	        vol_frac_string = "{:0{}d} {} Files".format(num_files_transfered, len(str(total_num_files)), total_num_files)
	        mem_frac_string = "{:0{}d} {} GB".format(int(total_gb_transfered), len(str(source_directory_size)), source_directory_size)
	        full_string = vol_frac_string + ' ' + bar_string + ' ' + mem_frac_string
	        
	        print("\r\r\r" + full_string + "\r\r\r", end='', flush=True)
	        # print("\r", flush=True)

	        first_loop = False
	        continue
	# break ## REMOVE <---------------------------

	print(F'all_checksums_true is {all_checksums_true}', flush=True)

	# close the client socket
	client.close()

	# Launch main file processing
	filename = os.path.normpath(filename)
	user, directory = filename.split(os.sep)[0], filename.split(os.sep)[1]

	# make sure there is no email file left from aborted or failed processing rounds
	try:
	    email_file = 'C:/Users/User/projects/brukerbridge/scripts/email.txt'
	    os.remove(email_file)
	except:
	    pass

	print("USER: {}".format(user), flush=True)
	print("DIRECTORY: {}".format(directory), flush=True)
	print("LOGFILE: {}".format(full_log_file), flush=True)
	sys.stdout.flush()
	os.system('python C:/Users/User/projects/brukerbridge/scripts/main.py "{}" "{}" "{}"'.format(user, directory, full_log_file))
	# added double quotes to accomidate spaces in directory name

	# email user informing of success or failure, and send relevant log file info
	os.system("python C:/Users/User/projects/brukerbridge/scripts/final_email.py")

	# close the server socket
	#sock.close()