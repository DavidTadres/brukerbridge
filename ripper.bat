@echo off
echo Started ripper: %date% %time%
set FOLDER_NAME=%1
echo Ripping from folder %FOLDER_NAME%.
SET mypath=%~dp0
%mypath:~0,-1%"\Prairie 5.5.64.600\Utilities\Image-Block Ripping Utility.exe" -isf -arfwsf %FOLDER_NAME% -cnv
echo Finished ripping: %date% %time%