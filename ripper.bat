@echo off
echo Started ripper: %date% %time%
set FOLDER_NAME=%1
set PVSCAN_VERSION=%2
echo Ripping from folder %FOLDER_NAME%.
echo Using PVScan version %PVSCAN_VERSION%.
::"C:\Program Files\Prairie %PVSCAN_VERSION%\Prairie View\Utilities\Image-Block Ripping Utility.exe"  "-IncludeSubFolders" "-AddRawFileWithSubFolders" %FOLDER_NAME% "-Convert"
"C:\Program Files\Prairie %PVSCAN_VERSION%\Prairie View\Utilities\Image-Block Ripping Utility.exe"  "-IncludeSubFolders" "-AddRawFileWithSubFolders" %FOLDER_NAME% "-Convert"
echo Finished ripping: %date% %time%