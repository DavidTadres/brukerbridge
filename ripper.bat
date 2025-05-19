@echo off
echo Started ripper: %date% %time%
set FOLDER_NAME=%1
set PVSCAN_VERSION=%2
echo Ripping from folder %FOLDER_NAME%.
echo Using PVScan version %PVSCAN_VERSION%
SET mypath=%~dp0
%mypath:~0,-1%"\Prairie %PVSCAN_VERSION%\Utilities\Image-Block Ripping Utility.exe" "-IncludeSubFolders" "-AddRawFileWithSubFolders" %FOLDER_NAME% "-Convert"
echo Finished ripping: %date% %time%