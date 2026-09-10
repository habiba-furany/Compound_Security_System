from ultralytics import YOLO
import cv2
import numpy as np

plate_model = YOLO(r"models/plate.pt")
ocr_model = YOLO(r"models/best.pt")

def map_to_arabic(numbers, letters):
    number_map = {
        '0': '٠', '1': '١', '2': '٢', '3': '٣', '4': '٤',
        '5': '٥', '6': '٦', '7': '٧', '8': '٨', '9': '٩'
    }
    letter_map = {
        'alif': 'ا', 'baa': 'ب', 'taa': 'ت', 'thaa': 'ث',
        'jeem': 'ج', 'haa': 'ح', 'khaa': 'خ', 'daal': 'د',
        'zaal': 'ذ', 'raa': 'ر', 'zay': 'ز', 'seen': 'س',
        'sheen': 'ش', 'saad': 'ص', 'daad': 'ض', 'Taa': 'ط',
        'Thaa': 'ظ', 'ain': 'ع', 'ghayn': 'غ', 'faa': 'ف',
        'qaaf': 'ق', 'kaaf': 'ك', 'laam': 'ل', 'meem': 'م',
        'noon': 'ن', 'haah': 'ه', 'waw': 'و', 'yaa': 'ي',
        '7aa': 'ح'
    }
    arabic_numbers = [number_map.get(num, num) for num in reversed(numbers)]
    arabic_letters = [letter_map.get(letter, letter) for letter in reversed(letters)]
    return ' '.join(arabic_letters + arabic_numbers)

def get_plate_number(frame):
  
    if frame is None:
        return None
        
    image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    plates = plate_model(image_rgb, verbose=False)[0]
    
    extracted_texts = []
    
    for plate in plates.boxes.data.tolist():
        x1, y1, x2, y2, score, class_id = plate
        plate_cropped = image_rgb[int(y1):int(y2), int(x1):int(x2)]
        
        if plate_cropped.size == 0:
            continue

        result = ocr_model.predict(source=plate_cropped, conf=0.25, verbose=False)[0]
        if not result.boxes:
            continue
            
        sorted_boxes = sorted(result.boxes, key=lambda b: b.xyxy[0][0].item())

        detected_numbers = []
        detected_letters = []

        for box in sorted_boxes:
            cls_id = int(box.cls)
            label = result.names[cls_id]
            if label.isdigit():
                detected_numbers.append(label)
            else:
                detected_letters.append(label)

        arabic_text = map_to_arabic(detected_numbers, detected_letters)
        if arabic_text:
            extracted_texts.append(arabic_text)

    if extracted_texts:
        return " - ".join(extracted_texts)  

    return None