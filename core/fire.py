from ultralytics import YOLO

fire_model = YOLO(r"models\fire_smoke.pt")

def check_fire_smoke(frame, conf_threshold=0.45):
    results = fire_model(frame, verbose=False)

    detection_result = {
        "has_fire": False,
        "has_smoke": False,
        "detections": []
    }

    for r in results:
        boxes = r.boxes
        for box in boxes:
            conf = float(box.conf[0])
            cls_id = int(box.cls[0])
            cls_name = fire_model.names[cls_id]

            if conf >= conf_threshold:
                if cls_name == 'fire':
                    detection_result["has_fire"] = True
                elif cls_name == 'smoke':
                    detection_result["has_smoke"] = True

                coords = box.xyxy[0].tolist()
                detection_result["detections"].append({
                    "class": cls_name,
                    "confidence": round(conf, 2),
                    "box": [int(c) for c in coords]
                })

    return detection_result