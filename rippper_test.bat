echo Started ripper: %date% %time%
set FOLDER_NAME=F:\brukerbridge\David\test_queue
echo Ripping from folder %FOLDER_NAME%.
SET mypath=%~dp0
%mypath:~0,-1%"\Prairie 5.5.64.600\Utilities\Image-Block Ripping Utility.exe" -isf -arfwsf %FOLDER_NAME% -cnv
