#!/usr/bin/env bash
set -e

echo "=========================================================="
echo " Installing Pantry Assistant Dependencies (No App Lab)"
echo "=========================================================="

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 1. System packages
echo "[1/4] Installing system Debian packages..."
sudo apt update
sudo apt install -y python3-pip python3-opencv python3-pyaudio portaudio19-dev python3-msgpack

# 2. Python packages
echo "[2/4] Installing Python dependencies..."
pip install -r "${SCRIPT_DIR}/src/requirements.txt" --break-system-packages

# 3. Model permissions
echo "[3/4] Ensuring model permissions..."
if [ -f "${SCRIPT_DIR}/src/model.eim" ]; then
    chmod +x "${SCRIPT_DIR}/src/model.eim"
else
    echo "[WARN] src/model.eim not found. Make sure to place your model there."
fi

# 4. Flash STM32 microcontroller
echo "[4/4] Flashing STM32 firmware using arduino-cli..."
arduino-cli lib update-index
arduino-cli lib install "Arduino_Modulino" "Arduino_RouterBridge"

cd "${SCRIPT_DIR}/firmware"
arduino-cli compile --fqbn arduino:zephyr:unoq -u .

echo "=========================================================="
echo " Done! Start the system with: ./run.sh"
echo "=========================================================="