@echo off
@echo HELLO I AM THE QUEUE WATCHER.
@echo IF I FIND A QUEUED DIRECTORY I WILL LAUNCH MAIN PROCESSING.
SET mypath=%~dp0
SET reporoot=%mypath:~0,-17%
call "%reporoot%\env_brukerbridge\Scripts\activate.bat"
python "%mypath%queue_watcher.py"
cmd /k