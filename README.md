# Tetris Python

A modern take on classic 2D Tetris built with Pygame. Full menu flow, ghost piece,
hold, three-piece preview, T-spin detection, combo/back-to-back/perfect-clear scoring,
persisted high score, and fully rebindable controls.

## How to Run

```bash
python Code/main.py
```

Requires Python 3 and Pygame (`pip install pygame`).

---

## Menu System

| Screen | Navigation |
|--------|-----------|
| **Main Menu** | Up / Down to highlight, Enter to select |
| **Pause Menu** | Press Pause (or `Esc`) during gameplay; `Esc` or Pause resumes |
| **Options** | Left / Right to change a value, `C` resets speeds, `Esc` goes back |
| **Settings** | Up / Down to select an action, Enter to rebind, `D` resets all bindings, `Esc` goes back |
| **Game Over** | Up / Down to highlight, Enter or Space to confirm, `Esc` for the main menu |

Both submenus and options screens accept Up / Down as well as Left / Right.

---

## Controls (Default)

| Action | Default Key | Description |
|--------|-------------|-------------|
| Move Left | `Left Arrow` | Move piece one column left |
| Move Right | `Right Arrow` | Move piece one column right |
| Rotate CW | `Up Arrow` | Rotate clockwise, with wall kick support |
| Rotate CCW | `Z` | Rotate counter-clockwise |
| Rotate 180 | `X` | Flip the piece upside down |
| Soft Drop | `Down Arrow` | Speed up the drop, 1 point per cell |
| Hard Drop | `Space` | Slam to the floor, 2 points per cell |
| Hold | `Left Shift` | Stash the current piece and pull the held one |
| Pause | `P` | Opens pause menu (Resume / Settings / Restart / Main Menu) |
| Restart | `R` | Restarts the current run |

All ten actions can be rebound in **Settings** — pick an action, press Enter, then press
the new key. Bindings are checked for conflicts, saved to `settings.json`, and reloaded on
the next launch.

---

## Game Features

### Scoring

- Clearing lines awards base points multiplied by the current level:
  Single 100, Double 300, Triple 500, Tetris 800.
- **Soft drop** adds 1 point per cell, **hard drop** 2 points per cell.
- **T-spins** (rotating a T piece into its own notch) pay 400 / 800 / 1200 / 1600 for
  0–3 lines, instead of the normal line values.
- **Back-to-back** multiplies difficult clears (Tetrises and T-spin line clears) by 1.5.
- **Combo** adds 50 × combo × level for each consecutive line-clearing lock.
- **Perfect clear** (emptying the whole well) adds a flat 1800 × level bonus.
- Your best score is stored in `settings.json` and shown on the game-over card.

### Level System

- You start at **Level 1**; every **10 lines** raises the level by 1.
- Levels 1–15 map to a gravity interval for the chosen difficulty (see below).

### Board & Pieces

- **10 × 20** well with a **3-piece** upcoming queue and a hold slot.
- **7-bag randomizer**: pieces are dealt in shuffled bags of all 7 types, so droughts
  are bounded and every piece stays playable.
- **Ghost piece** shows the exact landing position.
- **Lock delay** of 500ms lets you slide or rotate a grounded piece before it locks.
- **7-bag + wall kicks** (SRS-style offsets) let pieces rotate against walls and floors.
- **T-spin detection** checks the three corners around a rotated T piece.

### Modes & Difficulty

- **Difficulty** — Easy, Medium, Hard; each has its own 15-level gravity curve.
- **Line goal** — 10, 20, 40, or Endless. Reach the goal and you get a win screen;
  Endless keeps the high-score run going.
- **Speeds** — tune DAS delay, DAS repeat, soft-drop rate, and lock delay to taste.

### Feel

- Line clears flash, then collapse with a glow before the next piece spawns
  (170ms flash + 150ms glow).
- Screen shake on Tetrises and goal wins, particle bursts, and floating score popups.
- Pause, win, and game-over overlays share the same panel styling as the menus.

---

## Settings / Keybinds

Open Settings from the **Main Menu** or the **Pause Menu**.

| Key | Action in Settings |
|-----|-------------------|
| `Up` / `Down` | Navigate between actions |
| `Enter` | Start rebinding the selected action (then press any key) |
| `Escape` | Cancel rebinding / go back to the previous screen |
| `D` | Reset all keybinds to defaults |

Options (difficulty, line goal, speeds) and the high score live in the same
`settings.json` file at the repository root.

---

## Project Structure

```
TetrisPython/
├── Code/
│   ├── main.py        # entry point
│   ├── tetris.py      # game loop, state machine, scoring, input
│   ├── board.py       # playfield grid, locking, line clearing
│   ├── piece.py       # tetromino definitions and rotation state
│   ├── renderer.py    # all drawing: well, sidebar, menus, effects
│   └── constants.py   # geometry, theme, tuning, settings IO
├── Audio/             # (reserved for sound effects)
├── Graphic/           # (reserved for sprite assets)
├── settings.json      # persisted options, keybinds, high score
└── README.md
```

---

## Scoring Breakdown

| Clear | Base Points | × Level |
|-------|-------------|---------|
| Single | 100 | × level |
| Double | 300 | × level |
| Triple | 500 | × level |
| Tetris | 800 | × level |
| T-Spin (0–3 lines) | 400 / 800 / 1200 / 1600 | × level |
| Back-to-back difficult clear | ×1.5 on top | — |
| Combo (n-th consecutive clear) | 50 × n | × level |
| Perfect clear | +1800 | × level |

---

## Level Speed Table (ms per row)

| Level | Easy | Medium | Hard |
|-------|------|--------|------|
| 1 | 900 | 700 | 420 |
| 2 | 800 | 600 | 350 |
| 3 | 700 | 520 | 295 |
| 5 | 550 | 390 | 200 |
| 8 | 360 | 250 | 105 |
| 10 | 260 | 180 | 75 |
| 15 | 125 | 85 | 38 |
