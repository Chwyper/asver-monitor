@echo off
TITLE SSH Multi-Device Launcher
setlocal EnableDelayedExpansion

:: Membaca file config.txt baris per baris
for /f "tokens=*" %%a in (config.txt) do (
    set "line=%%a"
    if not "!line:~0,1!"=="#" if not "!line!"=="" (
        set %%a
    )
)

:MENU
cls
echo ========================================
echo        PILIH DEVICE UNTUK SSH
echo ========================================
echo   [1] Koneksi ke Device 1 (%HOST1%)
echo   [2] Koneksi ke Device 2 (%HOST2%)
echo   [3] Keluar
echo ========================================
set /p "pilihan=Masukkan pilihan Anda (1-3): "

if "%pilihan%"=="1" (
    set TARGET_HOST=%HOST1%
    set TARGET_USER=%USER1%
    set TARGET_PASS=%PASS1%
    goto LAUNCH
)
if "%pilihan%"=="2" (
    set TARGET_HOST=%HOST2%
    set TARGET_USER=%USER2%
    set TARGET_PASS=%PASS2%
    goto LAUNCH
)
if "%pilihan%"=="3" (
    exit
)

echo Pilihan tidak valid! Silakan coba lagi.
timeout /t 2 > nul
goto MENU

:LAUNCH
echo.
echo Membuka 2 jendela SSH untuk %TARGET_HOST% (User: %TARGET_USER%)...

:: Membuka Jendela Command Prompt Pertama
start "SSH Terminal 1 - %TARGET_HOST%" cmd /k "plink.exe -ssh %TARGET_USER%@%TARGET_HOST% -pw %TARGET_PASS%"

:: Membuka Jendela Command Prompt Kedua
start "SSH Terminal 2 - %TARGET_HOST%" cmd /k "plink.exe -ssh %TARGET_USER%@%TARGET_HOST% -pw %TARGET_PASS%"

endlocal
pause