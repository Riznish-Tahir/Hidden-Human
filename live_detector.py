import cv2
import numpy as np
from ultralytics import YOLO
import pygame
import threading
from pathlib import Path
import mediapipe as mp
import csv
import os
from datetime import datetime
from flask import Flask, Response, render_template_string

# ===================== PYGAME AUDIO SETUP =====================
pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)

alert_playing = False
alert_stop_event = threading.Event()

def play_alert_loop():
    """Continuously loops the alarm while hidden_mode is active."""
    global alert_playing
    try:
        pygame.mixer.music.load("alert.mp3")
        pygame.mixer.music.set_volume(1.0)
        pygame.mixer.music.play(-1)  # -1 = loop forever
        while not alert_stop_event.is_set():
            pygame.time.Clock().tick(10)
        pygame.mixer.music.stop()
    except Exception as e:
        print(f"[AUDIO ERROR] {e}")
    finally:
        alert_playing = False

def start_alarm():
    global alert_playing
    if not alert_playing:
        alert_playing = True
        alert_stop_event.clear()
        threading.Thread(target=play_alert_loop, daemon=True).start()

def stop_alarm():
    global alert_playing
    if alert_playing or pygame.mixer.music.get_busy():
        alert_stop_event.set()
        pygame.mixer.music.stop()
        alert_playing = False

# ===================== MEDIAPIPE IMPORTS =====================
from mediapipe.tasks.python.core.base_options import BaseOptions
from mediapipe.tasks.python.vision import HandLandmarker, HandLandmarkerOptions
from mediapipe.tasks.python.vision.core.vision_task_running_mode import VisionTaskRunningMode

# ===================== SETUP DIRECTORIES =====================
os.makedirs("incidents", exist_ok=True)
LOG_FILE = "incidents/incident_log.csv"
if not os.path.exists(LOG_FILE):
    with open(LOG_FILE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Timestamp", "ThreatLevel", "ThreatLabel", "Reason"])

# ===================== FLASK WEB DASHBOARD =====================
app          = Flask(__name__)
latest_frame = None
latest_stats = {
    "hidden":    False,
    "threat":    0,
    "persons":   0,
    "incidents": 0,
    "alerts":    True,
    "gesture":   "NONE",
    "label":     "LOW THREAT",
    "time":      ""
}

HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta http-equiv="refresh" content="1"/>
  <title>Security System Dashboard</title>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Rajdhani:wght@600;700&display=swap');
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    body { background: #060810; color: #c8d8e8; font-family: 'Share Tech Mono', monospace; min-height: 100vh; }
    header {
      display: flex; align-items: center; justify-content: space-between;
      padding: 14px 28px; background: #0b0f1a; border-bottom: 1px solid #1a2540;
    }
    header h1 {
      font-family: 'Rajdhani', sans-serif; font-size: 1.5rem; font-weight: 700;
      letter-spacing: 3px; color: #00e5cc; text-transform: uppercase;
    }
    .header-right { font-size: 0.78rem; color: #445566; }
    .dot {
      display: inline-block; width: 8px; height: 8px; border-radius: 50%;
      background: #00e5cc; margin-right: 6px; animation: pulse 1.4s ease-in-out infinite;
    }
    @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.2; } }
    .container { display: grid; grid-template-columns: 1fr 280px; gap: 0; height: calc(100vh - 57px); }
    .feed-panel { padding: 20px; display: flex; flex-direction: column; gap: 12px; }
    .feed-label { font-size: 0.68rem; letter-spacing: 2px; color: #445566; }
    .feed-wrap {
      position: relative; background: #000; border: 1px solid #1a2540;
      overflow: hidden; flex: 1; display: flex; align-items: center; justify-content: center;
    }
    .feed-wrap img { max-width: 100%; max-height: 100%; display: block; }
    .feed-corner { position: absolute; width: 16px; height: 16px; border-color: #00e5cc; border-style: solid; }
    .tl { top: 8px; left: 8px;   border-width: 2px 0 0 2px; }
    .tr { top: 8px; right: 8px;  border-width: 2px 2px 0 0; }
    .bl { bottom: 8px; left: 8px;  border-width: 0 0 2px 2px; }
    .br { bottom: 8px; right: 8px; border-width: 0 2px 2px 0; }
    .sidebar {
      background: #0b0f1a; border-left: 1px solid #1a2540;
      padding: 20px 16px; display: flex; flex-direction: column; gap: 16px; overflow-y: auto;
    }
    .card { background: #0f1520; border: 1px solid #1a2540; border-radius: 6px; padding: 12px 14px; }
    .card-label { font-size: 0.6rem; letter-spacing: 2px; color: #445566; margin-bottom: 6px; }
    .card-value { font-family: 'Rajdhani', sans-serif; font-size: 2rem; font-weight: 700; line-height: 1; }
    .card-sub { font-size: 0.65rem; color: #445566; margin-top: 4px; }
    .green  { color: #00e57a; } .red    { color: #ff2244; }
    .orange { color: #ff8800; } .cyan   { color: #00e5cc; }
    .dim    { color: #334455; }
    .bar-wrap { background: #0f1520; border: 1px solid #1a2540; border-radius: 6px; padding: 12px 14px; }
    .bar-track { background: #1a2030; border-radius: 3px; height: 10px; margin: 8px 0 6px; overflow: hidden; }
    .bar-fill { height: 100%; border-radius: 3px; transition: width 0.4s ease; }
    .alert-banner {
      background: #ff0022; color: #fff; text-align: center; padding: 8px;
      font-family: 'Rajdhani', sans-serif; font-size: 1rem; font-weight: 700;
      letter-spacing: 3px; border-radius: 4px; animation: flash 0.8s step-start infinite;
    }
    @keyframes flash { 0%, 100% { opacity: 1; } 50% { opacity: 0.15; } }
    .gesture-badge {
      display: inline-block; padding: 4px 10px; border-radius: 4px;
      font-family: 'Rajdhani', sans-serif; font-size: 1.1rem;
      font-weight: 700; letter-spacing: 2px; margin-top: 4px;
    }
    .legend { font-size: 0.6rem; color: #334455; line-height: 1.8; border-top: 1px solid #1a2540; padding-top: 12px; }
    .legend span { color: #556677; }
  </style>
</head>
<body>
<header>
  <h1><span class="dot"></span>Hidden Human Detector</h1>
  <div class="header-right">{{ stats.time }} &nbsp;|&nbsp; LIVE FEED</div>
</header>
<div class="container">
  <div class="feed-panel">
    <div class="feed-label">&#9654; CAMERA FEED — REAL TIME</div>
    <div class="feed-wrap">
      <div class="feed-corner tl"></div><div class="feed-corner tr"></div>
      <div class="feed-corner bl"></div><div class="feed-corner br"></div>
      <img src="/frame" alt="Live Feed"/>
    </div>
  </div>
  <div class="sidebar">
    {% if stats.hidden %}
    <div class="alert-banner">&#9888; HIDDEN HUMAN DETECTED</div>
    {% endif %}
    <div class="card">
      <div class="card-label">SYSTEM STATUS</div>
      <div class="card-value {{ 'red' if stats.hidden else 'green' }}">
        {{ 'ALERT' if stats.hidden else 'CLEAR' }}
      </div>
      <div class="card-sub">{{ 'Person hidden from camera' if stats.hidden else 'No threats detected' }}</div>
    </div>
    <div class="bar-wrap">
      <div class="card-label">THREAT LEVEL</div>
      <div class="card-value {{ 'red' if stats.threat >= 70 else 'orange' if stats.threat >= 40 else 'green' }}">
        {{ stats.threat }}%
      </div>
      <div class="bar-track">
        <div class="bar-fill" style="
          width: {{ stats.threat }}%;
          background: {{ '#ff2244' if stats.threat >= 70 else '#ff8800' if stats.threat >= 40 else '#00e57a' }};
        "></div>
      </div>
      <div class="card-sub">{{ stats.label }}</div>
    </div>
    <div class="card">
      <div class="card-label">PERSONS DETECTED</div>
      <div class="card-value {{ 'cyan' if stats.persons > 0 else 'dim' }}">{{ stats.persons }}</div>
    </div>
    <div class="card">
      <div class="card-label">INCIDENTS LOGGED</div>
      <div class="card-value {{ 'red' if stats.incidents > 0 else 'dim' }}">{{ stats.incidents }}</div>
      <div class="card-sub">Saved to incidents/</div>
    </div>
    <div class="card">
      <div class="card-label">AUDIO ALERTS</div>
      <div class="card-value {{ 'green' if stats.alerts else 'red' }}">
        {{ 'ENABLED' if stats.alerts else 'MUTED' }}
      </div>
    </div>
    <div class="card">
      <div class="card-label">LAST GESTURE</div>
      <div class="gesture-badge" style="
        background: {{ '#00e57a22' if stats.gesture == 'OK' else '#ff222422' if stats.gesture == 'STOP' else '#00e5cc22' if stats.gesture == 'HELP' else '#1a2030' }};
        color:      {{ '#00e57a'   if stats.gesture == 'OK' else '#ff2244'   if stats.gesture == 'STOP' else '#00e5cc'   if stats.gesture == 'HELP' else '#334455' }};
        border: 1px solid {{ '#00e57a44' if stats.gesture == 'OK' else '#ff224444' if stats.gesture == 'STOP' else '#00e5cc44' if stats.gesture == 'HELP' else '#1a2540' }};
      ">{{ stats.gesture }}</div>
    </div>
    <div class="legend">
      <span>OK</span> — Clear last person<br/>
      <span>STOP</span> — Mute audio alerts<br/>
      <span>HELP</span> — Enable audio alerts<br/>
      <span>Q</span> — Quit application
    </div>
  </div>
</div>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML, stats=latest_stats)

@app.route("/frame")
def get_frame():
    global latest_frame
    if latest_frame is None:
        return "", 204
    _, buf = cv2.imencode(".jpg", latest_frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
    return Response(buf.tobytes(), mimetype="image/jpeg")

def run_flask():
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)

threading.Thread(target=run_flask, daemon=True).start()
print("\n[WEB] Dashboard → http://localhost:5000")
print("[WEB] On your phone open → http://<YOUR-PC-IP>:5000\n")

# ===================== YOLO =====================
model = YOLO("yolov8n.pt")
url   = "http://162.198.190.132:4047/video"
cap   = cv2.VideoCapture(url)

# ===================== STATE =====================
last_persons      = []
prev_persons      = []
alerts_enabled    = True
hidden_duration   = 0
snapshot_cooldown = 0
incident_count    = 0
current_gesture   = None

# ===================== HAND LANDMARKER =====================
task_path    = Path("hand_landmarker.task").resolve()
hand_options = HandLandmarkerOptions(
    base_options=BaseOptions(model_asset_path=str(task_path)),
    running_mode=VisionTaskRunningMode.VIDEO,
    num_hands=1
)
hand_detector = HandLandmarker.create_from_options(hand_options)

# ===================== FULLSCREEN WINDOW SETUP =====================
WIN_NAME = "Hidden Human Detector — Security System"
cv2.namedWindow(WIN_NAME, cv2.WINDOW_NORMAL)
cv2.setWindowProperty(WIN_NAME, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

# Camera feed size (larger)
CAM_W, CAM_H = 1280, 720
# Dashboard panel width (larger)
DASH_W = 380

# ===================== GESTURE =====================
def detect_gesture(landmarks):
    thumb  = landmarks[4];  index  = landmarks[8]
    middle = landmarks[12]; ring   = landmarks[16]; pinky = landmarks[20]

    dist = ((thumb.x-index.x)**2 + (thumb.y-index.y)**2 + (thumb.z-index.z)**2)**0.5
    others_up = all([middle.y < landmarks[10].y,
                     ring.y   < landmarks[14].y,
                     pinky.y  < landmarks[18].y])
    if dist < 0.08 and others_up:
        return "OK"
    if all([index.y < landmarks[6].y,  middle.y < landmarks[10].y,
            ring.y  < landmarks[14].y, pinky.y  < landmarks[18].y]):
        return "HELP"
    if all([index.y > landmarks[6].y,  middle.y > landmarks[10].y,
            ring.y  > landmarks[14].y, pinky.y  > landmarks[18].y]):
        return "STOP"
    return None

# ===================== THREAT =====================
def calculate_threat(hidden_mode, hidden_duration, last_persons, prev_persons, shape):
    if not hidden_mode:
        return 0.0
    h, w   = shape[:2]
    threat = 0.0
    threat += min((hidden_duration / 90) * 40, 40)
    if last_persons and prev_persons:
        try:
            b1, b2 = last_persons[0], prev_persons[0]
            speed  = (((b1[0]+b1[2])/2 - (b2[0]+b2[2])/2)**2 +
                      ((b1[1]+b1[3])/2 - (b2[1]+b2[3])/2)**2)**0.5
            threat += min(speed * 0.5, 30)
        except Exception:
            pass
    if last_persons:
        try:
            box = last_persons[0]
            cx  = (box[0]+box[2])/2;  cy = (box[1]+box[3])/2
            if (w//4 < cx < 3*w//4) and (h//4 < cy < 3*h//4):
                threat += 30
        except Exception:
            pass
    return min(threat, 100.0)

def threat_meta(t):
    if t >= 70: return "HIGH THREAT", (0, 0, 255)
    if t >= 40: return "MED THREAT",  (0, 140, 255)
    return             "LOW THREAT",  (0, 220, 80)

# ===================== INCIDENT LOG =====================
def log_incident(frame, threat, label, reason):
    global incident_count
    incident_count += 1
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    cv2.imwrite(f"incidents/incident_{ts}.jpg", frame)
    with open(LOG_FILE, "a", newline="") as f:
        csv.writer(f).writerow([datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                 f"{threat:.1f}", label, reason])
    print(f"[INCIDENT] #{incident_count} — {label} ({threat:.0f}%)")

# ===================== DRAW ZONES =====================
def draw_zones(frame):
    h, w = frame.shape[:2]
    ov   = frame.copy()
    cv2.rectangle(ov, (w//4, h//4), (3*w//4, 3*h//4), (0, 0, 180), -1)
    cv2.addWeighted(ov, 0.10, frame, 0.90, 0, frame)
    cv2.rectangle(frame, (w//4, h//4), (3*w//4, 3*h//4), (0, 0, 220), 2)
    cv2.putText(frame, "RESTRICTED ZONE", (w//4+8, h//4-10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 0, 220), 2)

# ===================== DRAW DASHBOARD (LARGE) =====================
def draw_dashboard(persons_count, hidden_mode, threat, alerts_enabled, gesture, incidents):
    d = np.zeros((CAM_H, DASH_W, 3), dtype=np.uint8)
    d[:] = (11, 15, 26)
    t_label, t_color = threat_meta(threat)

    # ---- Header ----
    cv2.rectangle(d, (0, 0), (DASH_W, 64), (16, 20, 36), -1)
    cv2.putText(d, "SECURITY SYSTEM", (12, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.72, (0, 220, 180), 2)
    cv2.putText(d, datetime.now().strftime("%H:%M:%S"), (12, 54),
                cv2.FONT_HERSHEY_SIMPLEX, 0.65, (60, 80, 100), 1)
    cv2.line(d, (0, 64), (DASH_W, 64), (30, 40, 60), 1)

    # ---- Status ----
    y = 78
    cv2.putText(d, "STATUS", (12, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (60, 80, 100), 1)
    y += 36
    status_txt = "!! HIDDEN !!" if hidden_mode else "ALL CLEAR"
    status_col = (0, 0, 255) if hidden_mode else (0, 220, 80)
    cv2.putText(d, status_txt, (12, y), cv2.FONT_HERSHEY_SIMPLEX, 0.95, status_col, 3)
    y += 18
    cv2.line(d, (0, y), (DASH_W, y), (25, 35, 55), 1)

    # ---- Persons ----
    y += 22
    cv2.putText(d, "PERSONS DETECTED", (12, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (60, 80, 100), 1)
    y += 46
    cv2.putText(d, str(persons_count), (12, y), cv2.FONT_HERSHEY_SIMPLEX, 1.7,
                (0, 220, 180) if persons_count > 0 else (40, 50, 70), 3)
    y += 14
    cv2.line(d, (0, y), (DASH_W, y), (25, 35, 55), 1)

    # ---- Threat ----
    y += 22
    cv2.putText(d, f"THREAT  {threat:.0f}%", (12, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (60, 80, 100), 1)
    y += 22
    bar_w = int((threat / 100) * (DASH_W - 24))
    cv2.rectangle(d, (12, y), (DASH_W - 12, y + 22), (25, 35, 55), -1)
    if bar_w > 0:
        cv2.rectangle(d, (12, y), (12 + bar_w, y + 22), t_color, -1)
    y += 34
    cv2.putText(d, t_label, (12, y), cv2.FONT_HERSHEY_SIMPLEX, 0.75, t_color, 2)
    y += 14
    cv2.line(d, (0, y), (DASH_W, y), (25, 35, 55), 1)

    # ---- Audio ----
    y += 22
    cv2.putText(d, "AUDIO ALERTS", (12, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (60, 80, 100), 1)
    y += 38
    cv2.putText(d, "ENABLED" if alerts_enabled else "MUTED", (12, y), cv2.FONT_HERSHEY_SIMPLEX, 0.85,
                (0, 220, 80) if alerts_enabled else (0, 60, 200), 2)
    y += 14
    cv2.line(d, (0, y), (DASH_W, y), (25, 35, 55), 1)

    # ---- Gesture ----
    y += 22
    cv2.putText(d, "GESTURE", (12, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (60, 80, 100), 1)
    y += 40
    gc = {"OK": (0, 220, 80), "STOP": (0, 0, 255), "HELP": (0, 220, 220)}
    cv2.putText(d, gesture or "NONE", (12, y), cv2.FONT_HERSHEY_SIMPLEX, 0.95,
                gc.get(gesture, (50, 60, 80)), 2)
    y += 14
    cv2.line(d, (0, y), (DASH_W, y), (25, 35, 55), 1)

    # ---- Incidents ----
    y += 22
    cv2.putText(d, "INCIDENTS LOGGED", (12, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (60, 80, 100), 1)
    y += 46
    cv2.putText(d, str(incidents), (12, y), cv2.FONT_HERSHEY_SIMPLEX, 1.5,
                (0, 60, 220) if incidents > 0 else (40, 50, 70), 3)
    y += 14
    cv2.line(d, (0, y), (DASH_W, y), (25, 35, 55), 1)

    # ---- Web URL ----
    y += 20
    cv2.putText(d, "WEB: localhost:5000", (12, y), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (40, 60, 80), 1)
    y += 26
    cv2.putText(d, "OK=Clear  STOP=Mute", (12, y), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (35, 50, 70), 1)
    y += 22
    cv2.putText(d, "HELP=Unmute  Q=Quit", (12, y), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (35, 50, 70), 1)

    return d

# ===================== MAIN LOOP =====================
while True:
    ret, frame = cap.read()
    if not ret:
        break

    # Resize camera frame to larger size
    frame     = cv2.resize(frame, (CAM_W, CAM_H))
    annotated = frame.copy()
    draw_zones(annotated)

    # --- PERSON DETECTION ---
    results      = model(frame, conf=0.25, verbose=False)
    detected_now = [box for box, cls in zip(results[0].boxes.xyxy, results[0].boxes.cls)
                    if int(cls) == 0]

    hidden_mode = False
    if detected_now:
        prev_persons    = last_persons
        last_persons    = detected_now
        persons         = detected_now
        hidden_duration = 0
    else:
        persons = last_persons
        if last_persons:
            hidden_mode      = True
            hidden_duration += 1

    # --- HAND DETECTION ---
    rgb      = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    mp_img   = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
    ts_ms    = int(cv2.getTickCount() / cv2.getTickFrequency() * 1000)
    hand_res = hand_detector.detect_for_video(mp_img, timestamp_ms=ts_ms)

    current_gesture = None
    if hand_res.hand_landmarks:
        for lm in hand_res.hand_landmarks:
            current_gesture = detect_gesture(lm)
            if current_gesture == "STOP":
                alerts_enabled = False
                stop_alarm()
            elif current_gesture == "OK":
                last_persons    = []
                hidden_duration = 0
                stop_alarm()
            elif current_gesture == "HELP":
                alerts_enabled = True

    # --- THREAT ---
    threat           = calculate_threat(hidden_mode, hidden_duration,
                                        last_persons, prev_persons, frame.shape)
    t_label, t_color = threat_meta(threat)

    # --- ALERTS & LOGGING ---
    snapshot_cooldown = max(0, snapshot_cooldown - 1)

    if hidden_mode and alerts_enabled:
        # Large flashing warning text
        if (hidden_duration // 12) % 2 == 0:
            txt = "! HIDDEN HUMAN DETECTED !"
            font_scale = 1.4
            thickness  = 4
            (tw, th), _ = cv2.getTextSize(txt, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)
            tx = (CAM_W - tw) // 2
            # dark backdrop
            cv2.rectangle(annotated, (tx - 12, 18), (tx + tw + 12, 18 + th + 20), (0, 0, 0), -1)
            cv2.putText(annotated, txt, (tx, 18 + th + 4),
                        cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 0, 255), thickness)

        # ---- ALARM: loop continuously while hidden ----
        start_alarm()

        # Save snapshot on high threat
        if threat >= 70 and snapshot_cooldown == 0:
            log_incident(annotated, threat, t_label, "High threat hidden person")
            snapshot_cooldown = 90

    else:
        # Person visible again — stop alarm immediately
        stop_alarm()

    # --- PERSON BOXES ---
    for box in persons:
        x1, y1, x2, y2 = map(int, box)
        color = t_color if hidden_mode else (0, 220, 80)
        label = f"Hidden [{t_label}]" if hidden_mode else "Person"
        cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 3)
        cv2.putText(annotated, label, (x1, max(y1 - 14, 20)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.85, color, 2)

    # --- GESTURE OVERLAY ---
    if current_gesture:
        gc = {"OK": (0, 220, 80), "STOP": (0, 0, 255), "HELP": (0, 220, 220)}
        cv2.putText(annotated, f"GESTURE: {current_gesture}",
                    (20, CAM_H - 30), cv2.FONT_HERSHEY_SIMPLEX, 1.1,
                    gc.get(current_gesture, (255, 255, 255)), 3)

    # --- BUILD FINAL FRAME ---
    dash     = draw_dashboard(len(persons), hidden_mode, threat,
                               alerts_enabled, current_gesture, incident_count)
    combined = np.hstack([annotated, dash])

    # --- UPDATE WEB DASHBOARD ---
    latest_frame = combined
    latest_stats.update({
        "hidden":    hidden_mode,
        "threat":    int(threat),
        "persons":   len(persons),
        "incidents": incident_count,
        "alerts":    alerts_enabled,
        "gesture":   current_gesture or "NONE",
        "label":     t_label,
        "time":      datetime.now().strftime("%H:%M:%S")
    })

    cv2.imshow(WIN_NAME, combined)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

stop_alarm()
cap.release()
cv2.destroyAllWindows()
print(f"\n[DONE] Session ended. {incident_count} incidents logged to incidents/")
