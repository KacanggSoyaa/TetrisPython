import pygame
import math
import random
import time
from constants import (
    CELL, COLS, ROWS, SIDEBAR, WIDTH, HEIGHT, FPS,
    BLACK, WHITE, GRAY, DARK_GRAY, DARKER_GRAY, BORDER_COLOR, HIGHLIGHT, DIM,
    BG_TOP, BG_BOTTOM, ACCENT_CYAN, ACCENT_PINK, ACCENT_PURPLE, ACCENT_GOLD,
    COLORS, SHAPES, ACTION_LABELS, DEFAULT_KEYBINDS,
)
from constants import key_name


class Particle:
    def __init__(self, x, y, color, speed_x=None, speed_y=None, lifetime=None):
        self.x = x
        self.y = y
        self.color = color
        self.speed_x = speed_x if speed_x is not None else random.uniform(-3, 3)
        self.speed_y = speed_y if speed_y is not None else random.uniform(-5, -1)
        self.lifetime = lifetime if lifetime is not None else random.randint(20, 45)
        self.max_lifetime = self.lifetime
        self.size = random.randint(2, 5)

    def update(self):
        self.x += self.speed_x
        self.y += self.speed_y
        self.speed_y += 0.08
        self.lifetime -= 1
        self.size = max(1, int(self.size * (self.lifetime / self.max_lifetime)))

    def draw(self, screen):
        if self.lifetime > 0:
            alpha = int(255 * (self.lifetime / self.max_lifetime))
            color = tuple(min(255, c + int((255 - c) * 0.3)) for c in self.color)
            pygame.draw.circle(screen, color, (int(self.x), int(self.y)), self.size)


class LineClearEffect:
    def __init__(self, rows):
        self.rows = rows
        self.timer = 25
        self.max_timer = 25

    def draw(self, screen, particles):
        progress = 1.0 - (self.timer / self.max_timer)
        alpha = int(255 * (1.0 - progress))
        for row in self.rows:
            y = row * CELL
            flash_surf = pygame.Surface((COLS * CELL, CELL), pygame.SRCALPHA)
            flash_surf.fill((255, 255, 255, int(alpha * 0.6)))
            screen.blit(flash_surf, (0, y))

            if self.timer == self.max_timer:
                for _ in range(8):
                    px = random.randint(0, COLS * CELL)
                    particles.append(Particle(px, y + CELL // 2, ACCENT_CYAN,
                                              speed_y=random.uniform(-6, -2),
                                              lifetime=random.randint(25, 50)))

    def update(self):
        self.timer -= 1
        return self.timer <= 0


class Renderer:
    def __init__(self):
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Tetris")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("consolas", 22, bold=True)
        self.small_font = pygame.font.SysFont("consolas", 16)
        self.big_font = pygame.font.SysFont("consolas", 36, bold=True)
        self.title_font = pygame.font.SysFont("consolas", 48, bold=True)
        self.particles = []
        self.line_effects = []
        self.block_cache = {}
        self.frame = 0
        self._build_block_surfaces()

    def _build_block_surfaces(self):
        for name, color in COLORS.items():
            self.block_cache[name] = self._make_block_surface(color, CELL)

    def _make_block_surface(self, color, size):
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        surf.fill(color)
        lighter = tuple(min(c + 60, 255) for c in color)
        darker = tuple(max(c - 60, 0) for c in color)
        darkest = tuple(max(c - 90, 0) for c in color)
        inner = pygame.Rect(2, 2, size - 4, size - 4)
        highlight_rect = pygame.Rect(2, 2, size - 4, size // 3)
        highlight_surf = pygame.Surface((size - 4, size // 3), pygame.SRCALPHA)
        highlight_surf.fill((*lighter, 80))
        surf.blit(highlight_surf, (2, 2))
        pygame.draw.rect(surf, lighter, pygame.Rect(0, 0, size, 2))
        pygame.draw.rect(surf, lighter, pygame.Rect(0, 0, 2, size))
        pygame.draw.rect(surf, darker, pygame.Rect(0, size - 2, size, 2))
        pygame.draw.rect(surf, darker, pygame.Rect(size - 2, 0, 2, size))
        pygame.draw.rect(surf, darkest, pygame.Rect(size - 2, size - 2, 2, 2))
        pygame.draw.rect(surf, darkest, pygame.Rect(0, size - 2, 2, 2))
        return surf

    def _draw_block_at(self, x, y, color, offset_x=0):
        rect = pygame.Rect(offset_x + x * CELL, y * CELL, CELL, CELL)
        self.screen.fill(color, rect)
        lighter = tuple(min(c + 60, 255) for c in color)
        darker = tuple(max(c - 60, 0) for c in color)
        darkest = tuple(max(c - 90, 0) for c in color)
        highlight_surf = pygame.Surface((CELL - 4, CELL // 3), pygame.SRCALPHA)
        highlight_surf.fill((*lighter, 70))
        self.screen.blit(highlight_surf, (rect.x + 2, rect.y + 2))
        pygame.draw.line(self.screen, lighter, rect.topleft, rect.topright, 2)
        pygame.draw.line(self.screen, lighter, rect.topleft, rect.bottomleft, 2)
        pygame.draw.line(self.screen, darker, rect.bottomleft, rect.bottomright, 2)
        pygame.draw.line(self.screen, darker, rect.topright, rect.bottomright, 2)
        pygame.draw.line(self.screen, darkest, rect.bottomleft, rect.bottomleft, 1)
        pygame.draw.line(self.screen, darkest, rect.bottomright, rect.bottomright, 1)
        inner = pygame.Rect(rect.x + 4, rect.y + 4, CELL - 8, CELL - 8)
        glow_surf = pygame.Surface((CELL - 8, CELL - 8), pygame.SRCALPHA)
        glow_surf.fill((*lighter, 30))
        self.screen.blit(glow_surf, inner.topleft)

    def _draw_neon_line(self, start, end, color, width=2, glow=6):
        glow_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        for i in range(glow, 0, -1):
            alpha = int(30 * (1 - i / glow))
            pygame.draw.line(glow_surf, (*color, alpha), start, end, width + i * 2)
        self.screen.blit(glow_surf, (0, 0))
        pygame.draw.line(self.screen, color, start, end, width)

    def _draw_glow_rect(self, rect, color, alpha=40, radius=8):
        glow_surf = pygame.Surface((rect.w + 16, rect.h + 16), pygame.SRCALPHA)
        for i in range(8, 0, -1):
            a = int(alpha * (1 - i / 8))
            r = pygame.Rect(8 - i, 8 - i, rect.w + i * 2, rect.h + i * 2)
            pygame.draw.rect(glow_surf, (*color, a), r, border_radius=radius + i)
        self.screen.blit(glow_surf, (rect.x - 8, rect.y - 8))
        pygame.draw.rect(self.screen, color, rect, border_radius=radius)

    def add_line_clear_particles(self, rows):
        for row in rows:
            for _ in range(20):
                px = random.randint(0, COLS * CELL)
                py = row * CELL + CELL // 2
                color = random.choice([ACCENT_CYAN, ACCENT_PINK, ACCENT_PURPLE, ACCENT_GOLD, WHITE])
                self.particles.append(Particle(px, py, color))

    def add_hard_drop_particles(self, piece):
        for dx, dy in SHAPES[piece.shape][piece.rotation]:
            x = piece.x + dx
            y = piece.y + dy
            if y >= 0:
                for _ in range(4):
                    px = x * CELL + random.randint(0, CELL)
                    py = (y + 1) * CELL
                    self.particles.append(Particle(px, py, piece.color,
                                                   speed_y=random.uniform(-4, -1),
                                                   speed_x=random.uniform(-2, 2),
                                                   lifetime=random.randint(15, 30)))

    def update_particles(self):
        self.particles = [p for p in self.particles if p.lifetime > 0]
        for p in self.particles:
            p.update()

    def draw_particles(self):
        for p in self.particles:
            p.draw(self.screen)

    def draw_gradient_bg(self):
        for y in range(HEIGHT):
            t = y / HEIGHT
            r = int(BG_TOP[0] + (BG_BOTTOM[0] - BG_TOP[0]) * t)
            g = int(BG_TOP[1] + (BG_BOTTOM[1] - BG_TOP[1]) * t)
            b = int(BG_TOP[2] + (BG_BOTTOM[2] - BG_TOP[2]) * t)
            pygame.draw.line(self.screen, (r, g, b), (0, y), (WIDTH, y))

    def draw_game_bg(self):
        for y in range(HEIGHT):
            t = y / HEIGHT
            r = int(BG_TOP[0] + (BG_BOTTOM[0] - BG_TOP[0]) * t)
            g = int(BG_TOP[1] + (BG_BOTTOM[1] - BG_TOP[1]) * t)
            b = int(BG_TOP[2] + (BG_BOTTOM[2] - BG_TOP[2]) * t)
            pygame.draw.line(self.screen, (r, g, b), (0, y), (COLS * CELL, y))
        sidebar_x = COLS * CELL
        for y in range(HEIGHT):
            t = y / HEIGHT
            sr = int(20 + 10 * t)
            sg = int(15 + 10 * t)
            sb = int(35 + 15 * t)
            pygame.draw.line(self.screen, (sr, sg, sb), (sidebar_x, y), (WIDTH, y))

    def draw_grid(self):
        grid_surf = pygame.Surface((COLS * CELL, ROWS * CELL), pygame.SRCALPHA)
        for y in range(ROWS):
            for x in range(COLS):
                rect = pygame.Rect(x * CELL, y * CELL, CELL, CELL)
                pygame.draw.rect(grid_surf, (40, 40, 60, 30), rect, 1)
        self.screen.blit(grid_surf, (0, 0))

    def draw_board(self, board):
        for y in range(ROWS):
            for x in range(COLS):
                if board.grid[y][x]:
                    self._draw_block_at(x, y, board.grid[y][x])

    def draw_piece(self, piece):
        for x, y in piece.cells():
            if y >= 0:
                self._draw_block_at(x, y, piece.color)

    def draw_ghost(self, piece, ghost_y):
        ghost_color = tuple(c // 3 for c in piece.color)
        ghost_color_alpha = (*ghost_color, 100)
        for dx, dy in SHAPES[piece.shape][piece.rotation]:
            x, y = piece.x + dx, ghost_y + dy
            if y >= 0:
                rect = pygame.Rect(x * CELL, y * CELL, CELL, CELL)
                ghost_surf = pygame.Surface((CELL, CELL), pygame.SRCALPHA)
                pygame.draw.rect(ghost_surf, ghost_color_alpha, ghost_surf.get_rect(), border_radius=3)
                pygame.draw.rect(ghost_surf, (*piece.color, 60), ghost_surf.get_rect(), 2, border_radius=3)
                self.screen.blit(ghost_surf, rect.topleft)

    def draw_sidebar(self, score, level, lines, next_piece, settings):
        sx = COLS * CELL
        panel_rect = pygame.Rect(sx, 0, SIDEBAR, HEIGHT)
        self.screen.fill((15, 12, 28), panel_rect)
        self._draw_neon_line((sx, 0), (sx, HEIGHT), ACCENT_PURPLE, width=2, glow=8)
        x = sx + 15
        title = self.title_font.render("TETRIS", True, ACCENT_CYAN)
        self.screen.blit(title, (x + 10, 15))
        glow_surf = pygame.Surface((title.get_width() + 20, title.get_height() + 10), pygame.SRCALPHA)
        glow_surf.fill((*ACCENT_CYAN, 15))
        self.screen.blit(glow_surf, (x + 5, 12))

        self._draw_neon_line((x, 70), (sx + SIDEBAR - 15, 70), ACCENT_PURPLE, width=1, glow=4)

        labels = [("SCORE", score, ACCENT_GOLD), ("LEVEL", level, ACCENT_PINK), ("LINES", lines, ACCENT_CYAN)]
        for i, (label, val, accent) in enumerate(labels):
            y = 85 + i * 55
            lbl = self.small_font.render(label, True, accent)
            self.screen.blit(lbl, (x, y))
            val_surf = self.big_font.render(str(val), True, WHITE)
            self.screen.blit(val_surf, (x, y + 18))
            self._draw_neon_line((x, y + 58), (x + 130, y + 58), (*accent,), width=1, glow=3)

        self._draw_neon_line((x, 255), (sx + SIDEBAR - 15, 255), ACCENT_PURPLE, width=1, glow=4)

        nxt = self.small_font.render("NEXT", True, ACCENT_CYAN)
        self.screen.blit(nxt, (x, 270))
        shape = SHAPES[next_piece.shape][0]
        color = next_piece.color
        preview_x = x + 25
        preview_y = 300
        preview_bg = pygame.Rect(preview_x - 10, preview_y - 10, 110, 90)
        self._draw_glow_rect(preview_bg, ACCENT_PURPLE, alpha=20, radius=8)
        for dx, dy in shape:
            bx = preview_x + dx * 25
            by = preview_y + dy * 25
            block_surf = self._make_block_surface(color, 23)
            self.screen.blit(block_surf, (bx, by))

        self._draw_neon_line((x, 410), (sx + SIDEBAR - 15, 410), ACCENT_PURPLE, width=1, glow=4)

        ctrl_title = self.small_font.render("CONTROLS", True, ACCENT_PINK)
        self.screen.blit(ctrl_title, (x, 420))

        binds = settings["keybinds"]

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
        y_off = 440
        lbl_w = 55
        for i, (label, key1, key2) in enumerate(controls):
            y = y_off + i * 18
            lbl = self.small_font.render(label, True, (130, 130, 150))
            self.screen.blit(lbl, (x, y))
            k1 = self.small_font.render(key1, True, ACCENT_CYAN)
            self.screen.blit(k1, (x + lbl_w, y))
            if key2 is not None:
                k2 = self.small_font.render(key2, True, ACCENT_CYAN)
                self.screen.blit(k2, (x + lbl_w + 40, y))

    def draw_game_over(self, score):
        overlay = pygame.Surface((COLS * CELL, HEIGHT), pygame.SRCALPHA)
        for i in range(200):
            alpha = int(200 * (1 - i / 200))
            overlay.fill((0, 0, 0, max(0, min(255, alpha))))
        self.screen.blit(overlay, (0, 0))

        go_text = self.big_font.render("GAME OVER", True, ACCENT_PINK)
        sc_text = self.font.render(f"Score: {score}", True, WHITE)
        re_text = self.small_font.render("Press R to restart", True, DIM)

        glow_surf = pygame.Surface((go_text.get_width() + 40, go_text.get_height() + 20), pygame.SRCALPHA)
        glow_surf.fill((*ACCENT_PINK, 25))
        cx = COLS * CELL // 2
        self.screen.blit(glow_surf, (cx - go_text.get_width() // 2 - 20, HEIGHT // 2 - 50))
        self.screen.blit(go_text, (cx - go_text.get_width() // 2, HEIGHT // 2 - 40))
        self.screen.blit(sc_text, (cx - sc_text.get_width() // 2, HEIGHT // 2 + 5))
        self.screen.blit(re_text, (cx - re_text.get_width() // 2, HEIGHT // 2 + 40))

    def draw_pause(self, menu_selected):
        overlay = pygame.Surface((COLS * CELL, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        self.screen.blit(overlay, (0, 0))

        cx = COLS * CELL // 2
        items = ["Resume", "Settings", "Restart", "Quit"]
        pt = self.big_font.render("PAUSED", True, ACCENT_CYAN)
        self.screen.blit(pt, (cx - pt.get_width() // 2, HEIGHT // 2 - 70))

        for i, item in enumerate(items):
            if i == menu_selected:
                btn_rect = pygame.Rect(cx - 80, HEIGHT // 2 - 25 + i * 35 - 3, 160, 28)
                self._draw_glow_rect(btn_rect, ACCENT_CYAN, alpha=30, radius=6)
                color = ACCENT_CYAN
            else:
                color = (180, 180, 200)
            txt = self.font.render(item, True, color)
            self.screen.blit(txt, (cx - txt.get_width() // 2, HEIGHT // 2 - 22 + i * 35))

    def draw_menu(self, menu_selected):
        self.draw_gradient_bg()

        self.frame += 1
        cx = WIDTH // 2

        for i in range(5):
            px = (self.frame * (i + 1) * 3 + i * 170) % WIDTH
            py = (self.frame * (i + 1) * 2 + i * 90) % HEIGHT
            size = 2 + (i % 3)
            colors = [ACCENT_CYAN, ACCENT_PINK, ACCENT_PURPLE, ACCENT_GOLD]
            alpha = 40 + (i * 10)
            dot_surf = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
            pygame.draw.circle(dot_surf, (*colors[i % len(colors)], alpha), (size, size), size)
            self.screen.blit(dot_surf, (px, py))

        title_text = "T E T R I S"
        title = self.title_font.render(title_text, True, WHITE)
        glow_surf = pygame.Surface((title.get_width() + 40, title.get_height() + 20), pygame.SRCALPHA)
        glow_alpha = int(60 + 30 * math.sin(self.frame * 0.05))
        glow_surf.fill((*ACCENT_CYAN, glow_alpha))
        self.screen.blit(glow_surf, (cx - title.get_width() // 2 - 20, 105))
        self.screen.blit(title, (cx - title.get_width() // 2, 110))

        underline_w = title.get_width() + 40
        self._draw_neon_line((cx - underline_w // 2, 170), (cx + underline_w // 2, 170),
                             ACCENT_CYAN, width=2, glow=6)

        menu_items = ["Play", "Settings", "Quit"]
        for i, item in enumerate(menu_items):
            y = 210 + i * 55
            if i == menu_selected:
                btn_rect = pygame.Rect(cx - 90, y - 8, 180, 38)
                self._draw_glow_rect(btn_rect, ACCENT_CYAN, alpha=30, radius=8)
                color = ACCENT_CYAN
            else:
                color = (180, 180, 200)
            txt = self.font.render(item, True, color)
            self.screen.blit(txt, (cx - txt.get_width() // 2, y))

        sub = self.small_font.render("Arrow Keys + Enter", True, DIM)
        self.screen.blit(sub, (cx - sub.get_width() // 2, 410))

        version = self.small_font.render("v1.0", True, (50, 50, 70))
        self.screen.blit(version, (WIDTH - 50, HEIGHT - 25))

    def draw_settings(self, settings_selected, settings, rebinding, rebinding_action):
        self.draw_gradient_bg()
        cx = WIDTH // 2

        title = self.title_font.render("SETTINGS", True, ACCENT_CYAN)
        self.screen.blit(title, (cx - title.get_width() // 2, 15))
        self._draw_neon_line((cx - 100, 65), (cx + 100, 65), ACCENT_PURPLE, width=2, glow=5)

        if rebinding:
            prompt = self.font.render("Press any key...", True, ACCENT_PINK)
            self.screen.blit(prompt, (cx - prompt.get_width() // 2, 75))

        sub = self.small_font.render("Up/Down to select, Enter to rebind, Esc to go back", True, DIM)
        self.screen.blit(sub, (cx - sub.get_width() // 2, rebinding and 100 or 75))

        binds = settings["keybinds"]
        actions = list(ACTION_LABELS.keys())
        for i, action in enumerate(actions):
            y = 115 + i * 50
            label = ACTION_LABELS[action]
            key_const = pygame.key.key_code(binds[action]) if binds[action] else 0
            key_display = key_name(key_const) if key_const else "???"

            is_selected = (i == settings_selected)
            is_rebinding_now = rebinding and rebinding_action == action

            if is_rebinding_now:
                btn_rect = pygame.Rect(60, y - 5, WIDTH - 120, 40)
                self._draw_glow_rect(btn_rect, ACCENT_PINK, alpha=40, radius=6)
                lbl_color = ACCENT_PINK
                key_color = (255, 100, 100)
                key_txt = self.font.render("Press any key...", True, key_color)
            elif is_selected:
                btn_rect = pygame.Rect(60, y - 5, WIDTH - 120, 40)
                self._draw_glow_rect(btn_rect, ACCENT_CYAN, alpha=25, radius=6)
                lbl_color = ACCENT_CYAN
                key_color = ACCENT_CYAN
                key_txt = self.font.render(f"[ {key_display} ]", True, key_color)
            else:
                lbl_color = (180, 180, 200)
                key_color = (130, 130, 150)
                key_txt = self.font.render(f"[ {key_display} ]", True, key_color)

            lbl = self.font.render(label, True, lbl_color)
            self.screen.blit(lbl, (80, y + 2))
            self.screen.blit(key_txt, (WIDTH - 210, y + 2))

        self._draw_neon_line((50, HEIGHT - 55), (WIDTH - 50, HEIGHT - 55), ACCENT_PURPLE, width=1, glow=4)

        reset_txt = self.small_font.render("Press D to reset all to default", True, DIM)
        self.screen.blit(reset_txt, (cx - reset_txt.get_width() // 2, HEIGHT - 40))

    def draw_line_effects(self):
        for effect in self.line_effects:
            effect.draw(self.screen, self.particles)

    def update_line_effects(self):
        self.line_effects = [e for e in self.line_effects if not e.update()]

    def draw_all(self, game_state):
        self.frame += 1
        state = game_state["state"]

        if state == "menu":
            self.draw_menu(game_state["menu_selected"])
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
            self.draw_particles()
            self.update_particles()

            self.draw_sidebar(
                game_state["score"],
                game_state["level"],
                game_state["lines"],
                game_state["next_piece"],
                game_state["settings"],
            )

            if game_state["game_over"]:
                self.draw_game_over(game_state["score"])
            elif game_state["paused"]:
                self.draw_pause(game_state["menu_selected"])

        pygame.display.flip()
