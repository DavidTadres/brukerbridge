import os
import sys
import time
import subprocess
from time import strftime
import datetime
import brukerbridge as bridge

log_folder = 'C:/Users/User/Desktop/dataflow_logs'
root_directory = "H:/"

def main():

	age_limit = 60 # in days
	email = "brezovec@stanford.edu"
	error_info = "hello"
	#bridge.send_email(subject='BrukerBridge FAILED', message=error_info, recipient=email)

	#while True:
	for user_folder in os.listdir(root_directory):
		### need to skip this weird file
		if user_folder == 'System Volume Information':
			continue
		user_folder = os.path.join(root_directory, user_folder)

		if os.path.isdir(user_folder):
			for potential_old_folder in os.listdir(user_folder):
				potential_old_folder = os.path.join(user_folder, potential_old_folder)
				creation_time = os.path.getctime(potential_old_folder)
				age_in_seconds = time.time() - creation_time
				age_in_days = age_in_seconds/(60*60*24)
				if age_in_days > age_limit:
					print(F"{potential_old_folder}: {age_in_days}")

	#time.sleep(0.1)

if __name__ == '__main__':
	main()
