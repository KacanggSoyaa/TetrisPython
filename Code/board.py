from constants import COLS, ROWS


class Board:
    def __init__(self):
        self.grid = [[None] * COLS for _ in range(ROWS)]

    def valid(self, piece, dx=0, dy=0):
        for x, y in piece.cells():
            nx, ny = x + dx, y + dy
            if nx < 0 or nx >= COLS or ny >= ROWS:
                return False
            if ny >= 0 and self.grid[ny][nx] is not None:
                return False
        return True

    def filled(self, x, y):
        """T-spin corner test: the walls and the floor count as solid, the sky
        above the well does not."""
        if y < 0:
            return False
        if x < 0 or x >= COLS or y >= ROWS:
            return True
        return self.grid[y][x] is not None

    def lock(self, piece):
        for x, y in piece.cells():
            if 0 <= y < ROWS:
                self.grid[y][x] = piece.color

    def full_rows(self):
        return [i for i, row in enumerate(self.grid) if all(c is not None for c in row)]

    def clear_rows(self, rows):
        keep = [row for i, row in enumerate(self.grid) if i not in set(rows)]
        for _ in rows:
            keep.insert(0, [None] * COLS)
        self.grid = keep

    def is_empty(self):
        return all(cell is None for row in self.grid for cell in row)
