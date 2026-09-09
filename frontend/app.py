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

from core.gate_logic import process_entry, process_exit
from core.parking import analyze_parking_occupancy

sys.path.append(str(Path(__file__).resolve().parent.parent))


BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "database" / "compound.db"

def draw_fire_boxes(frame, detections):
    for det in detections:
        box = det["box"]  # [x1, y1, x2, y2]
        cls_name = det["class"]
        conf = det["confidence"]

        color = (0, 255, 0) if cls_name == "fire" else (0, 165, 255)

        cv2.rectangle(
            frame, (box[0], box[1]), (box[2], box[3]), color, 2
        )

        label = f"{cls_name})"
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

    # ============================================================
    # NO FILE
    # ============================================================

    if uploaded_file is None:
        with st.container(border=True):
            st.info(
                "Upload a vehicle image or video to preview the gate interface."
            )
            st.caption("AI processing will start after upload.")

        return

    # ============================================================
    # FILE TYPE
    # ============================================================

    file_name = uploaded_file.name.lower()

    image_extensions = (".jpg", ".jpeg", ".jfif", ".png")
    video_extensions = (".mp4", ".mov", ".avi")

    is_image = file_name.endswith(image_extensions)
    is_video = file_name.endswith(video_extensions)

    # ============================================================
    # IMAGE PROCESSING
    # ============================================================

    if is_image:

        file_bytes = uploaded_file.getvalue()
        file_array = np.frombuffer(file_bytes,dtype=np.uint8)
        frame = cv2.imdecode(file_array,cv2.IMREAD_COLOR)

        if frame is None:

            with st.container(border=True):
                st.error("Could not read the uploaded image.")

            return

        preview_col, result_col = st.columns(2)

        with preview_col:

            with st.container(border=True):

                st.subheader("Camera Input")

                st.image(
                    file_bytes,
                    caption="Original Camera Frame",
                    use_container_width=True
                )

        # --------------------------------------------------------
        # AI PROCESSING
        # --------------------------------------------------------

        with result_col:

            with st.container(border=True):

                st.subheader("AI Processed")

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

                # ------------------------------------------------
                # RESULT
                # ------------------------------------------------

                if result.get("decision") == "ALLOWED":

                    st.success(
                        "Vehicle approved for entry."
                    )

                elif result.get("decision") == "DENIED":

                    st.error(
                        "Vehicle is not allowed."
                    )

                elif result.get("status") == "exited":

                    st.success(
                        "Vehicle exit registered successfully."
                    )

                else:

                    st.error(
                        result.get(
                            "reason",
                            "Vehicle processing failed."
                        )
                    )

    # ============================================================
    # VIDEO PROCESSING
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

        preview_col, result_col = st.columns(2)

        # --------------------------------------------------------
        # VIDEO PREVIEW
        # --------------------------------------------------------

        with preview_col:

            with st.container(border=True):

                st.subheader("Camera Input")

                st.video(video_bytes)

        # --------------------------------------------------------
        # FIND STOPPED FRAME
        # --------------------------------------------------------
        with result_col:

            with st.container(border=True):

                st.subheader("AI Processed")

                status_text = st.empty()
                progress_bar = st.progress(0)

                cap = cv2.VideoCapture(video_path)

                if not cap.isOpened():
                    result = {
                        "decision": "ERROR",
                        "reason": "Could not open the video."
                    }

                else:

                    total_frames = int(
                        cap.get(cv2.CAP_PROP_FRAME_COUNT)
                    )

                    fps = cap.get(cv2.CAP_PROP_FPS)

                    if fps <= 0:
                        fps = 30

                    # ------------------------------------------------
                    # SETTINGS
                    # ------------------------------------------------

                    REQUIRED_STABLE_SECONDS = 1.5
                    FRAME_SKIP = max(int(fps * 0.2), 1)
                    MOTION_THRESHOLD = 6.0
                    REQUIRED_STABLE_COMPARISONS = max(
                        int(
                            REQUIRED_STABLE_SECONDS / 0.2
                        ),
                        5
                    )

                    # ------------------------------------------------
                    # VARIABLES
                    # ------------------------------------------------

                    # =================================================
                    # VEHICLE STOP DETECTION
                    # =================================================

                    previous_gray = None

                    stopped_frame = None

                    frame_number = 0

                    # -------------------------------------------------
                    # SETTINGS
                    # -------------------------------------------------

                    MOVING_THRESHOLD = 1.8
                    STABLE_THRESHOLD = 1.3
                    REQUIRED_STABLE_SECONDS = 1.5
                    FRAME_SKIP = 4

                    # -------------------------------------------------
                    # VARIABLES
                    # -------------------------------------------------

                    movement_detected = False

                    stable_count = 0

                    stable_frames = []

                    REQUIRED_STABLE_FRAMES = max(
                        int(
                            (fps / FRAME_SKIP)
                            * REQUIRED_STABLE_SECONDS
                        ),
                        5
                    )

                    frame_number = 0

                    # -------------------------------------------------
                    # READ VIDEO
                    # -------------------------------------------------

                    while True:

                        ret, current_frame = cap.read()

                        if not ret:
                            break

                        frame_number += 1

                        # ------------------------------------------------
                        # PROGRESS
                        # ------------------------------------------------

                        if total_frames > 0:

                            progress = min(
                                frame_number / total_frames,
                                1.0
                            )

                            progress_bar.progress(progress)

                        # ------------------------------------------------
                        # CHECK ONLY EVERY FEW FRAMES
                        # ------------------------------------------------

                        if frame_number % FRAME_SKIP != 0:
                            continue

                        status_text.info(
                            f"Analyzing video... "
                            f"Frame {frame_number}"
                        )

                        # ------------------------------------------------
                        # RESIZE
                        # ------------------------------------------------

                        small_frame = cv2.resize(
                            current_frame,
                            (320, 180)
                        )

                        gray_current = cv2.cvtColor(
                            small_frame,
                            cv2.COLOR_BGR2GRAY
                        )

                        # ------------------------------------------------
                        # FIRST FRAME
                        # ------------------------------------------------

                        if previous_gray is None:

                            previous_gray = gray_current

                            continue

                        # ------------------------------------------------
                        # FRAME DIFFERENCE
                        # ------------------------------------------------

                        difference = cv2.absdiff(
                            gray_current,
                            previous_gray
                        )

                        motion_score = float(
                            difference.mean()
                        )

                        # =================================================
                        # STATE 1:
                        # WAIT UNTIL THE CAR HAS ACTUALLY MOVED
                        # =================================================

                        if not movement_detected:

                            if motion_score >= MOVING_THRESHOLD:

                                movement_detected = True

                                stable_count = 0

                                stable_frames = []

                                status_text.info(
                                    "Vehicle movement detected..."
                                )

                            previous_gray = gray_current

                            continue

                        # =================================================
                        # STATE 2:
                        # VEHICLE HAS MOVED
                        # NOW LOOK FOR A REAL STOP
                        # =================================================

                        if motion_score < STABLE_THRESHOLD:

                            stable_count += 1

                            stable_frames.append(
                                current_frame.copy()
                            )

                        else:
                            stable_count = 0

                            stable_frames = []

                        # =================================================
                        # STATE 3:
                        # VEHICLE HAS BEEN STABLE LONG ENOUGH
                        # =================================================

                        if stable_count >= REQUIRED_STABLE_FRAMES:
                            middle_index = (
                                len(stable_frames) // 2
                            )

                            stopped_frame = stable_frames[
                                middle_index
                            ].copy()

                            status_text.success(
                                "Vehicle stopped. "
                                "Stable frame captured."
                            )

                            break

                        previous_gray = gray_current

                    cap.release()

                    # ------------------------------------------------
                    # NO STOPPED FRAME
                    # ------------------------------------------------

                    if stopped_frame is None:

                        result = {
                            "decision": "ERROR",
                            "reason":
                                "Could not detect a stopped vehicle in the video."
                        }

                    else:

                        status_text.success(
                            "Vehicle stopped. "
                            "Captured stable frame."
                        )

                        progress_bar.progress(1.0)

                        # ------------------------------------------------
                        # DISPLAY CAPTURED FRAME
                        # ------------------------------------------------

                        st.image(
                            cv2.cvtColor(
                                stopped_frame,
                                cv2.COLOR_BGR2RGB
                            ),
                            caption="Captured Vehicle Frame",
                            use_container_width=True
                        )

                        # ------------------------------------------------
                        # SEND FRAME TO AI
                        # ------------------------------------------------

                        with st.spinner(
                            "Running AI models on captured frame..."
                        ):

                            try:

                                if gate_mode == "Entry":

                                    result = process_entry(
                                        stopped_frame
                                    )

                                else:

                                    result = process_exit(
                                        stopped_frame
                                    )

                            except Exception as e:

                                result = {
                                    "decision": "ERROR",
                                    "reason": str(e)
                                }
        # --------------------------------------------------------
        # DELETE TEMP VIDEO
        # --------------------------------------------------------

        try:

            os.remove(video_path)

        except Exception:

            pass

        # --------------------------------------------------------
        # RESULT
        # --------------------------------------------------------

        if result.get("decision") == "ALLOWED":

            st.success(
                "Vehicle approved for entry."
            )

        elif result.get("decision") == "DENIED":

            st.error(
                "Vehicle is not allowed."
            )

        elif result.get("status") == "exited":

            st.success(
                "Vehicle exit registered successfully."
            )

        else:

            st.error(
                result.get(
                    "reason",
                    "Vehicle processing failed."
                )
            )

    # ============================================================
    # INVALID FILE
    # ============================================================

    else:

        with st.container(border=True):

            st.error(
                "Unsupported file type."
            )

        return

    # ============================================================
    # DETECTION INFORMATION
    # ============================================================

    st.write("")

    st.subheader("Detection Information")

    vehicle_type = result.get("type", "—")

    if gate_mode == "Entry" and vehicle_type != "Cars":

        c1 = st.columns(1)[0]

        with c1:
            st.metric("Vehicle Type",vehicle_type)

    else:

        c1, c2, c3, c4 = st.columns(4)

        with c1:st.metric("Vehicle Type",vehicle_type)
        with c2:
            st.metric("License Plate",result.get("plate", "—"))
        with c3:
            st.metric("Brand",result.get("brand", "—"))
        with c4:
            st.metric("Color",result.get("color", "—"))

    # ============================================================
    # ACCESS DECISION
    # ============================================================

    st.write("")

    with st.container(border=True):

        st.subheader("Access Decision")

        if result.get("decision") == "ALLOWED":

            st.success(
                "ACCESS GRANTED — Gate can be opened"
            )

            st.caption(
                "Vehicle information has been registered successfully."
            )

        elif result.get("decision") == "DENIED":

            st.error(
                f"ACCESS DENIED — "
                f"{result.get('reason', 'Vehicle not allowed')}"
            )

        elif result.get("status") == "exited":

            st.success("EXIT REGISTERED — Gate can be opened")

            st.caption(f"Plate: {result.get('plate', 'Unknown')}")

        else:

            st.warning(
                f"{result.get('reason', 'Processing failed')}"
            )

    # ============================================================
    # GATE INFORMATION
    # ============================================================

    st.write("")

    st.subheader("Gate Information")

    time1, time2, time3 = st.columns(3)

    with time1:
        st.metric("Operation",gate_mode)

    with time2:
        processing_status = (
            "Completed"
            if (
                result.get("decision") == "ALLOWED"
                or result.get("status") == "exited"
            )
            else "Failed"
        )

        st.metric("Processing",processing_status)

    with time3:
        gate_status = (
            "OPEN"
            if (
                result.get("decision") == "ALLOWED"
                or result.get("status") == "exited"
            )
            else "CLOSED"
        )

        st.metric("Gate Status",gate_status)

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
        
        total_fire_alerts = 0
        highest_threat = "LOW"
        active_cameras_count = 0
        
        # 2 Cameras Side by Side
        cam_col1, cam_col2 = st.columns(2)

        with cam_col1:
            with st.container(border=True):
                st.markdown("### 📹 Area 1")
                cam1_file = st.file_uploader(
                    "Upload Feed",
                    type=["jpg", "jpeg", "png", "mp4", "mov", "avi"],
                    key="area1",
                )
                
                area1_threat = "LOW"
                area1_alerts = 0
                if cam1_file:
                    active_cameras_count += 1
                    if cam1_file.type.startswith("image"):
                        file_bytes = np.asarray(bytearray(cam1_file.read()), dtype=np.uint8)
                        frame = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
                        
                        try:
                            files = {"file": cam1_file.getvalue()}
                            response = requests.post(
                                "http://127.0.0.1:8000/safety/fire-smoke", files=files
                            )
                            result = response.json()

                            has_fire = result.get("has_fire", False)
                            has_smoke = result.get("has_smoke", False)
                            detections = result.get("detections", [])
                            
                            if has_fire:
                                area1_threat = "HIGH"
                                area1_alerts += len(
                                    [d for d in detections if d["class"] == "fire"]
                                )
                            elif has_smoke:
                                area1_threat = "MEDIUM"
                                area1_alerts += len(
                                    [d for d in detections if d["class"] == "smoke"]
                                )

                            annotated_frame = draw_fire_boxes(frame, detections)
                            annotated_frame = cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB)
                            st.image(annotated_frame, use_container_width=True)
                        
                        except Exception as e:
                           st.error(f"Failed to connect to backend: {e}")
                    else:
                        st.video(cam1_file.getvalue())
                else:
                   st.info("Awaiting Area 1 feed...")   
                        
                                       
        with cam_col2:
            with st.container(border=True):
                st.markdown("### 📹 Area 2")
                cam2_file = st.file_uploader(
                    "Upload Feed",
                    type=["jpg", "jpeg", "png", "mp4", "mov", "avi"],
                    key="area2",
                )
                area2_threat = "LOW"
                area2_alerts = 0
                if cam2_file:
                    active_cameras_count += 1
                    if cam2_file.type.startswith("image"):
                        file_bytes = np.asarray(bytearray(cam2_file.read()), dtype=np.uint8)
                        frame = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
                        
                        try:
                            files = {"file": cam2_file.getvalue()}
                            response = requests.post(
                                "http://127.0.0.1:8000/safety/fire-smoke", files=files
                            )
                            result = response.json()

                            has_fire = result.get("has_fire", False)
                            has_smoke = result.get("has_smoke", False)
                            detections = result.get("detections", [])

                            if has_fire:
                                area2_threat = "HIGH"
                                area2_alerts += len(
                                    [d for d in detections if d["class"] == "fire"]
                                )
                            elif has_smoke:
                                area2_threat = "MEDIUM"
                                area2_alerts += len(
                                    [d for d in detections if d["class"] == "smoke"]
                                )

                            annotated_frame = draw_fire_boxes(frame, detections)
                            annotated_frame = cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB)
                            st.image(annotated_frame, use_container_width=True)
                        except Exception as e:
                            st.error(f"Failed to connect to backend: {e}")
                    else:
                        st.video(cam2_file.getvalue())
                else:
                   st.info("Awaiting Area 2 feed...")
                                            
        
        total_fire_alerts = area1_alerts + area2_alerts

        if area1_threat == "HIGH" or area2_threat == "HIGH":
            highest_threat = "HIGH"
        elif area1_threat == "MEDIUM" or area2_threat == "MEDIUM":
            highest_threat = "MEDIUM"
        else:
            highest_threat = "LOW"

        st.session_state.fire_alert_count = total_fire_alerts
        st.session_state.threat_level = highest_threat

        st.write("")
        
        st.subheader("Security Status Overview")

        s1, s2, s3 = st.columns(3)

        with s1:
            st.metric("Active Cameras", f"{active_cameras_count} / 2")

        with s2:
            st.metric("Fire/Smoke Alerts", str(total_fire_alerts))

        with s3:
            st.metric("Threat Level", highest_threat)

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