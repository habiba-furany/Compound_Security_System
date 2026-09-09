
from ultralytics import YOLO  
import numpy as np

parking_model = YOLO(r"models\parking.pt")   

def analyze_parking_occupancy(frame):
    results = parking_model(frame, verbose=False)
    
    if len(results[0].boxes) == 0:
        return {"occupied": 0, "free": 0, "total": 0}
    
    total_spots = len(results[0].boxes)
    
    classes = results[0].boxes.cls.tolist()
    occupied = classes.count(1)
    free = classes.count(0)
    
    return {"occupied": occupied, "free": free, "total": total_spots}