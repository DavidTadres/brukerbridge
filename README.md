# brukerbridge
This boutique package is used to make processing Bruker output files more convenient by automating several steps:
- Transfer of files from Bruker computer to "workhorse" computer in D217
- Conversion of Bruker Raw files to Tiffs
- Conversion of single tiff files to desired format (.nii, .tif stack)
- Upload of files to desired Oak (our lab's data storage) directory

How do I use it?
- New users must add their preferences on the bridge computer in D217 (this only needs to be done once)
  - navigate to C:\Users\User\projects\brukerbridge\users
  - each user has a .json file. Simply copy an existing user file, rename the file with your name, and adjust the preferences as desired
- When you are done with imaging for the day, simply double click the shortcut icon on the Bruker desktop "brukerbridge.bat". You will be prompted to select the folder you want to process. Upon selection, a terminal window will open and begin printing file transfer progress. Now, all you have to do is wait for the processing steps to complete.
- The pipeline assumes your Bruker directory will be located as Drive:\user\DIR, ie
  1. your username should be at the root of the drive, and 
  2. the directory you want to process must have your user directory as it's immediate parent, and
  3. your username must match the name of the .json preferences file created on the bridge computer
- When collecting bruker data, do not automatically convert to tif, since they take forever to transfer - the pipeline wants bruker raw files. This setting is in Prairie View Preferences/Automatically Convert Raw Files/Never
- To implement a queue, brukerbridge now consists of two main loops.
	1) server.py - this should always be running but if it hit an error you can restart it from the desktop shortcut LAUNCH SERVER.
	the server's only job is to transfer files from the bruker computer to the bridge computer. 

Some more details:
- The sub-directory structure of the directory you select for processing will be retained
- All files will be transfered (including Bruker .xml files, any .csv files for Voltage Recording or Output)
- Files will be automatically deleted from the bruker computer once they are transfered, as long as all files pass checksum (confirms that they are not corrupted).
- Currently, the pipeline makes separate nii files for each color channel imaged. Multichannel-support could be easily implemented, but may not work on large files due to memory constraints on workhorse computer.
- Bi-directional scans are correctly identified and parsed
- Single-plane imaging is supported.

Current user preferences:
- oak_target - upload directory on Oak
- convert_to - must be "nii" or "tiff"
- email - will send success or failure message here
- add_to_build_que - "False" unless you know otherwise
- transfer_fictrac - will transfer fictrac files from fictrac computer above bruker

Troubleshooting:
- failed connection error when running brukerbridge.bat?
    - There is a python server running on the workhorse computer that waits to recieve info from Bruker computer. This server must be running. A terminal should be open and say "Ready to recieve files from Bruker client." If this is not running, you must start the server by navigating to "C:\Users\User\projects\brukerbridge\brukerbridge" and running python server.py on the command line.
