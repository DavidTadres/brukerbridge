"""
Idea is to use the stimpack created h5 file to create the fly.json file for a given experiment!

Problems:
1) I think it makes mroe sense to define " fly_dict['male_parental_line'] + '_x_' + fly_dict['female_parental_line']"
for the genotype! That'll allow me to unambigously define which flies were used for an experiment. Using 'driver' and
'effector' is not as clean as 'FS131_x_FS141' or even 'FS131_nsyb-gal4_x_FS141_UAS-GCaMP6f'.
2) It probably makes sense to keep the driver and effector and drop the info into the master_2p.xls file!
3) need to add additional info either in fly.json (i.e. circadian info) or per 'func' (maybe move temp of inline heater
as a experimental and not an animal property)
4) Unclear how to do 'functional_channel' and 'structural_channel'. It's concievable that I want only record from
channel 1 and 2 for the first experiment and from all 3 channels afterwards. If I implement this, need to adapt
snakebrainsss code! Maybe too much!

"""

import pathlib
import h5py

example_path = pathlib.Path('F:\\brukerbridge\\David\\20240213_fly1.hdf5')
target_path = pathlib.Path('F:\\brukerbridge\\David\\')

date = example_path.name[0:8]

# Read the file
h5file = h5py.File(example_path, 'r')

# list(f.keys())
# ['Notes', 'Subjects']

subjects = h5file['Subjects']

# While I usually don't have more than one subject per file, it's likely I'll change to keep everything tidy
for current_subject in subjects:
    fly_dict = {}

    for current_attrs in subjects[str(current_subject)].attrs:
        fly_dict[current_attrs] = subjects[str(current_subject)].attrs[current_attrs]

    # Save the dict, can use it to directly write the fly.json file as well!
    save_path = pathlib.Path(target_path, date, 'fly_' + fly_dict["subject_id"], 'fly.json')

    dict_for_json = {}
    dict_for_json['Sex'] = fly_dict['sex']
    dict_for_json['Genotype'] = fly_dict['male_parental_line'] + '_x_' + fly_dict['female_parental_line']
    dict_for_json['Age'] = fly_dict['age']




"""
fly_age = subjects["1"].attrs['age']
fly_sex = subjects["1"].attrs['sex']
fly_species = subjects["1"].attrs['species']
driver_1 = subjects["1"].attrs['driver_1']
driver_2 = subjects["1"].attrs['driver_2']
effector = subjects["1"].attrs['effector_1']
indicator_1 = subjects["1"].attrs['indicator_1']

"""


