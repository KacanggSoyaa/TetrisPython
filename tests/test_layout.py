# Layout audit: records every draw op and checks containment / overlap.
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "Code"))

import pygame
import constants
from tetris import Tetris

BOUNDS = []


# Audit every screen for text that leaves the window or overlaps.
#
# Runs in two passes. The first wraps the draw primitives and checks that
# nothing is drawn outside the window, which catches clipped labels. The
# second wraps them again to tag text with a layer, so the overlay checks
# can tell "text over a card" apart from "text over text".
def main():
    game = Tetris()
    r = game.renderer
    real_blit = r.blit_t
    real_panel = r.panel
    real_keycap = r.keycap
    real_draw = pygame.draw.rect

    # Pass 1 wrappers: record the rect of everything drawn to the screen.
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

    # Draw one screen and report anything not fully inside the window.
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
        # Every selection index, because the widest label is often the selected
        # row and every row draws its highlight bar.
        for sel in range(6):
            key = {"menu": "menu_selected", "difficulty": "diff_selected",
                   "lines": "lines_selected", "speeds": "speed_selected",
                   "settings": "settings_selected"}[s]
            setattr(game, key, sel)
            audit(f"{s}[{sel}]")

    # A tall colourful stack plus popups and large numbers: the worst case for
    # text width in the sidebar and the well.
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

    # every pause and game-over selection, since only the selected row is wider
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

    # sidebar panel geometry: must fit and must not touch the next panel
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
    # printed so a regression in the numbers is visible even when it passes
    print("sidebar stack:", " -> ".join(f"{p.top}..{p.bottom}" for p in panels),
          f"window height {constants.HEIGHT}")
    print("window:", constants.WIDTH, "x", constants.HEIGHT)

    # keycap widths in the controls panel
    cell_w = constants.SIDE_INNER_W / 2
    for action in constants.ACTION_LABELS:
        label = constants.ACTION_LABELS[action]
        from constants import key_name
        # check the shortest and the longest bindable key name per action
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
    # Collected per screen: (label, rect, layer) for text, option rows, and cards.
    text_rects = []
    row_rects = []
    card_rects = []
    layer = {"v": 0}
    real_blit_t2 = r.blit_t
    real_option_row = r._option_row
    real_panel2 = r.panel
    real_draw_over = r.draw_over
    real_draw_pause = r.draw_pause

    # Pass 2 wrappers: same recording, plus the layer tag that separates the
    # live view from the overlay card drawn on top of it.
    def blit_t2(text, x, y, name="body", color=None, center=False, right=False):
        rect = real_blit_t2(text, x, y, name, color, center, right)
        text_rects.append((str(text)[:24], rect.copy(), layer["v"]))
        return rect

    def option_row2(cx, y, text, selected, right_text=None, **kw):
        out = real_option_row(cx, y, text, selected, right_text, **kw)
        row_rects.append((str(text)[:24], out.copy(), layer["v"]))
        return out

    def panel2(rect, *a, **kw):
        out = real_panel2(rect, *a, **kw)
        if layer["v"] == 1:
            card_rects.append(rect.copy())
        return out

    def draw_over(st):
        layer["v"] = 1
        card_rects.clear()
        return real_draw_over(st)

    def draw_pause(selected):
        layer["v"] = 1
        card_rects.clear()
        return real_draw_pause(selected)

    r.blit_t = blit_t2
    r._option_row = option_row2
    r.panel = panel2
    r.draw_over = draw_over
    r.draw_pause = draw_pause

    well_cx = constants.WELL_X + constants.WELL_W // 2
    # (name, state, option-row width, row centre x, label pad)
    screens = [
        ("menu", "menu", 356, constants.WIDTH // 2, 16),
        ("difficulty", "difficulty", None, constants.WIDTH // 2, 16),
        ("lines", "lines", 300, constants.WIDTH // 2, 16),
        ("speeds", "speeds", None, constants.WIDTH // 2, 16),
        ("settings", "settings", None, constants.WIDTH // 2, 16),
        ("pause", "game", 200, well_cx, 16),
        ("over", "game", 328, constants.WIDTH // 2, 16),
    ]
    try:
        for name, state, width, row_cx, pad in screens:
            game.state = state
            game.paused = state == "game" and name == "pause"
            game.game_over = name == "over"
            game.won = False
            layer["v"] = 0
            text_rects.clear()
            row_rects.clear()
            card_rects.clear()
            r.draw_all(game.get_game_state(), 16)
            texts = list(text_rects)
            rows = list(row_rects)
            cards = list(card_rects)

            # 1. no two strings on the same layer may overlap
            for i in range(len(texts)):
                ti, ri, li = texts[i]
                for j in range(i + 1, len(texts)):
                    tj, rj, lj = texts[j]
                    if li != lj:
                        continue          # card over the live view
                    if ri.inflate(-2, -2).colliderect(rj.inflate(-2, -2)):
                        problems.append(
                            f"{name}: text overlap '{ti}' {ri} vs '{tj}' {rj}")

            # option-row backgrounds must not overlap each other
            for i in range(len(rows)):
                ni, ri, li = rows[i]
                for j in range(i + 1, len(rows)):
                    nj, rj, lj = rows[j]
                    if ri.colliderect(rj):
                        problems.append(
                            f"{name}: option rows overlap '{ni}' {ri} vs '{nj}' {rj}")

            # each overlay row must sit inside the card it belongs to
            if rows and cards:
                card = max(cards, key=lambda q: q.w * q.h)
                if card.top != (constants.HEIGHT - card.h) // 2:
                    problems.append(
                        f"{name}: card not vertically centred "
                        f"(top {card.top}, want {(constants.HEIGHT - card.h) // 2})")
                for ni, ri, li in rows:
                    if li != 1:
                        continue
                    if (ri.left < card.left or ri.right > card.right
                            or ri.top < card.top or ri.bottom > card.bottom):
                        problems.append(
                            f"{name}: option row '{ni}' {ri} escapes card {card}")
                    for tj, rj, lj in texts:
                        if lj != 1 or tj == ni:
                            continue
                        if ri.colliderect(rj):
                            problems.append(
                                f"{name}: text '{tj}' {rj} collides with row bg '{ni}'")
                # every text drawn on the card must stay inside it
                for tj, rj, lj in texts:
                    if lj != 1:
                        continue
                    if (rj.left < card.left or rj.right > card.right
                            or rj.top < card.top or rj.bottom > card.bottom):
                        problems.append(
                            f"{name}: text '{tj}' {rj} escapes card {card}")

            info = ""
            if width:
                # 4. option columns: labels all start at the left edge and
                # values all end at the right edge, so they must not collide
                left_edge = row_cx - width // 2 + pad
                right_edge = row_cx + width // 2 - pad
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
            print(f"{name:10} texts {len(texts):3} rows {len(rows):2}  {info}")

        game.state = "game"
        game.paused = False
        game.game_over = False
    finally:
        r.blit_t = real_blit_t2
        r._option_row = real_option_row
        r.panel = real_panel2
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
