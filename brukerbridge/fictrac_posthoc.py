"""
Logic to get fictrac working in command line
"""

import os
import pathlib

parent_path = str(pathlib.Path(pathlib.Path(__file__).parent.absolute()).parent.absolute())

path_to_fictrac_bat = pathlib.Path(parent_path, 'fictrac.bat')

full_target_win = pathlib.Path('B:\\brukerbridge\\David\\20250501__queue__\\fly1\\func0\\stimpack')
# https://stackoverflow.com/questions/69697757/how-to-remove-the-first-part-of-a-path
full_target_linux = '/mnt/b/' + full_target_win.relative_to(full_target_win.parts[0]).as_posix()

os.system(str(path_to_fictrac_bat)+ " {}".format('"' + str(full_target_linux) + '"'))

# To reach windows from inside WSL
# cd /mnt/b/brukerbridge/David/20250501__queue__/20250501_jackfish/fly1/3
# To run fictrac
# ~/fictrac/bin/fictrac config_CL.txt