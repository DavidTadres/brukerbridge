import pathlib
import shutil
import subprocess
import time

CONFIG_FILE = 'config_CL.txt'
MARKER_FILE = '.fictrac_done'


def _process_series_folder(series_folder, sample_config, wsl_distro, fictrac_dir, marker_paths):
	"""Handle a single series folder: skip if done, copy config, launch WSL."""
	# Skip if .dat file exists (already processed)
	dat_files = list(series_folder.glob('*.dat'))
	if dat_files:
		print('Skipping FicTrac for {} -- .dat file found, already processed'.format(
			series_folder.parent.name + '/' + series_folder.name))
		return

	# Copy sample config if missing
	config_path = series_folder / CONFIG_FILE
	if not config_path.exists():
		if sample_config.exists():
			print('Copying sample {} to {}'.format(CONFIG_FILE,
				series_folder.parent.name + '/' + series_folder.name))
			shutil.copy2(str(sample_config), str(config_path))
		else:
			print('WARNING: No {} in {} and no sample to copy, skipping'.format(
				CONFIG_FILE, series_folder.name))
			return

	# Clean up any stale marker from a previous run
	marker_path = series_folder / MARKER_FILE
	if marker_path.exists():
		marker_path.unlink()
	marker_paths.append(marker_path)

	# Convert Windows path to WSL path: B:\foo\bar -> /mnt/b/foo/bar
	drive = series_folder.parts[0][0].lower()
	wsl_path = '/mnt/{}/{}'.format(drive, '/'.join(series_folder.parts[1:]))

	# configGui -> fictrac -> touch marker file on completion
	cmd = "cd '{}' && {}/configGui {} && {}/fictrac {} && touch {}".format(
		wsl_path, fictrac_dir, CONFIG_FILE, fictrac_dir, CONFIG_FILE, MARKER_FILE)

	label = series_folder.parent.name + '/' + series_folder.name
	print('Launching configGui + fictrac for {} ...'.format(label))
	subprocess.Popen(
		['wt.exe', '--title', 'FicTrac {}'.format(label),
		 'wsl', '-d', wsl_distro, '--', 'bash', '-c', cmd],
	)


def launch_fictrac_wsl(dir_to_process, users_directory, user, settings):
	"""Launch FicTrac configGui + tracking in parallel WSL windows.

	Expects jackfish folder structure: DATE_jackfish/flyX/series_num/
	Returns a list of marker file paths to poll for completion.
	"""
	wsl_distro = settings.get('wsl_distro', 'Ubuntu-22.04')
	fictrac_dir = settings.get('fictrac_dir', '~/fictrac/bin')

	marker_paths = []

	# Derive jackfish folder: strip __queue__/__error__ to get date string
	folder_name = dir_to_process.name
	date_string = folder_name.replace('__queue__', '').replace('__error__', '')
	jackfish_dir = dir_to_process / (date_string + '_jackfish')

	if not jackfish_dir.exists():
		print('No jackfish folder found at {}, skipping FicTrac'.format(jackfish_dir))
		return marker_paths

	# Sample config to copy if a folder doesn't have one
	sample_config = pathlib.Path(users_directory, user, 'fictrac', CONFIG_FILE)
	if not sample_config.exists():
		print('WARNING: Sample {} not found at {}'.format(CONFIG_FILE, sample_config))

	# Iterate: jackfish_dir/flyX/series_num/
	for fly_folder in sorted(jackfish_dir.iterdir()):
		if not fly_folder.is_dir():
			continue
		if not fly_folder.name.startswith('fly'):
			print('Skipping non-fly folder in jackfish dir: {}'.format(fly_folder.name))
			continue

		for series_folder in sorted(fly_folder.iterdir()):
			if not series_folder.is_dir():
				continue
			_process_series_folder(series_folder, sample_config, wsl_distro, fictrac_dir, marker_paths)

	print('Launched {} FicTrac window(s)'.format(len(marker_paths)))
	return marker_paths


def wait_for_fictrac(marker_paths, poll_interval=10):
	"""Block until all marker files exist, meaning all FicTrac sessions finished."""
	if not marker_paths:
		return

	print('Waiting for {} FicTrac session(s) to finish...'.format(len(marker_paths)))
	remaining = set(range(len(marker_paths)))

	while remaining:
		time.sleep(poll_interval)
		for i in list(remaining):
			if marker_paths[i].exists():
				print('  FicTrac finished: {}'.format(marker_paths[i].parent.name))
				remaining.discard(i)
		if remaining:
			print('  Still waiting on {} session(s)...'.format(len(remaining)))

	# Clean up marker files
	for marker in marker_paths:
		if marker.exists():
			marker.unlink()

	print('All FicTrac sessions finished.')
