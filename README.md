# brukerbridge
This boutique package is used to make processing Bruker output files more convenient by automating several steps:
- Transfer of files from Bruker computer to "workhorse" computer in D217
- Conversion of Bruker Raw files to Tiff avalanche
- Conversion of single tiff files to desired format (.nii, .tif stack)
- Upload of files to desired Oak (our lab's data storage) directory

How do I use it?
- New users MUST add their preferences on the workhorse computer
  - navigate to C:\Users\User\projects\brukerbridge\users
  - each user has a .json file. Simply copy an existing user file, rename the file with your name, and adjust the preferences as desired
