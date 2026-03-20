# Mikaela Onboarding TODO

## 1. Install environment on ripping PC

- Install Git: https://git-scm.com/downloads
- Install Miniconda: https://conda.io/miniconda.html
- Clone the repo: `git clone https://github.com/davidtadres/brukerbridge`
- Create and set up conda environment:
  ```
  conda create -n env_brukerbridge
  activate env_brukerbridge
  conda install python=3.8
  conda install numpy nibabel matplotlib scikit-image h5py
  conda install conda-forge::tqdm conda-forge::psutil conda-forge::ftputil
  ```
- Change Windows Defender settings to allow socket connections:
  https://stackoverflow.com/questions/53231849/python-socket-windows-10-connection-times-out

## 2. Fill in placeholders

All placeholder values are marked with `PLACEHOLDER_` in the files listed below.

### `users/Mikaela.json`
- [ ] `PLACEHOLDER_OAK_PATH` — Oak storage path (e.g. `//oak-smb-trc.stanford.edu/groups/trc/data/Mikaela/Bruker/imports`)
- [ ] `PLACEHOLDER_STIMPACK_H5_PATH` — Path to stimpack HDF5 files on the imaging PC (e.g. `E:/Mikaela/stimpack_data`)
- [ ] `PLACEHOLDER_STIMPACK_DATA_PATH` — Relative path to stimpack fictrac data on the FTP server
- [ ] `PLACEHOLDER_JACKFISH_DATA_PATH` — Relative path to jackfish data on the FTP server

### `brukerbridge/Imaging_PC/mikaela_client.py`
- [ ] `PLACEHOLDER_RIPPING_PC_IP` — IP address of the ripping PC (run `ipconfig` in a terminal on the ripping PC and look for the IPv4 Address)

### `brukerbridge/ripping_PC/mikaela_server.py`
- [ ] `PLACEHOLDER_RIPPING_DIRECTORY` — Local directory on ripping PC for data processing (e.g. `F:/brukerbridge`). Needs lots of space, ideally on an SSD.

### `users/Mikaela/queue_watcher.py`
- [ ] `PLACEHOLDER_LOG_PATH` — Directory for log files (e.g. `C:\Users\Mikaela\Desktop\brukerbridge_datalogs`)
- [ ] `PLACEHOLDER_RIPPING_DIRECTORY` — Same ripping directory as in mikaela_server.py above

### `users/Mikaela/launch_server.bat`
- [ ] `PLACEHOLDER_PYTHON_EXE_PATH` — Full path to python.exe in conda env (e.g. `C:\Users\Mikaela\.conda\envs\env_brukerbridge\python.exe`)
- [ ] `PLACEHOLDER_LOG_PATH` — Same log directory as in queue_watcher.py above

### `users/Mikaela/launch_queue_watcher.bat`
- [ ] `PLACEHOLDER_PYTHON_EXE_PATH` — Same python.exe path as in launch_server.bat above

## 3. Create directories
- [ ] Create the ripping directory on the ripping PC (e.g. `F:\brukerbridge`)
- [ ] Create the log directory on the ripping PC (e.g. `C:\Users\Mikaela\Desktop\brukerbridge_datalogs`)

## 4. Test
- [ ] Start the server: double-click `users/Mikaela/launch_server.bat` on the ripping PC
- [ ] Start the queue watcher: double-click `users/Mikaela/launch_queue_watcher.bat` on the ripping PC
- [ ] Run `users/Mikaela/mikaela_brukerbridge.bat` on the Bruker imaging PC and test a transfer
