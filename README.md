# 🔍 Hidden Human Detector — AI Security System

> A real-time AI-powered security system that detects when a person **hides from the camera**, triggers an alarm, logs incidents, and supports gesture-based controls. Built with YOLOv8, MediaPipe, OpenCV, and Flask.

---

## 📸 What It Does

- **Detects people** in real-time using YOLOv8
- **Triggers an alarm** when a previously detected person suddenly disappears (hides)
- **Calculates threat level** (Low / Medium / High) based on duration and position
- **Saves incident snapshots** automatically when threat is high
- **Gesture controls** — use your hand to mute alarm, clear alerts, or unmute
- **Live web dashboard** — view on your phone via browser
- **Fullscreen OpenCV display** with a built-in sidebar dashboard
- Works with **Webcam**, **DroidCam**, or **OBS Virtual Camera**

---

## 📁 Project Structure

```
hidden-human/
│
├── hidden_human_detector.py     # Main script
├── alert.mp3                    # Alarm sound file (add your own)
├── hand_landmarker.task         # MediaPipe hand model (download separately)
├── yolov8n.pt                   # YOLOv8 nano model (auto-downloads)
│
└── incidents/                   # Auto-created folder
    ├── incident_log.csv         # Log of all incidents
    └── incident_YYYYMMDD_*.jpg  # Snapshots saved on high threat
```

---

## 🖥️ System Requirements

| Requirement | Details |
|-------------|---------|
| OS | Windows 10/11, Ubuntu 20.04+, macOS 12+ |
| Python | **3.11** (recommended — see install link below) |
| RAM | 4GB minimum, 8GB recommended |
| Camera | Webcam / Phone (DroidCam) / OBS Virtual Cam |
| GPU | Optional but speeds up YOLO inference |

---

## ⬇️ Step 1 — Install Python 3.11

> ⚠️ Use **Python 3.11** specifically. MediaPipe may have issues on 3.12+.

- **Windows**: [https://www.python.org/downloads/release/python-3119/](https://www.python.org/downloads/release/python-3119/)
  - Scroll down → Download **Windows installer (64-bit)**
  - ✅ Check **"Add Python to PATH"** during install

- **Ubuntu/Debian**:
  ```bash
  sudo apt update
  sudo apt install python3.11 python3.11-pip python3.11-venv -y
  ```

- **macOS** (via Homebrew):
  ```bash
  brew install python@3.11
  ```

Verify install:
```bash
python --version
# Should show: Python 3.11.x
```

---

## ⬇️ Step 2 — Clone This Repo

```bash
git clone https://github.com/Riznish-Tahir/hidden-human.git
cd hidden-human
```

---

## ⬇️ Step 3 — Create a Virtual Environment (Recommended)

```bash
# Create environment
python -m venv venv

# Activate — Windows
venv\Scripts\activate

# Activate — Mac/Linux
source venv/bin/activate
```

---

## ⬇️ Step 4 — Install All Dependencies

```bash
pip install ultralytics opencv-python mediapipe pygame flask numpy
```

Install breakdown:

| Package | Purpose |
|---------|---------|
| `ultralytics` | YOLOv8 — person detection |
| `opencv-python` | Camera feed, drawing, display |
| `mediapipe` | Hand landmark detection for gestures |
| `pygame` | Playing the alarm sound |
| `flask` | Web dashboard (view on phone) |
| `numpy` | Frame manipulation |

---

## ⬇️ Step 5 — Download the MediaPipe Hand Model

The hand gesture system needs a `.task` model file. Download it here:

🔗 **[hand_landmarker.task](https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task)**

Place it in the **same folder** as `hidden_human_detector.py`:
```
hidden-human/
├── hidden_human_detector.py
├── hand_landmarker.task   ✅ here
```

---

## ⬇️ Step 6 — Add an Alarm Sound

Add any `.mp3` file named `alert.mp3` to the project folder.

You can download a free alarm sound from:
- [https://freesound.org](https://freesound.org) — search "alarm"
- [https://pixabay.com/sound-effects/](https://pixabay.com/sound-effects/) — search "siren"

Rename it to `alert.mp3` and place it next to the script.

---

## 📷 Step 7 — Choose Your Camera

The script has a `url` variable near the top. Change it depending on your camera:

### Option A — Webcam (built-in or USB)

```python
# In hidden_human_detector.py, find this line:
url = "http://182.968.180.132:4647/video"

# Replace with:
cap = cv2.VideoCapture(0)   # 0 = first webcam, try 1 or 2 if it doesn't work
```

> Change the full line `cap = cv2.VideoCapture(url)` to `cap = cv2.VideoCapture(0)`

### Option B — DroidCam (Use your Android phone as webcam)

1. Install **DroidCam** on your phone:
   - Android: [https://play.google.com/store/apps/details?id=com.dev47apps.droidcam](https://play.google.com/store/apps/details?id=com.dev47apps.droidcam)

2. Install **DroidCam Client** on your PC:
   - Windows: [https://www.dev47apps.com/droidcam/windows/](https://www.dev47apps.com/droidcam/windows/)

3. Connect phone and PC to the **same WiFi**

4. Open DroidCam on your phone — note the **IP address** shown (e.g. `192.168.1.5`)

5. Update the script:
```python
url = "http://192.168.1.5:4747/video"   # replace with YOUR phone's IP
cap = cv2.VideoCapture(url)
```

### Option C — OBS Virtual Camera

1. Install **OBS Studio**: [https://obsproject.com/](https://obsproject.com/)

2. In OBS → click **"Start Virtual Camera"** (bottom right)

3. Update the script:
```python
cap = cv2.VideoCapture(1)   # OBS Virtual Cam usually shows as index 1 or 2
```

> Try index `0`, `1`, `2` until you get the OBS feed

---

## ▶️ Step 8 — Run the System

```bash
python hidden_human_detector.py
```

The fullscreen security window will open. The web dashboard also runs quietly in the background at:
```
http://localhost:5000         ← your PC
http://<YOUR-PC-IP>:5000     ← your phone (same WiFi)
```

To find your PC IP:
```bash
# Windows
ipconfig

# Mac/Linux
ifconfig
```

---

## 🖐️ Gesture Controls

Hold your hand up in front of the camera:

| Gesture | Action |
|---------|--------|
| ✌️ **All 4 fingers up** | `HELP` — Enable audio alerts |
| ✊ **All 4 fingers down (fist)** | `STOP` — Mute audio alerts |
| 👌 **OK sign** (thumb + index circle) | `OK` — Clear hidden person & reset |

Press **`Q`** on keyboard to quit.

---

## ⚙️ How It Works — Full Explanation

### 1. Person Detection (YOLOv8)
Every frame is passed through YOLOv8 nano (`yolov8n.pt`), which detects all objects. We filter for **class 0** (person only). The model auto-downloads on first run.

### 2. Hidden Detection Logic
- If a person **was detected** in the last frame but **is not detected now** → `hidden_mode = True`
- The system keeps the **last known bounding box** and marks it with a warning color
- `hidden_duration` counter increases every frame until the person reappears

### 3. Threat Level Calculation
Threat is scored 0–100% based on:
- **Time hidden** — longer = higher threat (up to 40 points)
- **Movement speed** — fast movement before hiding = higher threat (up to 30 points)
- **Position** — was the person in the center restricted zone? (30 points)

| Threat % | Level | Color |
|----------|-------|-------|
| 0–39% | LOW THREAT | 🟢 Green |
| 40–69% | MED THREAT | 🟠 Orange |
| 70–100% | HIGH THREAT | 🔴 Red |

### 4. Alarm System
- Alarm starts **immediately** when hidden mode begins (if alerts enabled)
- Alarm **loops continuously** using `pygame.mixer.music.play(-1)`
- Alarm **stops immediately** when person reappears or gesture is used

### 5. Incident Logging
When threat reaches **70%+**, the system:
- Saves a **JPEG snapshot** to `incidents/`
- Writes a row to `incidents/incident_log.csv`
- Has a 90-frame cooldown to avoid spam

### 6. Hand Gesture Detection (MediaPipe)
Uses MediaPipe's Hand Landmarker to detect 21 hand keypoints. Gesture logic checks finger positions relative to knuckles to classify OK / STOP / HELP.

### 7. Web Dashboard (Flask)
A Flask server runs on port 5000, serving:
- `/` — HTML dashboard with live stats
- `/frame` — Latest JPEG frame (refreshes every second)

---

## 🐛 Common Errors & Fixes

| Error | Fix |
|-------|-----|
| `hand_landmarker.task not found` | Download file — see Step 5 |
| `alert.mp3 not found` | Add an mp3 file — see Step 6 |
| `Camera not opening` | Change `VideoCapture(0)` index to 1 or 2 |
| `ModuleNotFoundError` | Run `pip install ultralytics opencv-python mediapipe pygame flask` |
| Black screen / no feed | Check your camera URL or index |
| Alarm not playing | Check `alert.mp3` exists and pygame is installed |

---

## 📦 Requirements Summary (Copy-Paste)

```bash
pip install ultralytics opencv-python mediapipe pygame flask numpy
```

Python version: **3.11.x**
Download: [https://www.python.org/downloads/release/python-3119/](https://www.python.org/downloads/release/python-3119/)

---

## 📄 License

MIT License — free to use, modify, and share with credit.

---

## 🙌 Credits & Tools Used

- [Ultralytics YOLOv8](https://github.com/ultralytics/ultralytics)
- [MediaPipe by Google](https://ai.google.dev/edge/mediapipe/solutions/vision/hand_landmarker)
- [OpenCV](https://opencv.org/)
- [DroidCam by Dev47Apps](https://www.dev47apps.com/)
- [OBS Studio](https://obsproject.com/)
- [Flask](https://flask.palletsprojects.com/)

---

> 📌 Made for learning purposes. Part of an open-source AI computer vision learning repo.
> Follow along and build your own version!
