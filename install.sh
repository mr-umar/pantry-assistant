#!/usr/bin/env bash
set -e

# ANSI Color formatting
BOLD='\033[1m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

echo -e "${BOLD}${CYAN}==========================================================${NC}"
echo -e "${BOLD}${CYAN}   Installing Pantry Assistant (Arduino UNO Q Dedicated)   ${NC}"
echo -e "${BOLD}${CYAN}==========================================================${NC}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 1. System packages
echo -e "\n${BOLD}[1/4] Checking and installing Debian system packages...${NC}"
sudo apt update
sudo apt install -y python3-pip python3-opencv python3-pyaudio portaudio19-dev python3-msgpack

# 2. Python packages
echo -e "\n${BOLD}[2/4] Installing Python dependencies via pip...${NC}"
pip install -r "${SCRIPT_DIR}/src/requirements.txt" --break-system-packages

# 3. Model permissions
echo -e "\n${BOLD}[3/4] Checking Edge Impulse model binary...${NC}"
if [ -f "${SCRIPT_DIR}/src/model.eim" ]; then
    chmod +x "${SCRIPT_DIR}/src/model.eim"
    echo -e "${GREEN}✓ Execution permissions granted to src/model.eim${NC}"
else
    echo -e "${YELLOW}[WARN] src/model.eim not found. Make sure to place your model there.${NC}"
fi

# 4. Flash STM32 microcontroller
echo -e "\n${BOLD}[4/4] Setting up STM32 microcontroller firmware...${NC}"

# Check if libraries are already installed to skip slow index downloads
if ! arduino-cli lib list | grep -q "Arduino_Modulino" || ! arduino-cli lib list | grep -q "Arduino_RouterBridge"; then
    echo "Downloading missing Arduino libraries..."
    arduino-cli lib update-index
    arduino-cli lib install "Arduino_Modulino" "Arduino_RouterBridge"
else
    echo -e "${GREEN}✓ Arduino libraries already installed. Skipping download.${NC}"
fi

echo -e "\n${BOLD}${YELLOW}-----------------------------------------------------------------${NC}"
echo -e "${BOLD}${YELLOW} [NOTICE] Compiling Zephyr OS & flasing the STM32 microcontroller...${NC}"
echo -e "${YELLOW} This step typically takes 40-90 seconds on the UNO Q.${NC}"
echo -e "${YELLOW} Please DO NOT disconnect or cancel the process.${NC}"
echo -e "${BOLD}${YELLOW}-----------------------------------------------------------------${NC}\n"

cd "${SCRIPT_DIR}/firmware"

# Compile using all available CPU cores (--jobs 0) to speed up build time
arduino-cli compile --fqbn arduino:zephyr:unoq --jobs 0 -u .

echo -e "\n${BOLD}${GREEN}==========================================================${NC}"
echo -e "${BOLD}${GREEN}   Installation finished successfully!                    ${NC}"
echo -e "${BOLD}${GREEN}   Launch the assistant with: ./run.sh                    ${NC}"
echo -e "${BOLD}${GREEN}==========================================================${NC}\n"