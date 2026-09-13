# Dataset auto-labelling

Automates bounding box annotations for pantry items using Google Gemini Flash Lite and exports directly into Edge Impulse format (`bounding_boxes.labels`).

## Requirements

Install dependencies:

```bash
pip install google-genai pillow pillow-heif
```

Set your Gemini API key:

```bash
# Linux / macOS
export GEMINI_API_KEY="your_api_key"

# Windows (PowerShell)
$env:GEMINI_API_KEY="your_api_key"
```

## Usage

1. Place source images (`.heic`, `.jpg`, `.png`) into `./dataset_fotos/`.
2. Run the script:
   ```bash
   python labelling.py
   ```
3. Upload the resulting `./output_edge_impulse/` directory to Edge Impulse Studio.
