# All drawing. The renderer never mutates the game.
#
# `Tetris.get_game_state()` produces a read-only snapshot each frame, and this
# module turns it into pixels. It is organised bottom-up:
#
# * small colour and font helpers, and the animated background objects
#   (`Star`, `ShootingStar`, `Particle`, `Popup`)
# * `Renderer` primitives: cached text, panels, keycaps, blocks, previews
# * effects that respond to gameplay (particles, popups, shake)
# * the four screen groups: gameplay, sidebar, menus, overlays
import math
import random

import pygame

from constants import (
    CELL, COLS, ROWS, WELL_W, WELL_H, WELL_X, WELL_Y,
    WIDTH, HEIGHT, FPS, PREVIEW_COUNT,
    SIDE_X, SIDEBAR, SIDE_PAD, SIDE_INNER_X, SIDE_INNER_W,
    THEME, COLORS, SHAPES, CLEAR_FLASH_MS, CLEAR_GLOW_MS,
    DIFFICULTY_NAMES, DIFFICULTY_HINTS, DIFFICULTY_ORDER,
    LINE_GOALS, LINE_GOAL_LABELS, ACTION_LABELS, DEFAULT_KEYBINDS,
    SPEED_KEYS, SPEED_LABELS, SPEED_UNITS, SPEED_MIN, SPEED_MAX,
    SPEED_DEFAULTS, MENU_ITEMS, PAUSE_ITEMS, OVER_ITEMS, key_name,
)

# Font families in preference order; the first match wins, with Pygame's
# built-in default as the final fallback.
FONT_HEAD = ["segoeuiblack", "arialbd", "dejavusansbold",
             "liberationsansbold", "freesansbold", "arialblack"]
FONT_UI = ["segoeui", "arial", "dejavusans", "liberationsans", "freesans"]
FONT_MONO = ["consolas", "cascadiamono", "dejavusansmono",
             "liberationmono", "freesansmono", "couriernew"]

# Key names shortened to keep the sidebar keycaps narrow.
DISPLAY_ALIASES = (("LEFT ", "L "), ("RIGHT ", "R "), ("SHIFT", "SHIFT"))


# Blend a colour toward white by `amount` (0.0-1.0).
def lighten(color, amount):
    return tuple(min(255, int(c + (255 - c) * amount)) for c in color)


# Blend a colour toward black by `amount` (0.0-1.0).
def darken(color, amount):
    return tuple(max(0, int(c * (1 - amount))) for c in color)


# Shorten a key name for display, e.g. "LEFT SHIFT" -> "L SHIFT".
def pretty_key(name):
    for src, dst in DISPLAY_ALIASES:
        name = name.replace(src, dst)
    return name


# One twinkling background pixel, brightening and fading on its own cycle.
class Star:
    # Scatter a star at a random position with its own twinkle rate.
    def __init__(self, size):
        self.x = random.randint(0, size[0] - 1)
        self.y = random.randint(0, size[1] - 1)
        self.base = random.randint(50, 170)
        self.speed = random.uniform(0.008, 0.035)
        self.offset = random.uniform(0, math.tau)
        self.big = random.random() < 0.12

    # Draw the star at its current brightness for this frame. Roughly one
    # star in eight is drawn as a dot so the sky has some texture.
    def draw(self, surface, frame):
        value = self.base + int(45 * math.sin(frame * self.speed + self.offset))
        value = max(25, min(215, value))
        color = (value, value, min(255, value + 24))
        if self.big:
            pygame.draw.circle(surface, color, (self.x, self.y), 1)
        else:
            surface.set_at((self.x, self.y), color)


# A rare meteoric streak that crosses the sky and fades out.
class ShootingStar:
    # Start a streak somewhere above the horizon.
    def __init__(self, size):
        self.reset(size)

    # Pick a fresh start position, trajectory, and lifetime.
    def reset(self, size):
        self.x = random.randint(-40, size[0])
        self.y = random.randint(-20, size[1] // 3)
        angle = random.uniform(0.35, 0.85)
        speed = random.uniform(7, 12)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.life = self.max_life = random.randint(22, 40)
        self.tail = random.randint(4, 7)
        self.trail = []

    # Advance one frame, extending the fading tail behind the head.
    def update(self):
        self.trail.append((self.x, self.y))
        if len(self.trail) > self.tail:
            self.trail.pop(0)
        self.x += self.vx
        self.y += self.vy
        self.life -= 1

    # Draw the tail brightest at the head, plus a white head early on.
    def draw(self, surface):
        fade = self.life / max(1, self.max_life)
        for i, (tx, ty) in enumerate(self.trail):
            t = (i + 1) / len(self.trail)
            value = int(190 * t * fade)
            if value <= 6:
                continue
            pygame.draw.circle(surface, (value, value, min(255, value + 26)),
                               (int(tx), int(ty)), max(1, int(t * 1.6)))
        if self.life > self.max_life // 2:
            pygame.draw.circle(surface, (255, 255, 255), (int(self.x), int(self.y)), 1)


# A short-lived square of debris thrown up by drops and line clears.
class Particle:
    # Place a particle, randomising velocity and lifetime unless given.
    def __init__(self, x, y, color, vx=None, vy=None, life=None, gravity=0.07):
        self.x = x
        self.y = y
        self.color = color
        self.vx = random.uniform(-1.6, 1.6) if vx is None else vx
        self.vy = random.uniform(-3.4, -0.6) if vy is None else vy
        self.life = self.max_life = random.randint(14, 28) if life is None else life
        self.gravity = gravity
        self.size = random.choice([1, 1, 2, 2, 3])

    # Move one frame under gravity and age the particle.
    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += self.gravity
        self.life -= 1

    # Draw the particle, fading and shrinking toward its end of life.
    def draw(self, surface):
        t = self.life / self.max_life
        color = (int(self.color[0] * t), int(self.color[1] * t), int(self.color[2] * t))
        radius = max(1, int(self.size * t))
        surface.fill(color, (int(self.x) - radius // 2, int(self.y) - radius // 2, radius, radius))


# A scoring label ("TETRIS!", "COMBO x3") that rises and fades.
class Popup:
    # Queue a label; big popups stay on screen slightly longer.
    def __init__(self, text, color, big=False, y=0.0, drift=-0.9):
        self.text = text
        self.color = color
        self.big = big
        self.y = y
        self.drift = drift
        self.t = 0
        self.life = 78 if big else 64

    # Age the popup; returns False once it should be discarded.
    def update(self, dt):
        self.t += dt
        return self.t < self.life

    # Draw the label at its drifting position, fading out over time.
    def draw(self, surface, cx, cy, renderer):
        p = self.t / self.life
        if p >= 1:
            return
        alpha = int(255 * min(1.0, (1 - p) * 2.2))
        if alpha <= 4:
            return
        text = renderer.txt(self.text, "popup_big" if self.big else "popup", self.color)
        text = text.copy()
        text.set_alpha(alpha)
        y = cy + self.y + self.drift * self.t
        surface.blit(text, text.get_rect(center=(int(cx), int(y))))


# Owns the window, the font cache, the pre-rendered surfaces, and effects.
class Renderer:
    # Open the window and build every cache and static surface once, so
    # the per-frame work is only blits and small draws.
    def __init__(self):
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("TETRIS")
        self.clock = pygame.time.Clock()

        self.fonts = {
            "word": self._font(FONT_HEAD, 25, True),
            "h1": self._font(FONT_HEAD, 33, True),
            "h2": self._font(FONT_HEAD, 19, True),
            "body": self._font(FONT_UI, 17),
            "small": self._font(FONT_UI, 13),
            "tiny": self._font(FONT_UI, 12),
            "label": self._font(FONT_UI, 11, True),
            "num": self._font(FONT_HEAD, 28, True),
            "val": self._font(FONT_HEAD, 17, True),
            "val_sm": self._font(FONT_HEAD, 15, True),
            "key": self._font(FONT_MONO, 11, True),
            "popup": self._font(FONT_HEAD, 22, True),
            "popup_big": self._font(FONT_HEAD, 32, True),
        }
        self._text_cache = {}
        self._blocks = {}
        self._ghosts = {}

        self.well = pygame.Surface((WELL_W, WELL_H)).convert()
        self.well_grid = self._build_well_grid().convert()
        self.dim = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        self.dim.fill((3, 3, 9, 205))
        self.well_dim = pygame.Surface((WELL_W, WELL_H), pygame.SRCALPHA)
        self.well_dim.fill((3, 3, 9, 190))

        self.particles = []
        self.popups = []
        self.frame = 0
        self.shake_amount = 0
        self.stars = [Star((WIDTH, HEIGHT)) for _ in range(80)]
        self.shooting = []
        self._shoot_timer = 90
        self.bg = self._build_bg().convert()
        self._deco = self._build_deco().convert_alpha()

    # --------------------------------------------------------------- setup

    # Load the first available font from `names`, else Pygame's default.
    def _font(self, names, size, bold=False):
        path = pygame.font.match_font(names, bold=False) or \
            pygame.font.match_font(names, bold=True)
        font = pygame.font.Font(path, size) if path else pygame.font.Font(None, size)
        font.set_bold(bold)
        return font

    # Pre-render the window background: two vertical gradients split at
    # the sidebar edge, plus the seam line between them.
    def _build_bg(self):
        surface = pygame.Surface((WIDTH, HEIGHT))
        split = SIDE_X
        for y in range(HEIGHT):
            t = y / HEIGHT
            pygame.draw.line(surface, self._mix(THEME["bg_top"], THEME["bg_bottom"], t),
                             (0, y), (split, y))
            pygame.draw.line(surface, self._mix(THEME["side_top"], THEME["side_bottom"], t),
                             (split, y), (WIDTH, y))
        pygame.draw.line(surface, (34, 34, 56), (split, 0), (split, HEIGHT))
        return surface

    # Linear RGB blend between two colours; `t` of 0.0 gives `a`.
    @staticmethod
    def _mix(a, b, t):
        return (int(a[0] + (b[0] - a[0]) * t),
                int(a[1] + (b[1] - a[1]) * t),
                int(a[2] + (b[2] - a[2]) * t))

    # Pre-render the empty playfield: fill, cell grid lines, top edge.
    def _build_well_grid(self):
        surface = pygame.Surface((WELL_W, WELL_H))
        surface.fill(THEME["well"])
        for x in range(1, COLS):
            pygame.draw.line(surface, THEME["grid"], (x * CELL, 0), (x * CELL, WELL_H))
        for y in range(1, ROWS):
            pygame.draw.line(surface, THEME["grid"], (0, y * CELL), (WELL_W, y * CELL))
        pygame.draw.line(surface, THEME["well_edge"], (0, 1), (WELL_W, 1))
        return surface

    # Pre-render the faint row of all seven tetrominoes that sits along
    # the bottom of the menu background.
    def _build_deco(self):
        surface = pygame.Surface((WIDTH, 120), pygame.SRCALPHA)
        order = ["I", "O", "T", "S", "Z", "J", "L"]
        size = 22
        for i, shape in enumerate(order):
            color = (*COLORS[shape], 46)
            for dx, dy in SHAPES[shape][0]:
                rect = pygame.Rect(24 + i * 76 + dx * size, 12 + dy * size, size - 3, size - 3)
                pygame.draw.rect(surface, color, rect, border_radius=4)
        return surface

    # ----------------------------------------------------------- primitives

    # Render text to a cached surface, keyed by text, font, and colour.
    #
    # The cache is cleared wholesale past 4000 entries, which bounds memory
    # without needing an eviction policy.
    def txt(self, text, name, color=None):
        color = THEME["text"] if color is None else color
        key = (text, name, color)
        surface = self._text_cache.get(key)
        if surface is None:
            surface = self.fonts[name].render(str(text), True, color)
            if len(self._text_cache) > 4000:
                self._text_cache.clear()
            self._text_cache[key] = surface
        return surface

    # Blit cached text anchored top-left, centred, or top-right at (x, y).
    #
    # Returns the resulting rect, which the layout tests use to check that
    # labels do not overlap.
    def blit_t(self, text, x, y, name="body", color=None, center=False, right=False):
        surface = self.txt(text, name, color)
        if center:
            rect = surface.get_rect(center=(int(x), int(y)))
        elif right:
            rect = surface.get_rect(topright=(int(x), int(y)))
        else:
            rect = surface.get_rect(topleft=(int(x), int(y)))
        self.screen.blit(surface, rect)
        return rect

    # Draw a rounded panel with an optional translucent fill and border.
    #
    # `fill` and `border` accept either a THEME key or a literal colour.
    def panel(self, rect, fill="panel", alpha=232, border="border", radius=12, width=1):
        base = THEME.get(fill, fill)
        edge = THEME.get(border, border) if border else None
        if alpha >= 255:
            pygame.draw.rect(self.screen, base, rect, border_radius=radius)
        else:
            surface = pygame.Surface(rect.size, pygame.SRCALPHA)
            surface.fill((*base, alpha))
            self.screen.blit(surface, rect.topleft)
        if edge:
            pygame.draw.rect(self.screen, edge, rect, width, border_radius=radius)

    # Draw a small rounded keycap centred on (cx, cy) and return its rect.
    def keycap(self, text, cx, cy, color=None, bg="keycap", edge="keycap_hi"):
        surface = self.txt(pretty_key(text), "key", color or THEME["text_dim"])
        w = surface.get_width() + 14
        h = surface.get_height() + 6
        rect = pygame.Rect(int(cx - w / 2), int(cy - h / 2), w, h)
        pygame.draw.rect(self.screen, THEME[bg], rect, border_radius=4)
        pygame.draw.rect(self.screen, THEME[edge], rect, 1, border_radius=4)
        self.screen.blit(surface, surface.get_rect(center=rect.center))
        return rect

    # Return a cached bevelled block sprite: rounded body, lit top-left
    # edge, shaded bottom-right edge, and a soft top gloss.
    def block(self, color, size=CELL):
        key = (color, size)
        surface = self._blocks.get(key)
        if surface is not None:
            return surface
        surface = pygame.Surface((size, size), pygame.SRCALPHA)
        radius = max(2, size // 7)
        pygame.draw.rect(surface, color, (0, 0, size, size), border_radius=radius)
        hi = lighten(color, 0.42)
        lo = darken(color, 0.42)
        lw = max(1, size // 14)
        pad = max(2, size // 9)
        pygame.draw.line(surface, hi, (pad, pad), (size - pad, pad), lw)
        pygame.draw.line(surface, hi, (pad, pad), (pad, size - pad), lw)
        pygame.draw.line(surface, lo, (pad, size - pad), (size - pad, size - pad), lw)
        pygame.draw.line(surface, lo, (size - pad, pad), (size - pad, size - pad), lw)

        gloss = pygame.Surface((size, size), pygame.SRCALPHA)
        half = max(2, size // 2)
        for i in range(half):
            alpha = int(52 * (1 - i / half))
            pygame.draw.line(gloss, (255, 255, 255, alpha), (0, i), (size, i))
        mask = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.rect(mask, (255, 255, 255, 255), (0, 0, size, size), border_radius=radius)
        gloss.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        surface.blit(gloss, (0, 0))
        self._blocks[key] = surface
        return surface

    # Return a cached translucent outline sprite for the drop preview.
    def ghost(self, color, size=CELL):
        key = (color, size)
        surface = self._ghosts.get(key)
        if surface is not None:
            return surface
        surface = pygame.Surface((size, size), pygame.SRCALPHA)
        radius = max(2, size // 7)
        pygame.draw.rect(surface, (*color, 46), (0, 0, size, size), border_radius=radius)
        pygame.draw.rect(surface, (*lighten(color, 0.25), 130), (0, 0, size, size),
                         1, border_radius=radius)
        self._ghosts[key] = surface
        return surface

    # Blit a rotated tetromino onto `surface` at pixel offset (ox, oy).
    #
    # Cells above the top edge are skipped, so a piece spawning partly out of
    # view still draws correctly.
    def draw_shape(self, surface, shape, rotation, ox, oy, size, color, ghost=False):
        for dx, dy in SHAPES[shape][rotation]:
            x, y = ox + dx * size, oy + dy * size
            if y < 0:
                continue
            sprite = self.ghost(color, size) if ghost else self.block(color, size)
            surface.blit(sprite, (x, y))

    # Draw a tetromino centred inside `rect`, used by hold and next.
    #
    # Measures the spawn rotation's real bounds so every shape looks centred
    # even though they all live in a 4x4 box. `dim` renders a spent hold.
    def preview(self, shape, rect, size=16, dim=False):
        cells = SHAPES[shape][0]
        xs = [c[0] for c in cells]
        ys = [c[1] for c in cells]
        w = (max(xs) - min(xs) + 1) * size
        h = (max(ys) - min(ys) + 1) * size
        ox = rect.x + (rect.w - w) // 2 - min(xs) * size
        oy = rect.y + (rect.h - h) // 2 - min(ys) * size
        color = COLORS[shape]
        if dim:
            color = darken(color, 0.55)
        for dx, dy in cells:
            self.screen.blit(self.block(color, size), (ox + dx * size, oy + dy * size))

    # -------------------------------------------------------------- effects

    # Clear particles, popups, and shake; called when a run restarts.
    def reset_effects(self):
        self.particles.clear()
        self.popups.clear()
        self.shake_amount = 0

    # Request a screen shake; larger amounts win if one is already active
    # and it decays one frame at a time.
    def shake(self, amount):
        self.shake_amount = max(self.shake_amount, amount)

    # Queue a scoring label, keeping only the most recent six.
    def popup(self, text, color, big=False):
        self.popups.append(Popup(text, color, big))
        self.popups = self.popups[-6:]

    # Throw debris up from each cleared row; more lines means more of it,
    # and the shake scales with the clear size too.
    def burst(self, rows, count):
        palette = [COLORS["I"], COLORS["O"], THEME["text"], THEME["accent"]]
        for row in rows:
            for _ in range(10 + count * 3):
                self.particles.append(Particle(
                    random.uniform(0, WELL_W), row * CELL + CELL / 2,
                    random.choice(palette),
                    vy=random.uniform(-3.6, -0.8), life=random.randint(14, 26)))
        self.shake(2 + count)

    # Sprinkle a few bright particles along rows about to collapse.
    def add_line_clear_particles(self, rows):
        for row in rows:
            for _ in range(8):
                self.particles.append(Particle(
                    random.uniform(0, WELL_W), row * CELL + CELL / 2,
                    lighten(THEME["text"], 0.1)))

    # Kick up piece-coloured dust under each cell where the piece lands.
    def add_hard_drop_particles(self, piece, landing_y):
        for dx, dy in SHAPES[piece.shape][piece.rotation]:
            y = landing_y + dy
            if y < 0:
                continue
            for _ in range(3):
                self.particles.append(Particle(
                    (piece.x + dx) * CELL + random.uniform(0, CELL),
                    (y + 1) * CELL,
                    piece.color,
                    vy=random.uniform(-3.2, -0.5),
                    vx=random.uniform(-1.4, 1.4),
                    life=random.randint(10, 18)))

    # Advance particles, expire popups, and decay the shake each frame.
    def _update_fx(self, dt):
        for p in self.particles:
            p.update()
        self.particles = [p for p in self.particles if p.life > 0]
        kept = []
        for pop in self.popups:
            if pop.update(dt):
                kept.append(pop)
        self.popups = kept
        if self.shake_amount:
            self.shake_amount -= 1

    # Spawn the occasional shooting star and advance the live ones.
    def _update_sky(self):
        self._shoot_timer -= 1
        if self._shoot_timer <= 0 and len(self.shooting) < 2:
            self.shooting.append(ShootingStar((WIDTH, HEIGHT)))
            self._shoot_timer = random.randint(90, 220)
        for star in self.shooting:
            star.update()
        self.shooting = [s for s in self.shooting if s.life > 0]

    # Draw the stars, optionally clipped to `area` so the well is not
    # filled with sky pixels.
    def _draw_sky(self, area=None):
        ax, ay, aw, ah = area or (0, 0, WIDTH, HEIGHT)
        for star in self.stars:
            if ax <= star.x < ax + aw and ay <= star.y < ay + ah:
                star.draw(self.screen, self.frame)
        for star in self.shooting:
            if ax <= star.x < ax + aw and ay <= star.y < ay + ah:
                star.draw(self.screen)

    # ------------------------------------------------------------ gameplay

    # Draw the double border that frames the playfield.
    def draw_well_frame(self):
        outer = pygame.Rect(WELL_X - 5, WELL_Y - 5, WELL_W + 10, WELL_H + 10)
        pygame.draw.rect(self.screen, THEME["border"], outer, 1, border_radius=8)
        inner = pygame.Rect(WELL_X - 1, WELL_Y - 1, WELL_W + 2, WELL_H + 2)
        pygame.draw.rect(self.screen, THEME["well_edge"], inner, 1, border_radius=3)

    # Draw the two-phase line-clear effect onto the well.
    #
    # Phase one flashes the rows white with a brightening core; phase two
    # fades an accent bar over the rows the stack collapsed into.
    def draw_clear_anim(self, anim):
        t = anim["t"]
        if not anim["collapsed"]:
            p = min(1.0, t / CLEAR_FLASH_MS)
            alpha = int(210 * (1 - p))
            if alpha > 2:
                layer = pygame.Surface((WELL_W, WELL_H), pygame.SRCALPHA)
                for row in anim["rows"]:
                    rect = pygame.Rect(0, row * CELL, WELL_W, CELL)
                    layer.fill((255, 255, 255, alpha), rect)
                    core = int(6 * p) + 2
                    layer.fill((255, 255, 255, min(255, alpha + 40)),
                               pygame.Rect(0, row * CELL + CELL // 2 - core // 2,
                                           WELL_W, core))
                self.well.blit(layer, (0, 0))
            return

        p = min(1.0, (t - CLEAR_FLASH_MS) / CLEAR_GLOW_MS)
        if p >= 1:
            return
        alpha = int(150 * (1 - p))
        height = int(CELL * (0.3 + 1.9 * p))
        layer = pygame.Surface((WELL_W, WELL_H), pygame.SRCALPHA)
        for row in anim["landed"]:
            y = row * CELL + CELL // 2 - height // 2
            layer.fill((*lighten(THEME["accent"], 0.4), alpha),
                       pygame.Rect(0, y, WELL_W, height))
        self.well.blit(layer, (0, 0))

    # Draw the gameplay screen.
    #
    # The well is composited into an offscreen surface in a fixed order
    # (grid, stack, ghost, active piece, clear animation, particles) and then
    # blitted once, which keeps the cell-to-pixel mapping exact and makes the
    # screen shake a single blit offset.
    def draw_game(self, st, dt):
        self.screen.blit(self.bg, (0, 0))
        self._draw_sky((WELL_X, WELL_Y, WELL_W, WELL_H))
        self._update_fx(dt)

        well = self.well
        well.blit(self.well_grid, (0, 0))

        board = st["board"]
        for y in range(ROWS):
            for x in range(COLS):
                color = board.grid[y][x]
                if color:
                    well.blit(self.block(color), (x * CELL, y * CELL))

        piece = st["current"]
        if piece is not None and not st["game_over"] and not st["won"] and not st["clearing"]:
            ghost_y = st["ghost_y"]
            ox, oy = piece.x * CELL, piece.y * CELL
            if ghost_y is not None and ghost_y != piece.y:
                self.draw_shape(well, piece.shape, piece.rotation, ox, ghost_y * CELL,
                                CELL, piece.color, ghost=True)
            self.draw_shape(well, piece.shape, piece.rotation, ox, oy,
                            CELL, piece.color)

        if st["clear_anim"]:
            self.draw_clear_anim(st["clear_anim"])

        for p in self.particles:
            p.draw(well)

        offset = 0
        if self.shake_amount:
            offset = random.randint(-self.shake_amount, self.shake_amount)
        self.screen.blit(well, (WELL_X, WELL_Y + offset))
        self.draw_well_frame()

        if self.popups and not (st["game_over"] or st["won"] or st["paused"]):
            cx = WELL_X + WELL_W // 2
            base = WELL_Y + 190
            for i, pop in enumerate(self.popups):
                pop.y = i * 26
                pop.draw(self.screen, cx, base, self)

        self.draw_sidebar(st)

        if st["paused"] and not (st["game_over"] or st["won"]):
            self.draw_pause(st["menu_selected"])
        elif st["game_over"] or st["won"]:
            self.draw_over(st)


    # ------------------------------------------------------------- sidebar

    # Draw one left/right-aligned label and value pair inside a panel.
    def _stat_row(self, rect, label, value, y, value_font="val", value_color=None):
        self.blit_t(label, rect.x + SIDE_PAD, y, "label", THEME["text_faint"])
        self.blit_t(value, rect.right - SIDE_PAD, y, value_font,
                    value_color or THEME["text"], right=True)

    # Draw the right-hand column: wordmark, score, run summary, hold,
    # next queue, and the controls cheat-sheet.
    #
    # Panel rectangles are hard-coded and `tests/test_pixels.py` asserts the
    # gaps between them, so moving one panel means updating that test.
    def draw_sidebar(self, st):
        opts = st["settings"]["options"]
        binds = st["settings"]["keybinds"]

        # wordmark ---------------------------------------------------------
        self.draw_wordmark(SIDE_INNER_X, 16)
        diff = opts.get("difficulty", "medium")
        chip = self.txt(DIFFICULTY_NAMES.get(diff, "MEDIUM"), "label", THEME["accent"])
        chip_rect = pygame.Rect(SIDE_X + SIDEBAR - SIDE_PAD - chip.get_width() - 14, 18,
                                chip.get_width() + 14, 20)
        pygame.draw.rect(self.screen, (0, 208, 222, 30), chip_rect, border_radius=10)
        pygame.draw.rect(self.screen, THEME["accent_dim"], chip_rect, 1, border_radius=10)
        self.screen.blit(chip, chip.get_rect(center=chip_rect.center))

        # stats ------------------------------------------------------------
        rect = pygame.Rect(SIDE_X, 48, SIDEBAR, 130)
        self.panel(rect, "panel", 210, "border")
        self.blit_t("SCORE", rect.x + SIDE_PAD, rect.y + 6, "label", THEME["text_faint"])
        self.blit_t(f"{st['score']:,}", rect.x + SIDE_PAD, rect.y + 22, "num", THEME["text"])
        pygame.draw.line(self.screen, THEME["border"],
                         (rect.x + SIDE_PAD, rect.y + 62), (rect.right - SIDE_PAD, rect.y + 62))
        self._stat_row(rect, "LEVEL", st["level"], rect.y + 72)
        self._stat_row(rect, "LINES", f"{st['lines']}/{st['goal'] or '-'}", rect.y + 96)

        goal = st["goal"]
        bar = pygame.Rect(rect.x + SIDE_PAD, rect.y + 118, SIDE_INNER_W, 5)
        pygame.draw.rect(self.screen, THEME["well"], bar, border_radius=3)
        if goal:
            frac = min(1.0, st["lines"] / goal)
            if frac > 0:
                fill = bar.copy()
                fill.width = max(5, int(bar.w * frac))
                pygame.draw.rect(self.screen, THEME["accent"], fill, border_radius=3)

        # run summary ------------------------------------------------------
        rect = pygame.Rect(SIDE_X, 186, SIDEBAR, 58)
        self.panel(rect, "panel_soft", 210, "border")
        combo = max(st["combo"], 0)
        cell_w = SIDE_INNER_W // 2
        cells = [
            ("PIECES", st["pieces"], 0, 0, THEME["text"]),
            ("TETRIS", st["tetrises"], 1, 0,
             THEME["accent"] if st["tetrises"] else THEME["text"]),
            ("COMBO", f"x{combo}", 0, 1,
             THEME["accent"] if combo else THEME["text"]),
            ("TIME", self._clock(st["elapsed"]), 1, 1, THEME["text"]),
        ]
        for label, value, col, row, color in cells:
            x = SIDE_INNER_X + col * cell_w
            y = rect.y + 10 + row * 22
            self.blit_t(label, x, y + 5, "label", THEME["text_faint"])
            self.blit_t(value, x + cell_w, y, "val_sm", color, right=True)

        # hold -------------------------------------------------------------
        rect = pygame.Rect(SIDE_X, 252, SIDEBAR, 66)
        self.panel(rect, "panel", 210, "border")
        self.blit_t("HOLD", rect.x + SIDE_PAD, rect.y + 7, "label",
                    THEME["text"] if st["hold"] else THEME["text_faint"])
        box = pygame.Rect(rect.x + SIDE_PAD, rect.y + 23, SIDE_INNER_W, rect.h - 30)
        pygame.draw.rect(self.screen, THEME["well"], box, border_radius=8)
        if st["hold"]:
            self.preview(st["hold"], box, 16, dim=st["hold_used"])
        else:
            self.blit_t("EMPTY", box.centerx, box.centery, "small",
                        THEME["text_faint"], center=True)

        # next -------------------------------------------------------------
        rect = pygame.Rect(SIDE_X, 326, SIDEBAR, 66)
        self.panel(rect, "panel", 210, "border")
        self.blit_t("NEXT", rect.x + SIDE_PAD, rect.y + 7, "label", THEME["text_dim"])
        slot = (SIDE_INNER_W - 2 * 6) / 3
        for i in range(PREVIEW_COUNT):
            box = pygame.Rect(rect.x + SIDE_PAD + i * (slot + 6), rect.y + 23,
                              int(slot), rect.h - 30)
            pygame.draw.rect(self.screen, THEME["well"], box, border_radius=8)
            if i < len(st["queue"]):
                self.preview(st["queue"][i].shape, box, 14)

        # controls ---------------------------------------------------------
        rect = pygame.Rect(SIDE_X, 400, SIDEBAR, 208)
        self.panel(rect, "panel", 210, "border")
        self.blit_t("CONTROLS", rect.x + SIDE_PAD, rect.y + 8, "label", THEME["text_dim"])
        actions = list(ACTION_LABELS.keys())
        cell_w = SIDE_INNER_W / 2
        for i, action in enumerate(actions):
            cx = rect.x + SIDE_PAD + cell_w * (i % 2) + cell_w / 2
            y = rect.y + 32 + (i // 2) * 34
            key = binds.get(action, "")
            display = key_name(pygame.key.key_code(key)) if key else "---"
            self.blit_t(ACTION_LABELS[action], cx, y, "tiny", THEME["text_dim"],
                        center=True)
            self.keycap(display, cx, y + 22, color=THEME["text"])

    # Seconds as `M:SS` for the timer readouts.
    @staticmethod
    def _clock(seconds):
        return f"{seconds // 60}:{seconds % 60:02d}"

    # Draw the "TETRIS" wordmark letter by letter, with the accent bar
    # underneath, so the spacing stays even across systems.
    def draw_wordmark(self, x, y):
        font = self.fonts["word"]
        glyphs = [font.render(c, True, THEME["text"]) for c in "TETRIS"]
        spacing = 4
        total = sum(g.get_width() for g in glyphs) + spacing * (len(glyphs) - 1)
        cx = x
        for g in glyphs:
            self.screen.blit(g, (cx, y))
            cx += g.get_width() + spacing
        bar = pygame.Rect(x, y + font.get_height() + 3, total, 3)
        pygame.draw.rect(self.screen, THEME["accent_dim"], bar, border_radius=2)
        head = bar.copy()
        head.width = max(10, int(total * 0.42))
        pygame.draw.rect(self.screen, THEME["accent"], head, border_radius=2)

    # -------------------------------------------------------------- menus

    # Draw the animated menu background: gradient, stars, and optionally
    # the tetromino strip along the bottom.
    def _menu_bg(self, deco=True):
        self.screen.blit(self.bg, (0, 0))
        self._draw_sky()
        if deco:
            self.screen.blit(self._deco, (0, HEIGHT - self._deco.get_height()))

    # A menu row: label pinned to the left column, value pinned to the right
    # column, so labels and values line up across every row.
    #
    # The returned rect is the row's hit/overlap box; `tests/test_layout.py`
    # asserts that no two rows overlap and that the text stays inside it.
    def _option_row(self, cx, y, text, selected, right_text=None,
                    text_color=None, size="body", width=400, pad=16):
        row = pygame.Rect(cx - width // 2, y - 8, width, 36)
        if selected:
            pygame.draw.rect(self.screen, THEME["panel_hi"], row, border_radius=8)
            pygame.draw.rect(self.screen, THEME["border_hi"], row, 1, border_radius=8)
            pygame.draw.rect(self.screen, THEME["accent"],
                             (row.x + 1, row.y + 8, 3, 20), border_radius=2)
        color = text_color or (THEME["text"] if selected else THEME["text_dim"])
        self.blit_t(text, row.x + pad, y, size, color)
        if right_text:
            self.blit_t(right_text, row.right - pad, y, size,
                        THEME["accent"] if selected else THEME["text_faint"],
                        right=True)
        return row

    # Draw the main menu, with each row's current value right-aligned.
    def draw_menu(self, st):
        self._menu_bg()
        cx = WIDTH // 2
        self.blit_t("T E T R I S", cx, 74, "h1", THEME["text"], center=True)
        self.blit_t("python  ·  pygame", cx, 116, "small", THEME["text_faint"], center=True)

        opts = st["settings"]["options"]
        goal = opts.get("line_goal", 0)
        values = {
            "Play": None,
            "Difficulty": DIFFICULTY_NAMES.get(opts.get("difficulty"), "MEDIUM"),
            "Lines": LINE_GOAL_LABELS[LINE_GOALS.index(goal)] if goal in LINE_GOALS else "-",
            "Speeds": f"{opts.get('das_delay')} / {opts.get('das_repeat')} / {opts.get('soft_drop_ms')} ms",
            "Settings": None,
            "Quit": None,
        }

        top = 176
        height = len(MENU_ITEMS) * 40
        self.panel(pygame.Rect(cx - 190, top - 16, 380, height + 32), "panel", 225)
        for i, item in enumerate(MENU_ITEMS):
            y = top + 14 + i * 40
            value = values.get(item)
            self._option_row(cx, y, item, i == st["menu_selected"],
                             right_text=value, width=356)

        high = st["settings"].get("high", 0)
        self.blit_t(f"BEST  {high:,}", cx, HEIGHT - 96, "small", THEME["text_faint"],
                    center=True)
        self.blit_t("↑ ↓  move      ENTER  select", cx, HEIGHT - 66, "small",
                    THEME["text_faint"], center=True)
        self._toast(st)

    # Shared chrome for the option submenus: title, subtitle, footer hint,
    # and the toast slot.
    def _submenu(self, title, subtitle, hint, st):
        self._menu_bg(deco=False)
        cx = WIDTH // 2
        self.blit_t(title, cx, 58, "h1", THEME["text"], center=True)
        if subtitle:
            self.blit_t(subtitle, cx, 100, "small", THEME["text_faint"], center=True)
        self.blit_t(hint, cx, HEIGHT - 58, "small", THEME["text_faint"], center=True)
        self._toast(st)

    # Draw the difficulty picker; a dot marks the difficulty in use.
    def draw_difficulty(self, st):
        self._submenu("DIFFICULTY", "how fast the stack comes down",
                      "↑ ↓  choose      ENTER  confirm      ESC  back", st)
        cx = WIDTH // 2
        current = st["settings"]["options"].get("difficulty")
        top, pitch = 150, 62
        self.panel(pygame.Rect(cx - 190, top - 14, 380, pitch * 3 + 28), "panel", 225)
        for i, diff in enumerate(DIFFICULTY_ORDER):
            y = top + i * pitch
            selected = i == st["diff_selected"]
            active = diff == current
            row = pygame.Rect(cx - 178, y - 10, 356, 46)
            if selected:
                pygame.draw.rect(self.screen, THEME["panel_hi"], row, border_radius=9)
                pygame.draw.rect(self.screen, THEME["border_hi"], row, 1, border_radius=9)
                pygame.draw.rect(self.screen, THEME["accent"],
                                 (row.x + 1, row.y + 10, 3, 26), border_radius=2)
            name = DIFFICULTY_NAMES[diff]
            color = THEME["accent"] if active else (THEME["text"] if selected else THEME["text_dim"])
            self.blit_t(name, row.x + 16, y - 4, "h2", color)
            self.blit_t(DIFFICULTY_HINTS[diff], row.x + 16, y + 22, "small",
                        THEME["text_faint"])
            if active:
                pygame.draw.circle(self.screen, THEME["accent"],
                                   (row.right - 20, y + 2), 4)

    # Draw the line-goal picker, flagging the goal currently set.
    def draw_lines(self, st):
        self._submenu("LINES TO CLEAR", "clear the target to win the run",
                      "↑ ↓  choose      ENTER  confirm      ESC  back", st)
        cx = WIDTH // 2
        current = st["settings"]["options"].get("line_goal", 0)
        top, pitch = 150, 56
        self.panel(pygame.Rect(cx - 170, top - 14, 340, pitch * len(LINE_GOALS) + 28),
                   "panel", 225)
        for i, goal in enumerate(LINE_GOALS):
            y = top + i * pitch
            self._option_row(cx, y, LINE_GOAL_LABELS[i], i == st["lines_selected"],
                             right_text="current" if goal == current else None,
                             width=300)
        note = "ENDLESS keeps going until the stack tops out" if current == 0 else \
            f"Goal: {current} lines"
        self.blit_t(note, cx, top + pitch * len(LINE_GOALS) + 24, "small",
                    THEME["text_faint"], center=True)

    # Draw the three speed sliders with their min/max bounds, a filled
    # track, and a knob positioned by the current value.
    def draw_speeds(self, st):
        self._submenu("MOVEMENT SPEED", "lower numbers feel faster",
                      "↑ ↓  row      ← →  adjust      C  reset      ESC  back", st)
        cx = WIDTH // 2
        opts = st["settings"]["options"]
        top, pitch = 132, 96
        self.panel(pygame.Rect(cx - 220, top - 16, 440, pitch * 3 + 40), "panel", 225)
        bar_x, bar_w = cx - 180, 360
        for i, key in enumerate(SPEED_KEYS):
            y = top + i * pitch
            selected = i == st["speed_selected"]
            value = opts.get(key, SPEED_DEFAULTS[key])
            lo, hi = SPEED_MIN[key], SPEED_MAX[key]
            frac = max(0.0, min(1.0, (value - lo) / (hi - lo)))

            self.blit_t(SPEED_LABELS[key], cx - 200, y,
                        "body", THEME["text"] if selected else THEME["text_dim"])
            self.blit_t(f"{value} {SPEED_UNITS[key]}", cx + 200, y, "val",
                        THEME["accent"] if selected else THEME["text"], right=True)

            track = pygame.Rect(bar_x, y + 30, bar_w, 12)
            pygame.draw.rect(self.screen, THEME["well"], track, border_radius=6)
            pygame.draw.rect(self.screen, THEME["border"], track, 1, border_radius=6)
            if frac > 0:
                fill = track.copy()
                fill.width = max(12, int(track.w * frac))
                pygame.draw.rect(self.screen, THEME["accent"] if selected
                                 else THEME["accent_dim"], fill, border_radius=6)
            knob_x = bar_x + int(bar_w * frac)
            knob = pygame.Rect(knob_x - 5, y + 25, 10, 22)
            pygame.draw.rect(self.screen, THEME["text"], knob, border_radius=4)
            pygame.draw.rect(self.screen, THEME["border_hi"], knob, 1, border_radius=4)

            self.blit_t(str(lo), bar_x, y + 48, "tiny", THEME["text_faint"])
            self.blit_t(str(hi), bar_x + bar_w, y + 48, "tiny", THEME["text_faint"],
                        right=True)
            if selected:
                pygame.draw.rect(self.screen, THEME["border_hi"],
                                 (bar_x - 14, y + 18, bar_w + 28, 36), 1, border_radius=18)

    # Draw the control-binding screen. The row waiting for a key press is
    # highlighted in red and waits on the next keydown.
    def draw_settings(self, st):
        self._menu_bg(deco=False)
        cx = WIDTH // 2
        settings = st["settings"]
        self.blit_t("CONTROL BINDINGS", cx, 40, "h1", THEME["text"], center=True)
        self.blit_t("press ENTER on a row, then hit the new key",
                    cx, 82, "small", THEME["text_faint"], center=True)

        actions = list(ACTION_LABELS.keys())
        top, pitch = 116, 42
        self.panel(pygame.Rect(cx - 210, top - 12, 420, pitch * len(actions) + 24),
                   "panel", 225)
        for i, action in enumerate(actions):
            y = top + i * pitch
            selected = i == st["settings_selected"]
            waiting = st["rebinding"] and st["rebinding_action"] == action
            row = pygame.Rect(cx - 198, y - 4, 396, 36)
            if waiting:
                pygame.draw.rect(self.screen, (44, 26, 30), row, border_radius=8)
                pygame.draw.rect(self.screen, (150, 80, 86), row, 1, border_radius=8)
            elif selected:
                pygame.draw.rect(self.screen, THEME["panel_hi"], row, border_radius=8)
                pygame.draw.rect(self.screen, THEME["border_hi"], row, 1, border_radius=8)
                pygame.draw.rect(self.screen, THEME["accent"],
                                 (row.x + 1, row.y + 9, 3, 18), border_radius=2)
            self.blit_t(ACTION_LABELS[action], row.x + 16, y + 3, "body",
                        THEME["text"] if (selected or waiting) else THEME["text_dim"])
            if waiting:
                self.blit_t("press a key…", row.right - 16, y + 3, "body",
                            THEME["warn"], right=True)
            else:
                key = settings["keybinds"].get(action, "")
                display = key_name(pygame.key.key_code(key)) if key else "---"
                self.keycap(display, row.right - 34, y + 14,
                            color=THEME["text"] if selected else THEME["text_dim"])

        self.blit_t("ESC  back      D  restore defaults", cx, HEIGHT - 52, "small",
                    THEME["text_faint"], center=True)
        self._toast(st)

    # Draw the transient notice at the top of the screen, if one is
    # currently active.
    def _toast(self, st):
        if not st or not st.get("notice"):
            return
        text = self.txt(st["notice"], "small", THEME["accent"])
        rect = pygame.Rect(0, 0, text.get_width() + 32, 30)
        rect.center = (WIDTH // 2, 26)
        pygame.draw.rect(self.screen, THEME["panel_hi"], rect, border_radius=15)
        pygame.draw.rect(self.screen, THEME["accent_dim"], rect, 1, border_radius=15)
        self.screen.blit(text, text.get_rect(center=rect.center))

    # ------------------------------------------------------------ overlays

    # Draw the pause card over the dimmed well.
    #
    # Row pitch is 40px so the four rows never touch, and the hint sits at
    # top + 248 to stay inside the 264px card.
    def draw_pause(self, selected):
        self.screen.blit(self.well_dim, (WELL_X, WELL_Y))
        cx = WELL_X + WELL_W // 2
        top = HEIGHT // 2 - 132
        self.panel(pygame.Rect(cx - 120, top, 240, 264), "panel", 240)
        self.blit_t("PAUSED", cx, top + 20, "h2", THEME["text"], center=True)
        pygame.draw.line(self.screen, THEME["border"],
                         (cx - 92, top + 54), (cx + 92, top + 54))
        for i, item in enumerate(PAUSE_ITEMS):
            self._option_row(cx, top + 82 + i * 40, item, i == selected, width=200)
        self.blit_t("ESC  resume", cx, top + 248, "small", THEME["text_faint"], center=True)

    # Draw the win / game-over card with the run summary and two buttons.
    #
    # The card is 356x408 and vertically centred on the 616px window. The
    # stat block ends at card.y + 270, "BEST" sits below the divider, and the
    # buttons use a 40px pitch, so nothing overlaps or escapes the card.
    def draw_over(self, st):
        self.screen.blit(self.dim, (0, 0))
        cx = WIDTH // 2
        won = st["won"]
        card = pygame.Rect(cx - 178, HEIGHT // 2 - 204, 356, 408)
        accent = THEME["ok"] if won else THEME["bad"]
        self.panel(card, "panel", 245, accent, 16, 2)
        self.blit_t("GOAL REACHED" if won else "GAME OVER", cx, card.y + 42, "h1",
                    accent, center=True)
        self.blit_t("nice run" if won else "the stack topped out", cx, card.y + 79,
                    "small", THEME["text_faint"], center=True)

        rows = [
            ("SCORE", f"{st['score']:,}"),
            ("LINES", f"{st['lines']}"),
            ("LEVEL", st["level"]),
            ("TETRISES", st["tetrises"]),
            ("BEST COMBO", f"x{max(st['best_combo'], 0)}"),
            ("TIME", self._clock(st["elapsed"])),
        ]
        y = card.y + 106
        for label, value in rows:
            self.blit_t(label, card.x + 30, y, "small", THEME["text_faint"])
            self.blit_t(value, card.right - 30, y - 2, "val", THEME["text"], right=True)
            y += 26
        pygame.draw.line(self.screen, THEME["border"],
                         (card.x + 26, card.y + 270), (card.right - 26, card.y + 270))
        best = st["settings"].get("high", 0)
        self.blit_t(f"BEST  {best:,}", cx, card.y + 292, "small", THEME["accent"], center=True)

        # Button labels share the stat label column (card.x + 30) so the whole
        # card reads as one grid: row.x + pad == card.x + 30.
        for i, item in enumerate(OVER_ITEMS):
            self._option_row(cx, card.y + 326 + i * 40, item,
                             i == st["over_selected"], width=328)

    # ---------------------------------------------------------------- loop

    # Advance the animated background and draw the screen for the current
    # state, then present the frame.
    def draw_all(self, st, dt=16):
        self.frame += 1
        self._update_sky()
        state = st["state"]
        if state == "game":
            self.draw_game(st, dt)
        elif state == "menu":
            self.draw_menu(st)
        elif state == "difficulty":
            self.draw_difficulty(st)
        elif state == "lines":
            self.draw_lines(st)
        elif state == "speeds":
            self.draw_speeds(st)
        elif state == "settings":
            self.draw_settings(st)
        pygame.display.flip()
