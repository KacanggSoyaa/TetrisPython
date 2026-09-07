import pygame
import math
import random
from constants import (
    CELL, COLS, ROWS, SIDEBAR, WIDTH, HEIGHT,
    COLORS, SHAPES, ACTION_LABELS,
    DIFFICULTY_NAMES, DIFFICULTY_ORDER, LINE_GOALS,
    SPEED_KEYS, SPEED_LABELS, SPEED_UNITS,
    SPEED_MIN, SPEED_MAX, SPEED_DEFAULTS,
)
from constants import key_name


class Star:
    def __init__(self):
        self.x = random.randint(0, WIDTH)
        self.y = random.randint(0, HEIGHT)
        self.brightness = random.randint(60, 180)
        self.twinkle_speed = random.uniform(0.01, 0.04)
        self.twinkle_offset = random.uniform(0, math.pi * 2)
        self.size = random.choice([1, 1, 1, 2])

    def draw(self, screen, frame):
        b = self.brightness + int(40 * math.sin(frame * self.twinkle_speed + self.twinkle_offset))
        b = max(30, min(220, b))
        color = (b, b, min(255, b + 20))
        if self.size == 1:
            screen.set_at((int(self.x), int(self.y)), color)
        else:
            pygame.draw.circle(screen, color, (int(self.x), int(self.y)), 1)


class ShootingStar:
    def __init__(self):
        self.reset()

    def reset(self):
        self.x = random.randint(0, WIDTH)
        self.y = random.randint(0, HEIGHT // 3)
        angle = random.uniform(0.3, 0.8)
        speed = random.uniform(8, 14)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.life = random.randint(20, 40)
        self.max_life = self.life
        self.tail_len = random.randint(4, 8)
        self.trail = []

    def update(self):
        self.trail.append((self.x, self.y))
        if len(self.trail) > self.tail_len:
            self.trail.pop(0)
        self.x += self.vx
        self.y += self.vy
        self.life -= 1

    def draw(self, screen):
        for i, (tx, ty) in enumerate(self.trail):
            t = (i + 1) / len(self.trail)
            alpha = int(120 * t * (self.life / self.max_life))
            brightness = int(200 * t)
            color = (brightness, brightness, min(255, brightness + 30))
            size = max(1, int(t * 2))
            pygame.draw.circle(screen, color, (int(tx), int(ty)), size)
        if self.life > self.max_life // 2:
            pygame.draw.circle(screen, (255, 255, 255),
                               (int(self.x), int(self.y)), 1)


class Particle:
    def __init__(self, x, y, color, speed_x=None, speed_y=None, lifetime=None):
        self.x = x
        self.y = y
        self.color = color
        self.speed_x = speed_x if speed_x is not None else random.uniform(-2, 2)
        self.speed_y = speed_y if speed_y is not None else random.uniform(-3, -0.5)
        self.lifetime = lifetime if lifetime is not None else random.randint(15, 30)
        self.max_lifetime = self.lifetime
        self.size = random.randint(1, 3)

    def update(self):
        self.x += self.speed_x
        self.y += self.speed_y
        self.speed_y += 0.06
        self.lifetime -= 1

    def draw(self, screen):
        if self.lifetime > 0:
            t = self.lifetime / self.max_lifetime
            c = tuple(int(v * t) for v in self.color)
            s = max(1, int(self.size * t))
            pygame.draw.circle(screen, c, (int(self.x), int(self.y)), s)


class LineClearEffect:
    def __init__(self, rows):
        self.rows = rows
        self.timer = 18
        self.max_timer = 18

    def draw(self, screen, particles):
        t = self.timer / self.max_timer
        for row in self.rows:
            y = row * CELL
            flash = pygame.Surface((COLS * CELL, CELL), pygame.SRCALPHA)
            flash.fill((255, 255, 255, int(180 * t)))
            screen.blit(flash, (0, y))
            if self.timer == self.max_timer:
                for _ in range(6):
                    px = random.randint(0, COLS * CELL)
                    particles.append(Particle(
                        px, y + CELL // 2,
                        (200, 210, 230),
                        speed_y=random.uniform(-4, -1),
                        lifetime=random.randint(15, 30)))

    def update(self):
        self.timer -= 1
        return self.timer <= 0


class Renderer:
    def __init__(self):
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Tetris")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("segoeui", 18, bold=True)
        self.small_font = pygame.font.SysFont("segoeui", 14)
        self.big_font = pygame.font.SysFont("segoeui", 28, bold=True)
        self.title_font = pygame.font.SysFont("segoeui", 40, bold=True)
        self.stats_font = pygame.font.SysFont("segoeui", 22, bold=True)
        self.particles = []
        self.line_effects = []
        self.frame = 0
        self.stars = [Star() for _ in range(80)]
        self.shooting_stars = []
        self._shooting_timer = 0
        self._bg_surface = None
        self._sidebar_surface = None
        self._build_bg()

    def _build_bg(self):
        self._bg_surface = pygame.Surface((WIDTH, HEIGHT))
        for y in range(HEIGHT):
            t = y / HEIGHT
            r = int(8 + 6 * t)
            g = int(8 + 5 * t)
            b = int(18 + 8 * t)
            pygame.draw.line(self._bg_surface, (r, g, b), (0, y), (WIDTH, y))
        sx = COLS * CELL
        for y in range(HEIGHT):
            t = y / HEIGHT
            r = int(12 + 4 * t)
            g = int(11 + 4 * t)
            b = int(22 + 6 * t)
            pygame.draw.line(self._bg_surface, (r, g, b), (sx, y), (WIDTH, y))

    def _draw_block(self, x, y, color, offset_x=0, size=None):
        s = size or CELL
        rect = pygame.Rect(offset_x + x * s, y * s, s, s)
        self.screen.fill(color, rect)
        lighter = tuple(min(c + 50, 255) for c in color)
        darker = tuple(max(c - 50, 0) for c in color)
        darker2 = tuple(max(c - 80, 0) for c in color)
        bw = max(2, s // 8)
        pygame.draw.line(self.screen, lighter, rect.topleft, (rect.right - 1, rect.top), bw)
        pygame.draw.line(self.screen, lighter, rect.topleft, (rect.left, rect.bottom - 1), bw)
        pygame.draw.line(self.screen, darker, (rect.left, rect.bottom - 1), rect.bottomright, bw)
        pygame.draw.line(self.screen, darker, (rect.right - 1, rect.top), rect.bottomright, bw)
        inner = pygame.Rect(rect.x + bw, rect.y + bw, s - bw * 2, s - bw * 2)
        highlight = pygame.Surface((inner.w, inner.h), pygame.SRCALPHA)
        highlight.fill((*lighter, 35))
        self.screen.blit(highlight, inner.topleft)

    def _draw_block_plain(self, x, y, color, size):
        rect = pygame.Rect(x, y, size, size)
        self.screen.fill(color, rect)
        lighter = tuple(min(c + 45, 255) for c in color)
        darker = tuple(max(c - 45, 0) for c in color)
        bw = 2
        pygame.draw.line(self.screen, lighter, rect.topleft, (rect.right - 1, rect.top), bw)
        pygame.draw.line(self.screen, lighter, rect.topleft, (rect.left, rect.bottom - 1), bw)
        pygame.draw.line(self.screen, darker, (rect.left, rect.bottom - 1), rect.bottomright, bw)
        pygame.draw.line(self.screen, darker, (rect.right - 1, rect.top), rect.bottomright, bw)

    def add_line_clear_particles(self, rows):
        for row in rows:
            for _ in range(8):
                px = random.randint(0, COLS * CELL)
                py = row * CELL + CELL // 2
                self.particles.append(Particle(px, py, (200, 210, 230)))

    def add_hard_drop_particles(self, piece):
        for dx, dy in SHAPES[piece.shape][piece.rotation]:
            x = piece.x + dx
            y = piece.y + dy
            if y >= 0:
                for _ in range(3):
                    px = x * CELL + random.randint(0, CELL)
                    py = (y + 1) * CELL
                    self.particles.append(Particle(
                        px, py, piece.color,
                        speed_y=random.uniform(-3, -0.5),
                        speed_x=random.uniform(-1.5, 1.5),
                        lifetime=random.randint(10, 20)))

    def update_particles(self):
        self.particles = [p for p in self.particles if p.lifetime > 0]
        for p in self.particles:
            p.update()

    def update_stars(self):
        self._shooting_timer -= 1
        if self._shooting_timer <= 0 and len(self.shooting_stars) < 2:
            self.shooting_stars.append(ShootingStar())
            self._shooting_timer = random.randint(80, 200)
        self.shooting_stars = [s for s in self.shooting_stars if s.life > 0]
        for s in self.shooting_stars:
            s.update()

    def draw_stars(self, area=None):
        for star in self.stars:
            if area:
                sx, sy, sw, sh = area
                if sx <= star.x <= sx + sw and sy <= star.y <= sy + sh:
                    star.draw(self.screen, self.frame)
            else:
                star.draw(self.screen, self.frame)
        for ss in self.shooting_stars:
            ss.draw(self.screen)

    def draw_game_bg(self):
        self.screen.blit(self._bg_surface, (0, 0))
        self.draw_stars(area=(0, 0, COLS * CELL, HEIGHT))
        border_x = COLS * CELL
        pygame.draw.line(self.screen, (40, 38, 60), (border_x, 0), (border_x, HEIGHT), 2)

    def draw_full_bg(self):
        self.screen.blit(self._bg_surface, (0, 0))
        self.draw_stars()

    def draw_grid(self):
        for y in range(ROWS):
            for x in range(COLS):
                rect = pygame.Rect(x * CELL, y * CELL, CELL, CELL)
                pygame.draw.rect(self.screen, (22, 22, 35), rect, 1)

    def draw_board(self, board):
        for y in range(ROWS):
            for x in range(COLS):
                if board.grid[y][x]:
                    self._draw_block(x, y, board.grid[y][x])

    def draw_piece(self, piece):
        for x, y in piece.cells():
            if y >= 0:
                self._draw_block(x, y, piece.color)

    def draw_ghost(self, piece, ghost_y):
        for dx, dy in SHAPES[piece.shape][piece.rotation]:
            x, y = piece.x + dx, ghost_y + dy
            if y >= 0:
                rect = pygame.Rect(x * CELL, y * CELL, CELL, CELL)
                ghost_col = tuple(c // 4 for c in piece.color)
                ghost_col = (max(ghost_col[0], 30), max(ghost_col[1], 30), max(ghost_col[2], 30))
                pygame.draw.rect(self.screen, ghost_col, rect)
                pygame.draw.rect(self.screen, piece.color, rect, 1)

    def draw_sidebar(self, score, level, lines, next_piece, settings):
        sx = COLS * CELL
        x = sx + 16

        title = self.title_font.render("TETRIS", True, (220, 220, 235))
        self.screen.blit(title, (x + 8, 12))

        sep_y = 58
        pygame.draw.line(self.screen, (40, 38, 60), (x - 4, sep_y), (sx + SIDEBAR - 16, sep_y))

        diff_name = DIFFICULTY_NAMES.get(
            settings["options"].get("difficulty", "medium"), "MEDIUM")
        goal = settings["options"].get("line_goal", 0)
        goal_str = str(goal) if goal else "ENDLESS"

        labels = [
            ("SCORE", str(score), (180, 180, 200), (255, 255, 255)),
            ("LEVEL", str(level), (180, 180, 200), (255, 255, 255)),
            ("LINES", f"{lines}/{goal_str}", (180, 180, 200), (255, 255, 255)),
            ("DIFFICULTY", diff_name, (180, 180, 200), (255, 255, 255)),
        ]
        for i, (label, val, lbl_color, val_color) in enumerate(labels):
            y = 70 + i * 38
            lbl = self.small_font.render(label, True, lbl_color)
            self.screen.blit(lbl, (x, y))
            vtxt = self.stats_font.render(val, True, val_color)
            self.screen.blit(vtxt, (x, y + 18))

        sep_y2 = 230
        pygame.draw.line(self.screen, (40, 38, 60), (x - 4, sep_y2), (sx + SIDEBAR - 16, sep_y2))

        nxt_lbl = self.small_font.render("NEXT", True, (180, 180, 200))
        self.screen.blit(nxt_lbl, (x, 243))

        shape = SHAPES[next_piece.shape][0]
        color = next_piece.color
        preview_x = x + 20
        preview_y = 270

        preview_bg = pygame.Rect(preview_x - 8, preview_y - 8, 100, 80)
        pygame.draw.rect(self.screen, (18, 18, 30), preview_bg)
        pygame.draw.rect(self.screen, (40, 38, 60), preview_bg, 1)

        block_size = 22
        for dx, dy in shape:
            bx = preview_x + dx * block_size
            by = preview_y + dy * block_size
            self._draw_block_plain(bx, by, color, block_size)

        sep_y3 = 380
        pygame.draw.line(self.screen, (40, 38, 60), (x - 4, sep_y3), (sx + SIDEBAR - 16, sep_y3))

        ctrl_lbl = self.small_font.render("CONTROLS", True, (140, 140, 160))
        self.screen.blit(ctrl_lbl, (x, 392))

        binds = settings["keybinds"]

        def fmt_key(k):
            return key_name(pygame.key.key_code(k)) if k else "???"

        controls = [
            ("Move", fmt_key(binds['move_left']), fmt_key(binds['move_right'])),
            ("Rot Right", fmt_key(binds['rotate_right']), None),
            ("Rot Left", fmt_key(binds['rotate_left']), None),
            ("Rot 180", fmt_key(binds['rotate_180']), None),
            ("Soft", fmt_key(binds['soft_drop']), None),
            ("Hard", fmt_key(binds['hard_drop']), None),
            ("Pause", fmt_key(binds['pause']), None),
        ]
        y_off = 412
        for i, (label, key1, key2) in enumerate(controls):
            y = y_off + i * 17
            lbl = self.small_font.render(label, True, (120, 120, 140))
            self.screen.blit(lbl, (x, y))
            k1 = self.small_font.render(key1, True, (180, 190, 210))
            self.screen.blit(k1, (x + 50, y))
            if key2 is not None:
                k2 = self.small_font.render(key2, True, (180, 190, 210))
                self.screen.blit(k2, (x + 85, y))

    def draw_game_over(self, score):
        overlay = pygame.Surface((COLS * CELL, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        self.screen.blit(overlay, (0, 0))

        cx = COLS * CELL // 2

        box_w, box_h = 240, 160
        box_x = cx - box_w // 2
        box_y = HEIGHT // 2 - box_h // 2
        box_rect = pygame.Rect(box_x, box_y, box_w, box_h)
        pygame.draw.rect(self.screen, (20, 20, 35), box_rect)
        pygame.draw.rect(self.screen, (60, 58, 80), box_rect, 2)

        go_text = self.big_font.render("GAME OVER", True, (220, 220, 235))
        self.screen.blit(go_text, (cx - go_text.get_width() // 2, box_y + 20))

        sc_text = self.font.render(f"Score: {score}", True, (180, 180, 200))
        self.screen.blit(sc_text, (cx - sc_text.get_width() // 2, box_y + 65))

        re_text = self.small_font.render("Press R to restart", True, (120, 120, 140))
        self.screen.blit(re_text, (cx - re_text.get_width() // 2, box_y + 110))

    def draw_win(self, score):
        overlay = pygame.Surface((COLS * CELL, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        self.screen.blit(overlay, (0, 0))

        cx = COLS * CELL // 2

        box_w, box_h = 260, 170
        box_x = cx - box_w // 2
        box_y = HEIGHT // 2 - box_h // 2
        box_rect = pygame.Rect(box_x, box_y, box_w, box_h)
        pygame.draw.rect(self.screen, (20, 30, 35), box_rect)
        pygame.draw.rect(self.screen, (70, 110, 90), box_rect, 2)

        win_text = self.big_font.render("YOU WIN!", True, (140, 230, 160))
        self.screen.blit(win_text, (cx - win_text.get_width() // 2, box_y + 20))

        sc_text = self.font.render(f"Score: {score}", True, (180, 180, 200))
        self.screen.blit(sc_text, (cx - sc_text.get_width() // 2, box_y + 65))

        re_text = self.small_font.render("Press R to restart", True, (120, 120, 140))
        self.screen.blit(re_text, (cx - re_text.get_width() // 2, box_y + 115))

    def draw_pause(self, menu_selected):
        overlay = pygame.Surface((COLS * CELL, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        self.screen.blit(overlay, (0, 0))

        cx = COLS * CELL // 2
        items = ["Resume", "Settings", "Restart", "Quit"]

        box_w, box_h = 200, 180
        box_x = cx - box_w // 2
        box_y = HEIGHT // 2 - box_h // 2
        box_rect = pygame.Rect(box_x, box_y, box_w, box_h)
        pygame.draw.rect(self.screen, (20, 20, 35), box_rect)
        pygame.draw.rect(self.screen, (60, 58, 80), box_rect, 2)

        pt = self.font.render("PAUSED", True, (220, 220, 235))
        self.screen.blit(pt, (cx - pt.get_width() // 2, box_y + 12))

        for i, item in enumerate(items):
            y = box_y + 50 + i * 30
            if i == menu_selected:
                sel_rect = pygame.Rect(box_x + 15, y - 3, box_w - 30, 24)
                pygame.draw.rect(self.screen, (40, 40, 65), sel_rect)
                pygame.draw.rect(self.screen, (80, 80, 120), sel_rect, 1)
                color = (220, 220, 235)
            else:
                color = (140, 140, 160)
            txt = self.font.render(item, True, color)
            self.screen.blit(txt, (cx - txt.get_width() // 2, y))

    def draw_menu(self, menu_selected, settings):
        self.draw_full_bg()

        cx = WIDTH // 2
        title = self.title_font.render("T E T R I S", True, (230, 230, 245))
        self.screen.blit(title, (cx - title.get_width() // 2, 100))

        underline_y = 150
        uw = title.get_width() + 20
        pygame.draw.line(self.screen, (80, 80, 110),
                         (cx - uw // 2, underline_y), (cx + uw // 2, underline_y))

        diff_name = DIFFICULTY_NAMES.get(
            settings["options"].get("difficulty", "medium"), "MEDIUM")
        goal = settings["options"].get("line_goal", 0)
        goal_str = str(goal) if goal else "ENDLESS"
        d = settings["options"].get("das_delay", SPEED_DEFAULTS["das_delay"])
        r = settings["options"].get("das_repeat", SPEED_DEFAULTS["das_repeat"])
        s = settings["options"].get("soft_drop_ms", SPEED_DEFAULTS["soft_drop_ms"])
        speed_summary = f"{d}/{r}/{s}ms"

        menu_items = [
            "Play",
            f"Difficulty:  {diff_name}",
            f"Lines:  {goal_str}",
            f"Speeds:  {speed_summary}",
            "Settings",
            "Quit",
        ]
        for i, item in enumerate(menu_items):
            y = 175 + i * 35
            if i == menu_selected:
                sel_rect = pygame.Rect(cx - 140, y - 5, 280, 30)
                pygame.draw.rect(self.screen, (35, 35, 55), sel_rect)
                pygame.draw.rect(self.screen, (80, 80, 120), sel_rect, 1)
                color = (230, 230, 245)
            else:
                color = (150, 150, 170)
            txt = self.font.render(item, True, color)
            self.screen.blit(txt, (cx - txt.get_width() // 2, y))

        sub = self.small_font.render("Arrow Keys + Enter", True, (90, 90, 110))
        self.screen.blit(sub, (cx - sub.get_width() // 2, 410))

    def draw_difficulty_menu(self, selected, settings):
        self.draw_full_bg()
        cx = WIDTH // 2

        title = self.title_font.render("DIFFICULTY", True, (230, 230, 245))
        self.screen.blit(title, (cx - title.get_width() // 2, 120))

        pygame.draw.line(self.screen, (80, 80, 110),
                         (cx - 160, 170), (cx + 160, 170))

        hint = self.small_font.render("Left/Right to change  |  Enter to confirm  |  Esc to go back",
                                      True, (90, 90, 110))
        self.screen.blit(hint, (cx - hint.get_width() // 2, 200))

        current = settings["options"].get("difficulty", "medium")
        for i, diff in enumerate(DIFFICULTY_ORDER):
            y = 240 + i * 46
            if i == selected:
                sel_rect = pygame.Rect(cx - 100, y - 5, 200, 34)
                pygame.draw.rect(self.screen, (35, 35, 55), sel_rect)
                pygame.draw.rect(self.screen, (80, 80, 120), sel_rect, 1)
                color = (230, 230, 245)
            else:
                color = (150, 150, 170)
            name = DIFFICULTY_NAMES[diff]
            label = f"{name}  {'[X]' if diff == current else ''}"
            txt = self.font.render(label, True, color)
            self.screen.blit(txt, (cx - txt.get_width() // 2, y))

        sub = self.small_font.render(
            "Easy: slow  |  Medium: normal  |  Hard: fast",
            True, (90, 90, 110))
        self.screen.blit(sub, (cx - sub.get_width() // 2, 400))

    def draw_lines_menu(self, selected, settings):
        self.draw_full_bg()
        cx = WIDTH // 2

        title = self.title_font.render("LINES TO CLEAR", True, (230, 230, 245))
        self.screen.blit(title, (cx - title.get_width() // 2, 120))

        pygame.draw.line(self.screen, (80, 80, 110),
                         (cx - 160, 170), (cx + 160, 170))

        hint = self.small_font.render("Left/Right to change  |  Enter to confirm  |  Esc to go back",
                                      True, (90, 90, 110))
        self.screen.blit(hint, (cx - hint.get_width() // 2, 200))

        current = settings["options"].get("line_goal", 0)
        goal_labels = ["10 LINES", "20 LINES", "40 LINES", "ENDLESS"]
        for i, goal in enumerate(LINE_GOALS):
            y = 240 + i * 46
            if i == selected:
                sel_rect = pygame.Rect(cx - 100, y - 5, 200, 34)
                pygame.draw.rect(self.screen, (35, 35, 55), sel_rect)
                pygame.draw.rect(self.screen, (80, 80, 120), sel_rect, 1)
                color = (230, 230, 245)
            else:
                color = (150, 150, 170)
            label = f"{goal_labels[i]}  {'[X]' if current == LINE_GOALS[i] else ''}"
            txt = self.font.render(label, True, color)
            self.screen.blit(txt, (cx - txt.get_width() // 2, y))

        sub = self.small_font.render(
            "Clear the target number of lines to win!",
            True, (90, 90, 110))
        self.screen.blit(sub, (cx - sub.get_width() // 2, 400))

    def draw_speeds_menu(self, selected, settings):
        self.draw_full_bg()
        cx = WIDTH // 2

        title = self.title_font.render("MOVEMENT SPEED", True, (230, 230, 245))
        self.screen.blit(title, (cx - title.get_width() // 2, 40))

        pygame.draw.line(self.screen, (80, 80, 110),
                         (cx - 160, 90), (cx + 160, 90))

        hint = self.small_font.render("Up/Down: select row   Left/Right: adjust   Esc: back",
                                      True, (90, 90, 110))
        self.screen.blit(hint, (cx - hint.get_width() // 2, 105))

        bar_x = 140
        bar_w = 260
        row_y = 140
        row_h = 80
        for i, key in enumerate(SPEED_KEYS):
            y = row_y + i * row_h
            value = settings["options"].get(key, SPEED_DEFAULTS[key])
            lo = SPEED_MIN[key]
            hi = SPEED_MAX[key]
            frac = max(0.0, min(1.0, (value - lo) / (hi - lo)))

            is_sel = (i == selected)

            lbl_color = (230, 230, 235) if is_sel else (150, 150, 170)
            lbl = self.font.render(SPEED_LABELS[key], True, lbl_color)
            self.screen.blit(lbl, (40, y))

            unit = SPEED_UNITS[key]
            val = self.font.render(f"{value} {unit}", True, (235, 235, 245))
            self.screen.blit(val, (bar_x + bar_w - val.get_width(), y))

            track_y = y + 34
            track = pygame.Rect(bar_x, track_y, bar_w, 14)
            pygame.draw.rect(self.screen, (22, 22, 38), track)
            pygame.draw.rect(self.screen, (70, 70, 100), track, 1)
            if is_sel:
                pygame.draw.rect(self.screen, (90, 110, 170), track, 2)

            fill_w = int(bar_w * frac)
            if fill_w > 0:
                fill = pygame.Rect(bar_x, track_y, fill_w, 14)
                pygame.draw.rect(self.screen, (90, 160, 255), fill)

            knob_x = bar_x + int(bar_w * frac)
            pygame.draw.rect(self.screen, (240, 245, 255),
                             (knob_x - 4, track_y - 3, 8, 20))
            pygame.draw.rect(self.screen, (120, 130, 160),
                             (knob_x - 4, track_y - 3, 8, 20), 1)

            min_lbl = self.small_font.render(str(lo), True, (90, 90, 110))
            max_lbl = self.small_font.render(str(hi), True, (90, 90, 110))
            self.screen.blit(min_lbl, (bar_x, track_y + 20))
            self.screen.blit(max_lbl, (bar_x + bar_w - max_lbl.get_width(), track_y + 20))

        info = self.small_font.render("Lower = faster   Higher = slower",
                                      True, (90, 90, 110))
        self.screen.blit(info, (cx - info.get_width() // 2, 400))

        reset_txt = self.small_font.render("Press C to reset to defaults",
                                           True, (90, 90, 110))
        self.screen.blit(reset_txt, (cx - reset_txt.get_width() // 2, 420))

    def draw_settings(self, settings_selected, settings, rebinding, rebinding_action):
        self.draw_full_bg()
        cx = WIDTH // 2

        title = self.title_font.render("SETTINGS", True, (230, 230, 245))
        self.screen.blit(title, (cx - title.get_width() // 2, 15))

        pygame.draw.line(self.screen, (50, 48, 70), (50, 60), (WIDTH - 50, 60))

        if rebinding:
            prompt = self.small_font.render("Press any key to bind...", True, (200, 180, 140))
            self.screen.blit(prompt, (cx - prompt.get_width() // 2, 70))
        else:
            hint = self.small_font.render("Up/Down to select  |  Enter to rebind  |  Esc to go back", True, (90, 90, 110))
            self.screen.blit(hint, (cx - hint.get_width() // 2, 70))

        binds = settings["keybinds"]
        actions = list(ACTION_LABELS.keys())
        for i, action in enumerate(actions):
            y = 95 + i * 48
            label = ACTION_LABELS[action]
            key_const = pygame.key.key_code(binds[action]) if binds[action] else 0
            key_display = key_name(key_const) if key_const else "???"

            is_selected = (i == settings_selected)
            is_rebinding_now = rebinding and rebinding_action == action

            row_rect = pygame.Rect(50, y - 2, WIDTH - 100, 38)
            if is_rebinding_now:
                pygame.draw.rect(self.screen, (40, 30, 30), row_rect)
                pygame.draw.rect(self.screen, (140, 80, 80), row_rect, 1)
                lbl_color = (200, 140, 140)
                key_color = (220, 120, 120)
                key_txt = self.font.render("Press any key...", True, key_color)
            elif is_selected:
                pygame.draw.rect(self.screen, (30, 30, 50), row_rect)
                pygame.draw.rect(self.screen, (80, 80, 120), row_rect, 1)
                lbl_color = (220, 220, 235)
                key_color = (180, 190, 210)
                key_txt = self.font.render(f"[ {key_display} ]", True, key_color)
            else:
                lbl_color = (150, 150, 170)
                key_color = (110, 110, 130)
                key_txt = self.font.render(f"[ {key_display} ]", True, key_color)

            lbl = self.font.render(label, True, lbl_color)
            self.screen.blit(lbl, (70, y + 6))
            self.screen.blit(key_txt, (WIDTH - 210, y + 6))

        pygame.draw.line(self.screen, (50, 48, 70), (50, HEIGHT - 50), (WIDTH - 50, HEIGHT - 50))
        reset_txt = self.small_font.render("Press D to reset to default", True, (90, 90, 110))
        self.screen.blit(reset_txt, (cx - reset_txt.get_width() // 2, HEIGHT - 38))

    def draw_line_effects(self):
        for effect in self.line_effects:
            effect.draw(self.screen, self.particles)

    def update_line_effects(self):
        self.line_effects = [e for e in self.line_effects if not e.update()]

    def draw_all(self, game_state):
        self.frame += 1
        state = game_state["state"]

        if state == "menu":
            self.draw_menu(game_state["menu_selected"], game_state["settings"])
        elif state == "difficulty":
            self.draw_difficulty_menu(game_state["diff_selected"], game_state["settings"])
        elif state == "lines":
            self.draw_lines_menu(game_state["lines_selected"], game_state["settings"])
        elif state == "speeds":
            self.draw_speeds_menu(game_state["speed_selected"], game_state["settings"])
        elif state == "settings":
            self.draw_settings(
                game_state["settings_selected"],
                game_state["settings"],
                game_state["rebinding"],
                game_state["rebinding_action"],
            )
        elif state == "game":
            self.draw_game_bg()
            self.draw_grid()
            self.draw_board(game_state["board"])

            if not game_state["game_over"]:
                self.draw_ghost(game_state["current"], game_state["ghost_y"])
                self.draw_piece(game_state["current"])

            self.draw_line_effects()
            self.update_line_effects()

            self.update_particles()
            for p in self.particles:
                p.draw(self.screen)

            self.draw_sidebar(
                game_state["score"],
                game_state["level"],
                game_state["lines"],
                game_state["next_piece"],
                game_state["settings"],
            )

            if game_state["game_over"]:
                self.draw_game_over(game_state["score"])
            elif game_state["won"]:
                self.draw_win(game_state["score"])
            elif game_state["paused"]:
                self.draw_pause(game_state["menu_selected"])

        self.update_stars()
        pygame.display.flip()
