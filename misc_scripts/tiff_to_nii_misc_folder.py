"""
After transfering data and ripping (i.e. using USB stick) want to
get a proper nii file for easy further downstream analysis of
misc recording (i.e. checking PMT activity in the dark).
"""

import pathlib
import sys

parent_path = str(pathlib.Path(pathlib.Path(__file__).parent.absolute()).parent.absolute())
print(parent_path)
sys.path.insert(0, parent_path)
from brukerbridge import tiff_to_nii

path_to_convert_to_nii = pathlib.Path('F:\\misc_bruker_data\\20240702\\fly999\\shutter_closed\\TSeries-12172018-1322-008')

tiff_to_nii.convert_tiff_collections_to_nii(directory=path_to_convert_to_nii,
                                            brukerbridge_version_info='N/A',
                                            fly_json_from_h5=False,
                                            fly_json_already_created=False,
                                            autotransfer_stimpack=False,
                                            max_diff_imaging_and_stimpack_start_time_second=60)