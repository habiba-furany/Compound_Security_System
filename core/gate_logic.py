from core.vehicle import detect_vehicle_type
from core.plate import get_plate_number
from core.colour import get_dominant_color
from core.brand import predict_brand

from database.db import register_entry, register_exit

BANNED_TYPES = ["Auto rickshaw", "Trocyle"]   

def process_entry(frame):
    # 1.type
    vehicle_type, type_confidence = detect_vehicle_type(frame)

    if vehicle_type in BANNED_TYPES:
        return {"decision": "DENIED", "reason": "Vehicle type not allowed", "type": vehicle_type}

    # 2. plate
    plate = get_plate_number(frame)
    if plate is None:
        return {"decision": "ERROR", "reason": "Could not read plate"}

    # 3. colour
    color = get_dominant_color(frame)
    
    # 4. brand
    brand, brand_confidence = predict_brand(frame)   

    # 5. registeration
    register_entry(plate, vehicle_type, brand, color)

    return {
        "decision": "ALLOWED",
        "plate": plate,
        "type": vehicle_type,
        "brand": brand,
        "color": color,
    }

## exit gate
def process_exit(frame):
    plate = get_plate_number(frame)
    if plate is None:
        return {"decision": "ERROR", "reason": "Could not read plate"}

    register_exit(plate)
    return {"plate": plate, "status": "exited"}