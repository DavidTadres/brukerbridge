@echo off
@echo HELLO I AM THE QUEUE WATCHER.
@echo IF I FIND A QUEUED DIRECTORY I WILL LAUNCH MAIN PROCESSING.
SET mypath=%~dp0
echo %mypath:~0,-1%\queue_watcher.py
PLACEHOLDER_PYTHON_EXE_PATH %mypath:~0,-1%\queue_watcher.py
cmd /k
