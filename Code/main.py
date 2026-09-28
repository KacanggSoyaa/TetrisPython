# Entry point for the game.
#
#     python Code/main.py
#
# `Tetris` owns the entire game loop (input, gravity, scoring, rendering), so this
# file only has to build one instance and start it.
from tetris import Tetris

if __name__ == "__main__":
    game = Tetris()
    game.run()
