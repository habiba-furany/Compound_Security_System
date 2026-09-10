
from ultralytics import YOLO

brand_model = YOLO(r"models/brand.pt") 


def predict_brand(image):
    results = brand_model(image)
    result = results[0]

    if len(result.boxes) == 0:
        return "No car detected" , 0

    best_box = max(
        result.boxes,
        key=lambda x: float(x.conf[0])
    )

    class_id = int(best_box.cls[0])
    confidence = float(best_box.conf[0])
    brand = brand_model.names[class_id]

    return brand,confidence