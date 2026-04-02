@echo off
SET mypath=%~dp0
SET reporoot=%mypath:~0,-13%
@echo calling %reporoot%\brukerbridge\Imaging_PC\client.py David
C:\Users\User\AppData\Local\Programs\Python\Python37\python.exe "%reporoot%\brukerbridge\Imaging_PC\client.py" David
cmd /k