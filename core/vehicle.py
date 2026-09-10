import tensorflow as tf
import numpy as np
from PIL import Image
import cv2

MODEL_PATH = r"models/vehicle_classifier.keras"   
model = tf.keras.models.load_model(MODEL_PATH)

CLASS_NAMES = ["Auto rickshaw", "Cars", "Trocyle"]


def detect_vehicle_type(frame):
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    image = Image.fromarray(rgb_frame).resize((224, 224))

    image_array = np.expand_dims(np.array(image), axis=0)
    predictions = model.predict(image_array, verbose=0)

    predicted_index = np.argmax(predictions[0])
    predicted_class = CLASS_NAMES[predicted_index]
    confidence = float(predictions[0][predicted_index])

    return predicted_class, confidence