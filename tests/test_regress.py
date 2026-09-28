"""Regression checks for the fixes: pause keys, submenu navigation, best combo,
perfect-clear gating, and the clear-animation render state."""
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "Code"))

import pygame
import constants
from board import Board
from piece import Piece
from tetris import Tetris


def key(code):
    return pygame.event.Event(pygame.KEYDOWN, key=code, mod=0, unicode="", scancode=0)


def clear(game, rows):
    for r in rows:
        for c in range(constants.COLS):
            game.board.grid[r][c] = "X"
    game.board.clear_rows(rows)
    game.lock_info = {"rows": rows, "tspin": None, "level": 1}
    game.resolve_clear()


def main():
    game = Tetris()

    game.state = "game"
    game.reset_game()
    game.paused = True
    game.handle_pause_input(key(pygame.K_ESCAPE))
    assert game.paused is False, "ESC did not resume"
    game.paused = True
    game.handle_pause_input(key(pygame.K_p))
    assert game.paused is False, "P did not resume"
    game.paused = True
    game.handle_pause_input(key(pygame.K_DOWN))
    assert game.menu_selected == 1 and game.paused, "pause menu navigation broke"
    print("pause: ESC and P resume, menu still navigates")

    game.state = "difficulty"
    game._prev_state = "menu"
    game.diff_selected = 0
    n = len(constants.DIFFICULTY_ORDER)
    game.handle_difficulty_input(key(pygame.K_UP))
    assert game.diff_selected == n - 1, "difficulty UP should wrap back"
    game.handle_difficulty_input(key(pygame.K_DOWN))
    assert game.diff_selected == 0, "difficulty DOWN should wrap forward"
    game.handle_difficulty_input(key(pygame.K_RIGHT))
    assert game.diff_selected == 1, "difficulty RIGHT regressed"
    game.handle_difficulty_input(key(pygame.K_LEFT))
    assert game.diff_selected == 0, "difficulty LEFT regressed"

    game.state = "lines"
    game.lines_selected = 0
    game.handle_lines_input(key(pygame.K_DOWN))
    assert game.lines_selected == 1, "lines DOWN"
    game.handle_lines_input(key(pygame.K_UP))
    assert game.lines_selected == 0, "lines UP"
    print("submenus: UP/DOWN and LEFT/RIGHT both work")

    game.state = "game"
    game.reset_game()
    clear(game, [17, 18, 19])
    clear(game, [17, 18, 19])
    assert game.best_combo == 1 and game.combo == 1, f"best {game.best_combo} combo {game.combo}"
    clear(game, [17, 18])
    assert game.combo == 2, "any line clear should continue a combo"
    game.lock_info = {"rows": [], "tspin": None, "level": 1}
    game.resolve_clear()
    assert game.combo == -1, "locking without a clear should break the combo"
    assert game.best_combo == 2, "best_combo must not shrink"
    clear(game, [16, 17, 18])
    clear(game, [16, 17, 18])
    assert game.combo == 1, "combo restarts at 0 after a break"
    assert game.best_combo == 2, f"best_combo should hold at 2, got {game.best_combo}"
    print("best_combo: tracks the high-water mark (2)")

    lonely = Tetris()
    lonely.state = "game"
    lonely.reset_game()
    lonely.lock_info = {"rows": [], "tspin": None, "level": 1}
    lonely.resolve_clear()
    assert lonely.best_combo == 0, "no clear must not touch combo counters"

    perfect = Tetris()
    perfect.state = "game"
    perfect.reset_game()
    for c in range(constants.COLS):
        perfect.board.grid[19][c] = "X"
    perfect.board.clear_rows([19])
    perfect.lock_info = {"rows": [19], "tspin": None, "level": 1}
    perfect.resolve_clear()
    assert perfect.score >= constants.PERFECT_CLEAR, "single row on empty board should score"
    print("perfect clear: only awarded for a real line clear")

    clearing = Tetris()
    clearing.state = "game"
    clearing.reset_game()
    for c in range(constants.COLS):
        clearing.board.grid[19][c] = "X"
    clearing.lock_piece()
    assert clearing.clearing and clearing.current is not None
    st = clearing.get_game_state()
    assert st["clearing"] and st["ghost_y"] is None, "ghost must vanish while clearing"
    assert st["best_combo"] == 0
    print("clear phase: state reports clearing, no ghost")

    tspins = [
        ("left wall, full", [(1, 17), (1, 19)], 1, -1, 17, "T-SPIN"),
        ("right wall, full", [(8, 17), (8, 19)], 3, 8, 17, "T-SPIN"),
        ("left wall, mini", [(1, 17)], 1, -1, 17, "T-SPIN MINI"),
        ("floor, full", [(3, 18), (5, 18)], 0, 3, 18, "T-SPIN"),
        ("floor, mini", [(3, 18)], 0, 3, 18, "T-SPIN MINI"),
        ("nub down into notch", [(3, 19), (5, 19), (3, 17)], 2, 3, 17, "T-SPIN"),
        ("flat floor, nothing filled", [], 0, 3, 18, None),
    ]
    for name, fills, rot, px, py, expect in tspins:
        board = Board()
        for fx, fy in fills:
            board.grid[fy][fx] = "X"
        piece = Piece("T")
        piece.rotation = rot
        piece.x = px
        piece.y = py
        assert board.valid(piece), f"tspin setup '{name}' collides"
        game.board = board
        game.current = piece
        game.last_move_was_rotation = True
        got = game.tspin_kind()
        assert got == expect, f"{name}: got {got!r}, expected {expect!r}"
    game.last_move_was_rotation = False
    game.board = Board()
    assert game.tspin_kind() is None, "a slide must never count as a T-spin"
    print(f"t-spins: {len(tspins)} geometries detected, slides ignored")

    print("REGRESSION CHECKS OK")


if __name__ == "__main__":
    main()
