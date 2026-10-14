import os
import jwt
from functools import wraps
from jwt import PyJWKClient
from dotenv import load_dotenv
from pathlib import Path
from uuid import uuid4
import subprocess
import time

import imageio_ffmpeg
import cv2
import numpy as np
from flask import Flask, jsonify, render_template, request, url_for
from PIL import Image
from ultralytics import YOLO

app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
UPLOAD_DIR = STATIC_DIR / "uploads"
RESULT_DIR = STATIC_DIR / "results"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
RESULT_DIR.mkdir(parents=True, exist_ok=True)

app.config["MAX_CONTENT_LENGTH"] = 200 * 1024 * 1024

MODEL_PATH = BASE_DIR / "best.pt"
model = None

def ensure_model_loaded():
    global model

    if model is None and MODEL_PATH.exists():
        model = YOLO(str(MODEL_PATH))

    return model

IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
VIDEO_EXTENSIONS = {"mp4", "mov", "avi", "mkv", "webm"}


def has_extension(filename, allowed):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in allowed
    )


def class_name(class_id):
    names = model.names
    if isinstance(names, dict):
        return str(names.get(class_id, f"class_{class_id}"))
    return str(names[class_id])

def require_auth(view_function):
    @wraps(view_function)
    def wrapped(*args, **kwargs):
        if jwks_client is None:
            return jsonify({"error": "Supabase is not configured."}), 503

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "Authentication required."}), 401

        token = auth_header.split(" ", 1)[1].strip()

        try:
            signing_key = jwks_client.get_signing_key_from_jwt(token)

            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["ES256"],
                audience="authenticated",
                issuer=SUPABASE_ISSUER
            )

            if not payload.get("sub"):
                return jsonify({"error": "Invalid user token."}), 401

        except jwt.PyJWTError:
            return jsonify({"error": "Invalid or expired session. Please sign in again."}), 401
        except Exception:
            app.logger.exception("Supabase token verification failed")
            return jsonify({"error": "Authentication verification failed."}), 503

        return view_function(*args, **kwargs)

    return wrapped

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/status")
def status():
    return jsonify({
        "model_loaded": model is not None,
        "model": MODEL_PATH.name if model is not None else None
    })


@app.route("/api/detect-image", methods=["POST"])
@require_auth
def detect_image():
    if ensure_model_loaded() is None:
        return jsonify({"error": "Model weights best.pt were not found."}), 503

    file = request.files.get("file")
    if file is None or not file.filename:
        return jsonify({"error": "Please select an image."}), 400

    if not has_extension(file.filename, IMAGE_EXTENSIONS):
        return jsonify({"error": "Unsupported image format."}), 400

    try:
        image = Image.open(file.stream).convert("RGB")
        image_bgr = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

        confidence = float(request.form.get("confidence", 0.25))
        confidence = max(0.05, min(confidence, 0.95))

        result = model.predict(
            image_bgr,
            conf=confidence,
            imgsz=640,
            verbose=False
        )[0]

        counts = {}
        detections = []

        if result.boxes is not None:
            for box, cls, conf in zip(
                result.boxes.xyxy.cpu().numpy(),
                result.boxes.cls.cpu().numpy().astype(int),
                result.boxes.conf.cpu().numpy()
            ):
                name = class_name(int(cls))
                counts[name] = counts.get(name, 0) + 1
                detections.append({
                    "class": name,
                    "confidence": round(float(conf), 4),
                    "box": [round(float(v), 2) for v in box]
                })

        output_name = f"{uuid4().hex}.jpg"
        output_path = RESULT_DIR / output_name

        if not cv2.imwrite(str(output_path), result.plot()):
            return jsonify({"error": "Could not save the result image."}), 500

        return jsonify({
            "success": True,
            "result_url": url_for("static", filename=f"results/{output_name}"),
            "total_bees_detected": len(detections),
            "class_counts": counts,
            "detections": detections
        })

    except Exception:
        app.logger.exception("Image detection failed")
        return jsonify({"error": "Image processing failed."}), 500


@app.route("/api/process-video", methods=["POST"])
@require_auth
def process_video():
    if ensure_model_loaded() is None:
        return jsonify({"error": "Model weights best.pt were not found."}), 503

    file = request.files.get("video")
    if file is None or not file.filename:
        return jsonify({"error": "Please select a video."}), 400

    if not has_extension(file.filename, VIDEO_EXTENSIONS):
        return jsonify({"error": "Unsupported video format."}), 400

    input_path = None
    output_path = None
    converted_path = None
    cap = None
    writer = None

    try:
        confidence = float(request.form.get("confidence", 0.25))
        confidence = max(0.05, min(confidence, 0.95))

        line_percent = float(request.form.get("line_percent", 50))
        line_percent = max(10, min(line_percent, 90))

        input_path = UPLOAD_DIR / f"{uuid4().hex}_{Path(file.filename).name}"
        output_name = f"{uuid4().hex}.mp4"
        output_path = RESULT_DIR / output_name

        file.save(input_path)

        cap = cv2.VideoCapture(str(input_path))
        if not cap.isOpened():
            return jsonify({
                "error": "Could not open this video. Try converting it to MP4."
            }), 400

        fps = cap.get(cv2.CAP_PROP_FPS)
        if not fps or fps <= 0:
            fps = 25.0

        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        if width <= 0 or height <= 0:
            return jsonify({"error": "Invalid video dimensions."}), 400

        target_frames = 125
        frame_interval = max(1, round(total_frames / target_frames))
        output_fps = fps / frame_interval
        wall_top = int(height * 0.38)
        wall_bottom = int(height * 0.57)

        writer = cv2.VideoWriter(
            str(output_path),
            cv2.VideoWriter_fourcc(*"mp4v"),
            output_fps,
            (width, height)
        )

        if not writer.isOpened():
            return jsonify({
                "error": "Could not create output video on this system."
            }), 500

        previous_y = {}
        unique_bees = {}
        counted_ids = set()
        crossings = {
            "IN": {"Normal bees": 0, "Pollen bees": 0},
            "OUT": {"Normal bees": 0, "Pollen bees": 0}
        }

        processed_frames = 0
        detection_totals = {}
        frame_index = 0
        start_time = time.perf_counter()

        while True:
            ok, frame = cap.read()
            if not ok:
                break

            current_index = frame_index
            frame_index += 1

            if current_index % frame_interval != 0:
                continue

            result = model.track(
                frame,
                persist=True,
                tracker="bytetrack.yaml",
                conf=confidence,
                imgsz=640,
                verbose=False
            )[0]

            annotated = result.plot()
            overlay = annotated.copy()

            cv2.rectangle(
                overlay,
                (0, wall_top),
                (width - 1, wall_bottom),
                (0, 165, 255),
                -1
            )

            annotated = cv2.addWeighted(overlay, 0.25, annotated, 0.75, 0)

            cv2.line(
                annotated,
                (0, wall_top),
                (width - 1, wall_top),
                (0, 165, 255),
                2
            )

            cv2.line(
                annotated,
                (0, wall_bottom),
                (width - 1, wall_bottom),
                (0, 165, 255),
                2
            )

            cv2.putText(
                annotated,
                "VIRTUAL WALL",
                (20, max(25, wall_top - 8)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 165, 255),
                2
            )

            boxes = result.boxes

            if boxes is not None:
                for cls_id in boxes.cls.cpu().numpy().astype(int):
                    name = class_name(int(cls_id))
                    detection_totals[name] = (
                        detection_totals.get(name, 0) + 1
                    )

                if boxes.id is not None:
                    ids = boxes.id.cpu().numpy().astype(int)
                    xyxy = boxes.xyxy.cpu().numpy()
                    classes = boxes.cls.cpu().numpy().astype(int)

                    for track_id, box, cls_id in zip(ids, xyxy, classes):
                        x1, y1, x2, y2 = box
                        center_y = int((y1 + y2) / 2)
                        name = class_name(int(cls_id))
                        unique_bees[track_id] = name

                        if track_id in previous_y:
                            old_y = previous_y[track_id]
                            direction = None

                            if old_y < wall_top and center_y >= wall_top:
                                direction = "IN"
                            elif old_y > wall_bottom and center_y <= wall_bottom:
                                direction = "OUT"

                            if direction and track_id not in counted_ids:
                                if name not in crossings[direction]:
                                    crossings[direction][name] = 0

                                crossings[direction][name] += 1
                                counted_ids.add(track_id)

                        previous_y[track_id] = center_y

            cv2.putText(
                annotated,
                f"IN: {sum(crossings['IN'].values())}",
                (20, 35),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 255, 0),
                2
            )

            cv2.putText(
                annotated,
                f"OUT: {sum(crossings['OUT'].values())}",
                (20, 70),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 0, 255),
                2
            )

            writer.write(annotated)
            processed_frames += 1

        elapsed_seconds = time.perf_counter() - start_time
        processing_fps = (
            processed_frames / elapsed_seconds
            if elapsed_seconds > 0 else 0
        )

        cap.release()
        cap = None
        writer.release()
        writer = None

        input_path.unlink(missing_ok=True)

        if processed_frames == 0 or not output_path.exists():
            output_path.unlink(missing_ok=True)
            return jsonify({"error": "No video frames could be processed."}), 400

        converted_path = output_path.with_name(
            output_path.stem + "_h264.mp4"
        )

        try:
            ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()

            subprocess.run(
                [
                    ffmpeg_exe,
                    "-y",
                    "-i", str(output_path),
                    "-c:v", "libx264",
                    "-pix_fmt", "yuv420p",
                    "-movflags", "+faststart",
                    "-an",
                    str(converted_path)
                ],
                check=True,
                capture_output=True,
                text=True
            )

            if not converted_path.exists() or converted_path.stat().st_size == 0:
                raise RuntimeError("Converted video is empty.")

            output_path.unlink(missing_ok=True)
            converted_path.replace(output_path)

        except Exception:
            app.logger.exception("MP4 conversion failed")
            converted_path.unlink(missing_ok=True)
            output_path.unlink(missing_ok=True)
            return jsonify({
                "error": "Video was processed, but browser-compatible encoding failed."
            }), 500

        return jsonify({
            "success": True,
            "result_url": url_for("static", filename=f"results/{output_name}"),
            "processed_frames": processed_frames,
            "source_frames": total_frames,
            "sampling_interval": frame_interval,
            "target_frames": target_frames,
            "processing_seconds": round(elapsed_seconds, 2),
            "processing_fps": round(processing_fps, 2),
            "unique_tracks_seen": len(unique_bees),
            "detection_totals_across_frames": detection_totals,
            "unique_tracks_by_class": {
                name: sum(1 for value in unique_bees.values() if value == name)
                for name in set(unique_bees.values())
            },
            "crossings": crossings,
            "wall_position_percent": line_percent,
            "wall_thickness_pixels": wall_bottom - wall_top,
            "note": (
                "Counts are estimates. A track is counted at most once "
                "for IN or OUT combined. Tracking IDs can switch or disappear."
            )
        })

    except Exception:
        app.logger.exception("Video processing failed")
        return jsonify({
            "error": "Video processing failed. Check the server log."
        }), 500

    finally:
        if cap is not None:
            cap.release()
        if writer is not None:
            writer.release()
        if input_path is not None:
            input_path.unlink(missing_ok=True)

@app.route("/api/config")
def public_config():
    return jsonify({
        "supabase_url": os.getenv("SUPABASE_URL"),
        "supabase_publishable_key": os.getenv("SUPABASE_PUBLISHABLE_KEY")
    })

@app.route("/login")
def login_page():
    return render_template("login.html")


@app.route("/register")
def register_page():
    return render_template("register.html")

@app.errorhandler(413)
def file_too_large(error):
    return jsonify({"error": "File exceeds the 200 MB upload limit."}), 413


load_dotenv(BASE_DIR / ".env")

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_ISSUER = f"{SUPABASE_URL}/auth/v1"

jwks_client = (
    PyJWKClient(f"{SUPABASE_ISSUER}/.well-known/jwks.json")
    if SUPABASE_URL
    else None
)

@app.route("/health", methods=["GET"])
def health():
    return {"status": "healthy"}, 200


if __name__ == "__main__":
    app.run(debug=True)
