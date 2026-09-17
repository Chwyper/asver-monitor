@echo off
set "VENV_NAME=monitoring"
set "NEW_VENV=0"

:: Cek apakah folder venv sudah ada
if not exist "%VENV_NAME%" (
    echo Virtual environment '%VENV_NAME%' tidak ditemukan. Sedang membuat...
    python -m venv %VENV_NAME%
    echo Virtual environment berhasil dibuat!
    set "NEW_VENV=1"
)

:: Aktivasi venv
echo Mengaktifkan virtual environment '%VENV_NAME%'...
call %VENV_NAME%\Scripts\activate.bat

:: Jika venv baru dibuat, cek dan install req.txt
if "%NEW_VENV%"=="1" (
    if exist "req.txt" (
        echo Menginstal library dari req.txt...
        pip install -r req.txt
        echo Instalasi selesai!
    ) else (
        echo File req.txt tidak ditemukan, melewati instalasi library.
    )
)

echo Selesai! Virtual environment aktif.
cmd /k