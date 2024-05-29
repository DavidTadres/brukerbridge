@echo off
@echo HELLO I AM THE SERVER THAT TRANSFERS DATA FROM BRUKER TO THIS COMPUTER.
@echo LEAVE ME OPEN AND I WILL DO GOOD THINGS.
@echo YOU MUST START FILE TRANSFER FROM THE BRUKER COMPUTER.
@echo LOOK AT MY OUTPUT IN DATAFLOW_LOGS\SERVER_LOG.TXT. USING MTAIL PROGRAM IS CONVENIENT.
C:\Users\David\.conda\envs\env_brukerbridge\python.exe C:\Users\David\brukerbridge\brukerbridge\ripping_PC\server.py >> C:\Users\David\Desktop\brukerbridge_datalogs\server_log.txt 2>&1
cmd /k