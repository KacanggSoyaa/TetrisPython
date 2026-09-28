"""Layout audit: records every draw op and checks containment / overlap."""
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "Code"))

import pygame
import constants
from tetris import Tetris

BOUNDS = []


def main():
    game = Tetris()
    r = game.renderer
    real_blit = r.blit_t
    real_panel = r.panel
    real_keycap = r.keycap
    real_draw = pygame.draw.rect

    def blit_t(text, x, y, name="body", color=None, center=False, right=False):
        rect = real_blit(text, x, y, name, color, center, right)
        BOUNDS.append(("text:" + str(text)[:26], rect.copy()))
        return rect

    def panel(rect, *a, **kw):
        real_panel(rect, *a, **kw)
        BOUNDS.append(("panel", rect.copy()))

    def keycap(text, cx, cy, *a, **kw):
        rect = real_keycap(text, cx, cy, *a, **kw)
        BOUNDS.append(("keycap:" + str(text)[:10], rect.copy()))
        return rect

    def draw_rect(surface, color, rect, width=0, *a, **kw):
        rect = pygame.Rect(rect)
        if surface is r.screen:
            BOUNDS.append(("rect", rect.copy()))
        return real_draw(surface, color, rect, width, *a, **kw)

    r.blit_t = blit_t
    r.panel = panel
    r.keycap = keycap
    pygame.draw.rect = draw_rect

    problems = []

    def audit(label):
        BOUNDS.clear()
        r.draw_all(game.get_game_state(), 16)
        screen = r.screen.get_rect()
        for name, rect in BOUNDS:
            if not screen.contains(rect):
                problems.append(f"{label}: {name} outside window -> {rect}")
        # text must never overlap the sidebar divider or leave the window
        BOUNDS.clear()

    states = ["menu", "difficulty", "lines", "speeds", "settings"]
    for s in states:
        game.state = s
        for sel in range(6):
            key = {"menu": "menu_selected", "difficulty": "diff_selected",
                   "lines": "lines_selected", "speeds": "speed_selected",
                   "settings": "settings_selected"}[s]
            setattr(game, key, sel)
            audit(f"{s}[{sel}]")

    game.state = "game"
    game.reset_game()
    for y in (14, 16, 19):
        for x in range(constants.COLS):
            game.board.grid[y][x] = constants.COLORS["J"] if (x + y) % 3 else constants.COLORS["L"]
    game.score = 1234567
    game.lines = 7
    game.level = 1
    game.hold = "T"
    game.combo = 4
    game.tetrises = 3
    game.pieces = 88
    game.renderer.popup("TETRIS!", constants.THEME["accent"], big=True)
    game.renderer.popup("COMBO x4", constants.THEME["text"])
    audit("game")
    for p in game.settings["keybinds"].values():
        game.renderer.draw_all(game.get_game_state(), 16)

    # worst case text: every key set to the longest possible name
    longest = max(constants.DEFAULT_KEYBINDS.values(), key=len)
    game.settings["keybinds"] = {a: longest for a in constants.DEFAULT_KEYBINDS}
    audit("game-longest-keys")
    game.settings["keybinds"] = constants.DEFAULT_KEYBINDS.copy()

    game.paused = True
    for sel in range(4):
        game.menu_selected = sel
        audit(f"pause[{sel}]")
    game.paused = False

    game.won = True
    game.score = 987654
    audit("win")
    game.won = False
    game.game_over = True
    for sel in range(2):
        game.over_selected = sel
        audit(f"over[{sel}]")

    # sidebar panel geometry
    panels = [
        pygame.Rect(constants.SIDE_X, 48, constants.SIDEBAR, 130),
        pygame.Rect(constants.SIDE_X, 186, constants.SIDEBAR, 58),
        pygame.Rect(constants.SIDE_X, 252, constants.SIDEBAR, 66),
        pygame.Rect(constants.SIDE_X, 326, constants.SIDEBAR, 66),
        pygame.Rect(constants.SIDE_X, 400, constants.SIDEBAR, 208),
    ]
    for i, p in enumerate(panels):
        if p.right > constants.WIDTH or p.bottom > constants.HEIGHT:
            problems.append(f"sidebar panel {i} outside window: {p}")
        if i and panels[i - 1].colliderect(p):
            problems.append(f"sidebar panels {i-1}/{i} overlap")
    print("sidebar stack:", " -> ".join(f"{p.top}..{p.bottom}" for p in panels),
          f"window height {constants.HEIGHT}")
    print("window:", constants.WIDTH, "x", constants.HEIGHT)

    # keycap widths in the controls panel
    cell_w = constants.SIDE_INNER_W / 2
    for action in constants.ACTION_LABELS:
        label = constants.ACTION_LABELS[action]
        from constants import key_name
        for key_name_str in ("LEFT SHIFT", "SPACE", "A", "RETURN", "RIGHT SHIFT"):
            disp = key_name(pygame.key.key_code(key_name_str))
            w = max(r.txt(label, "tiny").get_width(), r.txt(disp, "key").get_width() + 14)
            if w > cell_w:
                problems.append(f"controls cell too wide: {label}/{disp} = {w} > {cell_w}")
    print("widest controls cell:",
          max(max(r.txt(constants.ACTION_LABELS[a], "tiny").get_width(),
                  r.txt("RIGHT SHIFT", "key").get_width() + 14)
              for a in constants.ACTION_LABELS), "of", int(cell_w))

    # --- text alignment: no two strings may overlap, columns must line up ---
    # Texts are tagged with the layer they were drawn on: the live view (0) or an
    # overlay card (1). An opaque card legitimately covers the view beneath it.
    text_rects = []
    layer = {"v": 0}
    real_blit_t2 = r.blit_t
    real_draw_over = r.draw_over
    real_draw_pause = r.draw_pause

    def blit_t2(text, x, y, name="body", color=None, center=False, right=False):
        rect = real_blit_t2(text, x, y, name, color, center, right)
        text_rects.append((str(text)[:24], rect.copy(), layer["v"]))
        return rect

    def draw_over(st):
        layer["v"] = 1
        return real_draw_over(st)

    def draw_pause(selected):
        layer["v"] = 1
        return real_draw_pause(selected)

    r.blit_t = blit_t2
    r.draw_over = draw_over
    r.draw_pause = draw_pause

    well_cx = constants.WELL_X + constants.WELL_W // 2
    screens = [
        ("menu", "menu", 356, constants.WIDTH // 2),
        ("difficulty", "difficulty", None, constants.WIDTH // 2),
        ("lines", "lines", 300, constants.WIDTH // 2),
        ("speeds", "speeds", None, constants.WIDTH // 2),
        ("settings", "settings", None, constants.WIDTH // 2),
        ("pause", "game", 200, well_cx),
        ("over", "game", 300, constants.WIDTH // 2),
    ]
    try:
        for name, state, width, row_cx in screens:
            game.state = state
            game.paused = state == "game" and name == "pause"
            game.game_over = name == "over"
            game.won = False
            layer["v"] = 0
            text_rects.clear()
            r.draw_all(game.get_game_state(), 16)
            texts = list(text_rects)

            for i in range(len(texts)):
                ti, ri, li = texts[i]
                for j in range(i + 1, len(texts)):
                    tj, rj, lj = texts[j]
                    if li != lj:
                        continue          # card over the live view
                    if ri.inflate(-2, -2).colliderect(rj.inflate(-2, -2)):
                        problems.append(
                            f"{name}: text overlap '{ti}' {ri} vs '{tj}' {rj}")

            info = ""
            if width:
                left_edge = row_cx - width // 2 + 16
                right_edge = row_cx + width // 2 - 16
                labels = [rect for _, rect, _ in texts
                          if round(rect.left) == round(left_edge)]
                values = [rect for _, rect, _ in texts
                          if round(rect.right) == round(right_edge)]
                if texts and not labels:
                    problems.append(f"{name}: no option label starts at {left_edge}")
                for a in labels:
                    for b in values:
                        if a.inflate(-2, -2).colliderect(b.inflate(-2, -2)):
                            problems.append(
                                f"{name}: option column collision {a} vs {b}")
                info = (f"labels@{sorted({round(x.left) for x in labels}) or '-'} "
                        f"values@{sorted({round(x.right) for x in values}) or '-'}")
            print(f"{name:10} texts {len(texts):3}  {info}")

        game.state = "game"
        game.paused = False
        game.game_over = False
    finally:
        r.blit_t = real_blit_t2
        r.draw_over = real_draw_over
        r.draw_pause = real_draw_pause

    if problems:
        print("\nPROBLEMS:")
        for p in dict.fromkeys(problems):
            print(" -", p)
        sys.exit(1)
    print("\nlayout audit clean")


if __name__ == "__main__":
    main()
