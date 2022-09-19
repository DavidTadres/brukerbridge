import os
import sys
import time
import subprocess
from time import strftime
import datetime
import brukerbridge as bridge
import numpy as np
import json

log_folder = 'C:/Users/User/Desktop/dataflow_logs'
users_directory = "C:/Users/User/projects/brukerbridge/users"
root_directory = "H:/"

def main():

	print("HELLO I AM THE OLD DATA TROLL")

	age_limit = 60 # in days
	exception_folders = ['fictrac', '$RECYCLE.BIN']
	exception_flag = "_old_"

	#while True:
	users_with_old_files = []
	old_files = []
	for user_folder in os.listdir(root_directory):
		### need to skip this weird file
		if user_folder == 'System Volume Information':
			continue
		if user_folder in exception_folders:
			continue

		user = user_folder
		user_folder = os.path.join(root_directory, user_folder)
		print(user_folder)

		if os.path.isdir(user_folder):
			print("hi1")
			for potential_old_folder in os.listdir(user_folder):
				print("hi2")
				if os.path.isdir(potential_old_folder):
					print("hi3")
					potential_old_folder = os.path.join(user_folder, potential_old_folder)
					creation_time = os.path.getctime(potential_old_folder)
					age_in_seconds = time.time() - creation_time
					age_in_days = age_in_seconds/(60*60*24)
					print(F"{potential_old_folder}: {age_in_days}")
					if age_in_days > age_limit and exception_flag not in potential_old_folder:
						print(F"{potential_old_folder}: {age_in_days}")
						users_with_old_files.append(user)
						old_files.append(potential_old_folder)

	for user in np.unique(users_with_old_files):
		json_file = os.path.join(users_directory, user + '.json')
		try:
			with open(json_file) as file:
				settings = json.load(file)
				email = settings.get('email')
		except:
			print(F"{user} has no json file to get email from. they should create one in {users_directory}")
			continue

		users_old_files = np.asarray(old_files)[np.where(user==np.asarray(users_with_old_files))[0]]
		print(users_old_files)

		message = F"You have the following old directories (older than {age_limit} days):\n {users_old_files}"
		if user == 'luke':
			bridge.send_email(subject='BrukerBridge Old Data Troll Says Hello!', message=message, recipient=email)


		#time.sleep(100)

if __name__ == '__main__':
	main()
