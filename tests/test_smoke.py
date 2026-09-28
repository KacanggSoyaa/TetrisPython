# Headless smoke test: walks every screen and game phase, saving screenshots.
import os
import random
import sys
import tempfile

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "Code"))

import pygame

import constants
import tetris as game_mod

OUT = os.environ.get("TETRIS_TEST_SHOTS") or os.path.join(
    tempfile.gettempdir(), "tetris_shots")
os.makedirs(OUT, exist_ok=True)

# The game writes settings.json, so snapshot it here and put it back at the end
# of the run rather than leaving the player's file modified.
SETTINGS_BACKUP = None
if os.path.exists(constants.SETTINGS_FILE):
    with open(constants.SETTINGS_FILE) as f:
        SETTINGS_BACKUP = f.read()


# Build a synthetic KEYDOWN event, as Pygame would deliver from a real key.
def key(k):
    return pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode="", scancode=0)


# Render the current state and save it to the screenshots folder.
def shot(game, name):
    game.renderer.draw_all(game.get_game_state(), 16)
    pygame.image.save(game.renderer.screen, os.path.join(OUT, name + ".png"))


# Walk every screen and every game phase, asserting as we go.
#
# A fixed RNG seed keeps the random-play section reproducible. The long fuzz
# run at the end is the broad crash check; anything that raises fails the
# file. settings.json is restored before the success message prints.
def main():
    random.seed(7)
    game = game_mod.Tetris()
    for name, state in (("01_menu", "menu"), ("02_difficulty", "difficulty"),
                        ("03_lines", "lines"), ("04_speeds", "speeds"),
                        ("05_settings", "settings")):
        game.state = state
        shot(game, name)

    # --- gameplay ------------------------------------------------------
    game.state = "game"
    game.reset_game()
    for _ in range(60):
        game.handle_game_continuous(16)
        game.drop_time += 16
        if game.drop_time >= game.get_speed():
            game.drop_time = 0
            if game.board.valid(game.current, 0, 1):
                game.current.y += 1
            else:
                game.locking = True
    shot(game, "06_game_early")

    # move / rotate / hold
    for k in (pygame.K_LEFT, pygame.K_UP, pygame.K_x, pygame.K_LSHIFT):
        game.handle_game_input(key(k))
    game.renderer.popup("TETRIS!", constants.THEME["accent"], big=True)
    game.renderer.popup("COMBO x3", constants.THEME["text"])
    game.renderer.burst([16, 17], 4)
    game.renderer.shake(5)
    for _ in range(4):
        shot(game, "07_game_fx")

    # fill a tetris row by hand
    game.reset_game()
    for y in (17, 18, 19):
        for x in range(constants.COLS):
            game.board.grid[y][x] = None if x == 4 else (90, 110, 190)
    game.current.set_shape("I")
    game.current.rotation = 1
    game.current.x = 2
    game.current.y = 0
    game.hard_drop()
    assert game.clearing, "no clear animation started"
    shot(game, "08_line_flash")
    for i in range(6):
        game.update_clear(16)
    shot(game, "09_line_glow")
    while game.clearing:
        game.update_clear(16)
    assert not game.clearing, "clear animation never finished"
    assert game.lines == 3, f"expected 3 lines cleared, got {game.lines}"
    filled = sum(1 for row in game.board.grid for c in row if c is not None)
    assert filled == 1, f"expected 1 leftover cell, got {filled}"
    assert game.score > 0
    print("triple:", game.score, "combo", game.combo, "b2b", game.b2b)

    # t-spin double: rotate a T into a notch with all four corners covered
    game.reset_game()
    for x in range(constants.COLS):
        if x != 5:
            game.board.grid[19][x] = (200, 40, 40)
        if x in (0, 1, 2, 3, 7, 8, 9):
            game.board.grid[18][x] = (40, 200, 40)
    game.board.grid[17][4] = (40, 40, 200)
    game.board.grid[17][6] = (40, 40, 200)
    game.current.set_shape("T")
    game.current.x = 4
    game.current.y = 17
    game.last_move_was_rotation = True
    before = game.score
    game.lock_piece()
    while game.clearing:
        game.update_clear(16)
    print("tspin:", game.lock_info["tspin"], "points", game.score - before)
    assert game.lock_info["tspin"] == "T-SPIN", "t-spin not detected"
    assert game.score - before == 800, "t-spin single should be 800 x level"
    shot(game, "16_tspin")

    # t-spin, no lines cleared
    game.reset_game()
    for x in range(constants.COLS):
        if x not in (5, 7):
            game.board.grid[19][x] = (200, 40, 40)
        if x in (0, 1, 2, 3, 7, 9):
            game.board.grid[18][x] = (40, 200, 40)
    game.board.grid[17][4] = (40, 40, 200)
    game.board.grid[17][6] = (40, 40, 200)
    game.current.set_shape("T")
    game.current.rotation = 2
    game.current.x = 4
    game.current.y = 17
    game.last_move_was_rotation = True
    before = game.score
    game.lock_piece()
    assert game.lock_info["rows"] == [], "should not clear a line"
    print("tspin empty:", game.lock_info["tspin"], "points", game.score - before)
    assert game.lock_info["tspin"] == "T-SPIN"
    assert game.score - before == 400, "bare t-spin should be 400 x level"

    # pause
    game.paused = True
    game.menu_selected = 1
    shot(game, "10_pause")
    game.paused = False

    # win overlay
    game.lines = game.settings["options"]["line_goal"] or 20
    game.won = True
    game.combo = 5
    game.score = 123456
    game.tetrises = 4
    shot(game, "11_win")

    # game over overlay
    game.won = False
    game.game_over = True
    game.over_selected = 1
    shot(game, "12_gameover")

    # endless goal reachable + all options values
    game.state = "lines"
    game.lines_selected = 3
    shot(game, "13_lines_endless")
    game.handle_lines_input(key(pygame.K_RETURN))
    assert game.settings["options"]["line_goal"] == 0, "endless not selectable"

    # speeds at both extremes
    game.state = "speeds"
    for _ in range(60):
        game.handle_speeds_input(key(pygame.K_RIGHT))
    game.speed_selected = 0
    for _ in range(40):
        game.handle_speeds_input(key(pygame.K_LEFT))
    shot(game, "14_speeds_extreme")

    # rebind conflict handling
    game.state = "settings"
    game.settings_selected = 0
    game.handle_settings_input(key(pygame.K_RETURN))
    game.handle_settings_input(key(pygame.K_RIGHT))
    assert not game.rebinding, "duplicate bind should be rejected"
    assert game.bind_notice, "no conflict message"
    game.handle_settings_input(key(pygame.K_ESCAPE))
    game.handle_settings_input(key(pygame.K_RETURN))
    game.handle_settings_input(key(pygame.K_m))
    assert game.settings["keybinds"]["move_left"] == "M", "rebind failed"
    shot(game, "15_settings_rebound")

    # a long random run to shake out edge cases
    game.state = "game"
    game.reset_game()
    binds = game.settings["keybinds"]
    pool = [pygame.K_LEFT, pygame.K_RIGHT, pygame.K_UP, pygame.K_z, pygame.K_x,
            pygame.K_c, pygame.K_LSHIFT, pygame.K_SPACE, pygame.K_DOWN, pygame.K_p,
            pygame.K_r, pygame.K_ESCAPE]
    for i in range(6000):
        game.handle_game_input(key(random.choice(pool)))
        game.handle_game_continuous(16)
        if game.clearing:
            game.update_clear(16)
        else:
            game.drop_time += 16
            if game.drop_time >= game.get_speed():
                game.drop_time = 0
                if game.board.valid(game.current, 0, 1):
                    game.current.y += 1
                    game.locking = False
                else:
                    game.locking = True
            if game.locking:
                game.lock_timer += 16
                if game.lock_timer >= game.lock_delay:
                    game.lock_piece()
        if game.game_over:
            game.reset_game()
        game.renderer.draw_all(game.get_game_state(), 16)
    print("fuzz done — score", game.score, "lines", game.lines, "level", game.level,
          "combo", game.combo, "tetrises", game.tetrises)

    if SETTINGS_BACKUP is not None:
        with open(constants.SETTINGS_FILE, "w") as f:
            f.write(SETTINGS_BACKUP)
    else:
        os.remove(constants.SETTINGS_FILE)
    print("smoke test OK")


if __name__ == "__main__":
    main()
