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

	email = "brezovec@stanford.edu"
	error_info = "hello"
	bridge.send_email(subject='BrukerBridge FAILED', message=error_info, recipient=email)

	# while True:
	# 	for user_folder in os.listdir(root_directory):
	# 		### need to skip this weird file
	# 		if user_folder == 'System Volume Information':
	# 			continue
	# 		user_folder = os.path.join(root_directory, user_folder)

	# 		if os.path.isdir(user_folder):
	# 			for potential_old_folder in os.listdir(user_folder):

	# 	time.sleep(0.1)

if __name__ == '__main__':
	main()
