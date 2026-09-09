from ultralytics import YOLO
import cv2


parking_model = YOLO(r"models\parking (2).pt")


def analyze_parking_occupancy(frame, return_annotated=False):

    results = parking_model(frame, verbose=False)
    result = results[0]

    if len(result.boxes) == 0:

        data = {
            "occupied": 0,
            "free": 0,
            "total": 0
        }

        if return_annotated:
            return data, frame

        return data

    total_spots = len(result.boxes)

    classes = result.boxes.cls.tolist()

    occupied = classes.count(1)
    free = classes.count(0)

    data = {
        "occupied": occupied,
        "free": free,
        "total": total_spots
    }

    # Draw bounding boxes without confidence
    if return_annotated:

        annotated_frame = frame.copy()

        for box, cls in zip(
            result.boxes.xyxy,
            result.boxes.cls
        ):

            x1, y1, x2, y2 = map(
                int,
                box.tolist()
            )

            class_id = int(cls.item())

            # Occupied = Blue
            if class_id == 1:
                label = "occupied"
                box_color = (255, 0, 0)

            # Empty = Red
            else:
                label = "empty"
                box_color = (0, 0, 255)

            # Draw bounding box
            cv2.rectangle(
                annotated_frame,
                (x1, y1),
                (x2, y2),
                box_color,
                2
            )

            # Draw class name without confidence
            cv2.putText(
                annotated_frame,
                label,
                (x1, max(y1 - 5, 20)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                box_color,
                2
            )

        return data, annotated_frame

    return data