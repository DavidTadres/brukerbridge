@echo off
@echo HELLO I AM THE QUEUE WATCHER.
@echo IF I FIND A QUEUED DIRECTORY I WILL LAUNCH MAIN PROCESSING.
SET mypath=%~dp0
C:\Users\David\.conda\envs\env_brukerbridge\python.exe %mypath:~0,-13%\scripts\queue_watcher.py
cmd /k