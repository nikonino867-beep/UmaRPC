# UmaRPC 

Discord Rich Presence for Uma Musume

##  Overview

UmaRPC is a Python tool that adds **Discord Rich Presence** support for *Uma Musume Pretty Derby (PC)*.

It detects the current game state using screen analysis and updates your Discord status in real time.

What it shows:

* Current training character
* Active scenario
* Lobby / training state

---

## Features

* Real-time Discord Rich Presence updates
* Screen-based detection (no game file modification)
* Scenario recognition support
* Simple batch launcher included

---

## How It Works

UmaRPC uses image/template detection to recognize UI elements from the game screen, then maps them into readable Discord status updates.

---

## Requirements

* Python 3.10+
* Discord Desktop App (Rich Presence enabled)
* Windows OS
* Required Python packages:

  * 'psutil'
  * 'keyboard'
  * 'customtkinter'
  * 'pystray'
  * 'pillow'
  * 'rapidfuzz'
  * 'pypresence'
  * 'rapidocr-onnxruntime'
  * 'opencv-python'
  * 'windows-capture'
  * 'numpy'
## Setup

1. Clone or download this repository
2. Run:

   ```
   First time Setup.bat
   ```
3. Start the app:

   ```
   UmaRPC.py
   ```
   or create a windows shortcut from 
   ```
   Uma.bat
   ```
   to the windows startup folder

## Usage

* Open Uma Musume (fullscreen recommended)
* Run UmaRPC
* Keep both Discord and the script running
* Status will update automatically

---

## Limitations

* Must keep application running in background (No Minimize)
* Only Work in Landscape and fullscreen mode
* Detection accuracy depends on screen visibility
* It's still unstable at the moment, as it uses image matching.
* Need to open "composite" menu to update the RPC

---

## Project Structure

```
UMA RPC/
├── UmaRPC.py
├── screen_detector.py
├── uma_list.json
├── Uma_Scenario.json
├── templates/
├── First time Setup.bat
├── UmaRPC.bat
├── models/
└── assets/
```

---

## Notes

This project is a personal tool and may require adjustments depending on game updates

---

## License

Feel free to modify for your own setup.

---

## 💬 Credits

Built by Teguh and ChatGPT
Powered by Python + Discord Rich Presence API


The best *vibecoding* project ever—*for me*
