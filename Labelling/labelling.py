import os
import time
import json
import shutil
from pathlib import Path
from PIL import Image
import pillow_heif
from google import genai
from google.genai import types

# Enable HEIC support
pillow_heif.register_heif_opener()

# Configuration
API_KEY = os.environ.get("GEMINI_API_KEY", "AQ.Ab8R_FAKE_API_KEY_AUo__46ID9r1A")
INPUT_DIR = "./dataset_fotos"
OUTPUT_DIR = "./output_edge_impulse"
MODEL_NAME = "gemini-3.5-flash-lite"

client = genai.Client(api_key=API_KEY)

PROMPT = """
Detect all food containers, jars, cans, or bottles of garbanzos (chickpeas) and tomate frito (fried tomato sauce) in this image.
Return the 2D bounding boxes as a clean JSON list.

Allowed labels ONLY:
- "garbanzos"
- "tomate"

Rules:
- Coordinates must be normalized integers [0, 1000] in the exact order: [ymin, xmin, ymax, xmax].
- Make each bounding box fit tightly around the container.
- If the image shows only an empty background, table, hands, or irrelevant objects without garbanzos or tomate, you MUST return an empty list: [].
- Do not label any other food, person, or background element.

Output schema:
[
  {
    "box_2d": [ymin, xmin, ymax, xmax],
    "label": "garbanzos" | "tomate"
  }
]
"""

def process_and_export_dataset(input_dir: str, output_dir: str):
    input_path = Path(input_dir)
    output_path = Path(output_dir)

    output_path.mkdir(parents=True, exist_ok=True)

    supported_extensions = {".heic", ".HEIC", ".jpg", ".jpeg", ".JPG", ".JPEG", ".png", ".PNG"}
    files_to_process = [f for f in input_path.iterdir() if f.suffix in supported_extensions]

    if not files_to_process:
        print(f"No se encontraron imágenes en: {input_dir}")
        return

    print(f"Total imágenes a procesar: {len(files_to_process)}")
    print(f"Guardando resultados limpios en: {output_path.resolve()}\n")

    ei_labels_data = {
        "version": 1,
        "type": "bounding-box-labels",
        "boundingBoxes": {}
    }

    for idx, file_path in enumerate(files_to_process, start=1):
        # Convert HEIC or copy image
        if file_path.suffix.lower() == ".heic":
            final_img_path = output_path / f"{file_path.stem}.jpg"
            with Image.open(file_path) as img:
                img.convert("RGB").save(final_img_path, "JPEG", quality=95)
        else:
            final_img_path = output_path / file_path.name
            shutil.copy2(file_path, final_img_path)

        print(f"[{idx}/{len(files_to_process)}] Analizando: {final_img_path.name} ...")

        # Query Gemini
        try:
            with Image.open(final_img_path) as pil_img:
                img_width, img_height = pil_img.size

            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=[
                    types.Part.from_bytes(
                        data=final_img_path.read_bytes(),
                        mime_type="image/jpeg" if final_img_path.suffix.lower() in [".jpg", ".jpeg"] else "image/png",
                    ),
                    PROMPT
                ],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.0
                )
            )

            detected_objects = json.loads(response.text.strip())

            # Convert normalized coordinates to pixels
            sample_boxes = []
            for obj in detected_objects:
                label = obj.get("label", "").lower()
                if label not in ["garbanzos", "tomate"]:
                    continue

                ymin_norm, xmin_norm, ymax_norm, xmax_norm = obj["box_2d"]

                xmin_px = int((xmin_norm / 1000.0) * img_width)
                ymin_px = int((ymin_norm / 1000.0) * img_height)
                xmax_px = int((xmax_norm / 1000.0) * img_width)
                ymax_px = int((ymax_norm / 1000.0) * img_height)

                width_px = max(1, xmax_px - xmin_px)
                height_px = max(1, ymax_px - ymin_px)

                sample_boxes.append({
                    "label": label,
                    "x": xmin_px,
                    "y": ymin_px,
                    "width": width_px,
                    "height": height_px
                })

            ei_labels_data["boundingBoxes"][final_img_path.name] = sample_boxes
            print(f"  -> {len(sample_boxes)} botes detectados.")

        except Exception as e:
            print(f"  -> Error en {final_img_path.name}: {e}")
            ei_labels_data["boundingBoxes"][final_img_path.name] = []

        # Rate limit (15 RPM)
        time.sleep(4.1)

    # Save Edge Impulse labels
    output_labels_file = output_path / "bounding_boxes.labels"
    with open(output_labels_file, "w", encoding="utf-8") as f:
        json.dump(ei_labels_data, f, indent=2)

    print("\n" + "="*60)
    print("PROCESO FINALIZADO CON ÉXITO")
    print(f"Directorio listo para subir: {output_path.resolve()}")
    print(f"Contenido: Todas las fotos (.jpg/.png) + {output_labels_file.name}")
    print("="*60)

if __name__ == "__main__":
    process_and_export_dataset(INPUT_DIR, OUTPUT_DIR)
