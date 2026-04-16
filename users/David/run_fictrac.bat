@echo off
setlocal enabledelayedexpansion

:: ---- Configuration ----
:: TARGET_PATH can be set here, or passed as the first argument
set "TARGET_PATH="
set "WSL_DISTRO=Ubuntu-22.04"
set "FICTRAC_DIR=~/fictrac/bin"
set "CONFIG_FILE=config_CL.txt"
:: -----------------------

:: Command line argument overrides the hardcoded value
if not "%~1"=="" set "TARGET_PATH=%~1"

if "%TARGET_PATH%"=="" (
    echo ERROR: Set TARGET_PATH at the top of this script, or pass it as an argument.
    pause
    exit /b 1
)

if not exist "%TARGET_PATH%" (
    echo ERROR: TARGET_PATH does not exist: %TARGET_PATH%
    pause
    exit /b 1
)

:: Extract the folder name from TARGET_PATH (last component)
for %%F in ("%TARGET_PATH%") do set "FOLDER_NAME=%%~nxF"

:: Strip __queue__ or __error__ suffixes to get the date string
set "DATE_STRING=%FOLDER_NAME:__queue__=%"
set "DATE_STRING=%DATE_STRING:__error__=%"

:: Build the jackfish folder path
set "JACKFISH_DIR=%TARGET_PATH%\%DATE_STRING%_jackfish"

if not exist "%JACKFISH_DIR%" (
    echo ERROR: Jackfish folder not found: %JACKFISH_DIR%
    pause
    exit /b 1
)

:: Path to sample config_CL.txt (same directory as this .bat file)
set "BAT_DIR=%~dp0"
set "SAMPLE_CONFIG=%BAT_DIR%fictrac\%CONFIG_FILE%"

if not exist "%SAMPLE_CONFIG%" (
    echo WARNING: Sample config not found at %SAMPLE_CONFIG%
    echo Folders without %CONFIG_FILE% will be skipped.
)

echo Target:   %TARGET_PATH%
echo Jackfish: %JACKFISH_DIR%
echo Expected structure: %DATE_STRING%_jackfish\flyX\series_num\
echo.

set LAUNCHED=0
set SKIPPED=0

:: Iterate: jackfish_dir\flyX\series_num\
for /d %%F in ("%JACKFISH_DIR%\fly*") do (
    set "FLY_NAME=%%~nxF"

    for /d %%D in ("%%F\*") do (
        set "SERIES_NAME=%%~nxD"
        set "LABEL=!FLY_NAME!/!SERIES_NAME!"

        :: Check if .dat file exists (already processed)
        set "SKIP=0"
        for %%X in ("%%D\*.dat") do set "SKIP=1"

        if !SKIP!==1 (
            echo Skipping !LABEL! -- .dat file found, already processed
            set /a SKIPPED+=1
        ) else (
            :: Copy sample config if missing
            if not exist "%%D\%CONFIG_FILE%" (
                if exist "%SAMPLE_CONFIG%" (
                    echo Copying sample %CONFIG_FILE% to !LABEL!
                    copy "%SAMPLE_CONFIG%" "%%D\%CONFIG_FILE%" >nul
                ) else (
                    echo WARNING: No %CONFIG_FILE% in !LABEL! and no sample to copy, skipping
                    set /a SKIPPED+=1
                    set "SKIP=1"
                )
            )

            if !SKIP!==0 (
                :: Convert Windows path to WSL path
                set "WIN_PATH=%%D"
                set "WSL_PATH=!WIN_PATH:\=/!"
                :: Extract and lowercase the drive letter
                for /f "tokens=1 delims=:" %%L in ("!WSL_PATH!") do set "DRIVE_LETTER=%%L"
                set "DRIVE_LOWER=!DRIVE_LETTER!"
                for %%A in (a b c d e f g h i j k l m n o p q r s t u v w x y z) do (
                    if /i "!DRIVE_LETTER!"=="%%A" set "DRIVE_LOWER=%%A"
                )
                set "WSL_PATH=/mnt/!DRIVE_LOWER!!WSL_PATH:~2!"

                echo Launching configGui + fictrac for !LABEL! ...
                start "FicTrac !LABEL!" wsl -d %WSL_DISTRO% -- bash -c "cd '!WSL_PATH!' && %FICTRAC_DIR%/configGui %CONFIG_FILE% && %FICTRAC_DIR%/fictrac %CONFIG_FILE%"
                set /a LAUNCHED+=1
            )
        )
    )
)

echo.
echo Done. Launched !LAUNCHED! window(s), skipped !SKIPPED! folder(s).
pause
