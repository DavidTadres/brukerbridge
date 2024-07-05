"""
Copying data from imaging computer to oak is super slow.

Maybe copying the data directly from imaging computer to a local computer
is faster?
"""

import pathlib
import sys
parent_path = str(pathlib.Path(pathlib.Path(__file__).parent.absolute()).parent.absolute())
print(parent_path)
sys.path.insert(0, parent_path)
from brukerbridge import utils


ip = '171.65.18.54'
username = 'user'
passwd = input('Please enter password for ' + ip + ' for username ' + username + ': ')
# Please do not hardcode the password here as it'll be publicly available.

remote_root_path = pathlib.Path('F:/David').as_posix()
folder_to_copy='20240702'

local_target_path = pathlib.Path('F:\\misc_bruker_data')
utils.DownloadFolderFTP(ip, username, passwd,
                        remote_root_path=remote_root_path,
                        folder_to_copy=folder_to_copy,
                        local_target_path=local_target_path
                        )

# Using ftplib
import ftplib

ftp = ftplib.FTP(ip)
ftp.login(username, passwd)
