# The falling piece: its type, rotation, and position on the board.
#
# A `Piece` is pure data plus small helpers. It never touches the `Board`, so the
# rules engine can test placements and render the piece without either of them
# knowing about the other.
from constants import COLS, COLORS, SHAPES


# One tetromino in play.
#
# `shape` is a letter key into `constants.SHAPES`, `rotation` is an index
# into that shape's four rotation states, and `x`/`y` are the top-left
# corner of the piece's 4x4 bounding box in board cells.
class Piece:
    # Spawn a piece centred horizontally, resting on the top row.
    def __init__(self, shape):
        self.shape = shape
        self.rotation = 0
        self.x = COLS // 2 - 2
        self.y = 0

    # RGB tuple used for both the locked stack and the piece preview.
    @property
    def color(self):
        return COLORS[self.shape]

    # Replace the tetromino, resetting to its spawn rotation.
    def set_shape(self, shape):
        self.shape = shape
        self.rotation = 0

    # Board-cell coordinates of the four filled squares, rotation applied.
    def cells(self):
        return [(self.x + dx, self.y + dy) for dx, dy in SHAPES[self.shape][self.rotation]]

    # Centre of the 4x4 box; used by the T-spin corner test.
    def center(self):
        return self.x + 1, self.y + 1
