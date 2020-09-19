from socket import *
import os
import sys
import subprocess
import brukerbridge as bridge

CHUNKSIZE = 1_000_000
SERVER_HOST = "0.0.0.0"
SERVER_PORT = 5001
target_directory = "G:/"

# SERVER_HOST = ""
# SERVER_PORT = 5000
# target_directory = "/Users/lukebrezovec/projects/dataflow/dataflow/target"

sock = socket()
sock.bind((SERVER_HOST, SERVER_PORT))
sock.listen(1)

while True:
    print(f"[*] Listening as {SERVER_HOST}:{SERVER_PORT}")
    print("[*] Ready to receive files from Bruker client")
    client,address = sock.accept()

    print(f"[+] {address} is connected.")
    with client,client.makefile('rb') as clientfile:
        while True:
            raw = clientfile.readline()
            if not raw: break # no more files, server closed connection.

            filename = raw.strip().decode()
            length = int(clientfile.readline())
            print(f'Downloading {filename}...\n  Expecting {length:,} bytes...',end='',flush=True)

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
                    print('Complete')
                    continue
    # close the client socket
    client.close()

    # Launch main file processing
    #user, directory = filename.split('/')[0], filename.split('/')[1]
    filename = os.path.normpath(filename)
    user, directory = filename.split(os.sep)[0], filename.split(os.sep)[1]

    # make sure there is no email file left from aborted or failed processing rounds
    try:
        email_file = 'C:/Users/User/projects/brukerbridge/scripts/email.txt'
        os.remove(email_file)
    except:
        pass

    print("USER: {}".format(user))
    print("DIRECTORY: {}".format(directory))
    sys.stdout.flush()
    os.system("python C:/Users/User/projects/brukerbridge/scripts/main.py '{}' '{}'".format(user, directory))
    # added single quotes to accomidate spaces in directory name

    # email user informing of success or failure, and send relevant log file info
    os.system("python C:/Users/User/projects/brukerbridge/scripts/final_email.py")

# close the server socket
#sock.close()