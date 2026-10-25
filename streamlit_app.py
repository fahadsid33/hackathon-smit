import streamlit as st
import cv2
import numpy as np
import math
import json
import os
from datetime import datetime, timezone

# --- Page Configuration ---
st.set_page_config(
    page_title="GeoFace Attendance AI",
    page_icon="📷",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for modern dark UI
st.markdown("""
<style>
    .main { background-color: #0b0f19; }
    .stMetric { background-color: #161f30; padding: 12px; border-radius: 10px; border: 1px solid #23334d; }
    .badge-approved { background-color: #064e3b; color: #34d399; padding: 4px 10px; border-radius: 12px; font-weight: bold; border: 1px solid #059669; }
    .badge-rejected { background-color: #4c0519; color: #f87171; padding: 4px 10px; border-radius: 12px; font-weight: bold; border: 1px solid #be123c; }
    .privacy-notice { background-color: #111827; border-left: 4px solid #6366f1; padding: 12px; border-radius: 6px; font-size: 13px; color: #9ca3af; }
</style>
""", unsafe_allow_html=True)

# --- Session State Initialization ---
if "office" not in st.session_state:
    st.session_state.office = {
        "name": "TechCorp HQ",
        "latitude": 37.789172,
        "longitude": -122.401449,
        "radius_meters": 150,
        "max_accuracy_meters": 100
    }

if "employees" not in st.session_state:
    st.session_state.employees = [
        {"id": "EMP-001", "name": "Alex Morgan", "dept": "Engineering"},
        {"id": "EMP-002", "name": "Sarah Chen", "dept": "Design"},
        {"id": "EMP-003", "name": "David Kumar", "dept": "DevOps"},
        {"id": "EMP-004", "name": "Elena Rostova", "dept": "Human Resources"}
    ]

if "attendance_logs" not in st.session_state:
    st.session_state.attendance_logs = [
        {
            "id": "att-101",
            "employee_id": "EMP-001",
            "employee_name": "Alex Morgan",
            "type": "CHECK_IN",
            "timestamp": "2026-10-25 09:02:14 UTC",
            "source": "camera",
            "status": "APPROVED",
            "distance_meters": 42.5,
            "accuracy_meters": 18.0,
            "face_count": 1,
            "rejection_reason": None
        }
    ]

if "corrections" not in st.session_state:
    st.session_state.corrections = [
        {
            "id": "corr-01",
            "employee_id": "EMP-003",
            "employee_name": "David Kumar",
            "type": "CHECK_IN",
            "date": "2026-10-25",
            "time": "09:05",
            "reason": "GPS drift in basement server room (rejected with accuracy > 100m)",
            "status": "PENDING"
        }
    ]

# --- Haversine Distance Calculation (Server Function) ---
def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371000  # Earth radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (math.sin(delta_phi / 2.0) ** 2 +
         math.cos(phi1) * math.cos(phi2) * (math.sin(delta_lambda / 2.0) ** 2))
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(R * c, 2)

# --- Face Detection Engine ---
def detect_faces(image_bytes):
    # Convert image bytes to OpenCV format
    file_bytes = np.asarray(bytearray(image_bytes.read()), dtype=np.uint8)
    img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Load Haar cascade classifier for frontal face
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')

    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60))
    face_count = len(faces)
    
    has_eyes = False
    annotated_img = img.copy()

    for (x, y, w, h) in faces:
        cv2.rectangle(annotated_img, (x, y), (x + w, y + h), (0, 255, 0), 3)
        roi_gray = gray[y:y+h, x:x+w]
        eyes = eye_cascade.detectMultiScale(roi_gray, scaleFactor=1.1, minNeighbors=3)
        if len(eyes) >= 1:
            has_eyes = True
        for (ex, ey, ew, eh) in eyes:
            cv2.rectangle(annotated_img, (x + ex, y + ey), (x + ex + ew, y + ey + eh), (255, 0, 0), 2)

    # Convert back to RGB for Streamlit rendering
    annotated_rgb = cv2.cvtColor(annotated_img, cv2.COLOR_BGR2RGB)
    return face_count, has_eyes, annotated_rgb

# --- Sidebar / Header ---
st.sidebar.title("🏢 GeoFace System")
selected_emp_name = st.sidebar.selectbox(
    "Active Employee Profile",
    options=[e["name"] for e in st.session_state.employees]
)
current_emp = next(e for e in st.session_state.employees if e["name"] == selected_emp_name)

st.sidebar.markdown(f"**ID:** `{current_emp['id']}`  \n**Department:** {current_emp['dept']}")
st.sidebar.divider()
st.sidebar.markdown(f"**Office:** {st.session_state.office['name']}  \n**Radius Limit:** {st.session_state.office['radius_meters']}m  \n**Max Accuracy:** {st.session_state.office['max_accuracy_meters']}m")

# Main Navigation Tabs
tabs = st.tabs(["📷 Mark Attendance", "📋 Attendance Logs", "📝 HR Correction Fallback", "⚙️ Admin Geofence"])

# ==================== TAB 1: MARK ATTENDANCE ====================
with tabs[0]:
    st.title("📷 Camera Attendance & Geofence Verification")
    st.write(f"Marking attendance for **{current_emp['name']}** ({current_emp['id']})")

    # Geolocation / Simulator Selector
    col_sim, col_acc = st.columns([2, 1])
    with col_sim:
        sim_mode = st.radio(
            "GPS Location Test Preset:",
            ["Inside Office (HQ - 25m away)", "Outside Radius (2.5 km away)", "Weak GPS Signal (>100m accuracy)", "Custom Coordinates"],
            horizontal=True
        )

    if sim_mode == "Inside Office (HQ - 25m away)":
        user_lat = st.session_state.office["latitude"] + 0.00015
        user_lon = st.session_state.office["longitude"] + 0.00010
        user_acc = 18.0
    elif sim_mode == "Outside Radius (2.5 km away)":
        user_lat = st.session_state.office["latitude"] + 0.022
        user_lon = st.session_state.office["longitude"] + 0.022
        user_acc = 22.0
    elif sim_mode == "Weak GPS Signal (>100m accuracy)":
        user_lat = st.session_state.office["latitude"]
        user_lon = st.session_state.office["longitude"]
        user_acc = 160.0  # Fails accuracy <= 100m
    else:
        c1, c2, c3 = st.columns(3)
        user_lat = c1.number_input("Latitude", value=st.session_state.office["latitude"], format="%.6f")
        user_lon = c2.number_input("Longitude", value=st.session_state.office["longitude"], format="%.6f")
        user_acc = c3.number_input("GPS Accuracy (m)", value=20.0, format="%.1f")

    # Real-time Telemetry Metrics
    dist = haversine_distance(user_lat, user_lon, st.session_state.office["latitude"], st.session_state.office["longitude"])
    is_inside = dist <= st.session_state.office["radius_meters"]
    is_acc_ok = user_acc <= st.session_state.office["max_accuracy_meters"]

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Office Distance", f"{dist} m", f"{'Within' if is_inside else 'Outside'} {st.session_state.office['radius_meters']}m limit", delta_color="normal" if is_inside else "inverse")
    m2.metric("GPS Accuracy", f"±{user_acc:.1f} m", "Valid (≤ 100m)" if is_acc_ok else "Too Weak (> 100m)", delta_color="normal" if is_acc_ok else "inverse")
    m3.metric("Geofence Status", "INSIDE" if is_inside else "OUTSIDE", delta_color="normal" if is_inside else "inverse")
    m4.metric("Authoritative Clock", datetime.now(timezone.utc).strftime("%H:%M:%S UTC"))

    st.markdown("""
    <div class="privacy-notice">
        🔒 <b>Data Transparency Notice:</b> Only your attendance telemetry (coordinates, distance, accuracy, and face match metrics) are recorded. Camera frames are processed strictly in memory and are not stored.
    </div>
    """, unsafe_allow_html=True)

    st.write("")
    
    # Camera Stream Input
    camera_file = st.camera_input("Look into the front camera and take a snapshot to verify attendance")

    col_btn1, col_btn2 = st.columns(2)
    action_type = "CHECK_IN"

    if camera_file is not None:
        face_count, has_eyes, annotated_img = detect_faces(camera_file)

        col_img, col_res = st.columns([1, 1])
        with col_img:
            st.image(annotated_img, caption=f"Face Analysis: {face_count} face(s) detected", use_container_width=True)

        with col_res:
            st.subheader("Verification Decision Engine")
            
            # 1. Face Count Check (Must be exactly 1)
            face_ok = face_count == 1
            if face_count == 0:
                st.error("❌ Rule Failed: No face detected in camera frame.")
            elif face_count > 1:
                st.error(f"❌ Rule Failed: Multiple faces detected ({face_count} faces). Exactly 1 required.")
            else:
                st.success("✅ Rule Passed: Exactly 1 face detected.")

            # 2. Geofence Distance Check
            if is_inside:
                st.success(f"✅ Rule Passed: Inside office perimeter ({dist}m ≤ {st.session_state.office['radius_meters']}m).")
            else:
                st.error(f"❌ Rule Failed: Outside company location ({dist}m > {st.session_state.office['radius_meters']}m).")

            # 3. GPS Accuracy Check
            if is_acc_ok:
                st.success(f"✅ Rule Passed: GPS accuracy valid (±{user_acc:.1f}m ≤ 100m).")
            else:
                st.error(f"❌ Rule Failed: GPS accuracy too low (±{user_acc:.1f}m > 100m).")

            # Overall Decision
            is_approved = face_ok and is_inside and is_acc_ok
            errors = []
            if not face_ok: errors.append(f"Invalid face count ({face_count})")
            if not is_inside: errors.append(f"Outside geofence ({dist}m)")
            if not is_acc_ok: errors.append(f"Poor GPS (±{user_acc}m)")

            server_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

            btn_in = st.button("Submit Check-In", type="primary", use_container_width=True)
            btn_out = st.button("Submit Check-Out", use_container_width=True)

            if btn_in or btn_out:
                chosen_type = "CHECK_IN" if btn_in else "CHECK_OUT"
                log_entry = {
                    "id": f"att-{int(datetime.now().timestamp())}",
                    "employee_id": current_emp["id"],
                    "employee_name": current_emp["name"],
                    "type": chosen_type,
                    "timestamp": server_time,
                    "source": "camera",
                    "status": "APPROVED" if is_approved else "REJECTED",
                    "distance_meters": dist,
                    "accuracy_meters": user_acc,
                    "face_count": face_count,
                    "rejection_reason": " | ".join(errors) if errors else None
                }
                st.session_state.attendance_logs.insert(0, log_entry)

                if is_approved:
                    st.balloons()
                    st.success(f"🎉 {chosen_type} APPROVED! Timestamped at {server_time}.")
                else:
                    st.error(f"⛔ Attendance REJECTED: {' | '.join(errors)}")
                    st.info("💡 A failed check can be submitted to HR for manual review in the 'HR Correction Fallback' tab.")

# ==================== TAB 2: ATTENDANCE LOGS ====================
with tabs[1]:
    st.title("📋 Official Attendance Audit Trail")
    st.write("Authoritative server logs with distance calculations and rejection audit reasons:")

    if st.session_state.attendance_logs:
        import pandas as pd
        df = pd.DataFrame(st.session_state.attendance_logs)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No attendance records logged yet.")

# ==================== TAB 3: HR CORRECTION FALLBACK ====================
with tabs[2]:
    st.title("📝 HR Attendance Correction Fallback")
    st.write("If camera or GPS verification fails, employees can submit a correction for HR review.")

    with st.form("hr_correction_form"):
        st.subheader("Submit New Request")
        corr_type = st.selectbox("Action", ["CHECK_IN", "CHECK_OUT"])
        corr_date = st.date_input("Target Date")
        corr_time = st.time_input("Target Time")
        corr_reason = st.text_area("Reason for Fallback", placeholder="e.g. GPS drift in basement parking, lighting glare...")
        submit_corr = st.form_submit_button("Submit to HR", type="primary")

        if submit_corr:
            if corr_reason.strip():
                new_corr = {
                    "id": f"corr-{int(datetime.now().timestamp())}",
                    "employee_id": current_emp["id"],
                    "employee_name": current_emp["name"],
                    "type": corr_type,
                    "date": str(corr_date),
                    "time": str(corr_time),
                    "reason": corr_reason.strip(),
                    "status": "PENDING"
                }
                st.session_state.corrections.insert(0, new_corr)
                st.success("Correction request submitted for HR review!")
            else:
                st.warning("Please provide a reason.")

    st.divider()
    st.subheader("Submitted Correction Requests")
    for c in st.session_state.corrections:
        st.markdown(f"**{c['employee_name']}** ({c['employee_id']}) — `{c['type']}` on {c['date']} at {c['time']}  \n*Reason:* {c['reason']}  \n*Status:* **{c['status']}**")
        if c['status'] == 'PENDING':
            col_a, col_r = st.columns(2)
            if col_a.button(f"Approve {c['id']}", key=f"app_{c['id']}"):
                c['status'] = 'APPROVED'
                st.rerun()
            if col_r.button(f"Reject {c['id']}", key=f"rej_{c['id']}"):
                c['status'] = 'REJECTED'
                st.rerun()
        st.write("---")

# ==================== TAB 4: ADMIN GEOFENCE SETTINGS ====================
with tabs[3]:
    st.title("⚙️ Admin Office Geofence Configuration")
    st.write("Configure office coordinates and geofence enforcement rules:")

    with st.form("office_config_form"):
        new_name = st.text_input("Office Name", value=st.session_state.office["name"])
        col_la, col_lo = st.columns(2)
        new_lat = col_la.number_input("Office Latitude", value=st.session_state.office["latitude"], format="%.6f")
        new_lon = col_lo.number_input("Office Longitude", value=st.session_state.office["longitude"], format="%.6f")
        
        col_r, col_acc = st.columns(2)
        new_rad = col_r.number_input("Office Radius (meters)", value=st.session_state.office["radius_meters"], min_value=10, max_value=5000)
        new_acc = col_acc.number_input("Max GPS Accuracy Threshold (meters)", value=st.session_state.office["max_accuracy_meters"], min_value=10, max_value=500)

        save_settings = st.form_submit_button("Update Geofence Rules", type="primary")
        if save_settings:
            st.session_state.office["name"] = new_name
            st.session_state.office["latitude"] = new_lat
            st.session_state.office["longitude"] = new_lon
            st.session_state.office["radius_meters"] = new_rad
            st.session_state.office["max_accuracy_meters"] = new_acc
            st.success("Office geofence settings updated successfully!")
