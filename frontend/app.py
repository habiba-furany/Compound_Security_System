import streamlit as st
import sqlite3
import pandas as pd
from pathlib import Path
from datetime import datetime
import cv2
import numpy as np
import requests
import streamlit as st
import sys
import tempfile
import os
import time

sys.path.append(str(Path(__file__).resolve().parent.parent))

from core.gate_logic import process_entry, process_exit
from core.parking import analyze_parking_occupancy

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "database" / "compound.db"

def draw_fire_boxes(frame, detections):
    for det in detections:
        box = det["box"]  
        cls_name = det["class"]
        conf = det["confidence"]

        color = (0, 255, 0) if cls_name == "fire" else (0, 165, 255)

        cv2.rectangle(
            frame, (box[0], box[1]), (box[2], box[3]), color, 2
        )

        label = f"{cls_name}"
        cv2.putText(
            frame,
            label,
            (box[0], max(20, box[1] - 10)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            color,
            2,
        )
    return frame

def process_single_video_for_fire(video_bytes, frame_placeholder, alerts_placeholder, threat_placeholder, sample_rate=5):
    temp_input = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
    temp_input.write(video_bytes)
    temp_input.close()

    cap = cv2.VideoCapture(temp_input.name)
    fps = cap.get(cv2.CAP_PROP_FPS) or 20
    frame_delay = 1 / fps

    area_threat = "LOW"
    frame_index = 0
    last_detections = []
    
    fire_count = 0
    smoke_count = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_index % sample_rate == 0:
            _, encoded = cv2.imencode(".jpg", frame)
            try:
                response = requests.post(
                    "http://127.0.0.1:8000/safety/fire-smoke",
                    files={"file": encoded.tobytes()},
                )
                result = response.json()
                last_detections = result.get("detections", [])

                fire_count = len([d for d in last_detections if d["class"] == "fire"])
                smoke_count = len([d for d in last_detections if d["class"] == "smoke"])

                if fire_count > 0:
                    area_threat = "HIGH"
                elif smoke_count > 0:
                    area_threat = "MEDIUM"
                else:
                    area_threat = "LOW"

                alerts_placeholder.metric("Fire/Smoke Alerts", f"🔥 {fire_count} / 💨 {smoke_count}")
                threat_placeholder.metric("Threat Level", area_threat)

                st.session_state.fire_alert_count = fire_count + smoke_count
                st.session_state.threat_level = area_threat

            except Exception:
                pass

        annotated_frame = draw_fire_boxes(frame, last_detections)
        annotated_rgb = cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB)
        frame_placeholder.image(annotated_rgb, use_container_width=True)

        time.sleep(frame_delay)
        frame_index += 1

    cap.release()
    os.remove(temp_input.name)

    st.session_state.fire_alert_count = fire_count + smoke_count
    st.session_state.threat_level = area_threat

    return area_threat

def process_two_videos_for_fire(
    video1_bytes, video2_bytes,
    frame_placeholder1, alerts_placeholder1, threat_placeholder1,
    frame_placeholder2, alerts_placeholder2, threat_placeholder2,
    sample_rate=5,
):
    temp1 = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
    temp1.write(video1_bytes)
    temp1.close()

    temp2 = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
    temp2.write(video2_bytes)
    temp2.close()

    cap1 = cv2.VideoCapture(temp1.name)
    cap2 = cv2.VideoCapture(temp2.name)

    fps1 = cap1.get(cv2.CAP_PROP_FPS) or 20
    fps2 = cap2.get(cv2.CAP_PROP_FPS) or 20
    frame_delay = 1 / max(fps1, fps2)

    area1_threat = "LOW"
    area2_threat = "LOW"
    last_detections1 = []
    last_detections2 = []
    frame_index = 0

    fire1, smoke1 = 0, 0
    fire2, smoke2 = 0, 0

    while True:
        ret1, frame1 = cap1.read()
        ret2, frame2 = cap2.read()

        if not ret1 and not ret2:
            break

        # ---- Area 1 ----
        if ret1:
            if frame_index % sample_rate == 0:
                _, encoded1 = cv2.imencode(".jpg", frame1)
                try:
                    response = requests.post(
                        "http://127.0.0.1:8000/safety/fire-smoke",
                        files={"file": encoded1.tobytes()},
                    )
                    result = response.json()
                    last_detections1 = result.get("detections", [])

                    fire1 = len([d for d in last_detections1 if d["class"] == "fire"])
                    smoke1 = len([d for d in last_detections1 if d["class"] == "smoke"])

                    area1_threat = "HIGH" if fire1 > 0 else ("MEDIUM" if smoke1 > 0 else "LOW")

                    alerts_placeholder1.metric("Fire/Smoke Alerts", f"🔥 {fire1} / 💨 {smoke1}")
                    threat_placeholder1.metric("Threat Level", area1_threat)

                except Exception:
                    pass

            annotated1 = draw_fire_boxes(frame1, last_detections1)
            annotated1 = cv2.cvtColor(annotated1, cv2.COLOR_BGR2RGB)
            frame_placeholder1.image(annotated1, use_container_width=True)

        # ---- Area 2 ----
        if ret2:
            if frame_index % sample_rate == 0:
                _, encoded2 = cv2.imencode(".jpg", frame2)
                try:
                    response = requests.post(
                        "http://127.0.0.1:8000/safety/fire-smoke",
                        files={"file": encoded2.tobytes()},
                    )
                    result = response.json()
                    last_detections2 = result.get("detections", [])

                    fire2 = len([d for d in last_detections2 if d["class"] == "fire"])
                    smoke2 = len([d for d in last_detections2 if d["class"] == "smoke"])

                    area2_threat = "HIGH" if fire2 > 0 else ("MEDIUM" if smoke2 > 0 else "LOW")

                    alerts_placeholder2.metric("Fire/Smoke Alerts", f"🔥 {fire2} / 💨 {smoke2}")
                    threat_placeholder2.metric("Threat Level", area2_threat)

                except Exception:
                    pass

            annotated2 = draw_fire_boxes(frame2, last_detections2)
            annotated2 = cv2.cvtColor(annotated2, cv2.COLOR_BGR2RGB)
            frame_placeholder2.image(annotated2, use_container_width=True)

        total_fires = fire1 + fire2
        total_smokes = smoke1 + smoke2
        st.session_state.fire_alert_count = total_fires + total_smokes

        overall_threat = "HIGH" if "HIGH" in [area1_threat, area2_threat] else (
            "MEDIUM" if "MEDIUM" in [area1_threat, area2_threat] else "LOW"
        )
        st.session_state.threat_level = overall_threat

        time.sleep(frame_delay)
        frame_index += 1

    cap1.release()
    cap2.release()
    os.remove(temp1.name)
    os.remove(temp2.name)

    st.session_state.fire_alert_count = (fire1 + fire2) + (smoke1 + smoke2)
    st.session_state.threat_level = "HIGH" if "HIGH" in [area1_threat, area2_threat] else (
        "MEDIUM" if "MEDIUM" in [area1_threat, area2_threat] else "LOW"
    )

    return area1_threat, area2_threat
# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="CompoundGuard",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# DATABASE SETUP & HELPER FUNCTIONS
# ============================================================

def get_all_vehicles_today():
    if not DB_PATH.exists():
        return pd.DataFrame(columns=["ID", "Plate", "Brand", "Color", "Entry Time", "Exit Time"])
    try:
        conn = sqlite3.connect(DB_PATH)
        query = """
            SELECT id, plate, brand, color, entry_time, exit_time
            FROM vehicles
            ORDER BY id DESC
        """
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    except Exception:
        return pd.DataFrame(columns=["ID", "Plate", "Brand", "Color", "Entry Time", "Exit Time"])

def get_dashboard_metrics():
    if not DB_PATH.exists():
        return {"inside": 0, "entries_today": 0, "exits_today": 0}

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT() FROM vehicles WHERE exit_time IS NULL OR exit_time = ''")
        vehicles_inside = cursor.fetchone()[0]

        today_date = datetime.now().strftime("%Y-%m-%d")
        cursor.execute("SELECT COUNT() FROM vehicles WHERE DATE(entry_time) = ?", (today_date,))
        entries_today = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM vehicles WHERE DATE(exit_time) = ?", (today_date,))
        exits_today = cursor.fetchone()[0]

        conn.close()
        return {
            "inside": vehicles_inside,
            "entries_today": entries_today,
            "exits_today": exits_today
        }
    except Exception:
        return {"inside": 0, "entries_today": 0, "exits_today": 0}


# ============================================================
# CUSTOM STYLE
# CSS ONLY — NO HTML COMPONENTS
# ============================================================

st.markdown(
    """
    <style>

    /* ---------- MAIN APP ---------- */

    .stApp {
        background: #08111f;
        color: #e8f1f8;
    }

    .block-container {
        max-width: 1450px;
        padding-top: 2rem;
        padding-bottom: 3rem;
    }

    /* ---------- SIDEBAR ---------- */

    section[data-testid="stSidebar"] {
        background: #060e1a;
        border-right: 1px solid #17283a;
    }

    section[data-testid="stSidebar"] .block-container {
        padding-top: 2rem;
    }

    /* ---------- HEADINGS ---------- */

    h1, h2, h3 {
        color: #f1f7fb !important;
    }

    h1 {
        font-size: 32px !important;
        font-weight: 700 !important;
    }

    h2 {
        font-size: 24px !important;
        font-weight: 650 !important;
    }

    h3 {
        font-size: 19px !important;
        font-weight: 600 !important;
    }

    p, label, span {
        color: #c7d5df;
    }

    /* ---------- METRICS ---------- */

    div[data-testid="stMetric"] {
        background: #0d1b2a;
        border: 1px solid #1b3145;
        border-radius: 14px;
        padding: 18px;
    }

    div[data-testid="stMetricLabel"] {
        color: #91a6b5 !important;
    }

    div[data-testid="stMetricValue"] {
        color: #f3f8fb !important;
    }

    /* ---------- BUTTONS ---------- */

    div.stButton > button {
        width: 100%;
        min-height: 44px;
        background: #087ca8;
        color: white;
        border: none;
        border-radius: 9px;
        font-weight: 600;
        transition: 0.2s;
    }

    div.stButton > button:hover {
        background: #0b91c2;
        color: white;
    }

    /* ---------- FILE UPLOADER ---------- */

    section[data-testid="stFileUploaderDropzone"] {
        background: #0b1827;
        border: 1px dashed #28516c;
        border-radius: 12px;
    }

    /* ---------- RADIO ---------- */

    div[role="radiogroup"] {
        gap: 10px;
    }

    /* ---------- DIVIDER ---------- */

    hr {
        border-color: #1a2b3d;
    }

    /* ---------- INFO / SUCCESS / WARNING ---------- */

    div[data-testid="stAlert"] {
        border-radius: 10px;
    }

    /* ---------- CONTAINERS ---------- */

    div[data-testid="stVerticalBlockBorderWrapper"] {
        background: #0b1827;
        border-color: #1b3145 !important;
        border-radius: 14px;
    }

    /* ---------- SIDEBAR RADIO ---------- */

    section[data-testid="stSidebar"] div[role="radiogroup"] {
        gap: 8px;
    }

    section[data-testid="stSidebar"] label {
        background: #0b1827;
        border-radius: 9px;
        padding: 8px 10px;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# SESSION STATE
# ============================================================
if "page" not in st.session_state:
    st.session_state.page = "Dashboard"

if "gate_mode" not in st.session_state:
    st.session_state.gate_mode = "Entry"

if "monitoring_mode" not in st.session_state:
    st.session_state.monitoring_mode = "Fire & Smoke"

if "fire_alert_count" not in st.session_state:
    st.session_state.fire_alert_count = 0

if "threat_level" not in st.session_state:
    st.session_state.threat_level = "LOW"

if "area_alerts" not in st.session_state:
    st.session_state.area_alerts = {}

if "last_shown_alert_signature" not in st.session_state:
    st.session_state.last_shown_alert_signature = None


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.title("🛡️ CompoundGuard")

    st.caption("AI-Powered Smart Security System")

    st.divider()

    st.subheader("Navigation")

    page = st.radio(
        "Navigation",
        [
            "Dashboard",
            "Gate Control",
            "Monitoring",
        ],
        index=[
            "Dashboard",
            "Gate Control",
            "Monitoring",
        ].index(st.session_state.page),
        label_visibility="collapsed",
    )

    st.session_state.page = page

    st.divider()

    st.subheader("System Status")

    st.success("● All Systems Online")

    st.caption("AI Monitoring Active")
    st.caption("Database Connected")
    st.caption("Gate Controller Ready")

    st.divider()

    st.caption("CompoundGuard v1.0")
    st.caption("Smart Security Platform")


# ============================================================
# DASHBOARD
# ============================================================

def dashboard_page():

    st.title("Dashboard")

    st.caption(
        "Real-time overview of the CompoundGuard security system"
    )

    st.divider()

    # -------------------- SYSTEM STATUS --------------------

    st.subheader("System Overview")
    metrics = get_dashboard_metrics()

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Vehicles Inside",
            metrics["inside"],
        )

    with col2:
        st.metric(
            "Today's Entries",
            metrics["entries_today"],
        )

    with col3:
        st.metric(
            "Today's Exits",
            metrics["exits_today"],
        )

        with col4:
            st.metric(
                "Security Alerts",
                st.session_state.fire_alert_count,
            )

    st.write("")

    # -------------------- MAIN STATUS --------------------

    left, right = st.columns(2)

    with left:

        with st.container(border=True):

            st.subheader("🚧 Gate Status")

            status_col1, status_col2 = st.columns(2)

            with status_col1:
                st.metric(
                    "Entry Gate",
                    "OPEN",
                )

            with status_col2:
                st.metric(
                    "Exit Gate",
                    "READY",
                )

            st.success("Gate system is operating normally.")

        with right:

            with st.container(border=True):

                st.subheader("🛡️ Security Status")

                st.metric(
                    "Threat Level",
                    st.session_state.threat_level,
                )

                if st.session_state.threat_level == "HIGH":
                    st.error("Active fire detected — immediate attention required")
                elif st.session_state.threat_level == "MEDIUM":
                    st.warning("Smoke detected in one or more areas")
                else:
                    st.success("No critical security threats detected.")

    st.write("")

    # -------------------- VEHICLES TABLE (ALL LOGS) --------------------

    st.subheader("📋 All Vehicle Entries & Exits Log")

    df_vehicles = get_all_vehicles_today()

    if df_vehicles.empty:
        with st.container(border=True):
            st.info("No vehicle records found in the database yet.")
    else:
        st.dataframe(
            df_vehicles,
            use_container_width=True,
            hide_index=True
        )


# ============================================================
# GATE CONTROL
# ============================================================


def gate_page():
    st.title("Gate Control")
    st.caption("Vehicle entry and exit monitoring")
    st.divider()

    st.subheader("Gate Operation")

    gate_mode = st.radio(
        "Select operation",
        ["Entry", "Exit"],
        horizontal=True,
        index=0 if st.session_state.gate_mode == "Entry" else 1,
    )

    st.session_state.gate_mode = gate_mode

    st.write("")

    st.subheader(
        f"{' Vehicle Entry' if gate_mode == 'Entry' else ' Vehicle Exit'}"
    )

    uploaded_file = st.file_uploader(
        "Upload camera image or video",
        type=["jpg","jpeg","jfif","png","mp4","mov","avi",],
        key=f"gate_{gate_mode}",
    )

    if uploaded_file is None:
        with st.container(border=True):
            st.info(
                "Upload a vehicle image or video to preview the gate interface."
            )
            st.caption("AI processing will start after upload.")
        return

    file_name = uploaded_file.name.lower()
    image_extensions = (".jpg", ".jpeg", ".jfif", ".png")
    video_extensions = (".mp4", ".mov", ".avi")

    is_image = file_name.endswith(image_extensions)
    is_video = file_name.endswith(video_extensions)

    result = {}

    # ============================================================
    # IMAGE PROCESSING (Full Width - No AI Processed Box)
    # ============================================================
    if is_image:
        file_bytes = uploaded_file.getvalue()
        file_array = np.frombuffer(file_bytes, dtype=np.uint8)
        frame = cv2.imdecode(file_array, cv2.IMREAD_COLOR)

        if frame is None:
            with st.container(border=True):
                st.error("Could not read the uploaded image.")
            return

        with st.container(border=True):
            st.subheader("Camera Input")
            st.image(
                file_bytes,
                caption="Original Camera Frame",
                use_container_width=True
            )

        with st.spinner("Analyzing vehicle..."):
            try:
                if gate_mode == "Entry":
                    result = process_entry(frame)
                else:
                    result = process_exit(frame)
            except Exception as e:
                result = {
                    "decision": "ERROR",
                    "reason": str(e)
                }

    # ============================================================
    # VIDEO PROCESSING (Full Width - Background AI Analysis)
    # ============================================================
    elif is_video:
        video_bytes = uploaded_file.getvalue()
        temp_video = tempfile.NamedTemporaryFile(
            delete=False,
            suffix=os.path.splitext(file_name)[1]
        )
        temp_video.write(video_bytes)
        temp_video.close()
        video_path = temp_video.name

        with st.container(border=True):
            st.subheader("Camera Input")
            
            import base64
            base64_video = base64.b64encode(video_bytes).decode("utf-8")
            
            video_html = f"""
                <video width="100%" controls autoplay muted>
                    <source src="data:video/mp4;base64,{base64_video}" type="video/mp4">
                    Your browser does not support the video tag.
                </video>
            """
            st.markdown(video_html, unsafe_allow_html=True)

        with st.spinner("Processing video and analyzing vehicle..."):
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                result = {
                    "decision": "ERROR",
                    "reason": "Could not open the video."
                }
            else:
                fps = cap.get(cv2.CAP_PROP_FPS)
                if fps <= 0:
                    fps = 30

                MOVING_THRESHOLD = 1.8
                STABLE_THRESHOLD = 1.3
                REQUIRED_STABLE_SECONDS = 1.5
                FRAME_SKIP = 4

                previous_gray = None
                movement_detected = False
                stable_count = 0
                stable_frames = []
                stopped_frame = None
                frame_number = 0

                REQUIRED_STABLE_FRAMES = max(
                    int((fps / FRAME_SKIP) * REQUIRED_STABLE_SECONDS),
                    5
                )

                while True:
                    ret, current_frame = cap.read()
                    if not ret:
                        break

                    frame_number += 1
                    if frame_number % FRAME_SKIP != 0:
                        continue

                    small_frame = cv2.resize(current_frame, (320, 180))
                    gray_current = cv2.cvtColor(small_frame, cv2.COLOR_BGR2GRAY)

                    if previous_gray is None:
                        previous_gray = gray_current
                        continue

                    difference = cv2.absdiff(gray_current, previous_gray)
                    motion_score = float(difference.mean())

                    if not movement_detected:
                        if motion_score >= MOVING_THRESHOLD:
                            movement_detected = True
                            stable_count = 0
                            stable_frames = []
                        previous_gray = gray_current
                        continue

                    if motion_score < STABLE_THRESHOLD:
                        stable_count += 1
                        stable_frames.append(current_frame.copy())
                    else:
                        stable_count = 0
                        stable_frames = []

                    if stable_count >= REQUIRED_STABLE_FRAMES:
                        stopped_frame = stable_frames[len(stable_frames) // 2].copy()
                        break

                    previous_gray = gray_current

                cap.release()

                if stopped_frame is None:
                    result = {
                        "decision": "ERROR",
                        "reason": "Could not detect a stopped vehicle in the video."
                    }
                else:
                    try:
                        if gate_mode == "Entry":
                            result = process_entry(stopped_frame)
                        else:
                            result = process_exit(stopped_frame)
                    except Exception as e:
                        result = {
                            "decision": "ERROR",
                            "reason": str(e)
                        }

        try:
            os.remove(video_path)
        except Exception:
            pass

    else:
        with st.container(border=True):
            st.error("Unsupported file type.")
        return

    # ============================================================
    # DETECTION INFORMATION
    # ============================================================

 
    st.write("")
    st.subheader("Detection Information")

    vehicle_type = result.get("type", "—")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Vehicle Type", vehicle_type)
    with c2:
        st.metric("License Plate", result.get("plate", "—"))
    with c3:
        st.metric("Brand", result.get("brand", "—"))
    with c4:
        st.metric("Color", result.get("color", "—"))

    # ============================================================
    # ACCESS DECISION
    # ============================================================

    st.write("")

    with st.container(border=True):
        st.subheader("Access Decision")

        if result.get("decision") == "ALLOWED":
            st.success("ACCESS GRANTED — Gate can be opened")
            st.caption("Vehicle information has been registered successfully.")
        elif result.get("decision") == "DENIED":
            st.error(f"ACCESS DENIED — {result.get('reason', 'Vehicle not allowed')}")
        elif result.get("status") == "exited":
            st.success("EXIT REGISTERED — Gate can be opened")
            st.caption(f"Plate: {result.get('plate', 'Unknown')}")
        else:
            st.warning(f"{result.get('reason', 'Processing failed')}")

    # ============================================================
    Info = st.container()
    st.write("")
    st.subheader("Gate Information")

    time1, time2, time3 = st.columns(3)

    with time1:
        st.metric("Operation", gate_mode)

    with time2:
        processing_status = (
            "Completed"
            if (result.get("decision") == "ALLOWED" or result.get("status") == "exited")
            else "Failed"
        )
        st.metric("Processing", processing_status)

    with time3:
        gate_status = (
            "OPEN"
            if (result.get("decision") == "ALLOWED" or result.get("status") == "exited")
            else "CLOSED"
        )
        st.metric("Gate Status", gate_status)

# ============================================================
# MONITORING (FIRE & SMOKE / PARKING)
# ============================================================

def monitoring_page():

    st.title("Monitoring")

    st.caption(
        "Security monitoring and parking management"
    )

    st.divider()

    # -------------------- MODULE SELECTOR --------------------

    st.subheader("Monitoring Modules")

    module = st.radio(
        "Select module",
        [
            "Fire & Smoke",
            "Parking",
        ],
        horizontal=True,
        index=(
            0
            if st.session_state.monitoring_mode == "Fire & Smoke"
            else 1
        ),
    )

    st.session_state.monitoring_mode = module

    st.write("")

    # ========================================================
    # FIRE & SMOKE (2 CAMERAS: AREA 1 & AREA 2)
    # ========================================================

    if module == "Fire & Smoke":

        st.subheader("🔥 Fire & Smoke Detection (Multi-Camera View)")
        st.caption("Monitoring compound areas simultaneously")

        st.write("")

        upload_col1, upload_col2 = st.columns(2)

        with upload_col1:
            st.markdown("### 📹 Area 1")
            cam1_file = st.file_uploader(
                "Upload Feed",
                type=["jpg", "jpeg", "png", "mp4", "mov", "avi"],
                key="area1",
            )

        with upload_col2:
            st.markdown("### 📹 Area 2")
            cam2_file = st.file_uploader(
                "Upload Feed",
                type=["jpg", "jpeg", "png", "mp4", "mov", "avi"],
                key="area2",
            )

        active_cameras_count = sum(1 for f in [cam1_file, cam2_file] if f is not None)

        st.write("")
        st.metric("Active Cameras", f"{active_cameras_count} / 2")
        st.write("")

        cam_col1, cam_col2 = st.columns(2)

        area1_threat = "LOW"
        area2_threat = "LOW"
        fire1, smoke1 = 0, 0
        fire2, smoke2 = 0, 0

        with cam_col1:
            container1 = st.container(border=True)
            with container1:
                m1a, m1b = st.columns(2)
                with m1a:
                    alerts_placeholder1 = st.empty()
                    alerts_placeholder1.metric("Fire/Smoke Alerts", "🔥 0 / 💨 0")
                with m1b:
                    threat_placeholder1 = st.empty()
                    threat_placeholder1.metric("Threat Level", "LOW")
                frame_placeholder1 = st.empty()
                if not cam1_file:
                    frame_placeholder1.info("Awaiting Area 1 feed...")

        with cam_col2:
            container2 = st.container(border=True)
            with container2:
                m2a, m2b = st.columns(2)
                with m2a:
                    alerts_placeholder2 = st.empty()
                    alerts_placeholder2.metric("Fire/Smoke Alerts", "🔥 0 / 💨 0")
                with m2b:
                    threat_placeholder2 = st.empty()
                    threat_placeholder2.metric("Threat Level", "LOW")
                frame_placeholder2 = st.empty()
                if not cam2_file:
                    frame_placeholder2.info("Awaiting Area 2 feed...")

        cam1_is_video = cam1_file and not cam1_file.type.startswith("image")
        cam2_is_video = cam2_file and not cam2_file.type.startswith("image")

        if cam1_is_video and cam2_is_video:
            area1_threat, area2_threat = process_two_videos_for_fire(
                cam1_file.getvalue(), cam2_file.getvalue(),
                frame_placeholder1, alerts_placeholder1, threat_placeholder1,
                frame_placeholder2, alerts_placeholder2, threat_placeholder2,
            )

        else:
            if cam1_file:
                if cam1_file.type.startswith("image"):
                    file_bytes = np.asarray(bytearray(cam1_file.read()), dtype=np.uint8)
                    frame = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
                    try:
                        response = requests.post(
                            "http://127.0.0.1:8000/safety/fire-smoke",
                            files={"file": cam1_file.getvalue()},
                        )
                        result = response.json()
                        detections = result.get("detections", [])
                        fire1 = len([d for d in detections if d["class"] == "fire"])
                        smoke1 = len([d for d in detections if d["class"] == "smoke"])
                        area1_threat = "HIGH" if fire1 > 0 else ("MEDIUM" if smoke1 > 0 else "LOW")

                        alerts_placeholder1.metric("Fire/Smoke Alerts", f"🔥 {fire1} / 💨 {smoke1}")
                        threat_placeholder1.metric("Threat Level", area1_threat)

                        annotated = draw_fire_boxes(frame, detections)
                        annotated = cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB)
                        frame_placeholder1.image(annotated, use_container_width=True)
                    except Exception as e:
                        frame_placeholder1.error(f"Failed to connect to backend: {e}")

                elif cam1_is_video:
                    area1_threat = process_single_video_for_fire(
                        cam1_file.getvalue(), frame_placeholder1, alerts_placeholder1, threat_placeholder1
                    )

            if cam2_file:
                if cam2_file.type.startswith("image"):
                    file_bytes = np.asarray(bytearray(cam2_file.read()), dtype=np.uint8)
                    frame = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
                    try:
                        response = requests.post(
                            "http://127.0.0.1:8000/safety/fire-smoke",
                            files={"file": cam2_file.getvalue()},
                        )
                        result = response.json()
                        detections = result.get("detections", [])
                        fire2 = len([d for d in detections if d["class"] == "fire"])
                        smoke2 = len([d for d in detections if d["class"] == "smoke"])
                        area2_threat = "HIGH" if fire2 > 0 else ("MEDIUM" if smoke2 > 0 else "LOW")

                        alerts_placeholder2.metric("Fire/Smoke Alerts", f"🔥 {fire2} / 💨 {smoke2}")
                        threat_placeholder2.metric("Threat Level", area2_threat)

                        annotated = draw_fire_boxes(frame, detections)
                        annotated = cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB)
                        frame_placeholder2.image(annotated, use_container_width=True)
                    except Exception as e:
                        frame_placeholder2.error(f"Failed to connect to backend: {e}")

                elif cam2_is_video:
                    area2_threat = process_single_video_for_fire(
                        cam2_file.getvalue(), frame_placeholder2, alerts_placeholder2, threat_placeholder2
                    )

        if not cam1_is_video and not cam2_is_video:
            current_f1 = fire1 if 'fire1' in locals() else 0
            current_s1 = smoke1 if 'smoke1' in locals() else 0
            current_f2 = fire2 if 'fire2' in locals() else 0
            current_s2 = smoke2 if 'smoke2' in locals() else 0

            st.session_state.fire_alert_count = (current_f1 + current_s1) + (current_f2 + current_s2)

            overall_threat = "HIGH" if "HIGH" in [area1_threat, area2_threat] else (
                "MEDIUM" if "MEDIUM" in [area1_threat, area2_threat] else "LOW"
            )
            st.session_state.threat_level = overall_threat

        st.session_state.area_alerts["Area 1"] = area1_threat
        st.session_state.area_alerts["Area 2"] = area2_threat

    # ========================================================
    # PARKING
    # ========================================================

    else:

        st.subheader("🅿️ Parking Monitoring")

        st.caption(
            "AI-based parking occupancy monitoring"
        )

        uploaded_file = st.file_uploader(
            "Upload parking image",
            type=[
                "jpg",
                "jpeg",
                "png"
            ],
            key="parking_upload",
        )

        if uploaded_file is None:

            with st.container(border=True):

                st.info(
                    "Upload a parking image to analyze parking occupancy."
                )

        else:

            # Read uploaded image
            file_bytes = np.asarray(
                bytearray(uploaded_file.read()),
                dtype=np.uint8
            )

            frame = cv2.imdecode(
                file_bytes,
                cv2.IMREAD_COLOR
            )

            # Run parking AI model and get bounding boxes
            result, annotated_frame = analyze_parking_occupancy(
                frame,
                return_annotated=True
            )

            # -----------------------------
            # IMAGE + AI RESULT
            # -----------------------------

            left, right = st.columns(2)

            with left:

                with st.container(border=True):

                    st.subheader("📷 Parking Camera")

                    st.image(
                        annotated_frame,
                        caption="Parking Detection",
                        channels="BGR",
                        use_container_width=True
                    )

            with right:

                with st.container(border=True):

                    st.subheader("🤖 AI Analysis")

                    st.success("Parking analysis completed.")

                    st.write(
                        f"Total parking spaces: **{result['total']}**"
                    )

                    st.write(
                        f"Occupied spaces: **{result['occupied']}**"
                    )

                    st.write(
                        f"Available spaces: **{result['free']}**"
                    )

            st.write("")

            # -----------------------------
            # PARKING OVERVIEW
            # -----------------------------

            st.subheader("Parking Overview")

            total = result["total"]
            occupied = result["occupied"]
            free = result["free"]

            if total > 0:
                occupancy = (occupied / total) * 100
            else:
                occupancy = 0

            p1, p2, p3, p4 = st.columns(4)

            with p1:
                st.metric(
                    "Total Spaces",
                    total
                )

            with p2:
                st.metric(
                    "Occupied",
                    occupied
                )

            with p3:
                st.metric(
                    "Available",
                    free
                )

            with p4:
                st.metric(
                    "Occupancy",
                    f"{occupancy:.1f}%"
                )

# ============================================================
# PAGE ROUTING
# ============================================================

if st.session_state.page == "Dashboard":

    dashboard_page()

elif st.session_state.page == "Gate Control":

    gate_page()

elif st.session_state.page == "Monitoring":

    monitoring_page()