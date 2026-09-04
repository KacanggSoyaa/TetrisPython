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
SPEEDS = [800, 720, 630, 550, 470, 380, 300, 220, 150, 100, 80, 60, 50, 40, 30]

SETTINGS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "settings.json")

DEFAULT_KEYBINDS = {
    "move_left": "LEFT",
    "move_right": "RIGHT",
    "soft_drop": "DOWN",
    "hard_drop": "SPACE",
    "rotate": "UP",
    "pause": "P",
    "restart": "R",
}

ACTION_LABELS = {
    "move_left": "Move Left",
    "move_right": "Move Right",
    "soft_drop": "Soft Drop",
    "hard_drop": "Hard Drop",
    "rotate": "Rotate",
    "pause": "Pause",
    "restart": "Restart",
}


def load_settings():
    try:
        with open(SETTINGS_FILE, "r") as f:
            data = json.load(f)
            binds = DEFAULT_KEYBINDS.copy()
            binds.update(data.get("keybinds", {}))
            return {"keybinds": binds}
    except (FileNotFoundError, json.JSONDecodeError):
        return {"keybinds": DEFAULT_KEYBINDS.copy()}


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
