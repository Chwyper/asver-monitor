#!/usr/bin/env bash
# Aktifkan venv "test" lalu jalankan monitoring.py
# Sesuaikan VENV_PATH kalau lokasi venv-mu bukan ./test

set -e

VENV_PATH="./test"
SCRIPT="monitoring.py"

if [ ! -f "$VENV_PATH/bin/activate" ]; then
    echo "Venv tidak ditemukan di $VENV_PATH"
    exit 1
fi

source "$VENV_PATH/bin/activate"
python3 "$SCRIPT" "$@"
