@echo off
@echo C:\Users\User\AppData\Local\Programs\Python\Python37\python.exe
SET mypath=%~dp0
@echo calling %mypath:~0,-13%\brukerbridge\Imaging_PC\david_client.py
C:\Users\User\AppData\Local\Programs\Python\Python37\python.exe %mypath:~0,-13%\brukerbridge\Imaging_PC\david_client.py
cmd /k