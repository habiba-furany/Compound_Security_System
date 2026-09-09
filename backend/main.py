from fastapi import FastAPI, UploadFile
import cv2
import numpy as np

from core.parking import analyze_parking_occupancy
from core.gate_logic import process_entry, process_exit
from database.db import create_tables

app = FastAPI()
create_tables()

### parking  endpoint
@app.post("/parking/status")
async def parking_status(file: UploadFile):
    contents = await file.read()
    frame = cv2.imdecode(np.frombuffer(contents, np.uint8), cv2.IMREAD_COLOR)
    
    result = analyze_parking_occupancy(frame)
    return result


### entry gate
@app.post("/gate/entry")
async def gate_entry(file: UploadFile):
    contents = await file.read()
    frame = cv2.imdecode(np.frombuffer(contents, np.uint8), cv2.IMREAD_COLOR)
    return process_entry(frame)

### exit gate
@app.post("/gate/exit")
async def gate_exit(file: UploadFile):
    contents = await file.read()
    frame = cv2.imdecode(np.frombuffer(contents, np.uint8), cv2.IMREAD_COLOR)
    return process_exit(frame)
 