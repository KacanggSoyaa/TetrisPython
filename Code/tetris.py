import pygame
import random
import sys
from constants import (
    COLS, ROWS, FPS,
    SCORE_TABLE, LINES_PER_LEVEL,
    SHAPES, DEFAULT_KEYBINDS,
    DIFFICULTY_NAMES, DIFFICULTY_SPEEDS, DIFFICULTY_ORDER, LINE_GOALS,
    SPEED_KEYS, SPEED_LABELS, SPEED_UNITS,
    SPEED_MIN, SPEED_MAX, SPEED_STEP, SPEED_DEFAULTS,
    load_settings, save_settings, resolve_keybind, key_name,
)
from piece import Piece
from board import Board
from renderer import Renderer, LineClearEffect


class Tetris:
    def __init__(self):
        pygame.init()
        self.renderer = Renderer()
        self.settings = load_settings()
        self.state = "menu"
        self.menu_selected = 0
        self.diff_selected = 0
        self.lines_selected = 0
        self.speed_selected = 0
        self.settings_selected = 0
        self.rebinding = False
        self.rebinding_action = None
        self.board = None
        self._prev_state = None
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
        self.won = False
        self.paused = False
        self.drop_time = 0
        self.lock_delay = 500
        self.lock_timer = 0
        self.locking = False
        self.das_timer = 0
        self.das_direction = 0
        self.das_delay = self.settings["options"].get("das_delay", SPEED_DEFAULTS["das_delay"])
        self.das_repeat = self.settings["options"].get("das_repeat", SPEED_DEFAULTS["das_repeat"])
        self.soft_drop_interval = max(1, self.settings["options"].get("soft_drop_ms", SPEED_DEFAULTS["soft_drop_ms"]))
        self.soft_drop_timer = 0
        self.renderer.particles.clear()
        self.renderer.line_effects.clear()

    def get_key_action(self, key):
        lookup = resolve_keybind(self.settings["keybinds"])
        return lookup.get(key)

    def get_speed(self):
        diff = self.settings["options"].get("difficulty", "medium")
        speeds = DIFFICULTY_SPEEDS.get(diff, DIFFICULTY_SPEEDS["medium"])
        idx = min(self.level - 1, len(speeds) - 1)
        return speeds[idx]

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
        self.renderer.add_hard_drop_particles(self.current)
        while self.board.valid(self.current, 0, 1):
            self.current.y += 1
            self.score += 2
        self.lock_piece()

    def lock_piece(self):
        self.board.lock(self.current)
        cleared, cleared_rows = self.board.clear_lines()
        self.lines += cleared
        self.score += SCORE_TABLE.get(cleared, 0) * self.level
        self.level = self.lines // LINES_PER_LEVEL + 1
        if cleared > 0:
            self.renderer.add_line_clear_particles(cleared_rows)
            self.renderer.line_effects.append(LineClearEffect(cleared_rows))
        goal = self.settings["options"].get("line_goal", 0)
        if goal and self.lines >= goal:
            self.won = True
            return
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

    def handle_menu_input(self, event):
        items = ["Play", "Difficulty", "Lines", "Speeds", "Settings", "Quit"]
        if event.key == pygame.K_UP:
            self.menu_selected = (self.menu_selected - 1) % len(items)
        elif event.key == pygame.K_DOWN:
            self.menu_selected = (self.menu_selected + 1) % len(items)
        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            if self.menu_selected == 0:
                self.reset_game()
                self.state = "game"
            elif self.menu_selected == 1:
                diff = self.settings["options"].get("difficulty", "medium")
                self.diff_selected = DIFFICULTY_ORDER.index(diff) if diff in DIFFICULTY_ORDER else 0
                self._prev_state = "menu"
                self.state = "difficulty"
            elif self.menu_selected == 2:
                goal = self.settings["options"].get("line_goal", 20)
                self.lines_selected = LINE_GOALS.index(goal) if goal in LINE_GOALS else 1
                self._prev_state = "menu"
                self.state = "lines"
            elif self.menu_selected == 3:
                self.speed_selected = 0
                self._prev_state = "menu"
                self.state = "speeds"
            elif self.menu_selected == 4:
                self.settings_selected = 0
                self.rebinding = False
                self._prev_state = "menu"
                self.state = "settings"
            elif self.menu_selected == 5:
                pygame.quit()
                sys.exit()

    def handle_difficulty_input(self, event):
        diff_options = DIFFICULTY_ORDER
        if event.key == pygame.K_LEFT:
            self.diff_selected = (self.diff_selected - 1) % len(diff_options)
        elif event.key == pygame.K_RIGHT:
            self.diff_selected = (self.diff_selected + 1) % len(diff_options)
        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            self.settings["options"]["difficulty"] = diff_options[self.diff_selected]
            save_settings(self.settings)
            self._go_back_from_submenu()
        elif event.key == pygame.K_ESCAPE:
            self._go_back_from_submenu()

    def handle_lines_input(self, event):
        if event.key == pygame.K_LEFT:
            self.lines_selected = (self.lines_selected - 1) % len(LINE_GOALS)
        elif event.key == pygame.K_RIGHT:
            self.lines_selected = (self.lines_selected + 1) % len(LINE_GOALS)
        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            self.settings["options"]["line_goal"] = LINE_GOALS[self.lines_selected]
            save_settings(self.settings)
            self._go_back_from_submenu()
        elif event.key == pygame.K_ESCAPE:
            self._go_back_from_submenu()

    def handle_speeds_input(self, event):
        if event.key == pygame.K_UP:
            self.speed_selected = (self.speed_selected - 1) % len(SPEED_KEYS)
        elif event.key == pygame.K_DOWN:
            self.speed_selected = (self.speed_selected + 1) % len(SPEED_KEYS)
        elif event.key == pygame.K_LEFT:
            self._adjust_speed(-1)
        elif event.key == pygame.K_RIGHT:
            self._adjust_speed(1)
        elif event.key == pygame.K_c:
            for k, v in SPEED_DEFAULTS.items():
                self.settings["options"][k] = v
            save_settings(self.settings)
        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_ESCAPE):
            self._go_back_from_submenu()

    def _adjust_speed(self, direction):
        key = SPEED_KEYS[self.speed_selected]
        cur = self.settings["options"].get(key, SPEED_DEFAULTS[key])
        step = SPEED_STEP[key]
        newv = max(SPEED_MIN[key], min(SPEED_MAX[key], cur + direction * step))
        if newv != cur:
            self.settings["options"][key] = newv
            save_settings(self.settings)

    def _go_back_from_submenu(self):
        self.state = self._prev_state or "menu"
        self._prev_state = None

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
            self.settings_selected = (self.settings_selected - 1) % len(DEFAULT_KEYBINDS)
        elif event.key == pygame.K_DOWN:
            self.settings_selected = (self.settings_selected + 1) % len(DEFAULT_KEYBINDS)
        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            self.rebinding_action = list(DEFAULT_KEYBINDS.keys())[self.settings_selected]
            self.rebinding = True
        elif event.key == pygame.K_d:
            self.settings["keybinds"] = DEFAULT_KEYBINDS.copy()
            save_settings(self.settings)
        elif event.key == pygame.K_ESCAPE:
            if self._prev_state == "pause":
                self.state = "pause"
            else:
                self.state = "menu"
            self._prev_state = None

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
                self._prev_state = "pause"
                self.state = "settings"
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

        if self.won:
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
                self.das_direction = -1
                self.das_timer = 0
                if self.locking:
                    self.lock_timer = 0
        elif action == "move_right":
            if self.board.valid(self.current, 1, 0):
                self.current.x += 1
                self.das_direction = 1
                self.das_timer = 0
                if self.locking:
                    self.lock_timer = 0
        elif action == "rotate_right":
            if self.try_rotate(1):
                if self.locking:
                    self.lock_timer = 0
        elif action == "rotate_left":
            if self.try_rotate(-1):
                if self.locking:
                    self.lock_timer = 0
        elif action == "rotate_180":
            if self.try_rotate(2):
                if self.locking:
                    self.lock_timer = 0
        elif action == "hard_drop":
            self.hard_drop()

    def handle_game_continuous(self, dt):
        keys = pygame.key.get_pressed()
        lookup = resolve_keybind(self.settings["keybinds"])
        actions = set()
        for key_const, act in lookup.items():
            if keys[key_const]:
                actions.add(act)

        if "soft_drop" in actions:
            self.soft_drop_timer += dt
            while self.soft_drop_timer >= self.soft_drop_interval:
                self.soft_drop_timer -= self.soft_drop_interval
                if self.board.valid(self.current, 0, 1):
                    self.current.y += 1
                    self.score += 1
                    self.drop_time = 0
                else:
                    self.soft_drop_timer = 0
                    break
        else:
            self.soft_drop_timer = 0

        def holding(action):
            for key_const, a in lookup.items():
                if a == action and keys[key_const]:
                    return True
            return False

        dirs = []
        if holding("move_left"):
            dirs.append(-1)
        if holding("move_right"):
            dirs.append(1)
        if dirs:
            direction = dirs[-1]
            if direction != self.das_direction:
                self.das_direction = direction
                self.das_timer = 0
                self._move_piece(direction)
            else:
                self.das_timer += dt
                if self.das_timer >= self.das_delay:
                    self._move_piece(direction)
                    self.das_timer = self.das_delay - self.das_repeat
        else:
            self.das_direction = 0
            self.das_timer = 0

    def _move_piece(self, dx):
        if self.board.valid(self.current, dx, 0):
            self.current.x += dx
            if self.locking:
                self.lock_timer = 0

    def get_game_state(self):
        return {
            "state": self.state,
            "menu_selected": self.menu_selected,
            "diff_selected": self.diff_selected,
            "lines_selected": self.lines_selected,
            "speed_selected": self.speed_selected,
            "settings_selected": self.settings_selected,
            "settings": self.settings,
            "rebinding": self.rebinding,
            "rebinding_action": self.rebinding_action,
            "board": self.board,
            "current": self.current,
            "next_piece": self.next_piece,
            "score": self.score,
            "level": self.level,
            "lines": self.lines,
            "game_over": self.game_over,
            "won": self.won,
            "paused": self.paused,
            "ghost_y": self.ghost_y() if self.current and not self.game_over else 0,
        }

    def run(self):
        while True:
            dt = self.renderer.clock.tick(FPS)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

                if event.type == pygame.KEYDOWN:
                    if self.state == "menu":
                        self.handle_menu_input(event)
                    elif self.state == "difficulty":
                        self.handle_difficulty_input(event)
                    elif self.state == "lines":
                        self.handle_lines_input(event)
                    elif self.state == "speeds":
                        self.handle_speeds_input(event)
                    elif self.state == "settings":
                        self.handle_settings_input(event)
                    elif self.state == "game":
                        if self.paused:
                            self.handle_pause_input(event)
                        else:
                            self.handle_game_input(dt, event)

            if self.state == "game" and not self.game_over and not self.won and not self.paused:
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

            self.renderer.draw_all(self.get_game_state())
