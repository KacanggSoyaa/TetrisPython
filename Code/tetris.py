import pygame
import random
import sys
import os
import json

pygame.init()

CELL = 30
COLS = 10
ROWS = 20
SIDEBAR = 200
WIDTH = COLS * CELL + SIDEBAR
HEIGHT = ROWS * CELL
FPS = 60

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GRAY = (40, 40, 40)
DARK_GRAY = (20, 20, 20)
BORDER_COLOR = (80, 80, 80)
HIGHLIGHT = (100, 180, 255)
DIM = (100, 100, 100)

COLORS = {
    'I': (0, 240, 240),
    'O': (240, 240, 0),
    'T': (160, 0, 240),
    'S': (0, 240, 0),
    'Z': (240, 0, 0),
    'J': (0, 0, 240),
    'L': (240, 160, 0),
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


class Piece:
    def __init__(self, shape):
        self.shape = shape
        self.rotation = 0
        self.x = COLS // 2 - 2
        self.y = 0
        self.color = COLORS[shape]

    def cells(self):
        return [(self.x + dx, self.y + dy) for dx, dy in SHAPES[self.shape][self.rotation]]


class Board:
    def __init__(self):
        self.grid = [[None] * COLS for _ in range(ROWS)]

    def valid(self, piece, dx=0, dy=0):
        for x, y in piece.cells():
            nx, ny = x + dx, y + dy
            if nx < 0 or nx >= COLS or ny >= ROWS:
                return False
            if ny >= 0 and self.grid[ny][nx] is not None:
                return False
        return True

    def lock(self, piece):
        for x, y in piece.cells():
            if 0 <= y < ROWS:
                self.grid[y][x] = piece.color

    def clear_lines(self):
        cleared = 0
        new_grid = []
        for row in self.grid:
            if all(cell is not None for cell in row):
                cleared += 1
            else:
                new_grid.append(row)
        for _ in range(cleared):
            new_grid.insert(0, [None] * COLS)
        self.grid = new_grid
        return cleared


class Tetris:
    def __init__(self):
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Tetris")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("consolas", 22, bold=True)
        self.small_font = pygame.font.SysFont("consolas", 16)
        self.settings = load_settings()
        self.state = "menu"
        self.menu_selected = 0
        self.settings_selected = 0
        self.settings_actions = list(ACTION_LABELS.keys())
        self.rebinding = False
        self.rebinding_action = None
        self.menu_items = ["Play", "Settings", "Quit"]
        self.board = None
        self.reset_game()

    def reset_game(self):
        self.board = Board()
        self.bag = []
        self.current = self.new_piece()
        self.next_piece = self.new_piece()
        self.score = 0
        self.lines = 0
        self.level = 1
        self.game_over = False
        self.paused = False
        self.drop_time = 0
        self.lock_delay = 500
        self.lock_timer = 0
        self.locking = False

    def get_key_action(self, key):
        lookup = resolve_keybind(self.settings["keybinds"])
        return lookup.get(key)

    def get_speed(self):
        idx = min(self.level - 1, len(SPEEDS) - 1)
        return SPEEDS[idx]

    def fill_bag(self):
        shapes = list(SHAPES.keys())
        random.shuffle(shapes)
        self.bag.extend(shapes)

    def new_piece(self):
        if len(self.bag) < 2:
            self.fill_bag()
        return Piece(self.bag.pop(0))

    def try_rotate(self, direction):
        old_rot = self.current.rotation
        self.current.rotation = (self.current.rotation + direction) % 4
        kicks = [(0,0),(-1,0),(1,0),(0,-1),(-1,-1),(1,-1),(-2,0),(2,0)]
        for dx, dy in kicks:
            if self.board.valid(self.current, dx, dy):
                self.current.x += dx
                self.current.y += dy
                return True
        self.current.rotation = old_rot
        return False

    def hard_drop(self):
        while self.board.valid(self.current, 0, 1):
            self.current.y += 1
            self.score += 2
        self.lock_piece()

    def lock_piece(self):
        self.board.lock(self.current)
        cleared = self.board.clear_lines()
        self.lines += cleared
        self.score += SCORE_TABLE.get(cleared, 0) * self.level
        self.level = self.lines // LINES_PER_LEVEL + 1
        self.current = self.next_piece
        self.next_piece = self.new_piece()
        self.locking = False
        self.lock_timer = 0
        if not self.board.valid(self.current):
            self.game_over = True

    def ghost_y(self):
        dy = 0
        while self.board.valid(self.current, 0, dy + 1):
            dy += 1
        return self.current.y + dy

    def draw_block(self, x, y, color, offset_x=0):
        rect = pygame.Rect(offset_x + x * CELL, y * CELL, CELL, CELL)
        pygame.draw.rect(self.screen, color, rect)
        lighter = tuple(min(c + 40, 255) for c in color)
        darker = tuple(max(c - 40, 0) for c in color)
        pygame.draw.line(self.screen, lighter, rect.topleft, rect.topright, 2)
        pygame.draw.line(self.screen, lighter, rect.topleft, rect.bottomleft, 2)
        pygame.draw.line(self.screen, darker, rect.bottomleft, rect.bottomright, 2)
        pygame.draw.line(self.screen, darker, rect.topright, rect.bottomright, 2)

    def draw_grid(self):
        for y in range(ROWS):
            for x in range(COLS):
                rect = pygame.Rect(x * CELL, y * CELL, CELL, CELL)
                pygame.draw.rect(self.screen, GRAY, rect, 1)

    def draw_board(self):
        for y in range(ROWS):
            for x in range(COLS):
                if self.board.grid[y][x]:
                    self.draw_block(x, y, self.board.grid[y][x])

    def draw_piece(self, piece):
        for x, y in piece.cells():
            if y >= 0:
                self.draw_block(x, y, piece.color)

    def draw_ghost(self):
        gy = self.ghost_y()
        ghost_color = tuple(c // 3 for c in self.current.color)
        for dx, dy in SHAPES[self.current.shape][self.current.rotation]:
            x, y = self.current.x + dx, gy + dy
            if y >= 0:
                rect = pygame.Rect(x * CELL, y * CELL, CELL, CELL)
                pygame.draw.rect(self.screen, ghost_color, rect, 2)

    def draw_sidebar(self):
        sx = COLS * CELL + 15
        title = self.font.render("TETRIS", True, WHITE)
        self.screen.blit(title, (sx, 10))
        pygame.draw.line(self.screen, BORDER_COLOR, (sx, 45), (sx + SIDEBAR - 30, 45))

        labels = ["SCORE", "LEVEL", "LINES"]
        values = [self.score, self.level, self.lines]
        for i, (label, val) in enumerate(zip(labels, values)):
            y = 60 + i * 55
            lbl = self.small_font.render(label, True, (150, 150, 150))
            self.screen.blit(lbl, (sx, y))
            vtxt = self.font.render(str(val), True, WHITE)
            self.screen.blit(vtxt, (sx, y + 20))

        pygame.draw.line(self.screen, BORDER_COLOR, (sx, 235), (sx + SIDEBAR - 30, 235))

        nxt = self.small_font.render("NEXT", True, (150, 150, 150))
        self.screen.blit(nxt, (sx, 250))
        shape = SHAPES[self.next_piece.shape][0]
        color = self.next_piece.color
        for dx, dy in shape:
            bx = sx + dx * 25
            by = 280 + dy * 25
            rect = pygame.Rect(bx, by, 23, 23)
            pygame.draw.rect(self.screen, color, rect)
            lighter = tuple(min(c + 40, 255) for c in color)
            darker = tuple(max(c - 40, 0) for c in color)
            pygame.draw.line(self.screen, lighter, rect.topleft, rect.topright, 2)
            pygame.draw.line(self.screen, lighter, rect.topleft, rect.bottomleft, 2)
            pygame.draw.line(self.screen, darker, rect.bottomleft, rect.bottomright, 2)
            pygame.draw.line(self.screen, darker, rect.topright, rect.bottomright, 2)

        pygame.draw.line(self.screen, BORDER_COLOR, (sx, 400), (sx + SIDEBAR - 30, 400))

        binds = self.settings["keybinds"]
        def fmt_key(k):
            return key_name(pygame.key.key_code(k)) if k else "???"
        controls = [
            ("Move", fmt_key(binds['move_left']), fmt_key(binds['move_right'])),
            ("Rotate", fmt_key(binds['rotate']), None),
            ("Soft", fmt_key(binds['soft_drop']), None),
            ("Hard", fmt_key(binds['hard_drop']), None),
            ("Pause", fmt_key(binds['pause']), None),
            ("Restart", fmt_key(binds['restart']), None),
        ]
        y_off = 410
        lbl_w = 55
        for i, (label, key1, key2) in enumerate(controls):
            y = y_off + i * 20
            lbl = self.small_font.render(label, True, (150, 150, 150))
            self.screen.blit(lbl, (sx, y))
            k1 = self.small_font.render(key1, True, HIGHLIGHT)
            self.screen.blit(k1, (sx + lbl_w, y))
            if key2 is not None:
                k2 = self.small_font.render(key2, True, HIGHLIGHT)
                self.screen.blit(k2, (sx + lbl_w + 45, y))

    def draw_game_over(self):
        overlay = pygame.Surface((COLS * CELL, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        self.screen.blit(overlay, (0, 0))

        go_text = self.font.render("GAME OVER", True, (255, 50, 50))
        sc_text = self.font.render(f"Score: {self.score}", True, WHITE)
        re_text = self.small_font.render("Press R to restart", True, (180, 180, 180))

        cx = COLS * CELL // 2
        self.screen.blit(go_text, (cx - go_text.get_width() // 2, HEIGHT // 2 - 40))
        self.screen.blit(sc_text, (cx - sc_text.get_width() // 2, HEIGHT // 2))
        self.screen.blit(re_text, (cx - re_text.get_width() // 2, HEIGHT // 2 + 40))

    def draw_pause(self):
        overlay = pygame.Surface((COLS * CELL, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        self.screen.blit(overlay, (0, 0))

        cx = COLS * CELL // 2
        items = ["Resume", "Settings", "Restart", "Quit"]
        pt = self.font.render("PAUSED", True, WHITE)
        self.screen.blit(pt, (cx - pt.get_width() // 2, HEIGHT // 2 - 60))

        for i, item in enumerate(items):
            color = HIGHLIGHT if i == self.menu_selected else WHITE
            txt = self.font.render(item, True, color)
            self.screen.blit(txt, (cx - txt.get_width() // 2, HEIGHT // 2 - 10 + i * 30))

    def draw_menu(self):
        self.screen.fill(DARK_GRAY)
        title = self.font.render("T E T R I S", True, WHITE)
        cx = WIDTH // 2
        self.screen.blit(title, (cx - title.get_width() // 2, 120))

        for i, item in enumerate(self.menu_items):
            color = HIGHLIGHT if i == self.menu_selected else WHITE
            txt = self.font.render(item, True, color)
            self.screen.blit(txt, (cx - txt.get_width() // 2, 220 + i * 50))

        sub = self.small_font.render("Arrow Keys + Enter to select", True, DIM)
        self.screen.blit(sub, (cx - sub.get_width() // 2, 410))

    def draw_settings(self):
        self.screen.fill(DARK_GRAY)
        cx = WIDTH // 2

        title = self.font.render("SETTINGS", True, WHITE)
        self.screen.blit(title, (cx - title.get_width() // 2, 20))

        sub = self.small_font.render("Up/Down to select, Enter to rebind, Esc to go back", True, DIM)
        self.screen.blit(sub, (cx - sub.get_width() // 2, 55))

        pygame.draw.line(self.screen, BORDER_COLOR, (50, 80), (WIDTH - 50, 80))

        binds = self.settings["keybinds"]
        for i, action in enumerate(self.settings_actions):
            y = 100 + i * 45
            label = ACTION_LABELS[action]
            key_const = pygame.key.key_code(binds[action]) if binds[action] else 0
            key_display = key_name(key_const) if key_const else "???"

            is_selected = (i == self.settings_selected)
            is_rebinding_now = self.rebinding and self.rebinding_action == action

            bg_color = (50, 70, 100) if is_selected else None
            if is_rebinding_now:
                bg_color = (80, 50, 50)

            if bg_color:
                pygame.draw.rect(self.screen, bg_color, (60, y - 5, WIDTH - 120, 38), border_radius=6)

            lbl_color = HIGHLIGHT if is_selected else WHITE
            lbl = self.font.render(label, True, lbl_color)
            self.screen.blit(lbl, (80, y + 2))

            if is_rebinding_now:
                key_color = (255, 100, 100)
                key_txt = self.font.render("Press any key...", True, key_color)
            else:
                key_color = HIGHLIGHT if is_selected else (180, 180, 180)
                key_txt = self.font.render(f"[ {key_display} ]", True, key_color)
            self.screen.blit(key_txt, (WIDTH - 200, y + 2))

        pygame.draw.line(self.screen, BORDER_COLOR, (50, HEIGHT - 60), (WIDTH - 50, HEIGHT - 60))

        reset_txt = self.small_font.render("Press D to reset all to default", True, DIM)
        self.screen.blit(reset_txt, (cx - reset_txt.get_width() // 2, HEIGHT - 45))

    def handle_menu_input(self, event):
        if event.key == pygame.K_UP:
            self.menu_selected = (self.menu_selected - 1) % len(self.menu_items)
        elif event.key == pygame.K_DOWN:
            self.menu_selected = (self.menu_selected + 1) % len(self.menu_items)
        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            choice = self.menu_items[self.menu_selected]
            if choice == "Play":
                self.reset_game()
                self.state = "game"
            elif choice == "Settings":
                self.settings_selected = 0
                self.rebinding = False
                self.state = "settings"
            elif choice == "Quit":
                pygame.quit()
                sys.exit()

    def handle_settings_input(self, event):
        if self.rebinding:
            if event.key == pygame.K_ESCAPE:
                self.rebinding = False
                return
            new_key_name = key_name(event.key)
            self.settings["keybinds"][self.rebinding_action] = new_key_name
            save_settings(self.settings)
            self.rebinding = False
            return

        if event.key == pygame.K_UP:
            self.settings_selected = (self.settings_selected - 1) % len(self.settings_actions)
        elif event.key == pygame.K_DOWN:
            self.settings_selected = (self.settings_selected + 1) % len(self.settings_actions)
        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            self.rebinding_action = self.settings_actions[self.settings_selected]
            self.rebinding = True
        elif event.key == pygame.K_d:
            self.settings["keybinds"] = DEFAULT_KEYBINDS.copy()
            save_settings(self.settings)
        elif event.key == pygame.K_ESCAPE:
            self.state = "menu"

    def handle_pause_input(self, event):
        pause_items = ["Resume", "Settings", "Restart", "Quit"]
        if event.key == pygame.K_UP:
            self.menu_selected = (self.menu_selected - 1) % len(pause_items)
        elif event.key == pygame.K_DOWN:
            self.menu_selected = (self.menu_selected + 1) % len(pause_items)
        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            choice = pause_items[self.menu_selected]
            if choice == "Resume":
                self.paused = False
            elif choice == "Settings":
                self.settings_selected = 0
                self.rebinding = False
                self.state = "settings"
                self._prev_state = "pause"
            elif choice == "Restart":
                self.reset_game()
                self.state = "game"
            elif choice == "Quit":
                self.state = "menu"
                self.menu_selected = 0

    def handle_game_input(self, dt, event):
        action = self.get_key_action(event.key)
        if action is None:
            if event.key == pygame.K_ESCAPE:
                self.menu_selected = 0
                self.paused = True
            return

        if self.game_over:
            if action == "restart":
                self.reset_game()
            return

        if action == "pause":
            self.menu_selected = 0
            self.paused = not self.paused
            return

        if self.paused:
            return

        if action == "move_left":
            if self.board.valid(self.current, -1, 0):
                self.current.x -= 1
                if self.locking:
                    self.lock_timer = 0
        elif action == "move_right":
            if self.board.valid(self.current, 1, 0):
                self.current.x += 1
                if self.locking:
                    self.lock_timer = 0
        elif action == "rotate":
            if self.try_rotate(1):
                if self.locking:
                    self.lock_timer = 0
        elif action == "hard_drop":
            self.hard_drop()

    def handle_game_continuous(self, dt):
        keys = pygame.key.get_pressed()
        action = None
        for key_const, act in resolve_keybind(self.settings["keybinds"]).items():
            if keys[key_const]:
                action = act
                break

        if action == "soft_drop" and self.board.valid(self.current, 0, 1):
            self.current.y += 1
            self.score += 1
            self.drop_time = 0

    def run(self):
        while True:
            dt = self.clock.tick(FPS)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

                if event.type == pygame.KEYDOWN:
                    if self.state == "menu":
                        self.handle_menu_input(event)
                    elif self.state == "settings":
                        self.handle_settings_input(event)
                    elif self.state == "game":
                        if self.paused:
                            self.handle_pause_input(event)
                        else:
                            self.handle_game_input(dt, event)

            if self.state == "game" and not self.game_over and not self.paused:
                self.handle_game_continuous(dt)
                self.drop_time += dt
                speed = self.get_speed()

                if self.drop_time >= speed:
                    self.drop_time = 0
                    if self.board.valid(self.current, 0, 1):
                        self.current.y += 1
                        self.locking = False
                        self.lock_timer = 0
                    else:
                        self.locking = True

                if self.locking:
                    self.lock_timer += dt
                    if self.lock_timer >= self.lock_delay:
                        self.lock_piece()

            if self.state == "menu":
                self.draw_menu()
            elif self.state == "settings":
                self.draw_settings()
            elif self.state == "game":
                self.screen.fill(DARK_GRAY)
                self.draw_grid()
                self.draw_board()
                if not self.game_over:
                    self.draw_ghost()
                    self.draw_piece(self.current)
                self.draw_sidebar()
                if self.game_over:
                    self.draw_game_over()
                elif self.paused:
                    self.draw_pause()

            pygame.display.flip()


if __name__ == "__main__":
    game = Tetris()
    game.run()
