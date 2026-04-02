@echo off
SET mypath=%~dp0
SET reporoot=%mypath:~0,-16%
@echo calling %reporoot%\brukerbridge\Imaging_PC\client.py Mikaela
C:\Users\User\AppData\Local\Programs\Python\Python37\python.exe "%reporoot%\brukerbridge\Imaging_PC\client.py" Mikaela
cmd /k
