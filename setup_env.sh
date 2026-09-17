#!/bin/bash

VENV_NAME="monitoring"
NEW_VENV=0

# Cek apakah folder venv sudah ada
if [ ! -d "$VENV_NAME" ]; then
    echo "Virtual environment '$VENV_NAME' tidak ditemukan. Sedang membuat..."
    python3 -m venv "$VENV_NAME"
    echo "Virtual environment berhasil dibuat!"
    NEW_VENV=1
fi

# Aktivasi venv
echo "Mengaktifkan virtual environment '$VENV_NAME'..."
source "$VENV_NAME/bin/activate"

# Jika venv baru dibuat, cek dan install req.txt
if [ $NEW_VENV -eq 1 ]; then
    if [ -f "req.txt" ]; then
        echo "Menginstal library dari req.txt..."
        pip install --upgrade pip
        pip install -r req.txt
        echo "Instalasi selesai!"
    else
        echo "File req.txt tidak ditemukan, melewati instalasi library."
    fi
fi

echo "Selesai! Virtual environment aktif."
# Membuka bash baru agar terminal tetap terbuka setelah venv aktif
exec "$SHELL"