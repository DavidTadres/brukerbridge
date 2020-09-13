# brukerbridge
This boutique package is used to make processing Bruker output files more convenient by automating several steps:
- Transfer of files from Bruker computer to "workhorse" computer in D217
- Conversion of Bruker Raw files to Tiffs
- Conversion of single tiff files to desired format (.nii, .tif stack)
- Upload of files to desired Oak (our lab's data storage) directory

How do I use it?
- New users must add their preferences on the workhorse computer in D217
  - navigate to C:\Users\User\projects\brukerbridge\users
  - each user has a .json file. Simply copy an existing user file, rename the file with your name, and adjust the preferences as desired
- When you are done with imaging for the day, simply double click the shortcut icon on the Bruker desktop "brukerbridge.bat". You will be prompted to select the folder you want to process. Upon selection, a terminal window will open and begin printing file transfer progress. Now, all you have to do is wait for the processing steps to complete. You will be notified via email upon success or failure of the pipeline.

Some more details:
- The pipeline assumes your Bruker directory will be located as drive:\user\DIR, ie
  1. your username should be at the root of the drive, and 
  2. the directory you want to process must have your user directory as it's immediate parent
- This pipeline will retain the sub-directory structure of the directory you select for processing.
- 
