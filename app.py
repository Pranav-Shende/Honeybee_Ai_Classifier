
from pathlib import Path
from uuid import uuid4

import cv2
import numpy as np
from flask import Flask, jsonify, render_template, request, url_for
from PIL import Image
from ultralytics import YOLO

app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "static" / "uploads"
RESULT_DIR = BASE_DIR / "static" / "results"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
RESULT_DIR.mkdir(parents=True, exist_ok=True)

app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024

MODEL_PATH = BASE_DIR / "best.pt"
model = YOLO(str(MODEL_PATH)) if MODEL_PATH.exists() else None

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}


def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


def get_class_name(class_id):
    names = model.names
    if isinstance(names, dict):
        return str(names.get(class_id, f"class_{class_id}"))
    return str(names[class_id])


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/status")
def status():
    return jsonify({
        "model_loaded": model is not None,
        "model": str(MODEL_PATH.name) if model is not None else None
    })


@app.route("/api/detect-image", methods=["POST"])
def detect_image():
    if model is None:
        return jsonify({"error": "Model weights best.pt were not found."}), 503

    if "file" not in request.files:
        return jsonify({"error": "Please upload an image."}), 400

    file = request.files["file"]

    if not file.filename or not allowed_file(file.filename):
        return jsonify({"error": "Unsupported image format."}), 400

    try:
        image = Image.open(file.stream).convert("RGB")
        image_array = cv2.cvtColor(np.array(image),
                                    cv2.COLOR_RGB2BGR)

        confidence = float(request.form.get("confidence", 0.25))
        confidence = max(0.05, min(confidence, 0.95))

        result = model.predict(
            image_array,
            conf=confidence,
            imgsz=640,
            verbose=False
        )[0]

        counts = {}
        detections = []

        if result.boxes is not None:
            boxes = result.boxes

            for xyxy, cls, conf in zip(
                boxes.xyxy.cpu().numpy(),
                boxes.cls.cpu().numpy().astype(int),
                boxes.conf.cpu().numpy()
            ):
                name = get_class_name(int(cls))
                counts[name] = counts.get(name, 0) + 1

                detections.append({
                    "class": name,
                    "confidence": round(float(conf), 4),
                    "box": [round(float(v), 2) for v in xyxy]
                })
                

        annotated = result.plot()
        output_name = f"{uuid4().hex}.jpg"
        output_path = RESULT_DIR / output_name

        if not cv2.imwrite(str(output_path), annotated):
            return jsonify({"error": "Could not save annotated image."}), 500

        return jsonify({
            "success": True,
            "result_url": url_for(
                "static",
                filename=f"results/{output_name}"
            ),
            "total_bees_detected": len(detections),
            "class_counts": counts,
            "detections": detections
        })

    except Exception as exc:
        app.logger.exception("Image detection failed")
        return jsonify({"error": str(exc)}), 500


@app.errorhandler(413)
def file_too_large(error):
    return jsonify({"error": "File exceeds the 50 MB limit."}), 413


if __name__ == "__main__":
    app.run(debug=True)
