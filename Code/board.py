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

    def lock(self, piece):
        for x, y in piece.cells():
            if 0 <= y < ROWS:
                self.grid[y][x] = piece.color

    def clear_lines(self):
        cleared = 0
        new_grid = []
        cleared_rows = []
        for i, row in enumerate(self.grid):
            if all(cell is not None for cell in row):
                cleared += 1
                cleared_rows.append(i)
            else:
                new_grid.append(row)
        for _ in range(cleared):
            new_grid.insert(0, [None] * COLS)
        self.grid = new_grid
        return cleared, cleared_rows
