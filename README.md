# Autonomous Pantry Assistant for Low-Vision Users

Automated pantry item recognition pipeline running on the **Arduino UNO Q** dual-brain architecture. It pairs hardware Time-of-Flight distance gating on the real-time microcontroller with on-device Edge Impulse inference and RapidOCR text reading on Debian Linux.

Developed for **Hackestiu 2026** (Càtedra CHIP UPC & Qualcomm).

---

## Authors & Affiliation
- **Umar** ([@mr-umar](https://github.com/mr-umar)) & Team
- Universitat Politècnica de Catalunya (UPC) — Barcelona, Spain

---

## Quick Start (One-Liner Installation)

Run this single command on your Arduino UNO Q terminal to clone the repository, install all dependencies, and flash the STM32 microcontroller:

```bash
git clone https://github.com/mr-umar/pantry-assistant.git && cd pantry-assistant && chmod +x install.sh run.sh src/model.eim && ./install.sh
```

Once installed, launch the pipeline:
```bash
./run.sh
```

Open a web browser on any device in the same local network:
```text
http://<ARDUINO_UNO_Q_IP>:5000
```

---

## System Architecture

The assistant helps individuals with low vision identify grocery packaging (e.g., canned chickpeas or fried tomato sauce) entirely on-device, ensuring zero latency from cloud roundtrips and complete privacy.

```text
+--------------------------------------------------------------------------+
|                            Arduino UNO Q                                 |
|                                                                          |
|  +---------------------------+       +--------------------------------+  |
|  |     STM32U585 (MCU)       |       |  Qualcomm Dragonwing QRB2210   |  |
|  |                           |       |         (Debian Linux)         |  |
|  |  - Modulino Distance      |       |                                |  |
|  |    (VL53L4CD ToF on Wire1)|  RPC  |  - UNIX Socket Bridge Client   |  |
|  |  - Arduino_RouterBridge   | ----> |  - Stability Gating (20-40 cm) |  |
|  |    service provider       |       |  - Edge Impulse Model (.eim)   |  |
|  +---------------------------+       |  - Fallback RapidOCR Engine    |  |
|                                      |  - Flask Telemetry Streamer    |  |
|                                      +--------------------------------+  |
+--------------------------------------------------------------------------+
```

### 1. Dual-Core Hardware Integration
- **Microcontroller (STM32U585)**: Continuously polls an **Arduino Modulino Distance** sensor connected to the physical Qwiic port (`Wire1` / I2C4 bus). It registers an RPC method (`get_distance`) using the official `Arduino_RouterBridge` library.
- **Microprocessor (Qualcomm Dragonwing)**: A lightweight Python client queries measurements directly through `/var/run/arduino-router.sock` using standard MessagePack-RPC, bypassing bulky graphical wrappers.

### 2. Distance Gating & Stability Filter
To prevent camera blur and unnecessary CPU usage, inference only triggers when a product is held steady within **200 mm to 400 mm** (20 to 40 cm) of the sensor across consecutive samples.

### 3. Cascading AI Pipeline
- **Primary Stage (Edge Impulse)**: Evaluates high-resolution camera frames using an on-device Edge Impulse model (`src/model.eim`) supporting both FOMO bounding boxes and classification.
- **Fallback Stage (RapidOCR)**: If the target product is not detected or the confidence score drops below 50%, the pipeline automatically forwards the frame to **RapidOCR** (ONNX Runtime) to extract packaging labels and brand text.

---

## Repository Structure

```text
pantry-assistant/
├── .gitignore
├── README.md
├── install.sh
├── run.sh
├── firmware/
│   └── firmware.ino
└── src/
    ├── main.py
    ├── model.eim
    └── requirements.txt
```

---

## Hardware Bill of Materials
- **Arduino UNO Q** (2GB or 4GB)
- **Arduino Modulino Distance** (VL53L4CD ToF)
- Standard Qwiic cable
- USB UVC Webcam (1080p compatible)
- USB Type-C Power Supply (5V/3A recommended)

---

## Manual Step-by-Step Setup

If you prefer to run each step manually instead of using `install.sh`:

### 1. Install Debian packages
```bash
sudo apt update
sudo apt install -y python3-pip python3-opencv python3-pyaudio portaudio19-dev python3-msgpack
```

### 2. Install Python dependencies
```bash
pip install -r src/requirements.txt --break-system-packages
```

### 3. Flash the STM32 firmware
```bash
arduino-cli lib update-index
arduino-cli lib install "Arduino_Modulino" "Arduino_RouterBridge"
cd firmware
arduino-cli compile --fqbn arduino:zephyr:unoq -u .
cd ..
```

### 4. Set permissions and run
```bash
chmod +x src/model.eim run.sh
./run.sh
```

---

## License
Developed for the **Hackestiu 2026** competition. Open source and available under the MIT License.