# The playfield grid and the operations the rules engine needs on it.
#
# `Board` only knows about cells: can this piece go here, which rows are full,
# and what happens when rows collapse. It has no concept of score, gravity, or
# rendering.
from constants import COLS, ROWS


# A `ROWS` x `COLS` grid where each cell is `None` or an RGB tuple.
class Board:
    # Start a fresh, empty well.
    def __init__(self):
        self.grid = [[None] * COLS for _ in range(ROWS)]

    # True if `piece` fits when offset by (dx, dy).
    #
    # Used for every move, rotation, and ghost landing, so it also doubles as
    # the block-out check. Cells above the well are ignored (standard
    # guideline behaviour) so a piece can still spawn into view.
    def valid(self, piece, dx=0, dy=0):
        for x, y in piece.cells():
            nx, ny = x + dx, y + dy
            if nx < 0 or nx >= COLS or ny >= ROWS:
                return False
            if ny >= 0 and self.grid[ny][nx] is not None:
                return False
        return True

    # T-spin corner test: the walls and the floor count as solid, the sky
    # above the well does not.
    def filled(self, x, y):
        if y < 0:
            return False
        if x < 0 or x >= COLS or y >= ROWS:
            return True
        return self.grid[y][x] is not None

    # Write the piece's cells into the stack as a permanent colour.
    def lock(self, piece):
        for x, y in piece.cells():
            if 0 <= y < ROWS:
                self.grid[y][x] = piece.color

    # Row indices that are completely filled, top to bottom.
    def full_rows(self):
        return [i for i, row in enumerate(self.grid) if all(c is not None for c in row)]

    # Remove the given rows and push fresh empty ones in at the top.
    def clear_rows(self, rows):
        keep = [row for i, row in enumerate(self.grid) if i not in set(rows)]
        for _ in rows:
            keep.insert(0, [None] * COLS)
        self.grid = keep

    # True when the well holds no cells; gates the perfect-clear bonus.
    def is_empty(self):
        return all(cell is None for row in self.grid for cell in row)
