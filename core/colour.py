from ultralytics import YOLO

color_model = YOLO(r"models\color2.pt")   


def get_dominant_color(frame, conf_threshold=0.5):
    results = color_model(frame, verbose=False)

    detections = []
    for r in results:
        for box in r.boxes:
            conf = float(box.conf[0])
            if conf >= conf_threshold:
                cls_id = int(box.cls[0])
                detections.append({
                    "color": color_model.names[cls_id],
                    "confidence": round(conf, 2),
                })

    if not detections:
        return None

    best = max(detections, key=lambda d: d["confidence"])
    return best["color"]