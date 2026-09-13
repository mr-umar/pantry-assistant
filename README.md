# Autonomous pantry assistant for low-Vision users

![Pantry Assistant](/media/pantry.png)

This is an automated system to recognize pantry items. It runs on the **Arduino UNO Q** dual-brain architecture. It uses a Time-of-Flight hardware sensor on the microcontroller to measure distance, combined with Edge Impulse AI and RapidOCR text reading on Debian Linux.

Developed for **[Hackestiu 2026](https://catedrachip.upc.edu/es/hackestiu_2026_democratiza_inteligencia_artificial/)** (Càtedra CHIP UPC & Qualcomm).

---

## Authors

* **Lluis Vidal** ([@Lluisvidal89](https://github.com/Lluisvidal89))
* **Umar Mohammad** ([@mr-umar](https://github.com/mr-umar))

---

## Quick Start (One-Liner Installation)

Run this single command in your Arduino UNO Q terminal. It will clone the repository, install all dependencies, and flash the STM32 microcontroller:

```bash
git clone https://github.com/mr-umar/pantry-assistant.git && cd pantry-assistant && chmod +x install.sh run.sh src/model.eim && ./install.sh

```

Once installed, start the system:

```bash
./run.sh

```

Open a web browser on any device connected to the same local network:

```text
http://<ARDUINO_UNO_Q_IP>:5000

```

---

## Demo

Click to watch:

[![Demo Hackestiu](https://img.youtube.com/vi/OMCTbtRUUI4/maxresdefault.jpg)](https://www.youtube.com/watch?v=OMCTbtRUUI4)

## System Architecture

This assistant helps people with low vision identify grocery packages (like canned chickpeas or tomato sauce). It works entirely on the device without needing the internet. This guarantees zero delay and keeps your data completely private.

```text
+--------------------------------------------------------------------------+
|                            Arduino UNO Q                                 |
|                                                                          |
|  +---------------------------+       +--------------------------------+  |
|  |     STM32U585 (MCU)       |       |  Qualcomm Dragonwing QRB2210   |  |
|  |                           |       |         (Debian Linux)         |  |
|  |  - Modulino Distance      |       |                                |  |
|  |                           |  RPC  |  - UNIX Socket Bridge Client   |  |
|  |  - Arduino_RouterBridge   | ----> |  - Stability Filter (25-50 cm) |  |
|  |    service provider       |       |  - Edge Impulse Model (.eim)   |  |
|  +---------------------------+       |  - Fallback RapidOCR Engine    |  |
|                                      |  - Flask Telemetry Streamer    |  |
|                                      +--------------------------------+  |
+--------------------------------------------------------------------------+

```

### 1. Dual-Core Hardware Integration

* **Microcontroller (STM32U585)**: It constantly checks an **Arduino Modulino Distance** sensor connected to the physical Qwiic port (`Wire1` / I2C4 bus). It sets up an RPC method (`get_distance`) using the official `Arduino_RouterBridge` library.
* **Microprocessor (Qualcomm Dragonwing)**: A light Python client asks for measurements directly through `/var/run/arduino-router.sock` using standard MessagePack-RPC, avoiding heavy graphical interfaces.

### 2. Distance & Stability Filter

To avoid blurry pictures and save computer power, the AI only works when you hold a product steady between **25 and 50 cm** (250 mm to 500 mm) from the sensor for a few seconds.

### 3. AI Pipeline

* **Primary Stage (Edge Impulse)**: It checks high-quality camera images using an Edge Impulse model (`src/model.eim`) saved on the device. This model finds the product and identifies it.
* **Fallback Stage (RapidOCR)**: If the system cannot find the product, or if it is not very sure (less than 80% confidence), it sends the image to **RapidOCR**. This tool reads the text and brand names on the packaging.

### Edge Impulse Machine Learning Pipeline
- **Edge Impulse Project:** [Pantry Detector](https://studio.edgeimpulse.com/studio/1106136)
- **Model Architecture:** YOLO-Pro (Float32 unoptimized for ARM Cortex-A)
- **Dataset:** 220+ images [automatically labeled with Gemini 3.5 Flash Lite](/Labelling/)
- **Deployment:** Compiled standalone `.eim` binary targeting Arduino UNO Q

---

## Hardware Bill of Materials

* **Arduino UNO Q** (2GB or 4GB)*
* **Arduino Modulino Distance** (ABX00102)
* **10cm Qwiic cable**
* **Any USB Webcam** (1080p compatible)**
* **USB Type-C Power Supply** - **USB-C Hub for power and camera**

* The 2GB version of the UNO Q should be enough for this project.
 
**We used the provided Logitech Brio 105 with manual focus set for our needs. You can adjust the focus of your webcam by turning the lens ring, as shown in the following image:

![Webcam Focus](/media/lens_adjust.gif)

Logitech adds glue to the ring, but you can remove it easily with isopropyl alcohol :) 

---

## Manual Step-by-Step Setup

If you prefer to run each step yourself instead of using `install.sh`:

### 1. Install Debian packages

```bash
sudo apt update
sudo apt install -y python3-pip python3-opencv python3-pyaudio portaudio19-dev python3-msgpack

```

### 2. Install Python dependencies

*(The following command installs them for the whole system. We recommend using a virtual environment instead).*

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

### 5. (Optional) Remote Access with Tailscale

If you want to connect to the assistant from a device outside your local network:

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up

```

---

## 3D Case

Check the 3D folder for the STL files if you need them.

---

## AI Assistance Disclaimer
Parts of the code and documentation in this repository were generated or refined with the assistance of AI tools. All AI-generated logic has been reviewed, tested, and modified by the authors to ensure it meets the specific hardware and software requirements of this project.

## License

Developed for the **Hackestiu 2026** competition. Open source and available under the MIT License.


