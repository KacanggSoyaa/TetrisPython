# Tetris Python

A classic 2D Tetris game built with Pygame. Features a scoreboard, level progression, line tracking, next piece preview, ghost piece, and fully rebindable controls.

## How to Run

```bash
python Code/tetris.py
```

Requires Python 3 and Pygame (`pip install pygame`).

---

## Menu System

| Screen | Navigation |
|--------|-----------|
| **Main Menu** | Arrow keys to highlight, Enter to select |
| **Pause Menu** | Press your Pause key during gameplay |
| **Settings** | Arrow keys to select a binding, Enter to rebind, Esc to go back |

---

## Controls (Default)

| Action | Default Key | Description |
|--------|-------------|-------------|
| Move Left | `Left Arrow` | Move piece one column left |
| Move Right | `Right Arrow` | Move piece one column right |
| Rotate | `Up Arrow` | Rotate piece clockwise with wall kick support |
| Soft Drop | `Down Arrow` |加速 dropping, awards 1 point per cell |
| Hard Drop | `Space` | Instantly drops piece to bottom, awards 2 points per cell |
| Pause | `P` | Opens pause menu with Resume / Settings / Restart / Quit |
| Restart | `R` | Resets the current game |

All controls can be changed in the **Settings** menu. Press `Escape` during gameplay to open the pause menu.

---

## Game Features

### Scoreboard
- **Score** increases by clearing lines: 1 line = 100, 2 = 300, 3 = 500, 4 (Tetris) = 800. The base score is multiplied by the current level.
- Soft drops add 1 point per cell, hard drops add 2 points per cell.

### Level System
- You start at **Level 1**.
- Every **10 lines** cleared increases your level by 1.
- Higher levels increase the gravity speed (pieces fall faster).

### Lines Counter
- Tracks the total number of lines cleared.

### Next Piece Preview
- Shows the upcoming piece in the sidebar so you can plan ahead.

### Ghost Piece
- A translucent outline shows where the current piece will land.

### Lock Delay
- When a piece lands, you have a brief window (500ms) to slide or rotate it before it locks in place.

### 7-Bag Randomizer
- Pieces are dealt in shuffled bags of all 7 types, ensuring fair distribution.

---

## Settings / Keybinds

Open the Settings screen from the **Main Menu** or **Pause Menu**.

| Key | Action in Settings |
|-----|-------------------|
| `Up` / `Down` | Navigate between actions |
| `Enter` | Start rebinding the selected action (press any key) |
| `Escape` | Cancel rebinding / Go back to previous menu |
| `D` | Reset all keybinds to default |

Your custom keybinds are saved to `settings.json` and persist between sessions.

---

## Project Structure

```
TetrisPython/
├── Code/
│   └── tetris.py       # Main game file
├── Audio/               # (reserved for sound effects)
├── Graphic/             # (reserved for sprite assets)
├── settings.json        # Auto-generated keybind config
└── README.md
```

---

## Scoring Breakdown

| Lines Cleared | Base Points | × Level |
|---------------|------------|---------|
| 1 (Single) | 100 | × level |
| 2 (Double) | 300 | × level |
| 3 (Triple) | 500 | × level |
| 4 (Tetris) | 800 | × level |

---

## Level Speed Table

| Level | Drop Interval (ms) |
|-------|-------------------|
| 1 | 800 |
| 2 | 720 |
| 3 | 630 |
| 5 | 470 |
| 8 | 220 |
| 10 | 100 |
| 15 | 30 |
