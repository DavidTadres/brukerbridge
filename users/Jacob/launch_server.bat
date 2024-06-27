@echo off
@echo HELLO I AM THE SERVER THAT TRANSFERS DATA FROM BRUKER TO THIS COMPUTER.
@echo LEAVE ME OPEN AND I WILL DO GOOD THINGS.
@echo YOU MUST START FILE TRANSFER FROM THE BRUKER COMPUTER.
@echo LOOK AT MY OUTPUT IN C:\Users\jcsimon\Documents\Stanford\brukerbridge\logs. USING MTAIL PROGRAM IS CONVENIENT.
SET mypath=%~dp0
C:\Users\jcsimon\miniconda3\envs\brukerbridge\python.exe %mypath:~0,-1%\brukerbridge\ripping_PC\jacob_server.py >> C:\Users\jcsimon\Documents\Stanford\brukerbridge\logs\server_log.txt 2>&1
cmd /k