@echo off
echo Started fictrac: %date% %time%
echo ubuntu2204.exe

set FOLDER_NAME=%1
echo running fictrac in folder %FOLDER_NAME%.

set WSL_HOME=\\wsl$\Ubuntu\home\clandininlab
echo %WSL_HOME%

cd %FOLDER_NAME%
\\wsl$\Ubuntu\home\clandininlab\fictrac\bin\fictrac config_CL.txt
