import random
import sys
import pygame

from constants import (
    FPS, PREVIEW_COUNT, LOCK_DELAY, CLEAR_FLASH_MS, CLEAR_GLOW_MS,
    LINES_PER_LEVEL, SCORE_TABLE, CLEAR_LABELS, TSPINS, COMBO_STEP,
    BACK_TO_BACK, PERFECT_CLEAR, SOFT_DROP_POINTS, HARD_DROP_POINTS,
    SHAPES, THEME, DIFFICULTY_ORDER, DIFFICULTY_SPEEDS, LINE_GOALS,
    SPEED_KEYS, SPEED_DEFAULTS, SPEED_STEP, SPEED_MIN, SPEED_MAX,
    ACTION_LABELS, DEFAULT_KEYBINDS, MENU_ITEMS, PAUSE_ITEMS, OVER_ITEMS,
    load_settings, save_settings, resolve_keybind, key_name,
)
from piece import Piece
from board import Board
from renderer import Renderer


KICKS = [(0, 0), (-1, 0), (1, 0), (0, -1), (-1, -1), (1, -1), (-2, 0), (2, 0)]
TSPIN_FRONT = {0: (0, 1), 1: (1, 3), 2: (2, 3), 3: (0, 2)}


class Tetris:
    def __init__(self):
        pygame.init()
        self.renderer = Renderer()
        self.settings = load_settings()
        self.state = "menu"
        self.menu_selected = 0
        self.over_selected = 0
        self.diff_selected = 0
        self.lines_selected = 0
        self.speed_selected = 0
        self.settings_selected = 0
        self.rebinding = False
        self.rebinding_action = None
        self.bind_notice = None
        self.notice_timer = 0
        self.board = None
        self._prev_state = None
        self.reset_game()

    # ------------------------------------------------------------ lifecycle
    def reset_game(self):
        opts = self.settings["options"]
        self.board = Board()
        self.bag = []
        self.hold = None
        self.hold_used = False
        self.queue = []
        self._refill_queue()
        self.current = self.queue.pop(0)
        self._refill_queue()

        self.score = 0
        self.lines = 0
        self.level = 1
        self.combo = -1
        self.b2b = False
        self.pieces_placed = 0
        self.tetrises = 0
        self.best_combo = 0
        self.start_time = pygame.time.get_ticks()

        self.game_over = False
        self.won = False
        self.paused = False
        self.clearing = False
        self.clear_anim = None
        self.pending_win = False
        self.drop_time = 0
        self.lock_delay = LOCK_DELAY
        self.lock_timer = 0
        self.locking = False
        self.last_move_was_rotation = False
        self.das_direction = 0
        self.das_timer = 0
        self.das_delay = opts.get("das_delay", SPEED_DEFAULTS["das_delay"])
        self.das_repeat = opts.get("das_repeat", SPEED_DEFAULTS["das_repeat"])
        self.soft_drop_interval = opts.get("soft_drop_ms", SPEED_DEFAULTS["soft_drop_ms"])
        self.soft_drop_timer = 0
        self.renderer.reset_effects()

    # ------------------------------------------------------------ bag logic
    def fill_bag(self):
        shapes = list(SHAPES.keys())
        random.shuffle(shapes)
        self.bag.extend(shapes)

    def _refill_queue(self):
        while len(self.queue) < PREVIEW_COUNT + 1:
            if not self.bag:
                self.fill_bag()
            self.queue.append(Piece(self.bag.pop(0)))

    def spawn_next(self):
        self.current = self.queue.pop(0)
        self._refill_queue()
        self.hold_used = False
        self.last_move_was_rotation = False
        self.locking = False
        self.lock_timer = 0
        self.drop_time = 0
        if not self.board.valid(self.current):
            self.game_over = True
            self.over_selected = 0
            self.record_high()

    def record_high(self):
        if self.score > self.settings.get("high", 0):
            self.settings["high"] = self.score
            save_settings(self.settings)
            return True
        return False

    # ------------------------------------------------------------- movement
    def get_key_action(self, key):
        return resolve_keybind(self.settings["keybinds"]).get(key)

    def get_speed(self):
        diff = self.settings["options"].get("difficulty", "medium")
        speeds = DIFFICULTY_SPEEDS.get(diff, DIFFICULTY_SPEEDS["medium"])
        return speeds[min(self.level - 1, len(speeds) - 1)]

    def try_rotate(self, direction):
        old_rot = self.current.rotation
        self.current.rotation = (self.current.rotation + direction) % 4
        for dx, dy in KICKS:
            if self.board.valid(self.current, dx, dy):
                self.current.x += dx
                self.current.y += dy
                self.last_move_was_rotation = True
                self.touch_lock()
                return True
        self.current.rotation = old_rot
        return False

    def touch_lock(self):
        if self.locking:
            self.lock_timer = 0

    def move(self, dx):
        if self.board.valid(self.current, dx, 0):
            self.current.x += dx
            self.last_move_was_rotation = False
            self.touch_lock()

    def hard_drop(self):
        self.renderer.shake(2)
        self.renderer.add_hard_drop_particles(self.current, self.ghost_y())
        while self.board.valid(self.current, 0, 1):
            self.current.y += 1
            self.score += HARD_DROP_POINTS
        self.lock_piece()

    def hold_piece(self):
        if self.hold_used or self.clearing or self.game_over or self.won:
            return
        self.hold_used = True
        current = self.current.shape
        if self.hold is None:
            self.hold = current
            self.current = self.queue.pop(0)
            self._refill_queue()
        else:
            self.hold, self.current.shape = self.current.shape, self.hold
            self.current.rotation = 0
        self.last_move_was_rotation = False
        self.locking = False
        self.lock_timer = 0
        self.drop_time = 0

    def ghost_y(self):
        dy = 0
        while self.board.valid(self.current, 0, dy + 1):
            dy += 1
        return self.current.y + dy

    # ---------------------------------------------------------------- lock
    def tspin_kind(self):
        if self.current.shape != "T" or not self.last_move_was_rotation:
            return None
        cx, cy = self.current.center()
        corners = [(cx - 1, cy - 1), (cx + 1, cy - 1),
                   (cx - 1, cy + 1), (cx + 1, cy + 1)]
        hits = [self.board.filled(x, y) for x, y in corners]
        if sum(hits) < 3:
            return None
        front = TSPIN_FRONT.get(self.current.rotation)
        if front and all(hits[i] for i in front):
            return "T-SPIN"
        return "T-SPIN MINI"

    def lock_piece(self):
        self.board.lock(self.current)
        self.pieces_placed += 1
        rows = self.board.full_rows()
        self.lock_info = {"rows": rows, "tspin": self.tspin_kind(), "level": self.level}
        self.locking = False
        if rows:
            self.clearing = True
            self.clear_anim = {
                "rows": rows,
                "t": 0,
                "collapsed": False,
                "landed": [r - len(rows) for r in rows],
                "count": len(rows),
            }
            return
        self.resolve_clear()
        self.spawn_next()

    def resolve_clear(self):
        info = self.lock_info
        rows = info["rows"]
        cleared = len(rows)
        level = info["level"]
        tspin = info["tspin"]

        points = 0
        labels = []

        if tspin:
            base = TSPINS.get(min(cleared, 3), 1600)
            points += base * level
            suffix = {0: "", 1: " SINGLE", 2: " DOUBLE", 3: " TRIPLE"}.get(cleared, "")
            labels.append((tspin + suffix, THEME["accent"]))
        elif cleared:
            points += SCORE_TABLE.get(cleared, 0) * level
            labels.append((CLEAR_LABELS.get(cleared, ""), THEME["accent"]))

        difficult = cleared == 4 or bool(tspin and cleared)
        if difficult and self.b2b:
            points = int(points * BACK_TO_BACK)
            labels.insert(0, ("BACK TO BACK", THEME["warn"]))
        self.b2b = difficult
        if cleared == 4:
            self.tetrises += 1

        if cleared:
            self.combo += 1
            self.best_combo = max(self.best_combo, self.combo)
            if self.combo > 0:
                points += COMBO_STEP * self.combo * level
                labels.append((f"COMBO x{self.combo}", THEME["text"]))
        else:
            self.combo = -1

        if cleared and self.board.is_empty():
            points += PERFECT_CLEAR * level
            labels.append(("PERFECT CLEAR", THEME["ok"]))

        self.score += points
        self.lines += cleared
        self.level = self.lines // LINES_PER_LEVEL + 1

        for text, color in labels:
            self.renderer.popup(text, color, big=("TETRIS" in text or "T-SPIN" in text))

        goal = self.settings["options"].get("line_goal", 0)
        if goal and self.lines >= goal and not self.won:
            self.pending_win = True
            self.renderer.shake(6)

    def update_clear(self, dt):
        anim = self.clear_anim
        anim["t"] += dt
        if not anim["collapsed"] and anim["t"] >= CLEAR_FLASH_MS:
            anim["collapsed"] = True
            self.board.clear_rows(anim["rows"])
            self.resolve_clear()
            self.renderer.burst(anim["landed"], anim["count"])
        if anim["t"] >= CLEAR_FLASH_MS + CLEAR_GLOW_MS:
            self.clear_anim = None
            self.clearing = False
            if self.pending_win:
                self.won = True
                self.record_high()
            else:
                self.spawn_next()

    # --------------------------------------------------------- menu states
    def handle_menu_input(self, event):
        if event.key == pygame.K_UP:
            self.menu_selected = (self.menu_selected - 1) % len(MENU_ITEMS)
        elif event.key == pygame.K_DOWN:
            self.menu_selected = (self.menu_selected + 1) % len(MENU_ITEMS)
        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            choice = MENU_ITEMS[self.menu_selected]
            if choice == "Play":
                self.reset_game()
                self.state = "game"
            elif choice == "Difficulty":
                diff = self.settings["options"].get("difficulty", "medium")
                self.diff_selected = DIFFICULTY_ORDER.index(diff)
                self._prev_state = "menu"
                self.state = "difficulty"
            elif choice == "Lines":
                goal = self.settings["options"].get("line_goal", 20)
                self.lines_selected = LINE_GOALS.index(goal)
                self._prev_state = "menu"
                self.state = "lines"
            elif choice == "Speeds":
                self.speed_selected = 0
                self._prev_state = "menu"
                self.state = "speeds"
            elif choice == "Settings":
                self.settings_selected = 0
                self.rebinding = False
                self._prev_state = "menu"
                self.state = "settings"
            elif choice == "Quit":
                pygame.quit()
                sys.exit()

    def handle_difficulty_input(self, event):
        n = len(DIFFICULTY_ORDER)
        if event.key in (pygame.K_UP, pygame.K_LEFT):
            self.diff_selected = (self.diff_selected - 1) % n
        elif event.key in (pygame.K_DOWN, pygame.K_RIGHT):
            self.diff_selected = (self.diff_selected + 1) % n
        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            self.settings["options"]["difficulty"] = DIFFICULTY_ORDER[self.diff_selected]
            save_settings(self.settings)
            self._back()
        elif event.key == pygame.K_ESCAPE:
            self._back()

    def handle_lines_input(self, event):
        n = len(LINE_GOALS)
        if event.key in (pygame.K_UP, pygame.K_LEFT):
            self.lines_selected = (self.lines_selected - 1) % n
        elif event.key in (pygame.K_DOWN, pygame.K_RIGHT):
            self.lines_selected = (self.lines_selected + 1) % n
        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            self.settings["options"]["line_goal"] = LINE_GOALS[self.lines_selected]
            save_settings(self.settings)
            self._back()
        elif event.key == pygame.K_ESCAPE:
            self._back()

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
            self.notice("Speeds reset to defaults")
        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_ESCAPE):
            self._back()

    def _adjust_speed(self, direction):
        key = SPEED_KEYS[self.speed_selected]
        cur = self.settings["options"].get(key, SPEED_DEFAULTS[key])
        newv = max(SPEED_MIN[key], min(SPEED_MAX[key], cur + direction * SPEED_STEP[key]))
        if newv != cur:
            self.settings["options"][key] = newv
            save_settings(self.settings)

    def _back(self):
        self.state = self._prev_state or "menu"
        self._prev_state = None

    def handle_settings_input(self, event):
        actions = list(ACTION_LABELS.keys())
        if self.rebinding:
            if event.key == pygame.K_ESCAPE:
                self.rebinding = False
                self.notice("Rebind cancelled")
                return
            conflict = self._conflict(actions.index(self.rebinding_action), event.key)
            if conflict:
                self.rebinding = False
                self.notice(conflict)
                return
            self.settings["keybinds"][self.rebinding_action] = key_name(event.key)
            save_settings(self.settings)
            self.rebinding = False
            self.notice(f"{ACTION_LABELS[self.rebinding_action]} bound")
            return

        if event.key == pygame.K_UP:
            self.settings_selected = (self.settings_selected - 1) % len(actions)
        elif event.key == pygame.K_DOWN:
            self.settings_selected = (self.settings_selected + 1) % len(actions)
        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            self.rebinding_action = actions[self.settings_selected]
            self.rebinding = True
        elif event.key == pygame.K_d:
            self.settings["keybinds"] = DEFAULT_KEYBINDS.copy()
            save_settings(self.settings)
            self.notice("Keybinds reset to default")
        elif event.key == pygame.K_ESCAPE:
            self.state = "pause" if self._prev_state == "pause" else "menu"
            self._prev_state = None

    def _conflict(self, index, key):
        actions = list(ACTION_LABELS.keys())
        for i, action in enumerate(actions):
            if i == index:
                continue
            bound = self.settings["keybinds"].get(action)
            if not bound:
                continue
            try:
                if pygame.key.key_code(bound) == key:
                    return f"Already bound to {ACTION_LABELS[action]}"
            except ValueError:
                continue
        return None

    def notice(self, text, duration=1800):
        self.bind_notice = text
        self.notice_timer = duration

    def handle_pause_input(self, event):
        if event.key in (pygame.K_ESCAPE, pygame.K_p):
            self.paused = False
        elif event.key == pygame.K_UP:
            self.menu_selected = (self.menu_selected - 1) % len(PAUSE_ITEMS)
        elif event.key == pygame.K_DOWN:
            self.menu_selected = (self.menu_selected + 1) % len(PAUSE_ITEMS)
        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            choice = PAUSE_ITEMS[self.menu_selected]
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

    def handle_over_input(self, event):
        if event.key in (pygame.K_UP, pygame.K_w):
            self.over_selected = (self.over_selected - 1) % len(OVER_ITEMS)
        elif event.key in (pygame.K_DOWN, pygame.K_s):
            self.over_selected = (self.over_selected + 1) % len(OVER_ITEMS)
        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            if OVER_ITEMS[self.over_selected] == "Restart":
                self.reset_game()
            else:
                self.state = "menu"
                self.menu_selected = 0
        elif event.key == pygame.K_ESCAPE:
            self.state = "menu"
            self.menu_selected = 0

    # ---------------------------------------------------------- game input
    def handle_game_input(self, event):
        if event.key == pygame.K_ESCAPE:
            if not (self.game_over or self.won):
                self.paused = not self.paused
                self.menu_selected = 0
            return

        action = self.get_key_action(event.key)
        if action is None:
            return

        if self.game_over or self.won:
            if action == "restart":
                self.reset_game()
            return

        if action == "pause":
            self.paused = not self.paused
            self.menu_selected = 0
            return

        if self.paused or self.clearing:
            return

        if action == "move_left":
            self.move(-1)
            self.das_direction = -1
            self.das_timer = 0
        elif action == "move_right":
            self.move(1)
            self.das_direction = 1
            self.das_timer = 0
        elif action == "rotate_right":
            self.try_rotate(1)
        elif action == "rotate_left":
            self.try_rotate(-1)
        elif action == "rotate_180":
            self.try_rotate(2)
        elif action == "hold":
            self.hold_piece()
        elif action == "hard_drop":
            self.hard_drop()

    def handle_game_continuous(self, dt):
        lookup = resolve_keybind(self.settings["keybinds"])
        keys = pygame.key.get_pressed()

        holding = set()
        for key_const, action in lookup.items():
            if keys[key_const]:
                holding.add(action)

        if "soft_drop" in holding:
            self.soft_drop_timer += dt
            while self.soft_drop_timer >= self.soft_drop_interval:
                self.soft_drop_timer -= self.soft_drop_interval
                if self.board.valid(self.current, 0, 1):
                    self.current.y += 1
                    self.score += SOFT_DROP_POINTS
                    self.drop_time = 0
                    self.last_move_was_rotation = False
                else:
                    self.soft_drop_timer = 0
                    break
        else:
            self.soft_drop_timer = 0

        if "move_left" in holding:
            direction = -1
        elif "move_right" in holding:
            direction = 1
        else:
            direction = 0

        if direction == 0:
            self.das_direction = 0
            self.das_timer = 0
        elif direction != self.das_direction:
            self.das_direction = direction
            self.das_timer = 0
        else:
            self.das_timer += dt
            if self.das_timer >= self.das_delay:
                self.move(direction)
                self.das_timer = self.das_delay - self.das_repeat

    # ------------------------------------------------------------- runtime
    def get_game_state(self):
        opts = self.settings["options"]
        goal = opts.get("line_goal", 0)
        goal = goal if goal else None
        playing = self.state == "game" and not (self.game_over or self.won or self.paused)
        return {
            "state": self.state,
            "menu_selected": self.menu_selected,
            "over_selected": self.over_selected,
            "diff_selected": self.diff_selected,
            "lines_selected": self.lines_selected,
            "speed_selected": self.speed_selected,
            "settings_selected": self.settings_selected,
            "settings": self.settings,
            "rebinding": self.rebinding,
            "rebinding_action": self.rebinding_action,
            "notice": self.bind_notice if self.notice_timer > 0 else None,
            "board": self.board,
            "current": self.current,
            "hold": self.hold,
            "hold_used": self.hold_used,
            "queue": self.queue[:PREVIEW_COUNT],
            "score": self.score,
            "level": self.level,
            "lines": self.lines,
            "goal": goal,
            "combo": self.combo,
            "b2b": self.b2b,
            "pieces": self.pieces_placed,
            "tetrises": self.tetrises,
            "best_combo": self.best_combo,
            "elapsed": (pygame.time.get_ticks() - self.start_time) // 1000,
            "game_over": self.game_over,
            "won": self.won,
            "paused": self.paused,
            "clearing": self.clearing,
            "clear_anim": self.clear_anim,
            "ghost_y": self.ghost_y() if playing and not self.clearing else None,
        }

    def run(self):
        while True:
            dt = self.renderer.clock.tick(FPS)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type != pygame.KEYDOWN:
                    continue
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
                    if self.game_over or self.won:
                        self.handle_over_input(event)
                    elif self.paused:
                        self.handle_pause_input(event)
                    else:
                        self.handle_game_input(event)

            if self.state == "game":
                if self.clearing:
                    self.update_clear(dt)
                elif not (self.game_over or self.won or self.paused):
                    self.handle_game_continuous(dt)
                    self.drop_time += dt
                    if self.drop_time >= self.get_speed():
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

            if self.notice_timer > 0:
                self.notice_timer -= dt

            self.renderer.draw_all(self.get_game_state(), dt)
