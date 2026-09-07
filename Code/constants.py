import os
import json
import pygame

CELL = 30
COLS = 10
ROWS = 20
SIDEBAR = 220
WIDTH = COLS * CELL + SIDEBAR
HEIGHT = ROWS * CELL
FPS = 60

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GRAY = (40, 40, 40)
DARK_GRAY = (18, 18, 28)
DARKER_GRAY = (12, 12, 20)
BORDER_COLOR = (80, 80, 80)
HIGHLIGHT = (100, 180, 255)
DIM = (100, 100, 100)

BG_TOP = (8, 8, 18)
BG_BOTTOM = (14, 13, 26)

COLORS = {
    'I': (0, 200, 220),
    'O': (210, 190, 40),
    'T': (140, 50, 200),
    'S': (50, 190, 50),
    'Z': (210, 50, 50),
    'J': (50, 80, 210),
    'L': (210, 140, 30),
}

SHAPES = {
    'I': [[(0,1),(1,1),(2,1),(3,1)],
          [(2,0),(2,1),(2,2),(2,3)],
          [(0,2),(1,2),(2,2),(3,2)],
          [(1,0),(1,1),(1,2),(1,3)]],
    'O': [[(1,0),(2,0),(1,1),(2,1)],
          [(1,0),(2,0),(1,1),(2,1)],
          [(1,0),(2,0),(1,1),(2,1)],
          [(1,0),(2,0),(1,1),(2,1)]],
    'T': [[(1,0),(0,1),(1,1),(2,1)],
          [(1,0),(1,1),(2,1),(1,2)],
          [(0,1),(1,1),(2,1),(1,2)],
          [(1,0),(0,1),(1,1),(1,2)]],
    'S': [[(1,0),(2,0),(0,1),(1,1)],
          [(1,0),(1,1),(2,1),(2,2)],
          [(1,1),(2,1),(0,2),(1,2)],
          [(0,0),(0,1),(1,1),(1,2)]],
    'Z': [[(0,0),(1,0),(1,1),(2,1)],
          [(2,0),(1,1),(2,1),(1,2)],
          [(0,1),(1,1),(1,2),(2,2)],
          [(1,0),(0,1),(1,1),(0,2)]],
    'J': [[(0,0),(0,1),(1,1),(2,1)],
          [(1,0),(2,0),(1,1),(1,2)],
          [(0,1),(1,1),(2,1),(2,2)],
          [(1,0),(1,1),(0,2),(1,2)]],
    'L': [[(2,0),(0,1),(1,1),(2,1)],
          [(1,0),(1,1),(1,2),(2,2)],
          [(0,1),(1,1),(2,1),(0,2)],
          [(0,0),(1,0),(1,1),(1,2)]],
}

LINES_PER_LEVEL = 10
SCORE_TABLE = {0: 0, 1: 100, 2: 300, 3: 500, 4: 800}

DIFFICULTY_NAMES = {
    "easy": "EASY",
    "medium": "MEDIUM",
    "hard": "HARD",
}

DIFFICULTY_SPEEDS = {
    "easy": [1400, 1250, 1100, 950, 800, 680, 560, 450, 360, 280, 220, 170, 130, 100, 80],
    "medium": [800, 720, 630, 550, 470, 380, 300, 220, 150, 100, 80, 60, 50, 40, 30],
    "hard": [350, 300, 260, 220, 190, 160, 135, 110, 90, 75, 60, 50, 40, 30, 25],
}

DIFFICULTY_ORDER = ["easy", "medium", "hard"]

LINE_GOALS = [10, 20, 40, 100]

SETTINGS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "settings.json")

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

SPEED_TIERS = {
    "slow": {"das_delay": 260, "das_repeat": 90, "soft_drop_ms": 83},
    "normal": {"das_delay": 170, "das_repeat": 50, "soft_drop_ms": 33},
    "fast": {"das_delay": 100, "das_repeat": 25, "soft_drop_ms": 17},
}

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
    "pause": "P",
    "restart": "R",
}

ACTION_LABELS = {
    "move_left": "Move Left",
    "move_right": "Move Right",
    "soft_drop": "Soft Drop",
    "hard_drop": "Hard Drop",
    "rotate_right": "Rotate Right",
    "rotate_left": "Rotate Left",
    "rotate_180": "Rotate 180",
    "pause": "Pause",
    "restart": "Restart",
}


def load_settings():
    try:
        with open(SETTINGS_FILE, "r") as f:
            data = json.load(f)
            binds = DEFAULT_KEYBINDS.copy()
            stored = data.get("keybinds", {})
            binds.update({k: v for k, v in stored.items() if k in DEFAULT_KEYBINDS})
            opts = DEFAULT_SETTINGS.copy()
            opts.update(data.get("options", {}))
            if "speed" in opts:
                tier = SPEED_TIERS.get(opts.pop("speed"))
                if tier:
                    for k, v in tier.items():
                        opts[k] = v
            return {"keybinds": binds, "options": opts}
    except (FileNotFoundError, json.JSONDecodeError):
        return {
            "keybinds": DEFAULT_KEYBINDS.copy(),
            "options": DEFAULT_SETTINGS.copy(),
        }


def save_settings(settings):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=4)


def key_name(k):
    name = pygame.key.name(k)
    if name is None:
        return "???"
    return name.upper()


def resolve_keybind(keybinds):
    lookup = {}
    for action, key_str in keybinds.items():
        key_const = pygame.key.key_code(key_str) if key_str else None
        if key_const is not None:
            lookup[key_const] = action
    return lookup
