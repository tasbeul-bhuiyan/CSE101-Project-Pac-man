"""
=============================================================
  PAC-MAN  —  Python / Pygame clone
=============================================================
  Dependencies : Python 3.10+  |  pip install pygame
  Run          : python pacman.py

  Controls
  --------
  Arrow keys / WASD  — move Pac-Man
  P                  — pause / unpause
  ENTER              — start game from menu
  R                  — restart after Game Over
  ESC                — quit
=============================================================
"""

from __future__ import annotations

import math
import random
import sys
from enum import Enum, auto
from typing import Optional

import pygame

# ---------------------------------------------------------------------------
# Window / timing constants
# ---------------------------------------------------------------------------
SCREEN_W: int = 600
SCREEN_H: int = 650
HUD_H: int = 50
FPS: int = 60

# ---------------------------------------------------------------------------
# Maze dimensions
# ---------------------------------------------------------------------------
COLS: int = 20
ROWS: int = 20
CELL: int = 28                              # pixels per cell
MAZE_X: int = (SCREEN_W - COLS * CELL) // 2
MAZE_Y: int = HUD_H + 10

# ---------------------------------------------------------------------------
# Speed constants  (pixels per second)
# ---------------------------------------------------------------------------
PACMAN_SPEED: float     = 180.0
GHOST_SPEED_BASE: float = 140.0
GHOST_SPEED_FRIGHT: float = 80.0
GHOST_SPEED_EYES: float  = 260.0
GHOST_ACCEL: float       = 5.0    # px/s added per second elapsed

# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------
PELLET_SCORE: int = 10
POWER_SCORE: int  = 50
GHOST_SCORES: tuple[int, ...] = (200, 400, 800, 1600)
FRUIT_SCORES: tuple[int, ...] = (100, 300, 500, 700, 1000, 2000, 3000, 5000)

# ---------------------------------------------------------------------------
# Timers (seconds)
# ---------------------------------------------------------------------------
FRIGHTENED_DURATION: float = 8.0
LIFE_LOST_PAUSE: float     = 1.8
FRUIT_DURATION: float      = 9.0

# Scatter → Chase phase cycle  [(scatter_secs, chase_secs), ...]
SCATTER_CHASE: tuple[tuple[float, float], ...] = (
    (7.0, 20.0),
    (7.0, 20.0),
    (0.0, 9999.0),   # indefinite chase after phase 2
)

# Ghost home pen centre
HOME_COL: int = 9
HOME_ROW: int = 9

# Pac-Man spawn tile
PACMAN_START_COL: int = 10
PACMAN_START_ROW: int = 14

# ---------------------------------------------------------------------------
# Colors
# ---------------------------------------------------------------------------
BLACK: pygame.Color     = pygame.Color(0,   0,   0)
WHITE: pygame.Color     = pygame.Color(255, 255, 255)
YELLOW: pygame.Color    = pygame.Color(255, 220,   0)
BLUE: pygame.Color      = pygame.Color(33,  33,  222)
RED: pygame.Color       = pygame.Color(220,   0,   0)
PINK: pygame.Color      = pygame.Color(255, 130, 180)
CYAN: pygame.Color      = pygame.Color(0,   220, 220)
ORANGE: pygame.Color    = pygame.Color(255, 160,  30)
DARK_BLUE: pygame.Color = pygame.Color(20,   20, 160)
GRAY: pygame.Color      = pygame.Color(160, 160, 160)
DARK_GRAY: pygame.Color = pygame.Color(40,   40,  40)
WALL_COL: pygame.Color  = pygame.Color(30,   60, 180)
PELLET_COL: pygame.Color = pygame.Color(255, 200, 150)
FRUIT_COL: pygame.Color  = pygame.Color(220,  60,  60)
GREEN: pygame.Color      = pygame.Color(0,   180,   0)

# ---------------------------------------------------------------------------
# Direction helpers
# ---------------------------------------------------------------------------
DIR_VEC: dict[str, tuple[int, int]] = {
    "UP":    (0, -1),
    "DOWN":  (0,  1),
    "LEFT":  (-1,  0),
    "RIGHT": (1,   0),
}
OPPOSITE: dict[str, str] = {
    "UP": "DOWN", "DOWN": "UP",
    "LEFT": "RIGHT", "RIGHT": "LEFT",
}

# Ghost scatter corners  {name: (col, row)}
SCATTER_CORNERS: dict[str, tuple[int, int]] = {
    "Blinky": (COLS - 2, 0),
    "Pinky":  (1, 0),
    "Inky":   (COLS - 2, ROWS - 1),
    "Clyde":  (1, ROWS - 1),
}

# ---------------------------------------------------------------------------
# Raw maze  (0=open, 1=wall, 2=pellet, 3=power-pellet, 4=pen-door)
# ---------------------------------------------------------------------------
RAW_MAZE: list[list[int]] = [
    [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
    [1,2,2,2,2,2,2,2,2,1,1,2,2,2,2,2,2,2,2,1],
    [1,3,1,1,2,1,1,1,2,1,1,2,1,1,1,2,1,1,3,1],
    [1,2,1,1,2,1,1,1,2,1,1,2,1,1,1,2,1,1,2,1],
    [1,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,1],
    [1,2,1,1,2,1,2,1,1,1,1,1,1,2,1,2,1,1,2,1],
    [1,2,2,2,2,1,2,2,2,1,1,2,2,2,1,2,2,2,2,1],
    [1,1,1,1,2,1,1,1,0,1,1,0,1,1,1,2,1,1,1,1],
    [1,1,1,1,2,1,0,0,0,0,0,0,0,0,1,2,1,1,1,1],
    [1,1,1,1,2,1,0,1,1,4,4,1,1,0,1,2,1,1,1,1],
    [0,0,0,0,2,0,0,1,0,0,0,0,1,0,0,2,0,0,0,0],
    [1,1,1,1,2,1,0,1,1,1,1,1,1,0,1,2,1,1,1,1],
    [1,1,1,1,2,1,0,0,0,0,0,0,0,0,1,2,1,1,1,1],
    [1,1,1,1,2,1,0,1,1,1,1,1,1,0,1,2,1,1,1,1],
    [1,2,2,2,2,2,2,2,2,1,1,2,2,2,2,2,2,2,2,1],
    [1,2,1,1,2,1,1,1,2,1,1,2,1,1,1,2,1,1,2,1],
    [1,3,2,1,2,2,2,2,2,2,2,2,2,2,2,2,1,2,3,1],
    [1,1,2,1,2,1,2,1,1,1,1,1,1,2,1,2,1,2,1,1],
    [1,2,2,2,2,1,2,2,2,1,1,2,2,2,1,2,2,2,2,1],
    [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
]

# Ghost start positions  (col, row, name, color)
GHOST_STARTS: list[tuple[int, int, str, pygame.Color]] = [
    (9,  9, "Blinky", RED),
    (10, 9, "Pinky",  PINK),
    (9,  10,"Inky",   CYAN),
    (10, 10,"Clyde",  ORANGE),
]


# ===========================================================================
#  State enum
# ===========================================================================
class State(Enum):
    MENU      = auto()
    PLAYING   = auto()
    PAUSED    = auto()
    LIFE_LOST = auto()
    GAME_OVER = auto()
    VICTORY   = auto()


# ===========================================================================
#  Maze
# ===========================================================================
class Maze:
    """Maze grid: stores cell data, handles pellet eating and rendering."""

    def __init__(self) -> None:
        """Deep-copy raw layout so it can be mutated during play."""
        self.grid: list[list[int]] = [row[:] for row in RAW_MAZE]
        self.total_pellets: int = sum(
            1 for row in self.grid for c in row if c in (2, 3)
        )
        self.pellets_eaten: int = 0

    def reset(self) -> None:
        """Restore maze to its original state for a new level."""
        self.grid = [row[:] for row in RAW_MAZE]
        self.pellets_eaten = 0

    def cell_center(self, col: int, row: int) -> tuple[float, float]:
        """Return the pixel centre of a grid cell."""
        return (
            float(MAZE_X + col * CELL + CELL // 2),
            float(MAZE_Y + row * CELL + CELL // 2),
        )

    def pixel_to_cell(self, px: float, py: float) -> tuple[int, int]:
        """Convert a pixel position to the nearest grid cell index."""
        col = int((px - MAZE_X) / CELL)
        row = int((py - MAZE_Y) / CELL)
        return (max(0, min(COLS - 1, col)), max(0, min(ROWS - 1, row)))

    def is_wall(self, col: int, row: int) -> bool:
        """Return True when the cell is a wall or out of bounds."""
        if row < 0 or row >= ROWS:
            return True
        return self.grid[row][col % COLS] == 1

    def is_pen_door(self, col: int, row: int) -> bool:
        """Return True when the cell is the ghost-pen door."""
        if row < 0 or row >= ROWS or col < 0 or col >= COLS:
            return False
        return self.grid[row][col] == 4

    def eat_pellet(self, col: int, row: int) -> int:
        """
        Consume the pellet at (col, row) if present.
        Returns points earned (0 if the cell has no pellet).
        """
        col = col % COLS
        cell = self.grid[row][col]
        if cell == 2:
            self.grid[row][col] = 0
            self.pellets_eaten += 1
            return PELLET_SCORE
        if cell == 3:
            self.grid[row][col] = 0
            self.pellets_eaten += 1
            return POWER_SCORE
        return 0

    def is_power_pellet(self, col: int, row: int) -> bool:
        """Return True when (col, row) holds a power pellet."""
        return self.grid[row][col % COLS] == 3

    def all_eaten(self) -> bool:
        """Return True when every pellet has been consumed."""
        return self.pellets_eaten >= self.total_pellets

    def draw(self, surface: pygame.Surface, tick: int) -> None:
        """Render walls, pellets, and power pellets each frame."""
        for row in range(ROWS):
            for col in range(COLS):
                cell = self.grid[row][col]
                rx = MAZE_X + col * CELL
                ry = MAZE_Y + row * CELL

                if cell == 1:
                    pygame.draw.rect(
                        surface, WALL_COL,
                        pygame.Rect(rx, ry, CELL, CELL),
                        border_radius=4,
                    )
                elif cell == 2:
                    pygame.draw.circle(
                        surface, PELLET_COL,
                        (rx + CELL // 2, ry + CELL // 2), 3,
                    )
                elif cell == 3:
                    pulse = 5 + int(3 * abs(math.sin(tick * 0.06)))
                    pygame.draw.circle(
                        surface, PELLET_COL,
                        (rx + CELL // 2, ry + CELL // 2), pulse,
                    )
                elif cell == 4:
                    door = pygame.Rect(rx, ry + CELL // 2 - 2, CELL, 4)
                    pygame.draw.rect(surface, PINK, door)


# ===========================================================================
#  PacMan
# ===========================================================================
class PacMan:
    """Player-controlled character."""

    RADIUS: int = CELL // 2 - 2

    def __init__(self, maze: Maze) -> None:
        """Initialise Pac-Man using the given maze reference."""
        self.maze  = maze
        self.lives = 3
        self._spawn()

    def _spawn(self) -> None:
        """Place Pac-Man at his spawn tile and reset movement state."""
        self.col, self.row = PACMAN_START_COL, PACMAN_START_ROW
        self.x, self.y    = self.maze.cell_center(self.col, self.row)
        self.direction    = "LEFT"
        self.next_dir     = "LEFT"
        self.mouth_angle  = 0.0
        self.mouth_open   = True
        self.speed        = PACMAN_SPEED

    def respawn(self) -> None:
        """Reset to spawn position after losing a life."""
        self._spawn()

    def handle_input(self, event: pygame.event.Event) -> None:
        """Queue a direction change from a KEYDOWN event."""
        key_map: dict[int, str] = {
            pygame.K_UP: "UP", pygame.K_w: "UP",
            pygame.K_DOWN: "DOWN", pygame.K_s: "DOWN",
            pygame.K_LEFT: "LEFT", pygame.K_a: "LEFT",
            pygame.K_RIGHT: "RIGHT", pygame.K_d: "RIGHT",
        }
        if event.type == pygame.KEYDOWN and event.key in key_map:
            self.next_dir = key_map[event.key]

    def _can_move(self, direction: str, col: int, row: int) -> bool:
        """Return True if moving in the given direction from (col, row) is legal."""
        dc, dr = DIR_VEC[direction]
        return not self.maze.is_wall((col + dc) % COLS, row + dr)

    def update(self, dt: float) -> int:
        """
        Move Pac-Man, animate mouth, and eat any pellet underfoot.
        Returns points scored this frame.
        """
        cx, cy = self.maze.cell_center(self.col, self.row)
        near = abs(self.x - cx) < 4 and abs(self.y - cy) < 4

        if near:
            if (self.next_dir != self.direction
                    and self._can_move(self.next_dir, self.col, self.row)):
                self.direction = self.next_dir
                self.x, self.y = cx, cy
            if not self._can_move(self.direction, self.col, self.row):
                self._animate_mouth(dt)
                return 0

        dc, dr = DIR_VEC[self.direction]
        self.x += dc * self.speed * dt
        self.y += dr * self.speed * dt

        # Horizontal tunnel wrap
        total_w = COLS * CELL
        if self.x < MAZE_X - CELL:
            self.x = MAZE_X + total_w
        elif self.x > MAZE_X + total_w:
            self.x = MAZE_X - CELL

        self.col, self.row = self.maze.pixel_to_cell(self.x, self.y)
        self._animate_mouth(dt)
        return self.maze.eat_pellet(self.col, self.row)

    def _animate_mouth(self, dt: float) -> None:
        """Oscillate the mouth opening angle."""
        speed_deg = 280.0
        if self.mouth_open:
            self.mouth_angle = min(self.mouth_angle + speed_deg * dt, 40.0)
            if self.mouth_angle >= 40.0:
                self.mouth_open = False
        else:
            self.mouth_angle = max(self.mouth_angle - speed_deg * dt, 2.0)
            if self.mouth_angle <= 2.0:
                self.mouth_open = True

    def get_rect(self) -> pygame.Rect:
        """Return an axis-aligned bounding rectangle for collision."""
        r = self.RADIUS
        return pygame.Rect(self.x - r, self.y - r, r * 2, r * 2)

    def draw(self, surface: pygame.Surface) -> None:
        """Draw Pac-Man as a filled yellow pie with an animated mouth."""
        cx, cy = int(self.x), int(self.y)
        r = self.RADIUS

        angle_offset: dict[str, float] = {
            "RIGHT": 0.0, "LEFT": 180.0,
            "UP": 90.0,   "DOWN": 270.0,
        }
        base = math.radians(angle_offset[self.direction])
        gap  = math.radians(self.mouth_angle)

        start_a = base + gap
        end_a   = base + 2 * math.pi - gap

        steps = 32
        pts   = [(cx, cy)]
        step  = (end_a - start_a) / steps
        a     = start_a
        for _ in range(steps + 1):
            pts.append((cx + r * math.cos(a), cy - r * math.sin(a)))
            a += step
        pygame.draw.polygon(surface, YELLOW, pts)

        # Eye dot
        eye_ox = int(-r * 0.25 * math.sin(base))
        eye_oy = int(-r * 0.25 * math.cos(base)) - r // 2 + 2
        pygame.draw.circle(surface, BLACK, (cx + eye_ox, cy + eye_oy), 2)


# ===========================================================================
#  Ghost
# ===========================================================================
class Ghost:
    """
    A single ghost with full Pac-Man-accurate AI:
    scatter → chase mode cycling, frightened on power pellet,
    eyes-only return-to-pen after being eaten, and escalating speed.
    """

    RADIUS: int = CELL // 2 - 2

    def __init__(
        self,
        col: int, row: int,
        name: str, color: pygame.Color,
        maze: Maze,
    ) -> None:
        """Construct the ghost at its pen starting tile."""
        self.name       = name
        self.color      = color
        self.maze       = maze
        self.start_col  = col
        self.start_row  = row
        self._spawn()

    # ------------------------------------------------------------------
    def _spawn(self) -> None:
        """Reset position and all AI state."""
        self.col, self.row = self.start_col, self.start_row
        self.x, self.y    = self.maze.cell_center(self.col, self.row)
        self.direction    = random.choice(list(DIR_VEC.keys()))
        self.mode         = "scatter"
        self.fright_timer = 0.0
        self.speed        = GHOST_SPEED_BASE
        self.eaten        = False
        self.scatter_phase = 0
        self.phase_timer  = 0.0
        self.pen_timer    = random.uniform(0.5, 2.0)
        self.in_pen       = True

    def respawn(self) -> None:
        """Return ghost to its pen after Pac-Man loses a life."""
        self._spawn()

    # ------------------------------------------------------------------
    def set_frightened(self) -> None:
        """Trigger frightened mode (from power pellet)."""
        if self.mode != "eyes":
            self.mode = "frightened"
            self.fright_timer = FRIGHTENED_DURATION
            self.eaten = False

    def eat_ghost(self) -> None:
        """Switch ghost to eyes-only mode so it returns to pen."""
        self.mode  = "eyes"
        self.eaten = True

    # ------------------------------------------------------------------
    def _target_tile(
        self,
        pac: "PacMan",
        blinky: Optional["Ghost"],
    ) -> tuple[int, int]:
        """Calculate target tile based on current mode and personality."""
        if self.mode == "scatter":
            return SCATTER_CORNERS[self.name]
        if self.mode == "frightened":
            return (random.randint(0, COLS - 1), random.randint(0, ROWS - 1))
        if self.mode == "eyes":
            return (self.start_col, self.start_row)

        # Chase mode — personality-specific targeting
        pc, pr  = pac.col, pac.row
        dc, dr  = DIR_VEC[pac.direction]

        if self.name == "Blinky":
            return (pc, pr)

        if self.name == "Pinky":
            return (pc + dc * 4, pr + dr * 4)

        if self.name == "Inky":
            pivot_c = pc + dc * 2
            pivot_r = pr + dr * 2
            if blinky:
                return (2 * pivot_c - blinky.col, 2 * pivot_r - blinky.row)
            return (pc, pr)

        if self.name == "Clyde":
            if math.hypot(self.col - pc, self.row - pr) > 8:
                return (pc, pr)
            return SCATTER_CORNERS["Clyde"]

        return (pc, pr)

    # ------------------------------------------------------------------
    def _best_direction(self, target_col: int, target_row: int) -> str:
        """Choose the legal move that minimises Manhattan distance to target."""
        best_dir  = self.direction
        best_dist = float("inf")
        for d, (dc, dr) in DIR_VEC.items():
            if d == OPPOSITE.get(self.direction):
                continue
            nc = (self.col + dc) % COLS
            nr = self.row + dr
            if self.maze.is_wall(nc, nr):
                continue
            if self.maze.is_pen_door(nc, nr) and self.mode != "eyes":
                continue
            dist = math.hypot(nc - target_col, nr - target_row)
            if dist < best_dist:
                best_dist = dist
                best_dir  = d
        return best_dir

    # ------------------------------------------------------------------
    def update(
        self,
        dt: float,
        pac: "PacMan",
        blinky: Optional["Ghost"],
        elapsed: float,
    ) -> None:
        """
        Advance ghost AI by dt seconds.
        elapsed — total seconds since the level started (drives speed scaling).
        """
        # ---- Speed ----
        current_base = GHOST_SPEED_BASE + GHOST_ACCEL * elapsed
        if self.mode == "frightened":
            self.speed = GHOST_SPEED_FRIGHT
        elif self.mode == "eyes":
            self.speed = GHOST_SPEED_EYES
        else:
            self.speed = current_base

        # ---- Pen exit delay ----
        if self.in_pen:
            self.pen_timer -= dt
            if self.pen_timer > 0:
                return
            # Move toward pen exit
            exit_c, exit_r = HOME_COL, HOME_ROW - 2
            ex, ey = self.maze.cell_center(exit_c, exit_r)
            if abs(self.x - ex) < 4 and abs(self.y - ey) < 4:
                self.in_pen = False
            else:
                self._step_toward_pixel(ex, ey, dt)
            return

        # ---- Frightened timer ----
        if self.mode == "frightened":
            self.fright_timer -= dt
            if self.fright_timer <= 0:
                self.mode = "scatter"
                self.phase_timer = 0.0

        # ---- Scatter / chase phase cycling ----
        elif self.mode in ("scatter", "chase"):
            self.phase_timer += dt
            phase = min(self.scatter_phase, len(SCATTER_CHASE) - 1)
            scat_t, chase_t = SCATTER_CHASE[phase]
            if self.mode == "scatter" and self.phase_timer >= scat_t:
                self.mode = "chase"
                self.phase_timer = 0.0
            elif self.mode == "chase" and self.phase_timer >= chase_t:
                self.mode = "scatter"
                self.phase_timer = 0.0
                self.scatter_phase = min(
                    self.scatter_phase + 1, len(SCATTER_CHASE) - 1
                )

        # ---- Eyes return-to-pen ----
        if self.mode == "eyes":
            hx, hy = self.maze.cell_center(self.start_col, self.start_row)
            if abs(self.x - hx) < 4 and abs(self.y - hy) < 4:
                self.x, self.y = hx, hy
                self.col, self.row = self.start_col, self.start_row
                self.mode = "scatter"
                self.eaten = False
                self.in_pen = False
                return
            self._step_toward_pixel(hx, hy, dt)
            return

        # ---- Regular tile-based movement ----
        cx, cy = self.maze.cell_center(self.col, self.row)
        near   = abs(self.x - cx) < 3 and abs(self.y - cy) < 3
        if near:
            target = self._target_tile(pac, blinky)
            self.direction = self._best_direction(target[0], target[1])
            self.x, self.y = cx, cy

        dc, dr  = DIR_VEC[self.direction]
        self.x += dc * self.speed * dt
        self.y += dr * self.speed * dt

        total_w = COLS * CELL
        if self.x < MAZE_X - CELL:
            self.x = MAZE_X + total_w
        elif self.x > MAZE_X + total_w:
            self.x = MAZE_X - CELL

        self.col, self.row = self.maze.pixel_to_cell(self.x, self.y)

    # ------------------------------------------------------------------
    def _step_toward_pixel(self, tx: float, ty: float, dt: float) -> None:
        """Glide smoothly toward a pixel-space target (pen exit / eyes mode)."""
        dx, dy = tx - self.x, ty - self.y
        dist   = math.hypot(dx, dy)
        if dist < 1:
            return
        ratio   = min(self.speed * dt / dist, 1.0)
        self.x += dx * ratio
        self.y += dy * ratio
        self.col, self.row = self.maze.pixel_to_cell(self.x, self.y)

    # ------------------------------------------------------------------
    def get_rect(self) -> pygame.Rect:
        """Return a bounding rectangle for collision testing."""
        r = self.RADIUS
        return pygame.Rect(self.x - r, self.y - r, r * 2, r * 2)

    # ------------------------------------------------------------------
    def draw(self, surface: pygame.Surface, tick: int) -> None:
        """Draw ghost body, eyes, and frightened / eaten variants."""
        cx, cy = int(self.x), int(self.y)
        r = self.RADIUS

        if self.mode == "eyes":
            self._draw_eyes(surface, cx, cy, r)
            return

        if self.mode == "frightened":
            flash = (self.fright_timer < 2.5) and (tick // 15 % 2 == 0)
            body_col = WHITE if flash else DARK_BLUE
        else:
            body_col = self.color

        # --- Body ---
        pygame.draw.ellipse(surface, body_col,
                            pygame.Rect(cx - r, cy - r, r * 2, r * 2))
        pygame.draw.rect(surface, body_col,
                         pygame.Rect(cx - r, cy, r * 2, r))

        # Wavy skirt
        pts: list[tuple[int, int]] = []
        n = 6
        for i in range(n + 1):
            bx  = cx - r + i * (r * 2 // n)
            bump = 3 if i % 2 == 0 else 0
            pts.append((bx, cy + r - bump))
        pts.append((cx + r, cy + r + 2))
        pts.append((cx - r, cy + r + 2))
        pygame.draw.polygon(surface, body_col, pts)

        # --- Frightened face ---
        if self.mode == "frightened":
            pygame.draw.circle(surface, WHITE, (cx - r // 3, cy - 2), 3)
            pygame.draw.circle(surface, WHITE, (cx + r // 3, cy - 2), 3)
        else:
            self._draw_eyes(surface, cx, cy, r)

    def _draw_eyes(self, surface: pygame.Surface,
                   cx: int, cy: int, r: int) -> None:
        """Draw the two white-and-blue directional eyes."""
        for ex in (cx - r // 3, cx + r // 3):
            pygame.draw.circle(surface, WHITE, (ex, cy - 2), 4)
            pygame.draw.circle(surface, BLUE,  (ex + 1, cy - 1), 2)


# ===========================================================================
#  HUD
# ===========================================================================
class HUD:
    """Heads-up display drawn at the top of the window."""

    def __init__(self) -> None:
        """Initialise fonts once."""
        pygame.font.init()
        self.font_lg = pygame.font.SysFont("consolas", 22, bold=True)
        self.font_sm = pygame.font.SysFont("consolas", 14)

    def draw(
        self,
        surface: pygame.Surface,
        score: int,
        lives: int,
        level: int,
        ghost_speed: float,
    ) -> None:
        """Render score, level, lives and a speed warning."""
        pygame.draw.rect(surface, DARK_GRAY, pygame.Rect(0, 0, SCREEN_W, HUD_H))

        # Score
        surface.blit(
            self.font_lg.render(f"SCORE  {score:06d}", True, YELLOW), (12, 10)
        )

        # Level
        lv = self.font_lg.render(f"LVL {level}", True, CYAN)
        surface.blit(lv, (SCREEN_W // 2 - lv.get_width() // 2, 10))

        # Lives as mini pac-man icons
        for i in range(lives):
            lx = SCREEN_W - 20 - i * 24
            ly = HUD_H // 2
            pts = [(lx, ly)]
            for deg in range(30, 331, 10):
                rad = math.radians(deg)
                pts.append((lx + 8 * math.cos(rad), ly - 8 * math.sin(rad)))
            pygame.draw.polygon(surface, YELLOW, pts)

        # Speed escalation warning
        if ghost_speed > GHOST_SPEED_BASE + 30:
            warn = self.font_sm.render(
                f"!  GHOST SPEED {ghost_speed:.0f}  !", True, RED
            )
            surface.blit(warn, (12, HUD_H - 18))


# ===========================================================================
#  Game  — top-level controller
# ===========================================================================
class Game:
    """Main game: window, state machine, event routing, rendering."""

    def __init__(self) -> None:
        """Initialise pygame, window, and start at the menu."""
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        pygame.display.set_caption("PAC-MAN")
        self.clock  = pygame.time.Clock()
        self.hud    = HUD()

        self.font_xl = pygame.font.SysFont("consolas", 44, bold=True)
        self.font_lg = pygame.font.SysFont("consolas", 26, bold=True)
        self.font_md = pygame.font.SysFont("consolas", 17)
        self.font_sm = pygame.font.SysFont("consolas", 14)

        self._new_game()

    # ------------------------------------------------------------------
    def _new_game(self) -> None:
        """Reset score / level and go to the menu."""
        self.score = 0
        self.level = 1
        self.state = State.MENU
        self._setup_level()

    def _setup_level(self) -> None:
        """Build a fresh maze, Pac-Man and four ghosts for the current level."""
        self.maze   = Maze()
        self.pacman = PacMan(self.maze)
        self.ghosts: list[Ghost] = [
            Ghost(c, r, name, col, self.maze)
            for c, r, name, col in GHOST_STARTS
        ]
        self.elapsed: float        = 0.0
        self.ghost_eat_count: int  = 0
        self.state_timer: float    = 0.0
        self.tick: int             = 0

        # Fruit
        self.fruit_active: bool  = False
        self.fruit_col: int      = HOME_COL
        self.fruit_row: int      = HOME_ROW - 3
        self.fruit_timer: float  = 0.0
        self.fruit_shown: int    = 0
        self.fruit_trig1: int    = self.maze.total_pellets // 3
        self.fruit_trig2: int    = 2 * self.maze.total_pellets // 3

    @property
    def blinky(self) -> Ghost:
        """Convenience: Blinky is always ghosts[0]."""
        return self.ghosts[0]

    # ------------------------------------------------------------------
    def run(self) -> None:
        """Main loop — runs until the window is closed."""
        while True:
            dt = min(self.clock.tick(FPS) / 1000.0, 0.05)
            self._handle_events()
            self._update(dt)
            self._draw()
            pygame.display.flip()

    # ------------------------------------------------------------------
    def _handle_events(self) -> None:
        """Dispatch pygame events to the correct state handler."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()

            if event.type == pygame.KEYDOWN:
                k = event.key

                if k == pygame.K_ESCAPE:
                    pygame.quit(); sys.exit()

                elif self.state == State.MENU and k == pygame.K_RETURN:
                    self.state = State.PLAYING

                elif self.state in (State.PLAYING, State.PAUSED):
                    if k == pygame.K_p:
                        self.state = (
                            State.PAUSED if self.state == State.PLAYING
                            else State.PLAYING
                        )
                    else:
                        self.pacman.handle_input(event)

                elif self.state == State.GAME_OVER and k == pygame.K_r:
                    self._new_game()
                    self.state = State.PLAYING

                elif self.state == State.VICTORY and k == pygame.K_RETURN:
                    self.level += 1
                    self._setup_level()
                    self.state = State.PLAYING

    # ------------------------------------------------------------------
    def _update(self, dt: float) -> None:
        """Advance game logic based on the current state."""
        if self.state == State.PLAYING:
            self._update_playing(dt)
        elif self.state == State.LIFE_LOST:
            self.state_timer -= dt
            if self.state_timer <= 0:
                if self.pacman.lives <= 0:
                    self.state = State.GAME_OVER
                else:
                    self.pacman.respawn()
                    for g in self.ghosts:
                        g.respawn()
                    self.state = State.PLAYING
        elif self.state == State.VICTORY:
            self.state_timer -= dt

    def _update_playing(self, dt: float) -> None:
        """All active gameplay logic."""
        self.elapsed += dt
        self.tick    += 1

        # Pac-Man moves and eats pellets
        pts = self.pacman.update(dt)
        if pts == POWER_SCORE:
            self.score += pts
            self.ghost_eat_count = 0
            for g in self.ghosts:
                g.set_frightened()
        elif pts:
            self.score += pts

        # Fruit spawning
        eaten = self.maze.pellets_eaten
        if self.fruit_shown == 0 and eaten >= self.fruit_trig1:
            self._spawn_fruit()
        elif self.fruit_shown == 1 and eaten >= self.fruit_trig2:
            self._spawn_fruit()

        if self.fruit_active:
            self.fruit_timer -= dt
            if self.fruit_timer <= 0:
                self.fruit_active = False
            elif self.pacman.col == self.fruit_col and self.pacman.row == self.fruit_row:
                idx = min(self.level - 1, len(FRUIT_SCORES) - 1)
                self.score += FRUIT_SCORES[idx]
                self.fruit_active = False

        # Ghost updates
        for g in self.ghosts:
            g.update(dt, self.pacman, self.blinky, self.elapsed)

        # Collisions
        pac_rect = self.pacman.get_rect()
        for g in self.ghosts:
            if not pac_rect.colliderect(g.get_rect()):
                continue
            if g.mode == "frightened":
                g.eat_ghost()
                self.ghost_eat_count += 1
                idx = min(self.ghost_eat_count - 1, len(GHOST_SCORES) - 1)
                self.score += GHOST_SCORES[idx]
            elif g.mode not in ("eyes",):
                self._catch_pacman()
                return

        if self.maze.all_eaten():
            self.state = State.VICTORY
            self.state_timer = 2.5

    def _spawn_fruit(self) -> None:
        """Make a bonus fruit appear in the maze."""
        if self.fruit_shown < 2:
            self.fruit_active = True
            self.fruit_timer  = FRUIT_DURATION
            self.fruit_shown += 1

    def _catch_pacman(self) -> None:
        """Handle Pac-Man being caught by a non-frightened ghost."""
        self.pacman.lives -= 1
        self.state        = State.LIFE_LOST
        self.state_timer  = LIFE_LOST_PAUSE

    # ------------------------------------------------------------------
    #  Drawing
    # ------------------------------------------------------------------
    def _draw(self) -> None:
        """Master render method."""
        self.screen.fill(BLACK)

        if self.state == State.MENU:
            self._draw_menu()
            return

        # Always draw gameplay elements
        self.maze.draw(self.screen, self.tick)
        self._draw_fruit()
        self.pacman.draw(self.screen)
        for g in self.ghosts:
            g.draw(self.screen, self.tick)

        ghost_speed = GHOST_SPEED_BASE + GHOST_ACCEL * self.elapsed
        self.hud.draw(
            self.screen, self.score, self.pacman.lives,
            self.level, ghost_speed,
        )

        # State overlays
        if self.state == State.PAUSED:
            self._overlay("PAUSED", "Press  P  to continue", YELLOW)
        elif self.state == State.LIFE_LOST:
            self._overlay("CAUGHT!", "Respawning…", RED)
        elif self.state == State.GAME_OVER:
            self._overlay(
                "GAME  OVER",
                f"Final score: {self.score}     Press R to restart",
                RED,
            )
        elif self.state == State.VICTORY:
            self._overlay("LEVEL  CLEAR!", "Press ENTER for next level", CYAN)

    def _draw_menu(self) -> None:
        """Render the title / start screen."""
        # Title
        t = self.font_xl.render("PAC-MAN", True, YELLOW)
        self.screen.blit(t, (SCREEN_W // 2 - t.get_width() // 2, 100))

        s = self.font_lg.render("Press  ENTER  to start", True, WHITE)
        self.screen.blit(s, (SCREEN_W // 2 - s.get_width() // 2, 175))

        hints = [
            "Arrow keys / WASD  —  move",
            "P  —  pause / unpause",
            "Eat  ●  power pellets to frighten ghosts",
            "Ghosts accelerate the longer you survive!",
            "Eat frightened ghosts for bonus points",
        ]
        for i, line in enumerate(hints):
            surf = self.font_md.render(line, True, GRAY)
            self.screen.blit(
                surf, (SCREEN_W // 2 - surf.get_width() // 2, 255 + i * 30)
            )

        # Decorative ghost row
        gcolors = [RED, PINK, CYAN, ORANGE]
        for i, gc in enumerate(gcolors):
            gx = SCREEN_W // 2 - 80 + i * 52
            gy = 440
            r  = 16
            pygame.draw.ellipse(
                self.screen, gc, pygame.Rect(gx - r, gy - r, r * 2, r * 2)
            )
            pygame.draw.rect(
                self.screen, gc, pygame.Rect(gx - r, gy, r * 2, r)
            )
            # eyes
            for ex in (gx - r // 3, gx + r // 3):
                pygame.draw.circle(self.screen, WHITE, (ex, gy - 2), 4)
                pygame.draw.circle(self.screen, BLUE,  (ex + 1, gy - 1), 2)

        esc = self.font_sm.render("ESC — quit", True, DARK_GRAY)
        self.screen.blit(esc, (SCREEN_W - esc.get_width() - 10, SCREEN_H - 22))

    def _overlay(self, title: str, subtitle: str, color: pygame.Color) -> None:
        """Draw a semi-transparent overlay with a title and subtitle."""
        veil = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        veil.fill((0, 0, 0, 165))
        self.screen.blit(veil, (0, 0))

        t = self.font_xl.render(title, True, color)
        self.screen.blit(t, (SCREEN_W // 2 - t.get_width() // 2, 230))

        s = self.font_md.render(subtitle, True, WHITE)
        self.screen.blit(s, (SCREEN_W // 2 - s.get_width() // 2, 298))

    def _draw_fruit(self) -> None:
        """Render the bonus cherry if currently active."""
        if not self.fruit_active:
            return
        fx, fy = self.maze.cell_center(self.fruit_col, self.fruit_row)
        ix, iy = int(fx), int(fy)
        pygame.draw.circle(self.screen, FRUIT_COL, (ix, iy), 7)
        pygame.draw.line(self.screen, GREEN, (ix, iy - 7), (ix + 6, iy - 14), 2)


# ===========================================================================
#  Entry point
# ===========================================================================
def main() -> None:
    """Create and run the Pac-Man game."""
    game = Game()
    game.run()


if __name__ == "__main__":
    main()
