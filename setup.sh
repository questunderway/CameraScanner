#!/bin/bash

echo "[+] Starting setup..."

if [ -n "$PREFIX" ] && [ -x "$(command -v pkg)" ]; then
    echo "[+] Detected Termux. Installing dependencies with pkg..."
    pkg update -y
    pkg upgrade -y
    pkg install python -y
    pkg install python2 -y
    pkg install git -y
    pkg install clang
    pip install --upgrade pip
else
    echo "[+] Assuming Linux. Installing dependencies with apt..."
    sudo apt update
    sudo apt install -y python3 python3-pip
fi

if ! command -v pip &> /dev/null; then
    if command -v pip3 &> /dev/null; then
        alias pip=pip3
    fi
fi

echo "[+] Installing Python dependencies..."
pip install --upgrade pip
pip install tqdm

echo "[+] Setup complete! You can now run the tool with:"
echo "    python CameraScanner.py"