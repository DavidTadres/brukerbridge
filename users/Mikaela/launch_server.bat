@echo off
@echo HELLO I AM THE SERVER THAT TRANSFERS DATA FROM BRUKER TO THIS COMPUTER.
@echo LEAVE ME OPEN AND I WILL DO GOOD THINGS.
@echo YOU MUST START FILE TRANSFER FROM THE BRUKER COMPUTER.
@echo LOOK AT MY OUTPUT IN DATAFLOW_LOGS\SERVER_LOG.TXT. USING MTAIL PROGRAM IS CONVENIENT.
SET mypath=%~dp0
SET reporoot=%mypath:~0,-16%
call "%reporoot%\env_brukerbridge\Scripts\activate.bat"
python "%reporoot%\brukerbridge\ripping_PC\server.py" Mikaela >> PLACEHOLDER_LOG_PATH\server_log.txt 2>&1
cmd /k
