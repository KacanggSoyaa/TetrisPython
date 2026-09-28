# Every tunable number, colour, and lookup table the game uses.
#
# Nothing in this file has behaviour beyond the four settings helpers at the
# bottom. Keeping the data here means the rules engine, the renderer, and the
# tests all read the same source of truth, and adjusting feel (gravity, scoring,
# lock delay) never means hunting through logic.
import os
import json
import pygame

# --------------------------------------------------------------- geometry

# Board size and window layout. The window is derived from the well so the
# playfield and the sidebar always stay in proportion.
CELL = 30
COLS = 10
ROWS = 20
WELL_W = COLS * CELL
WELL_H = ROWS * CELL

WELL_PAD = 8
SIDEBAR = 234
SIDE_GAP = 16

WIDTH = WELL_PAD * 2 + WELL_W + SIDE_GAP + SIDEBAR
HEIGHT = WELL_PAD * 2 + WELL_H

WELL_X = WELL_PAD
WELL_Y = WELL_PAD
SIDE_X = WELL_X + WELL_W + SIDE_GAP
SIDE_PAD = 12
SIDE_INNER_X = SIDE_X + SIDE_PAD
SIDE_INNER_W = SIDEBAR - SIDE_PAD * 2

FPS = 60
PREVIEW_COUNT = 3

# ----------------------------------------------------------------- theme

# One dark palette shared by the game view, the menus, and the overlays.
# Every colour the renderer draws comes from here.
THEME = {
    "bg_top": (9, 9, 19),
    "bg_bottom": (19, 17, 36),
    "side_top": (12, 12, 24),
    "side_bottom": (16, 15, 30),
    "panel": (23, 23, 39),
    "panel_hi": (30, 31, 49),
    "panel_soft": (19, 19, 33),
    "border": (45, 46, 70),
    "border_hi": (78, 84, 124),
    "accent": (0, 208, 222),
    "accent_dim": (0, 116, 128),
    "text": (233, 237, 248),
    "text_dim": (154, 160, 184),
    "text_faint": (98, 103, 130),
    "well": (13, 13, 24),
    "well_edge": (34, 36, 60),
    "grid": (24, 24, 40),
    "grid_hi": (33, 34, 54),
    "keycap": (40, 42, 62),
    "keycap_hi": (54, 57, 82),
    "ok": (88, 216, 142),
    "warn": (243, 190, 80),
    "bad": (240, 96, 100),
}

# Piece fill colours, keyed by tetromino letter.
COLORS = {
    "I": (56, 206, 226),
    "O": (245, 205, 60),
    "T": (170, 94, 240),
    "S": (88, 214, 118),
    "Z": (240, 88, 102),
    "J": (72, 126, 240),
    "L": (242, 152, 48),
}

# Tetromino geometry. Each letter holds four rotation states, and each state
# is the four filled offsets inside a 4x4 box, clockwise from spawn.
SHAPES = {
    "I": [[(0, 1), (1, 1), (2, 1), (3, 1)],
          [(2, 0), (2, 1), (2, 2), (2, 3)],
          [(0, 2), (1, 2), (2, 2), (3, 2)],
          [(1, 0), (1, 1), (1, 2), (1, 3)]],
    "O": [[(1, 0), (2, 0), (1, 1), (2, 1)],
          [(1, 0), (2, 0), (1, 1), (2, 1)],
          [(1, 0), (2, 0), (1, 1), (2, 1)],
          [(1, 0), (2, 0), (1, 1), (2, 1)]],
    "T": [[(1, 0), (0, 1), (1, 1), (2, 1)],
          [(1, 0), (1, 1), (2, 1), (1, 2)],
          [(0, 1), (1, 1), (2, 1), (1, 2)],
          [(1, 0), (0, 1), (1, 1), (1, 2)]],
    "S": [[(1, 0), (2, 0), (0, 1), (1, 1)],
          [(1, 0), (1, 1), (2, 1), (2, 2)],
          [(1, 1), (2, 1), (0, 2), (1, 2)],
          [(0, 0), (0, 1), (1, 1), (1, 2)]],
    "Z": [[(0, 0), (1, 0), (1, 1), (2, 1)],
          [(2, 0), (1, 1), (2, 1), (1, 2)],
          [(0, 1), (1, 1), (1, 2), (2, 2)],
          [(1, 0), (0, 1), (1, 1), (0, 2)]],
    "J": [[(0, 0), (0, 1), (1, 1), (2, 1)],
          [(1, 0), (2, 0), (1, 1), (1, 2)],
          [(0, 1), (1, 1), (2, 1), (2, 2)],
          [(1, 0), (1, 1), (0, 2), (1, 2)]],
    "L": [[(2, 0), (0, 1), (1, 1), (2, 1)],
          [(1, 0), (1, 1), (1, 2), (2, 2)],
          [(0, 1), (1, 1), (2, 1), (0, 2)],
          [(0, 0), (1, 0), (1, 1), (1, 2)]],
}

# ---------------------------------------------------------------- scoring

# Points are multiplied by the current level, which rises every 10 lines.
LINES_PER_LEVEL = 10
SCORE_TABLE = {1: 100, 2: 300, 3: 500, 4: 800}
CLEAR_LABELS = {1: "SINGLE", 2: "DOUBLE", 3: "TRIPLE", 4: "TETRIS!"}
TSPINS = {0: 400, 1: 800, 2: 1200, 3: 1600}
COMBO_STEP = 50
BACK_TO_BACK = 1.5
PERFECT_CLEAR = 1800
SOFT_DROP_POINTS = 1
HARD_DROP_POINTS = 2

# ----------------------------------------------------------------- timing

# Lock delay is how long a grounded piece waits for a last-second input.
# The two clear timings drive the flash-then-glow line-clear animation.
LOCK_DELAY = 500
CLEAR_FLASH_MS = 170
CLEAR_GLOW_MS = 150

# ------------------------------------------------------------- difficulty

# Display names, one-line blurbs, and per-level gravity in milliseconds.
# The speed list is indexed by level-1 and clamped to its last entry.
DIFFICULTY_NAMES = {
    "easy": "EASY",
    "medium": "MEDIUM",
    "hard": "HARD",
}

DIFFICULTY_HINTS = {
    "easy": "relaxed gravity, room to think",
    "medium": "classic pace, fair and steady",
    "hard": "fast gravity, no room to breathe",
}

DIFFICULTY_SPEEDS = {
    "easy": [900, 800, 700, 620, 550, 480, 420, 360, 310, 260, 220, 190, 165, 145, 125],
    "medium": [700, 600, 520, 450, 390, 340, 290, 250, 210, 180, 155, 135, 115, 100, 85],
    "hard": [420, 350, 295, 245, 200, 170, 145, 125, 105, 90, 75, 65, 55, 45, 38],
}

DIFFICULTY_ORDER = ["easy", "medium", "hard"]

# Win condition. 0 means endless, so the game only ends by topping out.
LINE_GOALS = [10, 20, 40, 0]
LINE_GOAL_LABELS = ["10 LINES", "20 LINES", "40 LINES", "ENDLESS"]

# The three slider settings, with their bounds, step, and fallback values.
# DAS = delayed auto-shift: the hold delay before auto-repeat kicks in.
SPEED_KEYS = ["das_delay", "das_repeat", "soft_drop_ms"]
SPEED_LABELS = {
    "das_delay": "Move Hold Delay",
    "das_repeat": "Move Repeat",
    "soft_drop_ms": "Soft Drop",
}
SPEED_UNITS = {
    "das_delay": "ms",
    "das_repeat": "ms",
    "soft_drop_ms": "ms/row",
}
SPEED_MIN = {
    "das_delay": 60,
    "das_repeat": 20,
    "soft_drop_ms": 10,
}
SPEED_MAX = {
    "das_delay": 400,
    "das_repeat": 150,
    "soft_drop_ms": 120,
}
SPEED_STEP = {
    "das_delay": 10,
    "das_repeat": 5,
    "soft_drop_ms": 5,
}
SPEED_DEFAULTS = {
    "das_delay": 170,
    "das_repeat": 50,
    "soft_drop_ms": 33,
}
# Named speed presets, kept only so older settings files still load.
SPEED_TIERS = {
    "slow": {"das_delay": 260, "das_repeat": 90, "soft_drop_ms": 83},
    "normal": {"das_delay": 170, "das_repeat": 50, "soft_drop_ms": 33},
    "fast": {"das_delay": 100, "das_repeat": 25, "soft_drop_ms": 17},
}

# --------------------------------------------------------------- settings

# Persisted to settings.json next to the Code folder, so custom binds and the
# best score survive between runs.
SETTINGS_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "settings.json")

DEFAULT_SETTINGS = {
    "difficulty": "medium",
    "line_goal": 20,
    "das_delay": 170,
    "das_repeat": 50,
    "soft_drop_ms": 33,
}

DEFAULT_KEYBINDS = {
    "move_left": "LEFT",
    "move_right": "RIGHT",
    "soft_drop": "DOWN",
    "hard_drop": "SPACE",
    "rotate_right": "UP",
    "rotate_left": "Z",
    "rotate_180": "X",
    "hold": "LEFT SHIFT",
    "pause": "P",
    "restart": "R",
}

# Every rebindable action and the label shown in the settings screen.
ACTION_LABELS = {
    "move_left": "Move Left",
    "move_right": "Move Right",
    "soft_drop": "Soft Drop",
    "hard_drop": "Hard Drop",
    "rotate_right": "Rotate CW",
    "rotate_left": "Rotate CCW",
    "rotate_180": "Rotate 180",
    "hold": "Hold Piece",
    "pause": "Pause",
    "restart": "Restart",
}

# Row labels for the main menu, the pause overlay, and the game-over overlay.
MENU_ITEMS = ["Play", "Difficulty", "Lines", "Speeds", "Settings", "Quit"]
PAUSE_ITEMS = ["Resume", "Settings", "Restart", "Quit"]
OVER_ITEMS = ["Restart", "Main Menu"]


# Read settings.json and return a clean, validated settings dict.
#
# Never raises: a missing, corrupt, or hand-edited file falls back to the
# defaults. Unknown keys are dropped, speed values are clamped to their
# allowed range, and the legacy "speed" tier is expanded into the three
# individual sliders. The result is always
# `{"keybinds": {...}, "options": {...}, "high": int}`.
def load_settings():
    data = {}
    try:
        with open(SETTINGS_FILE, "r") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        data = {}

    binds = DEFAULT_KEYBINDS.copy()
    stored = data.get("keybinds", {})
    if isinstance(stored, dict):
        binds.update({k: v for k, v in stored.items() if k in DEFAULT_KEYBINDS})

    opts = DEFAULT_SETTINGS.copy()
    stored_opts = data.get("options", {})
    if isinstance(stored_opts, dict):
        opts.update(stored_opts)
    if "speed" in opts:
        tier = SPEED_TIERS.get(opts.pop("speed"))
        if tier:
            for k, v in tier.items():
                opts[k] = v

    for key, lo in SPEED_MIN.items():
        try:
            opts[key] = max(lo, min(SPEED_MAX[key], int(opts.get(key, SPEED_DEFAULTS[key]))))
        except (TypeError, ValueError):
            opts[key] = SPEED_DEFAULTS[key]
    if opts.get("difficulty") not in DIFFICULTY_ORDER:
        opts["difficulty"] = "medium"
    if opts.get("line_goal") not in LINE_GOALS:
        opts["line_goal"] = 20

    high = data.get("high", 0)
    if not isinstance(high, int) or high < 0:
        high = 0

    return {"keybinds": binds, "options": opts, "high": high}


# Write the settings dict back to settings.json, pretty-printed.
def save_settings(settings):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=4)


# Pygame key constant to the uppercase name shown in the UI ("LEFT SHIFT").
def key_name(k):
    if k is None:
        return "---"
    name = pygame.key.name(k)
    if not name:
        return "???"
    return name.upper()


# Invert the action->name mapping into a key constant -> action lookup.
#
# The game loop does this every frame, so a key press is a single dict hit.
# Names that pygame cannot parse are skipped instead of crashing.
def resolve_keybind(keybinds):
    lookup = {}
    for action, key_str in keybinds.items():
        if not key_str:
            continue
        try:
            key_const = pygame.key.key_code(key_str)
        except ValueError:
            continue
        if key_const is not None:
            lookup[key_const] = action
    return lookup
