
from pathlib import Path
from ultralytics import YOLO

DATA_YAML = "dataset/data.yaml"
V2_WEIGHTS = "best.pt"

if not Path(DATA_YAML).exists():
    raise FileNotFoundError(f"Dataset YAML not found: {DATA_YAML}")

if Path(V2_WEIGHTS).exists():
    try:
        model = YOLO(V2_WEIGHTS)
        print("Loaded V2 weights.")
    except Exception as e:
        print(f"V2 weights could not be loaded: {e}")
        print("Using official YOLO26 Small weights instead.")
        model = YOLO("yolo26s.pt")
else:
    model = YOLO("yolo26s.pt")

model.train(
    data=DATA_YAML,
    epochs=50,
    imgsz=640,
    batch=8,
    patience=10,
    workers=2,
    project="runs/honeybee",
    name="prototype"
)

best_model = Path("runs/honeybee/prototype/weights/best.pt")
if best_model.exists():
    print(f"Training complete. Best weights: {best_model}")
