# Brukerbridge (David's fork)

## Overview

**Brukerbridge** is an automated pipeline for processing **Bruker two-photon microscopy** imaging data in a distributed, multi-computer lab environment (Stanford TRC lab). It handles the full lifecycle from raw acquisition to processed neuroimaging files on network storage.

### Core Workflow

1. **Transfer** — User on the Bruker imaging PC selects a scan folder via GUI. A socket-based client sends all files (with MD5 checksums) to a processing/ripping PC.
2. **Raw → TIFF** — Calls Bruker's "Image-Block Ripping Utility" to convert proprietary raw files to TIFFs.
3. **TIFF → NIfTI** — Converts TIFF stacks into `.nii.gz` neuroimaging format, handling volumetric scans, multiple channels, bidirectional Z-scanning, and voxel metadata from XML.
4. **Upload to Oak** — Copies processed files to Stanford's Oak network storage (`//oak-smb-trc.stanford.edu/...`).
5. **Optional: FicTrac/Stimpack** — Downloads behavioral tracking data (FicTrac `.dat`/`.log` files) and experimental metadata (stimpack HDF5) from separate computers, and auto-generates `fly.json` metadata.

### Architecture

- **Client** (`Imaging_PC/*_client.py`) — Runs on the Bruker PC, sends files over TCP (port 5005).
- **Server** (`ripping_PC/*_server.py`) — Receives files, appends `__queue__` flag to directories.
- **Queue Watcher** (`users/*/queue_watcher.py`) — Continuously polls for queued directories, launches `scripts/main.py` for each.
- **Ripper Killer** (`scripts/ripper_killer.py`) — Monitors the Bruker ripper process and kills it once done (it doesn't exit on its own).

### Key Design Features

- **Multi-user** — Per-user JSON configs in `users/` (oak paths, output format, stimpack settings).
- **Multi-version** — Detects Prairie View version (5.5, 5.8.x, 5.8.9) from XML and adjusts ripper paths accordingly.
- **Data integrity** — MD5 checksums on transfer, file-size deduplication on upload.
- **Memory-efficient** — Chunked processing for large image stacks.
- **Error handling** — Detects aborted scans, logs failures, email notifications, `__error__` flags on failed directories.

### Key Files

| File | Purpose |
|---|---|
| `scripts/main.py` | Main orchestrator |
| `brukerbridge/utils.py` | Utilities (~1200 lines): checksums, email, FTP, metadata |
| `brukerbridge/tiff_to_nii.py` | TIFF→NIfTI conversion engine (~730 lines) |
| `brukerbridge/raw_to_tiff.py` | Wrapper around Bruker's ripper CLI |
| `brukerbridge/transfer_to_oak.py` | Network storage upload |
| `brukerbridge/transfer_fictrac.py` | FicTrac behavioral data FTP transfer |
| `users/David/David.json` | User config (oak path, output format, etc.) |

##
Installation
##

make environment:

Install Git https://git-scm.com/downloads

clone the repo:

`git clone https://github.com/davidtadres/brukerbridge`

create and activate the virtual environment (run from inside the cloned repo):

`cd brukerbridge`

`python -m venv env_brukerbridge`

`env_brukerbridge\Scripts\activate`

install dependencies:

`pip install numpy nibabel matplotlib tqdm psutil scikit-image ftputil h5py`

`pip install git+https://github.com/davidtadres/anatomical_orientation.git`

`pip install git+https://github.com/DavidTadres/bruker_ultima_utils.git`

changed windows defender settings on ripping PC: 
https://stackoverflow.com/questions/53231849/python-socket-windows-10-connection-times-out

1) Make a copy of the file 'blueprint.json' in folder `\users'. Change settings as desired

2) Make a copy of file 'blueprint_client.py' in folder 'Imaging PC' and call it YOURNAME_client.py.

   Then change the "host_IP" to the IP of the ripping computer and the 'user_json' variable to the name of your user file
   in 'users\'.

3) Make copy of file 'blueprint_server.py' and name it YOURNAME_server.py

   In that file, in line 10 change the 'target_directory' variable to where on your ripping PC you want the ripping
   to take place (Lots of space, ideally an SSD for speed). 

4) Create a folder with your name in folder 'users' and copy the files from folder 'blueprint' into that folder.  

   a) 'blueprint_brukerbridge.bat' will be used on the Bruker imaging computer. You need to change it such 
      that it points to the client.pyfile you created before. For example for David would say 
      `%mypath:~0,-13%\brukerbridge\Imaging_PC\david_client.py`.

      It is strongly adviced to rename the file to something unique so that no-one except you uses this link to send
      data to your computer!

      Note that the number after %mypath:~0 refers to the number of charaters to go 'back up' to the root path.
      For example, david needs to go from '../brukerbridge/users/David/' to '../brukerbridge' and remove '/users/David/'
      which is exactly 13 characters.

   b) 'launch_queue_watcher.bat' and 'launch_server.bat' automatically activate the virtual environment
      relative to the repo root. You only need to update the character count in `%mypath:~0,-XX%` to match
      your folder name length. The number XX should equal the length of `\users\YOURNAME\` (including both
      backslashes). For example, `\users\David\` is 13 characters, `\users\blueprint\` is 17 characters.

   e) 'queue_wacher.py', change 'log_folder' and 'root_directory' (where the ripping on your PC happens) as desired