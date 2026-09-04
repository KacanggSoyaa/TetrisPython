from constants import COLS, COLORS, SHAPES


class Piece:
    def __init__(self, shape):
        self.shape = shape
        self.rotation = 0
        self.x = COLS // 2 - 2
        self.y = 0
        self.color = COLORS[shape]

    def cells(self):
        return [(self.x + dx, self.y + dy) for dx, dy in SHAPES[self.shape][self.rotation]]
