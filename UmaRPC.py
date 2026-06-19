import json
import threading
import time
import psutil
import keyboard
import customtkinter as ctk
import pystray

from screen_detector import (
    grab_screen,
    detect_state_from_screen,
    detect_scenario_from_screen,
    detect_uma_text_from_screen,
)
from pathlib import Path
from PIL import Image
from rapidfuzz import fuzz
from pypresence import Presence

# =========================
# CONFIG
# =========================

DISCORD_CLIENT_ID = "1503392534611886261"

# Watcher ini cuma buat cek game jalan/tidak.
# Screen detector nanti bisa punya interval sendiri, misalnya 2 detik.
CHECK_INTERVAL = 5
DETECTOR_INTERVAL = 0.5
OCR_INTERVAL = 5
PROCESS_NAMES = ["umamusume.exe", "UmamusumePrettyDerby.exe"]

BASE_DIR = Path(__file__).resolve().parent
UMA_LIST_PATH = BASE_DIR / "uma_list.json"
SCENARIO_PATH = BASE_DIR / "Uma_Scenario.json"
ICON_PATH = BASE_DIR / "icon.png"

# =========================
# LOAD JSON
# =========================

def load_json(path: Path, fallback):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[WARN] Failed to load {path.name}: {e}")
        return fallback


UMA_DATA = load_json(UMA_LIST_PATH, [])
SCENARIO_DATA = load_json(SCENARIO_PATH, [])

UMA_NAMES = [u["name"] for u in UMA_DATA if "name" in u]
SCENARIO_NAMES = [s["name"] for s in SCENARIO_DATA if "name" in s]

# =========================
# DISCORD RPC
# =========================

RPC = None
rpc_connected = False
rpc_running = False

start_timestamp = None
last_rpc_payload = None
last_detected_state = None
last_ocr_time = 0
cached_uma = None
cached_uma_text = ""

# =========================
# TKINTER SETUP
# =========================

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

root = ctk.CTk()
root.title("Uma RPC")
root.geometry("420x230")
root.attributes("-topmost", True)
root.resizable(False, False)

# hidden at start
root.withdraw()

# =========================
# SMALL HELPERS
# =========================

def set_status(text: str):
    """Thread-safe status label update."""
    try:
        root.after(0, lambda: status_label.configure(text=text))
    except Exception:
        print(text)


def normalize_process_name(name: str) -> str:
    return (name or "").lower().strip()


def normalize_text(text: str) -> str:
    return (text or "").lower().strip()


# =========================
# DISCORD HELPERS
# =========================

def ensure_rpc_connected() -> bool:
    """Connect Discord RPC only when needed, so app does not crash if Discord is closed."""
    global RPC
    global rpc_connected

    if rpc_connected:
        return True

    try:
        RPC = Presence(DISCORD_CLIENT_ID)
        RPC.connect()
        rpc_connected = True
        return True
    except Exception as e:
        rpc_connected = False
        set_status(f"Discord RPC not connected: {e}")
        return False


def rpc_update_once(payload: dict) -> bool:
    global last_rpc_payload
    global start_timestamp

    if not ensure_rpc_connected():
        return False

    if start_timestamp is None:
        start_timestamp = int(time.time())

    final_payload = {
        "details": payload["details"],
        "state": payload["state"],
        "large_image": payload.get("large_image") or "uma",
        "large_text": payload.get("large_text") or "Uma Musume | JPN",
        "small_image": payload.get("small_image") or "small_icon",
        "small_text": payload.get("small_text") or "Script by Teguh Marcelio and ChatGPT",
    }

    if final_payload == last_rpc_payload:
        return True

    RPC.update(
        details=final_payload["details"],
        state=final_payload["state"],
        large_image=final_payload["large_image"],
        large_text=final_payload["large_text"],
        small_image=final_payload["small_image"],
        small_text=final_payload["small_text"],
        start=start_timestamp,
    )

    last_rpc_payload = final_payload
    return True

def update_training_rpc(uma_name: str, scenario_name: str):
    """
    Main entry point for training RPC.
    Manual UI and future screen detector should both call this.
    """
    global rpc_running

    payload = {
        "details": f"Training {uma_name}",
        "state": f"Scenario: {scenario_name}",
        "large_image": "uma",
        "large_text": "Uma Musume",
    }

    try:
        rpc_update_once(payload)
        rpc_running = True
        set_status(f"RPC Running: {uma_name} | {scenario_name}")
    except Exception as e:
        set_status(f"RPC Error: {e}")


def set_lobby_rpc():
    global start_timestamp

    payload = {
        "details": "In Lobby",
        "state": "Idle",
        "large_image": "uma",
        "large_text": "Uma Musume",
    }

    if payload != last_rpc_payload:
        start_timestamp = int(time.time())

    try:
        if rpc_update_once(payload):
            set_status("RPC Running: Lobby")
    except Exception as e:
        set_status(f"RPC Error: {e}")

def clear_rpc():
    global rpc_connected
    global rpc_running
    global start_timestamp
    global last_rpc_payload

    try:
        if RPC and rpc_connected:
            RPC.clear()
    except Exception:
        pass

    rpc_running = False
    start_timestamp = None
    last_rpc_payload = None


# =========================
# GAME PROCESS
# =========================

def is_uma_running() -> bool:
    targets = {normalize_process_name(name) for name in PROCESS_NAMES}

    for process in psutil.process_iter(["name"]):
        try:
            proc_name = normalize_process_name(process.info.get("name"))
            if proc_name in targets:
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
        except Exception:
            continue

    return False


# =========================
# SEARCH / MATCHING
# =========================

def smart_search(query: str, choices: list[str], min_score: int = 60):
    query_norm = normalize_text(query)

    if not query_norm or not choices:
        return None

    best_score = 0
    best_match = None

    for choice in choices:
        choice_norm = normalize_text(choice)

        score = fuzz.partial_ratio(query_norm, choice_norm)

        for word in query_norm.split():
            if word in choice_norm:
                score += 10

        if score > best_score:
            best_score = score
            best_match = choice

    if best_score < min_score:
        return None

    return best_match


def compact_text(text: str) -> str:
    text = normalize_text(text)
    return "".join(ch for ch in text if ch.isalnum())


def find_uma(query: str):
    query_norm = normalize_text(query)
    query_compact = compact_text(query)

    if not query_norm:
        return None

    best_score = 0
    best_uma = None

    for uma in UMA_DATA:
        name = uma.get("name", "")
        name_norm = normalize_text(name)
        name_compact = compact_text(name)

        score = fuzz.partial_ratio(query_norm, name_norm)

        # Bonus normal word match
        for word in query_norm.split():
            if word in name_norm:
                score += 10

        # Bonus kalau OCR ilang spasi: SakuraChiyonoO vs Sakura Chiyono O
        compact_score = fuzz.partial_ratio(query_compact, name_compact)

        # Kalau compact match lebih bagus, pakai itu
        score = max(score, compact_score)

        # Extra bonus kalau salah satu compact string contain yang lain
        if query_compact and name_compact:
            if query_compact in name_compact or name_compact in query_compact:
                score += 25

        if score > best_score:
            best_score = score
            best_uma = uma

    if best_score < 60:
        return None

    return best_uma

def find_scenario(query: str):
    match = smart_search(query, SCENARIO_NAMES, min_score=60)

    if not match:
        return None

    for scenario in SCENARIO_DATA:
        if scenario.get("name") == match:
            return scenario

    return None


# =========================
# MAIN ACTIONS
# =========================

def start_rpc():
    scenario_input = scenario_entry.get().strip()
    uma_text = detect_uma_text_from_screen(grab_screen())


    scenario = find_scenario(scenario_input)
    uma = find_uma(uma_text)

    if not scenario:
        set_status("Scenario not found")
        return

    if not uma:
        set_status("Uma not found")
        return

    update_training_rpc(
        uma_name=uma["name"],
        scenario_name=scenario["name"],
    )


def stop_rpc():
    if is_uma_running():
        set_lobby_rpc()
    else:
        clear_rpc()
        set_status("RPC Cleared")


def watcher_loop():
    was_running = False

    while True:
        running = is_uma_running()

        if running and not was_running:
            set_lobby_rpc()
            # root.after(0, root.deiconify)  # disabled: keep UI hidden
        elif not running and was_running:
            clear_rpc()
            set_status("Waiting for Umamusume...")
            root.after(0, root.withdraw)

        was_running = running
        time.sleep(CHECK_INTERVAL)


def tray_open():
    root.after(0, root.deiconify)


def tray_exit(icon=None, item=None):
    clear_rpc()

    try:
        tray_icon.stop()
    except Exception:
        pass

    root.destroy()


# =========================
# FUTURE SCREEN DETECTOR HOOK
# =========================

def detector_loop():
    global last_detected_state
    global last_ocr_time
    global cached_uma
    global cached_uma_text

    while True:
        if not is_uma_running():
            time.sleep(DETECTOR_INTERVAL)
            continue

        try:
            screen = grab_screen()
            state, score, scores = detect_state_from_screen(screen)

            if state == "lobby":
                if last_detected_state != "lobby":
                    set_lobby_rpc()
                    last_detected_state = "lobby"
                    set_status(f"Detected: Lobby ({score:.2f})")

            elif state == "training":
                # Scenario auto dari template detector
                scenario, scenario_score, scenario_scores = detect_scenario_from_screen(
                    screen,
                    SCENARIO_DATA
                )

                # Uma auto dari OCR, tapi OCR cuma jalan tiap OCR_INTERVAL
                now = time.time()

                if now - last_ocr_time >= OCR_INTERVAL or cached_uma is None:
                    uma_text = detect_uma_text_from_screen(screen)
                    uma = find_uma(uma_text)

                    if uma:
                        cached_uma = uma
                        cached_uma_text = uma_text

                    last_ocr_time = now
                    # print("UMA OCR:", uma_text)

                else:
                    uma = cached_uma
                    uma_text = cached_uma_text

                if scenario and uma:
                    update_training_rpc(
                        uma_name=uma["name"],
                        scenario_name=scenario["name"],
                    )

                    last_detected_state = "training"

                    set_status(
                        f"Detected: Training ({score:.2f}) | "
                        f"OCR: {uma_text} | "
                        f"{uma['name']} | "
                        f"{scenario['name']} ({scenario_score:.2f})"
                    )

                elif not scenario:
                    last_detected_state = "training"

                    set_status(
                        f"Training detected, but scenario not found "
                        f"(best: {scenario_score:.2f})"
                    )

                    print("Scenario scores:", scenario_scores)

                elif not uma:
                    last_detected_state = "training"

                    set_status(
                        f"Training detected, but Uma OCR invalid: {uma_text}"
                    )

            else:
                if last_detected_state != "unknown":
                    last_detected_state = "unknown"
                    set_status(f"Detected: Unknown ({score:.2f})")

        except Exception as e:
            set_status(f"Detector error: {e}")

        time.sleep(DETECTOR_INTERVAL)

# =========================
# UI
# =========================

frame = ctk.CTkFrame(root)
frame.pack(fill="both", expand=True, padx=10, pady=10)

scenario_label = ctk.CTkLabel(frame, text="Scenario")
scenario_label.pack(pady=(10, 0))

scenario_entry = ctk.CTkEntry(frame, width=320)
scenario_entry.pack(pady=5)

uma_label = ctk.CTkLabel(frame, text="Uma")
uma_label.pack(pady=(10, 0))

uma_entry = ctk.CTkEntry(frame, width=320)
uma_entry.pack(pady=5)

button_frame = ctk.CTkFrame(frame, fg_color="transparent")
button_frame.pack(pady=10)

start_button = ctk.CTkButton(
    button_frame,
    text="Start RPC",
    command=start_rpc,
)
start_button.pack(side="left", padx=5)

stop_button = ctk.CTkButton(
    button_frame,
    text="Stop RPC",
    command=stop_rpc,
)
stop_button.pack(side="left", padx=5)

status_label = ctk.CTkLabel(
    frame,
    text="Waiting for Umamusume...",
)
status_label.pack(pady=10)

# =========================
# HOTKEY
# =========================

try:
    keyboard.add_hotkey("ctrl+shift+end", stop_rpc)
except Exception as e:
    print(f"[WARN] Failed to register hotkey: {e}")

# =========================
# SYSTEM TRAY
# =========================

try:
    image = Image.open(ICON_PATH)
except Exception:
    image = Image.new("RGB", (64, 64), color=(40, 40, 40))

tray_menu = pystray.Menu(
    pystray.MenuItem("Open", lambda icon, item: tray_open()),
    pystray.MenuItem("Stop RPC", lambda icon, item: stop_rpc()),
    pystray.MenuItem("Exit", tray_exit),
)

tray_icon = pystray.Icon(
    "UmaRPC",
    image,
    "Uma RPC",
    tray_menu,
)

tray_thread = threading.Thread(
    target=tray_icon.run,
    daemon=True,
)
tray_thread.start()

# =========================
# WATCHER THREAD
# =========================

watcher_thread = threading.Thread(
    target=watcher_loop,
    daemon=True,
)
watcher_thread.start()
detector_thread = threading.Thread(
    target=detector_loop,
    daemon=True
)
detector_thread.start()
# =========================
# START APP
# =========================

root.mainloop()
