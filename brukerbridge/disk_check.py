"""Pre-upload disk-space check for the ripping server.

Pure function — no side effects, no logging. The caller decides what to do
with the result (print warnings, send notifications, etc.).
"""
import pathlib
import shutil
import socket


def check_disk_space(target_directory, source_size_gb):
    """Compare free space on the target drive against announced upload size.

    Returns (low_disk, info) where:
        low_disk: bool. True if free_gb < source_size_gb + margin_gb.
        info: dict with keys free_gb, required_gb, margin_gb,
              source_size_gb, drive, hostname.
    """
    target = pathlib.Path(target_directory)
    usage = shutil.disk_usage(target)
    free_gb = usage.free / 1e9
    margin_gb = max(source_size_gb * 0.10, 50.0)
    required_gb = source_size_gb + margin_gb
    drive = target.anchor or str(target)
    info = {
        'free_gb': free_gb,
        'required_gb': required_gb,
        'margin_gb': margin_gb,
        'source_size_gb': source_size_gb,
        'drive': drive,
        'hostname': socket.gethostname(),
    }
    return (free_gb < required_gb, info)


if __name__ == '__main__':
    # Smoke test: zero-size upload must always fit; impossibly large upload
    # must always fail.
    target = pathlib.Path.home()
    low, info = check_disk_space(target, 0)
    print('source_size=0 GB:  ', 'LOW' if low else 'OK ', info)
    assert not low, 'Expected OK for zero-size upload'
    low, info = check_disk_space(target, 10**9)  # 1 billion GB
    print('source_size=1e9 GB:', 'LOW' if low else 'OK ', info)
    assert low, 'Expected LOW for impossible upload size'
    print('disk_check smoke test passed.')
