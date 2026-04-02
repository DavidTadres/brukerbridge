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

- **Client** (`Imaging_PC/client.py`) — Runs on the Bruker PC, sends files over TCP (port 5005). Takes user name as argument.
- **Server** (`ripping_PC/server.py`) — Receives files, appends `__queue__` flag to directories. Takes user name as argument.
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

### Adding a new user

1) **Create your user JSON.** Copy `users/blueprint.json` to `users/YOURNAME.json` and fill in the settings:

   | Field | Description | Example |
   |---|---|---|
   | `host_IP` | IP address of your ripping PC | `"171.65.16.149"` |
   | `initial_browse_dir` | Starting folder for the file browser on the imaging PC | `"E:/"` |
   | `server_target_directory` | Where received files are written on the ripping PC (ideally a fast SSD with lots of space) | `"B:/brukerbridge"` |
   | `oak_target` | Your Oak network storage path | `"//oak-smb-trc.stanford.edu/groups/trc/data/YOURNAME/Bruker/imports"` |
   | `convert_to` | Output format: `"nii"` or `"nii.gz"` | `"nii.gz"` |
   | `fly_json_from_h5` | Create fly.json from stimpack h5 file | `"True"` or `"False"` |
   | `stimpack_h5_path` | Path to stimpack h5 files on imaging PC (optional) | `"E:/YOURNAME/stimpack_data"` |
   | `stimpack_data_path` | Remote path to stimpack/fictrac data on the fictrac computer (optional) | `"../../data/YOURNAME/stimpack_data/fictrac"` |
   | `autotransfer_stimpack` | Auto-download stimpack data from fictrac computer | `"True"` or `"False"` |
   | `autotransfer_jackfish` | Auto-download Jackfish video data (optional) | `"True"` or `"False"` |
   | `jackfish_data_path` | Remote path to Jackfish data (only needed if above is True) | `"../../data/YOURNAME/jackfish"` |
   | `max_diff_imaging_and_stimpack_start_time_second` | Max time difference (seconds) to match stimpack to imaging | `"120"` |
   | `copy_SingleImage` | Copy SingleImage folders to Oak | `"True"` or `"False"` |
   | `imaging_orientation` | Anatomical orientation code | `"LSP"` |

2) **Create your user folder.** Copy `users/blueprint/` to `users/YOURNAME/` and edit the `.bat` files inside:

   a) **`blueprint_brukerbridge.bat`** → rename to `YOURNAME_brukerbridge.bat`. This is the shortcut used on
      the Bruker imaging PC. Change it to call `client.py` with your name:
      ```
      python "%reporoot%\brukerbridge\Imaging_PC\client.py" YOURNAME
      ```
      Update the character count in `%mypath:~0,-XX%` so it resolves to the repo root.
      XX = length of `\users\YOURNAME\` (including both backslashes).
      For example: `\users\David\` = 13, `\users\Mikaela\` = 16, `\users\blueprint\` = 17.

   b) **`launch_server.bat`** runs on the ripping PC. Change it to call `server.py` with your name:
      ```
      python "%reporoot%\brukerbridge\ripping_PC\server.py" YOURNAME
      ```
      Update the character count the same way as above. Also update the log path to point to
      a log directory on your ripping PC.

   c) **`launch_queue_watcher.bat`** — update the character count the same way as above.

   d) **`queue_watcher.py`** — change `log_folder` and `root_directory` to match your ripping PC paths.
      `root_directory` should match the `server_target_directory` in your JSON.