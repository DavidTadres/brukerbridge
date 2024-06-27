@echo off
@echo C:\Users\User\AppData\Local\Programs\Python\Python37\python.exe
SET mypath=%~dp0
@echo %mypath:~0,-1%
C:\Users\David\.conda\envs\env_brukerbridge\python.exe %mypath:~0,-13%\brukerbridge\Imaging_PC\david_client.py
cmd /k