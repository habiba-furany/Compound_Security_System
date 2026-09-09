import cv2
from fast_alpr import ALPR

alpr = ALPR(
    detector_model="yolo-v9-t-384-license-plate-end2end",
    ocr_model="cct-xs-v2-global-model",
    detector_providers=["CPUExecutionProvider"],
    ocr_providers=["CPUExecutionProvider"],
)


def get_plate_number(frame):
    results = alpr.predict(frame)

    extracted_texts = []
    for r in results:
        if r.ocr and r.ocr.text:
            text = r.ocr.text.strip()
            if text:
                extracted_texts.append(text)

    if extracted_texts:
        return "".join(extracted_texts)

    return None