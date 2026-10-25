# GeoFace Attendance: AI Camera & Geofencing System

[![Node.js](https://img.shields.io/badge/Node.js-v18%2B-green.svg)](https://nodejs.org/)
[![React](https://img.shields.io/badge/React-18-blue.svg)](https://reactjs.org/)
[![Vite](https://img.shields.io/badge/Vite-6-646CFF.svg)](https://vitejs.dev/)
[![Tailwind CSS](https://img.shields.io/badge/TailwindCSS-3.4-38B2AC.svg)](https://tailwindcss.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A complete, production-grade attendance verification system powered by **biometric face detection**, **liveness blink analysis**, and **authoritative server-side GPS geofencing**. 

Includes a **Full Web Application** (React 18 + Vite + Tailwind + Face API) and an optional **Mobile App** (React Native / Expo with `expo-camera` + `expo-location`).

---

## 📋 System Architecture & Verification Flow

```
[ FRONTEND (Web / Mobile) ]
      │
      ├─ 1. Open front camera with live video preview
      ├─ 2. Real-time Face Detection (Check: exactly 1 face in frame)
      ├─ 3. Eye Aspect Ratio (EAR) Liveness Check (Blink verification)
      ├─ 4. Acquire GPS Coordinates (Latitude, Longitude & Accuracy)
      │
      ▼ Send Payload to Server (Device time is NEVER trusted)
{ employeeId, latitude, longitude, accuracy, faceCount, faceDescriptor, livenessVerified, source }
      │
      ▼
[ BACKEND SERVER (Node.js / Express) ]
      │
      ├─ 1. Stamp Authoritative Server Time: new Date()
      ├─ 2. Calculate Distance via Haversine Formula & geolib:
      │       d = 2R · atan2(√a, √(1-a))
      ├─ 3. Evaluate Verification Rules:
      │       ├── Face Rule: Must have faceCount === 1 (reject if 0 or >1)
      │       ├── Accuracy Rule: Must have GPS accuracy ≤ 100 meters
      │       ├── Geofence Rule: Distance to office must be ≤ office.radiusMeters
      │       ├── Biometric Rule: Match 128-d descriptor vector (Euclidean dist ≤ 0.55)
      │       └── Liveness Rule: Liveness flag confirmed
      │
      ├─ 4. Apply Attendance Business Rules (Late calculation, duplicate check)
      ├─ 5. Record Result (Stores telemetry & verification metadata, NOT raw photos)
      │
      ▼
[ RESULT RESPONSE ]
      ├── APPROVED: Status 200, official timestamp, distance, face confidence
      └── REJECTED: Status 422, explicit reason, 1-click fallback to HR Correction
```

---

## ⚡ Key Features

### 1. Web App (MERN / React 18)
- **Live Camera Feed**: Front-facing webcam stream with target oval and real-time bounding boxes.
- **Single-Face Detection**: Real-time evaluation ensuring strictly 1 face is present; flags 0 faces or multi-person frames.
- **Blink & Liveness Verification**: Eye Aspect Ratio (EAR) calculation to detect natural eye blinks and prevent photo spoofing.
- **128-D Biometric Matching**: Calculates Euclidean distance between detected face descriptors and enrolled employee embeddings.
- **High-Accuracy Geolocation**: Browser Geolocation API monitoring latitude, longitude, and accuracy in meters.
- **Testing Simulator**: 1-click simulator bar to test:
  - *Inside Office (HQ Room - 25m distance, 15m accuracy)*
  - *Outside Office (2.5 km away - triggers geofence rejection)*
  - *Weak GPS (165m accuracy - triggers GPS accuracy rejection)*
  - *Set Office to My Real GPS (Calibrate office center to your actual device location)*

### 2. Mobile App (React Native / Expo)
- **Expo Camera**: Front-facing preview with custom guidance overlay and scan lines.
- **Expo Location**: Reads GPS with `Accuracy.High`. Rejects check-in if phone accuracy is worse than 100 meters.
- **Dedicated Screens**: Camera Attendance, Biometric Enrollment, Attendance Logs, HR Correction Fallback, and Settings.

### 3. Server-Side Geofencing Engine
- **Server Authoritative Time**: Client time is discarded; all check-in/out timestamps are generated directly on the server.
- **Dual Distance Calculations**: Haversine formula implemented in pure JavaScript alongside `geolib.getDistance()`.
- **Admin Office Configuration**: Configurable Office Name, Latitude, Longitude, Radius (meters), Max GPS Accuracy threshold, and Work Hours.
- **HR Correction Workflow**: When camera or GPS verification fails, employees submit a manual correction request. HR Admins can review and approve it, which immediately validates and logs official attendance.
- **Privacy By Design**: Stores only attendance metadata, verification metrics, and distance calculations. Raw photos are not retained unless explicitly enabled by company policy.

---

## 📁 Repository Structure

```
.
├── client/                     # Web Application (React 18 + Vite + Tailwind)
│   ├── src/
│   │   ├── components/         # BoundingBoxOverlay, GpsStatusBadge, GeofenceSimulator, etc.
│   │   ├── pages/              # AttendanceCheckInPage, EmployeeEnrollPage, AdminOfficeSettingsPage, etc.
│   │   ├── services/           # api.js, faceDetection.js, geolocation.js
│   │   ├── App.jsx             # Root React view
│   │   └── main.jsx
│   ├── package.json
│   └── vite.config.js
│
├── server/                     # Backend API (Node.js + Express + geolib)
│   ├── src/
│   │   ├── config/             # Database & persistence config
│   │   ├── controllers/        # attendanceController, officeController, employeeController, correctionController
│   │   ├── models/             # store.js (In-memory + JSON-persisted database engine)
│   │   ├── routes/             # attendanceRoutes, officeRoutes, employeeRoutes, correctionRoutes
│   │   ├── services/           # attendanceService.js
│   │   ├── utils/              # haversine.js, faceMatcher.js
│   │   ├── app.js
│   │   └── index.js
│   ├── tests/                  # Automated unit and integration tests
│   └── package.json
│
├── mobile/                     # Mobile Application (React Native / Expo)
│   ├── src/
│   │   ├── screens/            # CameraAttendanceScreen, FaceEnrollScreen, HistoryScreen, CorrectionScreen, SettingsScreen
│   │   └── services/           # api.js, location.js
│   ├── App.js
│   ├── app.json
│   └── package.json
│
└── package.json                # Root orchestration workspace
```

---

## 🚀 Quick Start Guide

### 1. Prerequisites
- **Node.js**: v18 or later
- **npm**: v9 or later

### 2. Run Backend Server
```bash
cd server
npm install
npm start
```
The backend starts on `http://localhost:5000`.  
Health check endpoint: `http://localhost:5000/api/health`.

Run backend unit tests:
```bash
npm test
```

### 3. Run Web App (Frontend)
In a separate terminal:
```bash
cd client
npm install
npm run dev
```
Open your browser at: `http://localhost:5173`.

### 4. Run Mobile App (Optional)
In a separate terminal:
```bash
cd mobile
npm install
npm start
```
- Open on Web: Press `w` in terminal or run `npm run web`.
- Open on Android Emulator: Press `a`.
- Open on Physical Phone: Scan the QR code using the **Expo Go** app (ensure phone is on the same local Wi-Fi as your computer, and set your computer's IP in the app's Config tab).

---

## 🧪 Testing the Rejection Rules

The web app includes an integrated **Geofence Simulator** toolbar at the top of the Camera Attendance screen:

| Scenario | Toolbar Button | Expected Server Decision |
| :--- | :--- | :--- |
| **All Checks Pass** | `Inside Office (25m)` + Blink into camera | **APPROVED**: Attendance saved with server timestamp |
| **No Face Detected** | Turn away or select `Faces: 0` | **REJECTED**: *"No face detected in camera frame"* |
| **Multiple Faces** | Select `Faces: 2` | **REJECTED**: *"Multiple faces detected (2 faces). Exactly one person must be present"* |
| **Outside Radius** | `Outside Radius (2.5 km away)` | **REJECTED**: *"Outside company location. Distance to office is 2500m, allowed radius is 150m"* |
| **Weak GPS** | `Poor GPS (160m accuracy)` | **REJECTED**: *"GPS accuracy is too low (160m). Required: ≤ 100m"* |
| **Real Device Test** | Click `Set Office to My Real GPS` | Aligns office coordinates to your real location, allowing physical test approval |

---

## 📡 API Reference

### Attendance Endpoints
- `POST /api/attendance/check-in`: Process camera attendance check-in.
- `POST /api/attendance/check-out`: Process camera attendance check-out.
- `GET /api/attendance/today?employeeId=EMP-001`: Get today's attendance logs for an employee.
- `GET /api/attendance/history`: Filterable attendance audit trail.
- `GET /api/attendance/stats`: Summary counts of present employees, rejections, and pending requests.

### Office & Geofence Endpoints
- `GET /api/office`: Get current office coordinates, radius, and rules.
- `PUT /api/office`: Update office location, radius, and attendance rules.
- `POST /api/office/test-geofence`: Test any arbitrary (latitude, longitude) coordinate against the office boundary.

### Employee Endpoints
- `GET /api/employees`: List all registered staff and biometric status.
- `GET /api/employees/:id`: Retrieve single employee details.
- `POST /api/employees/:id/enroll-face`: Register 128-d face descriptor vector.

### HR Correction Fallback Endpoints
- `GET /api/corrections`: View pending or historical correction requests.
- `POST /api/corrections`: Submit new fallback request when camera or GPS fails.
- `PATCH /api/corrections/:id`: HR Admin approves or rejects a request.

---

## 🔒 Biometrics & Data Privacy Policy

1. **No Raw Photo Retention**: Camera video is processed locally in the user's browser using client-side neural models. Images are not stored on disk or database unless the company administrator activates the explicit photo compliance backup policy.
2. **Biometric Descriptors**: Faces are represented as 128-dimensional floating-point embedding vectors. Original photos cannot be reconstructed from descriptor vectors.
3. **Transparent Capture**: The user is continuously informed via an on-screen privacy disclosure detailing exactly which metrics (coordinates, distance, accuracy, and face match score) are recorded.

---

## 📄 License
This project is licensed under the MIT License.
