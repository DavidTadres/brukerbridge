# Brukerbridge (David's fork)

## Overview

**Brukerbridge** is an automated pipeline for processing **Bruker two-photon microscopy** imaging data in a distributed, multi-computer lab environment (Stanford TRC lab). It handles the full lifecycle from raw acquisition to processed neuroimaging files on network storage.

### Core Workflow

1. **Transfer** — User on the Bruker imaging PC selects a scan folder via GUI. A socket-based client sends all files (with MD5 checksums) to a processing/ripping PC.
2. **FicTrac (parallel)** — If `autotransfer_jackfish` is enabled, launches FicTrac `configGui` + tracking in parallel WSL terminal windows. Runs concurrently with steps 3-4.
3. **Raw → TIFF** — Calls Bruker's "Image-Block Ripping Utility" to convert proprietary raw files to TIFFs.
4. **TIFF → NIfTI** — Converts TIFF stacks into `.nii.gz` neuroimaging format, handling volumetric scans, multiple channels, bidirectional Z-scanning, and voxel metadata from XML.
5. **Wait for FicTrac** — Blocks until all FicTrac sessions finish (polls for marker files).
6. **Assign jackfish data** — Writes `flyID.json` metadata into jackfish folders and copies FicTrac output into corresponding `func*/stimpack/jackfish/` imaging directories.
7. **Upload to Oak** — Copies processed files to Stanford's Oak network storage (`//oak-smb-trc.stanford.edu/...`).
8. **Optional: Stimpack** — Downloads behavioral tracking data (FicTrac `.dat`/`.log` files) and experimental metadata (stimpack HDF5) from separate computers, and auto-generates `fly.json` metadata.

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
| `brukerbridge/fictrac_wsl.py` | Launches FicTrac configGui + tracking via WSL |
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

## FicTrac post-hoc analysis

When `autotransfer_jackfish` is `"True"` in the user JSON, the pipeline automatically launches FicTrac ball-tracking on Jackfish video data via WSL. This runs in parallel with the rest of the pipeline (raw-to-tiff, tiff-to-nii), and the pipeline waits for all FicTrac sessions to finish before assigning jackfish data to imaging folders and transferring to Oak.

### How it works

1. `main.py` calls `fictrac_wsl.launch_fictrac_wsl()` before raw-to-tiff conversion.
2. The function finds the `DATESTRING_jackfish/` folder inside the queued directory and iterates two levels deep: `flyX/` subdirectories (matching stimpack h5 subjects), then series number subfolders within each (e.g., `fly1/2/`, `fly1/3/`, `fly1/5/`).
3. For each series folder:
   - **Skip** if a `.dat` file already exists (already processed).
   - **Copy** `users/YOURNAME/fictrac/config_CL.txt` into the folder if no config exists.
   - **Open** a Windows Terminal window (`wt.exe`) running WSL with: `configGui config_CL.txt && fictrac config_CL.txt && touch .fictrac_done`
4. All windows open in parallel. The user works through `configGui` in any order. When `configGui` is closed, `fictrac` starts automatically in that same terminal.
5. After tiff-to-nii conversion completes, `main.py` calls `wait_for_fictrac()` which polls for `.fictrac_done` marker files (created by `touch` after `fictrac` finishes) to ensure all sessions are complete.
6. Once all FicTrac sessions finish, `main.py` runs jackfish assignment: writes `flyID.json` metadata into jackfish folders and copies FicTrac output (`.dat`, `.log`, etc.) into the corresponding `func*/stimpack/jackfish/` imaging directories. This runs after `wait_for_fictrac` to guarantee all `.dat` files are fully written before copying.

### Prerequisites

- **WSL** with a registered Ubuntu distribution (check with `wsl -l`).
- **Windows Terminal** (`wt.exe`) installed (comes with Windows 11).
- **FicTrac** built inside WSL at the path specified by `fictrac_dir` in user JSON (default: `~/fictrac/bin`).
- A sample `config_CL.txt` at `users/YOURNAME/fictrac/config_CL.txt`.

### User JSON settings

| Field | Description | Example |
|---|---|---|
| `autotransfer_jackfish` | Enable FicTrac integration | `"True"` |
| `wsl_distro` | WSL distribution name (from `wsl -l`) | `"Ubuntu-22.04"` |
| `fictrac_dir` | Path to FicTrac binaries inside WSL | `"~/fictrac/bin"` |

### Standalone usage

`users/YOURNAME/run_fictrac.bat` can also be run manually outside the pipeline. Set `TARGET_PATH` at the top of the file or pass it as a command line argument:
```
run_fictrac.bat B:\brukerbridge\David\20260415
```

### Expected directory structure

The jackfish data folder must be organized with **fly subdirectories** matching the stimpack h5 subject numbering, with series numbers nested inside. The pipeline uses the h5 file to determine which subject (`fly1`, `fly2`, ...) owns which series (`2`, `3`, ...) and looks for data at `DATE_jackfish/flyX/series_num/`.

```
B:\brukerbridge\David\20260415__queue__\
  2026-04-15.hdf5                          <- stimpack h5 (defines subjects + series)
  20260415_jackfish\
    fly1\                                  <- matches subject 1 in h5 file
      2\          <- video.mp4 + config_CL.txt
      3\
      5\
      6\
    fly2\                                  <- matches subject 2 (if multi-fly experiment)
      7\
```

If your jackfish computer stores videos flat (e.g., `20260415/2/`, `20260415/3/` without a `fly1/` subdirectory), you must manually create the `flyX/` folders and move the numbered series folders into them before the pipeline can assign the data. The log will print the exact expected path for each series, e.g.:
```
Looking for jackfish data at: .../20260415_jackfish/fly1/5
```

## Troubleshooting

### Client socket timeout: `TimeoutError` at `sock.connect((host_IP, port))`

**Symptom.** `client.py` prints something like:
```
Connecting to host_IP='171.65.16.149' on port=5005
TimeoutError: A connection attempt failed because the connected party did not properly respond after a period of time...
```
The server PC reports it is listening correctly:
```
[*] Listening as 0.0.0.0:5005
[*] Ready to receive files from Bruker client
```

**Diagnosis.**
1. On the client PC, confirm it loads the correct IP (the print above shows it). If wrong, fix `host_IP` in `users/YOURNAME.json`.
2. On the server PC, run `ipconfig` and confirm its `IPv4 Address` matches `host_IP`.
3. From the client PC (PowerShell):
   ```
   Test-NetConnection <server_ip> -Port 5005
   ```
   If `PingSucceeded: True` but `TcpTestSucceeded: False` (or both fail while the server→client direction works), the server PC is blocking inbound traffic.

**Root cause.** Windows Defender Firewall on the server PC has **inbound block rules for Python** that override any allow rules. These are typically created automatically the first time Python tried to open a listening socket and someone clicked "Cancel" on the firewall popup.

**Fix.** On the server PC:
1. Open *Windows Defender Firewall with Advanced Security* → *Inbound Rules*.
2. Find any rules named `Python` (e.g., two entries for `Python 3.13`) with **Action = Block**.
3. Right-click each → **Disable Rule** (or delete them).
4. Re-run `server.py`. If Windows shows a firewall popup, click **Allow access** for both Private and Public profiles.

Optionally, to make the allow explicit, run in an **admin** command prompt on the server PC:
```
netsh advfirewall firewall add rule name="brukerbridge" dir=in action=allow protocol=TCP localport=5005
netsh advfirewall firewall add rule name="Allow ICMPv4-In" protocol=icmpv4:8,any dir=in action=allow
```

After disabling the block rules, the client's `sock.connect` succeeds and file transfer proceeds.