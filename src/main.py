import sys
import os
import time
import socket
import msgpack
import threading
from unittest.mock import MagicMock

# Mock pyaudio to prevent edge_impulse_linux from failing on headless Linux
sys.modules['pyaudio'] = MagicMock()

import cv2
import numpy as np
from flask import Flask, render_template_string, Response, request, jsonify
from rapidocr_onnxruntime import RapidOCR
from edge_impulse_linux.image import ImageImpulseRunner

app = Flask(__name__)

# Absolute paths resolution
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_FILE = os.path.join(SCRIPT_DIR, "model.eim")
ROUTER_SOCKET = "/var/run/arduino-router.sock"

# Detection parameters
CONFIDENCE_THRESHOLD = 0.50
MIN_DISTANCE_MM = 200
MAX_DISTANCE_MM = 400
STABLE_SAMPLES = 3
STABLE_TOLERANCE_MM = 30
DETECTION_COOLDOWN_SEC = 2.0

# Global state variables
camera_index = 0
cap = None
current_frame_1080 = None
frame_lock = threading.Lock()

latest_distance = -1
latest_status = "Waiting for stable object at 20-40 cm..."
latest_result = "-"
latest_process_time = 0.0

# Initialize RapidOCR
ocr_engine = RapidOCR()

# Initialize Edge Impulse Runner
runner = None
if os.path.isfile(MODEL_FILE):
    try:
        print(f"[INIT] Loading Edge Impulse model from: {MODEL_FILE}")
        runner = ImageImpulseRunner(MODEL_FILE)
        model_info = runner.init()
        print(f"[INIT] Model loaded successfully: {model_info.get('project', {}).get('name', 'N/A')}")
        print(f"[INIT] Model labels: {model_info['model_parameters']['labels']}")
    except Exception as e:
        print(f"[ERROR] Failed to initialize Edge Impulse model: {e}")
        runner = None
else:
    print(f"[WARN] Model file not found at: {MODEL_FILE}. Fallback OCR will run exclusively.")

# HTML Dashboard Template
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>UNO Q Pantry Assistant</title>
    <meta charset="utf-8">
    <style>
        body { font-family: sans-serif; text-align: center; margin-top: 20px; background-color: #f4f4f4; }
        .container { background: white; padding: 20px; display: inline-block; border-radius: 10px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }
        img { border: 2px solid #333; border-radius: 5px; max-width: 100%; }
        .card { margin-top: 15px; text-align: left; background: #eee; padding: 15px; border-radius: 5px; }
        .highlight { font-size: 1.2em; font-weight: bold; color: #0056b3; }
    </style>
</head>
<body>
    <div class="container">
        <h2>UNO Q - Automated Pantry Assistant</h2>
        <img id="videofeed" src="/videofeed" width="854" height="480"><br><br>

        <div class="card">
            <p><strong>Distance Sensor:</strong> <span id="dist-span">--</span> mm</p>
            <p><strong>Status:</strong> <span id="status-span">Scanning...</span></p>
            <p><strong>Result:</strong> <span id="res-span" class="highlight">-</span></p>
            <p><strong>Processing Time:</strong> <span id="time-span">0.000</span> s</p>
        </div>
    </div>

    <script>
        setInterval(() => {
            fetch('/telemetry')
                .then(r => r.json())
                .then(data => {
                    document.getElementById('dist-span').innerText = data.distance;
                    document.getElementById('status-span').innerText = data.status;
                    document.getElementById('res-span').innerText = data.result;
                    document.getElementById('time-span').innerText = data.time.toFixed(3);
                })
                .catch(err => console.error(err));
        }, 300);
    </script>
</body>
</html>
"""

def read_modulino_distance():
    """Reads real-time distance from STM32 through the arduino-router UNIX socket."""
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.settimeout(0.3)
            s.connect(ROUTER_SOCKET)
            payload = msgpack.packb([0, 1, "get_distance", [""]])
            s.sendall(payload)
            response = msgpack.unpackb(s.recv(1024))
            
            if len(response) >= 4 and response[2] is None:
                val = response[3]
                if isinstance(val, (int, float)):
                    return int(val)
                elif isinstance(val, str) and val.strip().lstrip('-').isdigit():
                    return int(val.strip())
            return -1
    except Exception:
        return -1

def camera_reader_thread():
    """Continuously reads frames from the USB camera to keep buffer fresh."""
    global cap, camera_index, current_frame_1080
    while True:
        if cap is None or not cap.isOpened():
            cap = cv2.VideoCapture(camera_index)
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            time.sleep(1)
            continue

        success, frame = cap.read()
        if success:
            with frame_lock:
                current_frame_1080 = frame
        else:
            time.sleep(0.01)

def run_model_inference(frame_bgr):
    """Matches the exact inference logic for FOMO and Classification."""
    if runner is None:
        return None, 0.0

    rgb_frame = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    features, _ = runner.get_features_from_image(rgb_frame)
    res = runner.classify(features)

    best_label = None
    best_score = 0.0
    result_data = res.get("result", {})

    # Check Bounding Boxes (FOMO / Object Detection)
    if "bounding_boxes" in result_data:
        for bb in result_data["bounding_boxes"]:
            score = bb.get("value", 0.0)
            if score > best_score:
                best_score = score
                best_label = bb.get("label", "unknown")

    # Check Standard Image Classification
    elif "classification" in result_data:
        for label, score in result_data["classification"].items():
            if score > best_score:
                best_score = score
                best_label = label

    return best_label, best_score

def run_ocr_inference(frame_bgr):
    """Executes RapidOCR fallback and concatenates detected text lines."""
    results, _ = ocr_engine(frame_bgr)
    extracted = []
    if results:
        for item in results:
            extracted.append(item[1])
        return " ".join(extracted)
    return "No text identified"

def automation_worker():
    """Monitors stability between 200mm and 400mm and runs the detection pipeline."""
    global latest_distance, latest_status, latest_result, latest_process_time
    history = []

    while True:
        dist = read_modulino_distance()
        latest_distance = dist

        # Range filter
        if dist < MIN_DISTANCE_MM or dist > MAX_DISTANCE_MM:
            history.clear()
            latest_status = "Waiting for object at 20-40 cm..."
            time.sleep(0.1)
            continue

        history.append(dist)
        if len(history) > STABLE_SAMPLES:
            history.pop(0)

        # Stability verification
        is_stable = False
        if len(history) == STABLE_SAMPLES:
            diff = max(history) - min(history)
            if diff <= STABLE_TOLERANCE_MM:
                is_stable = True

        if is_stable:
            with frame_lock:
                frame_to_process = None if current_frame_1080 is None else current_frame_1080.copy()

            if frame_to_process is not None:
                latest_status = f"Object stable at {dist} mm. Evaluating..."
                t0 = time.time()

                # Step 1: Run Edge Impulse model
                label, score = run_model_inference(frame_to_process)

                if label and score >= CONFIDENCE_THRESHOLD:
                    latest_result = f"Model: {label} ({score:.2f})"
                    print(f"[DETECTION] {latest_result} at {dist} mm")
                else:
                    # Step 2: Fallback to RapidOCR
                    score_str = f"{score:.2f}" if label else "0.00"
                    latest_status = f"Confidence low ({score_str}). Running OCR..."
                    ocr_text = run_ocr_inference(frame_to_process)
                    latest_result = f"OCR Fallback: {ocr_text}"
                    print(f"[FALLBACK] {latest_result} at {dist} mm")

                latest_process_time = time.time() - t0
                history.clear()
                time.sleep(DETECTION_COOLDOWN_SEC)

        time.sleep(0.1)

def get_video_stream():
    """Generates JPEG stream for the web browser."""
    global current_frame_1080
    while True:
        with frame_lock:
            frame = None if current_frame_1080 is None else current_frame_1080.copy()

        if frame is None:
            time.sleep(0.1)
            continue

        frame_preview = cv2.resize(frame, (854, 480))
        ret, buffer = cv2.imencode('.jpg', frame_preview, [cv2.IMWRITE_JPEG_QUALITY, 60])
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
        time.sleep(0.05)

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/videofeed')
def videofeed():
    return Response(get_video_stream(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/telemetry')
def telemetry():
    return jsonify({
        "distance": latest_distance,
        "status": latest_status,
        "result": latest_result,
        "time": latest_process_time
    })

if __name__ == '__main__':
    threading.Thread(target=camera_reader_thread, daemon=True).start()
    threading.Thread(target=automation_worker, daemon=True).start()
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)