"""Pixel assertions: the well must show the stack, ghost, and active piece in the
right cells. Run after any renderer change."""
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "Code"))

import pygame
import constants
from tetris import Tetris

W, H = constants.WIDTH, constants.HEIGHT


def cell_px(cx, cy):
    return constants.WELL_X + cx * constants.CELL + 15, constants.WELL_Y + cy * constants.CELL + 15


def near(a, b, tol=26):
    return all(abs(x - y) <= tol for x, y in zip(a[:3], b[:3]))


def main():
    game = Tetris()
    r = game.renderer
    game.state = "game"
    game.reset_game()
    for x in range(constants.COLS):
        game.board.grid[19][x] = constants.COLORS["L"]
    for x in range(0, 6):
        game.board.grid[18][x] = constants.COLORS["S"]
    game.current.set_shape("T")
    game.current.x = 3
    game.current.y = 2
    game.hold = "I"
    game.queue[0].set_shape("O")
    game.queue[1].set_shape("Z")
    game.queue[2].set_shape("L")
    game.score = 4242
    game.lines = 6
    game.combo = 3
    r.draw_all(game.get_game_state(), 16)
    screen = pygame.display.get_surface()

    bad = []
    ghost_y = game.ghost_y()

    # active piece cells are the piece colour
    for cx, cy in game.current.cells():
        got = screen.get_at(cell_px(cx, cy))
        if not near(got, constants.COLORS["T"]):
            bad.append(f"piece cell ({cx},{cy}) = {got[:3]} expected T")

    # ghost landing cells are tinted but clearly dimmer than the piece
    for cx, cy in game.current.cells():
        gy = ghost_y + (cy - game.current.y)
        if gy <= cy:
            continue
        got = screen.get_at(cell_px(cx, gy))[:3]
        if got == constants.THEME["well"]:
            bad.append(f"ghost cell ({cx},{gy}) not drawn")
        if sum(got) > sum(constants.COLORS["T"]) * 0.6:
            bad.append(f"ghost cell ({cx},{gy}) = {got} too bright")
        if not got[2] >= got[0]:
            bad.append(f"ghost cell ({cx},{gy}) = {got} wrong hue")

    # locked stack
    for cx, cy in ((0, 19), (5, 19), (0, 18), (5, 18)):
        got = screen.get_at(cell_px(cx, cy))
        want = constants.COLORS["L"] if cy == 19 else constants.COLORS["S"]
        if not near(got, want):
            bad.append(f"stack cell ({cx},{cy}) = {got[:3]} expected {want}")

    # nothing painted outside the well and sidebar
    def bg_at(x, y):
        t = y / constants.HEIGHT
        if x < constants.SIDE_X:
            a, b = constants.THEME["bg_top"], constants.THEME["bg_bottom"]
        else:
            a, b = constants.THEME["side_top"], constants.THEME["side_bottom"]
        return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))

    for x, y in ((constants.WELL_X - 3, constants.HEIGHT // 2),
                 (constants.SIDE_X - 6, constants.HEIGHT // 2),
                 (constants.WIDTH - 2, constants.HEIGHT - 2),
                 (0, constants.HEIGHT - 1), (constants.WELL_X - 6, 2)):
        got = screen.get_at((x, y))
        if not near(got, bg_at(x, y), 3):
            bad.append(f"stray paint at ({x},{y}) = {got[:3]} expected {bg_at(x, y)}")

    # every sidebar panel row is separated by a visible gap
    gap = screen.get_at((constants.SIDE_X + 40, 181))[:3]
    if not near(gap, constants.THEME["side_top"], 12):
        bad.append(f"sidebar panel gap at y=181 = {gap}")

    # hold + next previews are lit
    for label, box in (("hold", (constants.SIDE_INNER_X, 275, 210, 36)),
                       ("next", (constants.SIDE_INNER_X, 349, 60, 36))):
        lit = any(sum(screen.get_at((box[0] + i, box[1] + j))[:3]) > 90
                  for i in range(0, box[2], 2) for j in range(0, box[3], 2))
        if not lit:
            bad.append(f"{label} preview looks empty")

    # controls panel: 10 keycaps lit
    keys_lit = 0
    for i, action in enumerate(constants.ACTION_LABELS):
        cx = constants.SIDE_INNER_X + (constants.SIDE_INNER_W / 2) * (i % 2) + constants.SIDE_INNER_W / 4
        cy = 400 + 32 + (i // 2) * 34 + 22
        bright = any(sum(screen.get_at((int(cx) + dx, int(cy) + dy))[:3]) > 130
                     for dx in range(-6, 7) for dy in range(-4, 5))
        if bright:
            keys_lit += 1
    if keys_lit != len(constants.ACTION_LABELS):
        bad.append(f"only {keys_lit}/{len(constants.ACTION_LABELS)} keycaps drawn")

    # score digits visible
    if not any(sum(screen.get_at((336 + i, 66 + j))[:3]) > 500
               for i in range(70) for j in range(24)):
        bad.append("score value not visible")

    if bad:
        print("PIXEL PROBLEMS:")
        for b in bad:
            print(" -", b)
        sys.exit(1)
    print("pixel checks clean (piece, ghost, stack, panels, previews, keycaps)")


if __name__ == "__main__":
    main()
