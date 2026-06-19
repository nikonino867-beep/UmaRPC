import time
from pathlib import Path
from rapidocr_onnxruntime import RapidOCR
import cv2
import mss
import numpy as np



# =========================
# PATH SETUP
# =========================

BASE_DIR = Path(__file__).resolve().parent

STATE_TEMPLATE_DIR = BASE_DIR / "templates" / "state"
SCENARIO_TEMPLATE_DIR = BASE_DIR / "templates" / "scenario"


# =========================
# CONFIG
# =========================

STATE_THRESHOLD = 0.82
SCENARIO_THRESHOLD = 0.78

STATE_TEMPLATES = {
    "lobby": STATE_TEMPLATE_DIR / "lobby.png",
    "training": STATE_TEMPLATE_DIR / "training.png",
}

LOADED_STATE_TEMPLATES = None
LOADED_SCENARIO_TEMPLATES = None
SCENARIO_BY_NAME = {}

# Crop area nama Uma di training screen.
# Format: x1, y1, x2, y2
# Semua koordinat crop di bawah ini tetap ditulis berdasarkan referensi 1920x1080.
# Nanti akan otomatis di-map ke area game 16:9 aktual, misalnya 1920x1200 => offset Y +60.
REFERENCE_WIDTH = 1920
REFERENCE_HEIGHT = 1080
REFERENCE_ASPECT = REFERENCE_WIDTH / REFERENCE_HEIGHT

UMA_NAME_CROP = (1180, 190, 1650, 290)
STATE_SEARCH_CROP = (1620, 0, 1920, 1080)
SCENARIO_SEARCH_CROP = (1055, 90, 1155, 160)
OCR_ENGINE = RapidOCR()

# =========================
# DEBUG
# =========================

def print_template_debug():
    print("BASE_DIR:", BASE_DIR)
    print("STATE_TEMPLATE_DIR:", STATE_TEMPLATE_DIR)
    print("SCENARIO_TEMPLATE_DIR:", SCENARIO_TEMPLATE_DIR)

    print("\n[STATE TEMPLATES]")
    for name, path in STATE_TEMPLATES.items():
        print(name, "=>", path, "| exists:", path.exists())

    print("\n[SCENARIO TEMPLATE DIR]")
    print("exists:", SCENARIO_TEMPLATE_DIR.exists())


# =========================
# SCREENSHOT
# =========================

def grab_screen():
    """
    Capture primary monitor.
    Returns OpenCV BGR image.
    """
    with mss.mss() as sct:
        monitor = sct.monitors[1]
        shot = sct.grab(monitor)

        img = np.array(shot)
        img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

        return img


def get_game_viewport(screen):
    """
    Return posisi area game 16:9 di dalam screenshot.

    Semua koordinat detector ditulis berdasarkan 1920x1080.
    Fungsi ini membuat detector tetap pas di resolusi 16:10 / 4:3 / dll.

    returns:
    offset_x, offset_y, game_width, game_height, scale
    """
    screen_h, screen_w = screen.shape[:2]

    scale = min(
        screen_w / REFERENCE_WIDTH,
        screen_h / REFERENCE_HEIGHT,
    )

    game_w = int(round(REFERENCE_WIDTH * scale))
    game_h = int(round(REFERENCE_HEIGHT * scale))

    offset_x = max(0, (screen_w - game_w) // 2)
    offset_y = max(0, (screen_h - game_h) // 2)

    return offset_x, offset_y, game_w, game_h, scale


def map_reference_box(screen, box):
    """
    Convert crop box dari koordinat referensi 1920x1080 ke koordinat screenshot aktual.
    """
    x1, y1, x2, y2 = box
    ox, oy, game_w, game_h, scale = get_game_viewport(screen)
    screen_h, screen_w = screen.shape[:2]

    mapped = (
        int(round(ox + x1 * scale)),
        int(round(oy + y1 * scale)),
        int(round(ox + x2 * scale)),
        int(round(oy + y2 * scale)),
    )

    mx1, my1, mx2, my2 = mapped

    # Clamp biar nggak out of bounds kalau resolusi aneh.
    mx1 = max(0, min(mx1, screen_w))
    mx2 = max(0, min(mx2, screen_w))
    my1 = max(0, min(my1, screen_h))
    my2 = max(0, min(my2, screen_h))

    return mx1, my1, mx2, my2


def crop_reference_box(screen, box):
    return crop_image(screen, map_reference_box(screen, box))


def crop_game_viewport(screen):
    ox, oy, game_w, game_h, scale = get_game_viewport(screen)
    return screen[oy:oy + game_h, ox:ox + game_w]

# =========================
# OCR DETECTOR
# =========================

def crop_templates_area(screen, crop_box):
    return crop_reference_box(screen, crop_box)

def crop_image(screen, box):
    x1, y1, x2, y2 = box
    return screen[y1:y2, x1:x2]

def crop_right_sidebar(screen, width=260, y1=0, y2=760):
    h, w = screen.shape[:2]
    return screen[y1:min(y2, h), max(0, w - width):w]

def ocr_image(image) -> str:
    """
    OCR image using RapidOCR.
    Returns joined text.
    """
    result, _ = OCR_ENGINE(image)

    if not result:
        return ""

    texts = []

    for line in result:
        # RapidOCR format biasanya:
        # [box, text, confidence]
        if len(line) >= 2:
            texts.append(str(line[1]))

    return " ".join(texts).strip()


def detect_uma_text():
    """
    Crop Uma name area from current screen, then OCR it.

    returns:
    text
    """
    screen = grab_screen()
    crop = crop_reference_box(screen, UMA_NAME_CROP)

    text = ocr_image(crop)
    return text


def save_uma_crop_debug(filename="debug_uma_crop.png"):
    """
    Save crop image so we can check if coordinates are correct.
    """
    screen = grab_screen()
    crop = crop_reference_box(screen, UMA_NAME_CROP)

    output_path = BASE_DIR / filename
    cv2.imwrite(str(output_path), crop)

    return output_path

def save_state_crop_debug(filename="debug_state_crop.png"):
    screen = grab_screen()
    crop = crop_reference_box(screen, STATE_SEARCH_CROP)

    output_path = BASE_DIR / filename
    cv2.imwrite(str(output_path), crop)

    return output_path


def save_scenario_crop_debug(filename="debug_scenario_crop.png"):
    """
    Save the scenario search crop area.
    """
    screen = grab_screen()
    crop = crop_reference_box(screen, SCENARIO_SEARCH_CROP)

    output_path = BASE_DIR / filename
    cv2.imwrite(str(output_path), crop)

    return output_path


def save_detection_overlay_debug(filename="debug_detection_overlay.png"):
    """
    Save a full screenshot with rectangles showing:
    - UMA OCR crop
    - Scenario crop
    - State crop
    """
    screen = grab_screen().copy()
    h, w = screen.shape[:2]

    # ===== UMA crop (red) =====
    ux1, uy1, ux2, uy2 = map_reference_box(screen, UMA_NAME_CROP)
    cv2.rectangle(screen, (ux1, uy1), (ux2, uy2), (0, 0, 255), 3)
    cv2.putText(
        screen,
        "UMA_NAME_CROP",
        (ux1, max(30, uy1 - 10)),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (0, 0, 255),
        2,
        cv2.LINE_AA,
    )

    # ===== Scenario crop (green) =====
    sx1, sy1, sx2, sy2 = map_reference_box(screen, SCENARIO_SEARCH_CROP)
    cv2.rectangle(screen, (sx1, sy1), (sx2, sy2), (0, 255, 0), 3)
    cv2.putText(
        screen,
        "SCENARIO_SEARCH_CROP",
        (sx1, max(30, sy1 - 10)),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (0, 255, 0),
        2,
        cv2.LINE_AA,
    )

    # ===== State crop (blue) =====
    stx1, sty1, stx2, sty2 = map_reference_box(screen, STATE_SEARCH_CROP)

    cv2.rectangle(screen, (stx1, sty1), (stx2, sty2), (255, 0, 0), 3)
    cv2.putText(
        screen,
        "STATE_SEARCH_CROP",
        (stx1, max(30, sty1 + 30)),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (255, 0, 0),
        2,
        cv2.LINE_AA,
    )

    output_path = BASE_DIR / filename
    cv2.imwrite(str(output_path), screen)

    return output_path
# =========================
# TEMPLATE MATCHING
# =========================

def load_template(template_path: Path):
    if not template_path.exists():
        return None

    template = cv2.imread(str(template_path))

    if template is None:
        return None

    return template

def preload_templates(path_templates: dict) -> dict:
    loaded = {}

    for name, path in path_templates.items():
        template = load_template(path)
        if template is not None:
            loaded[name] = template

    return loaded

def match_template(screen, template_path: Path) -> float:
    """
    Returns confidence score 0.0 - 1.0-ish.
    """
    template = load_template(template_path)

    if template is None:
        return 0.0

    screen_h, screen_w = screen.shape[:2]
    template_h, template_w = template.shape[:2]

    # Template can't be bigger than screen.
    if template_h > screen_h or template_w > screen_w:
        return 0.0

    result = cv2.matchTemplate(
        screen,
        template,
        cv2.TM_CCOEFF_NORMED,
    )

    _, max_val, _, _ = cv2.minMaxLoc(result)
    return float(max_val)

def resize_template_for_screen(screen, template):
    """Resize template 1920x1080 reference ke scale game aktual."""
    if template is None:
        return None

    _, _, _, _, scale = get_game_viewport(screen)

    if abs(scale - 1.0) < 0.01:
        return template

    template_h, template_w = template.shape[:2]
    new_w = max(1, int(round(template_w * scale)))
    new_h = max(1, int(round(template_h * scale)))

    return cv2.resize(template, (new_w, new_h), interpolation=cv2.INTER_AREA)


def match_loaded_template(screen, template) -> float:
    if template is None:
        return 0.0

    # Match cuma di area game 16:9, bukan full monitor yang mungkin ada letterbox.
    game_screen = crop_game_viewport(screen)
    template = resize_template_for_screen(screen, template)

    screen_h, screen_w = game_screen.shape[:2]
    template_h, template_w = template.shape[:2]

    if template_h > screen_h or template_w > screen_w:
        return 0.0

    result = cv2.matchTemplate(
        game_screen,
        template,
        cv2.TM_CCOEFF_NORMED,
    )

    _, max_val, _, _ = cv2.minMaxLoc(result)
    return float(max_val)

def best_loaded_template_match(screen, loaded_templates: dict, threshold: float):
    scores = {}

    for name, template in loaded_templates.items():
        scores[name] = match_loaded_template(screen, template)

    if not scores:
        return "unknown", 0.0, {}

    best_name = max(scores, key=scores.get)
    best_score = scores[best_name]

    if best_score >= threshold:
        return best_name, best_score, scores

    return "unknown", best_score, scores

def best_template_match(screen, templates: dict, threshold: float):
    """
    Generic matcher.

    templates format:
    {
        "name": Path("template.png")
    }

    returns:
    name, score, all_scores
    """
    scores = {}

    for name, template_path in templates.items():
        scores[name] = match_template(screen, template_path)

    if not scores:
        return "unknown", 0.0, {}

    best_name = max(scores, key=scores.get)
    best_score = scores[best_name]

    if best_score >= threshold:
        return best_name, best_score, scores

    return "unknown", best_score, scores


# =========================
# STATE DETECTOR
# =========================

def detect_state():
    """
    Detect current screen state.

    returns:
    state, score, scores

    example:
    "training", 0.94, {"lobby": 0.31, "training": 0.94}
    """
    screen = grab_screen()

    return best_template_match(
        screen=screen,
        templates=STATE_TEMPLATES,
        threshold=STATE_THRESHOLD,
    )


# =========================
# SCENARIO DETECTOR
# =========================

def build_scenario_templates(scenario_data: list[dict]) -> dict:
    """
    Build scenario template map from Uma_Scenario.json.

    Expected scenario format:
    {
        "id": "beyond_dreams",
        "name": "Beyond Dreams",
        "template": "beyond_dreams.png"
    }

    Fallback:
    if "template" missing, use "{id}.png"
    """
    templates = {}

    for scenario in scenario_data:
        scenario_id = scenario.get("id")
        scenario_name = scenario.get("name")

        if not scenario_id or not scenario_name:
            continue

        template_file = scenario.get("template")

        if not template_file:
            template_file = f"{scenario_id}.png"

        template_path = SCENARIO_TEMPLATE_DIR / template_file

        templates[scenario_name] = template_path

    return templates

def preload_scenario_templates(scenario_data: list[dict]):
    templates = build_scenario_templates(scenario_data)
    loaded = preload_templates(templates)

    by_name = {
        scenario.get("name"): scenario
        for scenario in scenario_data
        if scenario.get("name")
    }

    return loaded, by_name

def detect_scenario(scenario_data: list[dict]):
    """
    Detect scenario using template matching.

    returns:
    scenario_object, score, scores

    If not found:
    None, score, scores
    """
    screen = grab_screen()
    templates = build_scenario_templates(scenario_data)

    scenario_name, score, scores = best_template_match(
        screen=screen,
        templates=templates,
        threshold=SCENARIO_THRESHOLD,
    )

    if scenario_name == "unknown":
        return None, score, scores

    for scenario in scenario_data:
        if scenario.get("name") == scenario_name:
            return scenario, score, scores

    return None, score, scores

# =========================
# ONE-SCREEN DETECTOR HELPERS
# =========================

def detect_state_from_screen(screen):
    global LOADED_STATE_TEMPLATES

    if LOADED_STATE_TEMPLATES is None:
        LOADED_STATE_TEMPLATES = preload_templates(STATE_TEMPLATES)

    return best_loaded_template_match(
        screen=screen,
        loaded_templates=LOADED_STATE_TEMPLATES,
        threshold=STATE_THRESHOLD,
    )

def detect_uma_text_from_screen(screen):
    crop = crop_reference_box(screen, UMA_NAME_CROP)
    return ocr_image(crop)


def detect_scenario_from_screen(screen, scenario_data: list[dict]):
    global LOADED_SCENARIO_TEMPLATES
    global SCENARIO_BY_NAME

    if LOADED_SCENARIO_TEMPLATES is None:
        LOADED_SCENARIO_TEMPLATES, SCENARIO_BY_NAME = preload_scenario_templates(
            scenario_data
        )

    scenario_name, score, scores = best_loaded_template_match(
        screen=screen,
        loaded_templates=LOADED_SCENARIO_TEMPLATES,
        threshold=SCENARIO_THRESHOLD,
    )

    if scenario_name == "unknown":
        return None, score, scores

    return SCENARIO_BY_NAME.get(scenario_name), score, scores

# =========================
# TEST MODE
# =========================

if __name__ == "__main__":
    import json

    print_template_debug()

    scenario_path = BASE_DIR / "Uma_Scenario.json"

    with open(scenario_path, "r", encoding="utf-8") as f:
        scenario_data = json.load(f)

    print("\n[SCENARIO TEMPLATES]")
    scenario_templates = build_scenario_templates(scenario_data)
    for name, path in scenario_templates.items():
        print(name, "=>", path, "| exists:", path.exists())

    print("\nRunning detector test...")
    print("Press Ctrl+C to stop.\n")

    overlay_path = save_detection_overlay_debug()
    state_crop_path = save_state_crop_debug()
    scenario_crop_path = save_scenario_crop_debug()
    uma_crop_path = save_uma_crop_debug()

    print("Saved overlay debug:", overlay_path)
    print("Saved state crop:", state_crop_path)
    print("Saved scenario crop:", scenario_crop_path)
    print("Saved uma crop:", uma_crop_path)

    last_ocr_time = 0
    cached_uma_text = ""

    last_scenario_time = 0
    cached_scenario = None
    cached_scenario_score = 0.0

    OCR_TEST_INTERVAL = 7
    SCENARIO_TEST_INTERVAL = 20

    while True:
        loop_start = time.time()

        screen = grab_screen()

        state, state_score, state_scores = detect_state_from_screen(screen)

        now = time.time()

        if (
            cached_scenario is None
            or now - last_scenario_time >= SCENARIO_TEST_INTERVAL
        ):
            cached_scenario, cached_scenario_score, scenario_scores = detect_scenario_from_screen(
                screen,
                scenario_data,
            )
            last_scenario_time = now
        else:
            scenario_scores = {}

        if now - last_ocr_time >= OCR_TEST_INTERVAL:
            cached_uma_text = detect_uma_text_from_screen(screen)
            last_ocr_time = now

        scenario_name = cached_scenario["name"] if cached_scenario else "unknown"

        print(
            f"STATE: {state} ({state_score:.3f}) | "
            f"SCENARIO: {scenario_name} ({cached_scenario_score:.3f}) | "
            f"UMA OCR: {cached_uma_text} | "
            f"loop: {time.time() - loop_start:.2f}s"
        )

        time.sleep(1)