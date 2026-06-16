import streamlit as st
from database.db import init_db, get_statistics, get_recent_violations
import config


st.set_page_config(
    page_title="TRINETRA AI - Traffic Violation Detection",
    page_icon="🚦",
    layout="wide",
    initial_sidebar_state="expanded",
)


def apply_custom_style():
    st.markdown("""
    <style>
    .main-header {
        text-align: center;
        padding: 2rem 0;
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
        border-radius: 10px;
        margin-bottom: 2rem;
    }
    .main-header h1 {
        color: #ff4444;
        font-size: 2.5rem;
        margin-bottom: 0.5rem;
    }
    .main-header p {
        color: #cccccc;
        font-size: 1.1rem;
    }
    .metric-card {
        background: #1e1e1e;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 4px solid #ff4444;
        text-align: center;
    }
    .metric-card h3 {
        color: #ffffff;
        margin: 0;
        font-size: 1rem;
    }
    .metric-card .value {
        color: #ff4444;
        font-size: 2rem;
        font-weight: bold;
    }
    .detection-item {
        background: #262730;
        padding: 0.75rem;
        border-radius: 5px;
        margin-bottom: 0.5rem;
        border-left: 3px solid #00ff88;
    }
    </style>
    """, unsafe_allow_html=True)


def home_page():
    apply_custom_style()
    st.markdown("""
    <div class="main-header">
        <h1>TRINETRA AI</h1>
        <p>AI-Powered Traffic Violation Detection &amp; Enforcement Intelligence Platform</p>
    </div>
    """, unsafe_allow_html=True)

    stats = get_statistics()
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="value">{stats['total']}</div>
            <h3>Total Violations</h3>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="value">{stats['no_helmet']}</div>
            <h3>Helmet Violations</h3>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="value">{stats['triple_riding']}</div>
            <h3>Triple Riding Cases</h3>
        </div>
        """, unsafe_allow_html=True)
    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="value">{stats['unique_vehicles']}</div>
            <h3>Unique Vehicles</h3>
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Supported Violations")
        violations_info = [
            {
                "name": "No Helmet",
                "desc": "Detects motorcycle riders without helmets using YOLO-based person detection and head region analysis",
                "color": "#ff4444"
            },
            {
                "name": "Triple Riding",
                "desc": "Identifies motorcycles carrying more than 2 persons by analyzing person-vehicle overlap",
                "color": "#ffaa00"
            },
            {
                "name": "License Plate Recognition",
                "desc": "Extracts vehicle registration numbers using OCR with contour-based plate detection",
                "color": "#00ff88"
            }
        ]
        for v in violations_info:
            st.markdown(f"""
            <div class="detection-item" style="border-left-color: {v['color']};">
                <strong>{v['name']}</strong><br>
                <small>{v['desc']}</small>
            </div>
            """, unsafe_allow_html=True)

    with col2:
        st.subheader("Recent Detections")
        recent = get_recent_violations(limit=5)
        if recent:
            for v in recent:
                vname = config.VIOLATION_TYPES.get(v.violation_type, v.violation_type)
                vnum = v.vehicle_number if v.vehicle_number else "Unknown"
                st.markdown(f"""
                <div class="detection-item">
                    <strong>{vname}</strong> - {vnum}<br>
                    <small>{v.timestamp[:19]}</small>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No violations recorded yet. Upload an image to get started.")

    st.divider()
    st.markdown("""
    ### System Workflow
    1. **Upload Image** - Upload traffic camera images
    2. **Image Enhancement** - AI-powered preprocessing (brightness, contrast, noise reduction)
    3. **Object Detection** - YOLOv8 detects vehicles, persons, and objects
    4. **Violation Detection** - Helmet compliance & triple riding checks
    5. **License Plate OCR** - Extract vehicle registration numbers
    6. **Evidence Generation** - Annotated images with violation markers
    7. **Database Storage** - All records stored in SQLite
    8. **Analytics Dashboard** - Visual insights and trends
    """)


def main():
    if 'db_initialized' not in st.session_state:
        init_db()
        st.session_state.db_initialized = True

    st.sidebar.image(
        "https://img.icons8.com/color/96/traffic-jam.png",
        width=80,
    )
    st.sidebar.title("TRINETRA AI")
    st.sidebar.markdown("---")

    pages = {
        "Home": home_page,
        "Upload Image": "upload",
        "Violation Records": "records",
        "Analytics": "analytics",
        "AI Copilot": "copilot",
    }

    selection = st.sidebar.radio("Navigation", list(pages.keys()))

    st.sidebar.markdown("---")
    st.sidebar.markdown("### System Status")
    st.sidebar.markdown("🟢 **AI Engine:** Ready")
    st.sidebar.markdown("🟢 **Database:** Connected")
    st.sidebar.markdown("🟢 **OCR:** Loaded")

    st.sidebar.markdown("---")
    st.sidebar.markdown("**TRINETRA AI v1.0**")
    st.sidebar.markdown("Powered by YOLOv8 + EasyOCR")

    if selection == "Home":
        home_page()
    elif selection == "Upload Image":
        from pages.upload import show as upload_show
        upload_show()
    elif selection == "Violation Records":
        from pages.records import show as records_show
        records_show()
    elif selection == "Analytics":
        from pages.analytics import show as analytics_show
        analytics_show()
    elif selection == "AI Copilot":
        from pages.copilot import show as copilot_show
        copilot_show()


if __name__ == '__main__':
    main()
