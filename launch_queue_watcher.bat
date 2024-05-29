@echo off
@echo HELLO I AM THE QUEUE WATCHER.
@echo IF I FIND A QUEUED DIRECTORY I WILL LAUNCH MAIN PROCESSING.
SET mypath=%~dp0
C:\Users\User\AppData\Local\Programs\Python\Python37\python.exe %mypath:~0,-1%\brukerbridge\ripping_PC\scripts\queue_watcher.py
cmd /k