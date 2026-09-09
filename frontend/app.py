import streamlit as st
import sqlite3
import pandas as pd
from pathlib import Path

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

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "smart_gate.db"

def get_all_vehicles_today():
    """جلب كل سجلات العربيات المسجلة في الداتا بيز"""
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

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Vehicles Inside",
            "24",
            "+3 today",
        )

    with col2:
        st.metric(
            "Today's Entries",
            "47",
            "+8",
        )

    with col3:
        st.metric(
            "Today's Exits",
            "23",
            "+5",
        )

    with col4:
        st.metric(
            "Security Alerts",
            "02",
            "-1",
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
                "LOW",
            )

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

    st.caption(
        "Vehicle entry and exit monitoring"
    )

    st.divider()

    # -------------------- GATE MODE --------------------

    st.subheader("Gate Operation")

    gate_mode = st.radio(
        "Select operation",
        ["Entry", "Exit"],
        horizontal=True,
        index=0 if st.session_state.gate_mode == "Entry" else 1,
    )

    st.session_state.gate_mode = gate_mode

    st.write("")

    # -------------------- UPLOAD --------------------

    st.subheader(
        f"{'🚘 Vehicle Entry' if gate_mode == 'Entry' else '🚘 Vehicle Exit'}"
    )

    uploaded_file = st.file_uploader(
        "Upload camera image or video",
        type=[
            "jpg",
            "jpeg",
            "png",
            "mp4",
            "mov",
            "avi",
        ],
        key=f"gate_{gate_mode}",
    )

    if uploaded_file is None:

        with st.container(border=True):

            st.info(
                "Upload a vehicle image or video to preview the gate interface."
            )

            st.caption(
                "AI processing will be connected later."
            )

        return

    # -------------------- PREVIEW --------------------

    st.write("")

    preview_col, result_col = st.columns(2)

    with preview_col:

        with st.container(border=True):

            st.subheader("📷 Camera Input")

            if uploaded_file.type.startswith("image"):

                st.image(
                    uploaded_file,
                    caption="Original Camera Frame",
                    use_container_width=True,
                )

            else:

                st.video(
                    uploaded_file.getvalue()
                )

    with result_col:

        with st.container(border=True):

            st.subheader("🤖 AI Processed")

            st.info(
                "Waiting for AI analysis"
            )

            st.caption(
                "The processed frame will appear here after backend integration."
            )

    st.write("")

    # -------------------- DETECTION INFORMATION --------------------

    st.subheader("Detection Information")

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.metric(
            "Vehicle Type",
            "—",
        )

    with c2:
        st.metric(
            "License Plate",
            "—",
        )

    with c3:
        st.metric(
            "Brand",
            "—",
        )

    with c4:
        st.metric(
            "Color",
            "—",
        )

    st.write("")

    # -------------------- ACCESS DECISION --------------------

    with st.container(border=True):

        st.subheader("Access Decision")

        if gate_mode == "Entry":

            st.warning(
                "Awaiting vehicle analysis..."
            )

            st.caption(
                "The gate decision will be displayed here after AI integration."
            )

        else:

            st.info(
                "Awaiting license plate verification..."
            )

            st.caption(
                "Exit verification will be connected to the database later."
            )

    st.write("")

    # -------------------- TIMING --------------------

    st.subheader("Gate Information")

    time1, time2, time3 = st.columns(3)

    with time1:
        st.metric(
            "Detection Time",
            "—",
        )

    with time2:
        st.metric(
            "Processing Time",
            "—",
        )

    with time3:
        st.metric(
            "Gate Status",
            "READY",
        )


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

        # 2 Cameras Side by Side
        cam_col1, cam_col2 = st.columns(2)

        with cam_col1:
            with st.container(border=True):
                st.markdown("### 📹 Area 1")
                cam1_file = st.file_uploader("Upload Feed", type=["jpg", "jpeg", "png", "mp4", "mov", "avi"], key="area1")
                if cam1_file:
                    if cam1_file.type.startswith("image"):
                        st.image(cam1_file, use_container_width=True)
                    else:
                        st.video(cam1_file.getvalue())
                else:
                    st.info("Awaiting Area 1 feed...")

        with cam_col2:
            with st.container(border=True):
                st.markdown("### 📹 Area 2")
                cam2_file = st.file_uploader("Upload Feed", type=["jpg", "jpeg", "png", "mp4", "mov", "avi"], key="area2")
                if cam2_file:
                    if cam2_file.type.startswith("image"):
                        st.image(cam2_file, use_container_width=True)
                    else:
                        st.video(cam2_file.getvalue())
                else:
                    st.info("Awaiting Area 2 feed...")

        st.write("")
        st.subheader("Security Status Overview")

        s1, s2, s3 = st.columns(3)
        with s1:
            st.metric("Active Cameras", "2 / 2")
        with s2:
            st.metric("Fire Alerts", "0")
        with s3:
            st.metric("Threat Level", "LOW")

    # ========================================================
    # PARKING
    # ========================================================

    else:

        st.subheader("🅿️ Parking Monitoring")

        st.caption(
            "AI-based parking occupancy monitoring"
        )

        uploaded_file = st.file_uploader(
            "Upload parking image or video",
            type=[
                "jpg",
                "jpeg",
                "png",
                "mp4",
                "mov",
                "avi",
            ],
            key="parking_upload",
        )

        if uploaded_file is None:

            with st.container(border=True):

                st.info(
                    "Upload a parking image or video to preview the parking interface."
                )

                st.caption(
                    "Parking detection will be connected later."
                )

        else:

            left, right = st.columns(2)

            with left:

                with st.container(border=True):

                    st.subheader("📷 Camera Input")

                    if uploaded_file.type.startswith("image"):

                        st.image(
                            uploaded_file,
                            caption="Parking Camera",
                            use_container_width=True,
                        )

                    else:

                        st.video(
                            uploaded_file.getvalue()
                        )

            with right:

                with st.container(border=True):

                    st.subheader("🤖 AI Analysis")

                    st.info(
                        "Waiting for AI analysis"
                    )

                    st.caption(
                        "Parking detection results will appear here after backend integration."
                    )

            st.write("")

            st.subheader("Parking Overview")

            p1, p2, p3, p4 = st.columns(4)

            with p1:
                st.metric(
                    "Total Spaces",
                    "—",
                )

            with p2:
                st.metric(
                    "Occupied",
                    "—",
                )

            with p3:
                st.metric(
                    "Available",
                    "—",
                )

            with p4:
                st.metric(
                    "Occupancy",
                    "—",
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