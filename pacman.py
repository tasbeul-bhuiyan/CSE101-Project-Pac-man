import pygame
import sys
import math
import random
from collections import deque

CELL  = 24
COLS  = 28
ROWS  = 31
W     = COLS * CELL
H     = ROWS * CELL + 60
FPS   = 60

BLACK     = (  0,   0,   0)
WHITE     = (255, 255, 255)
YELLOW    = (255, 220,   0)
BLUE      = ( 33,  33, 255)
RED       = (255,   0,   0)
PINK      = (255, 182, 193)
CYAN      = (  0, 220, 220)
ORANGE    = (255, 165,   0)
DARK_BLUE = (  0,   0, 160)
SCARED_C  = ( 30,  30, 200)
SCARED2_C = (200, 200, 200)
DOT_C     = (255, 200, 150)
POWER_C   = (255, 255, 100)

UP    = ( 0, -1)
DOWN  = ( 0,  1)
LEFT  = (-1,  0)
RIGHT = ( 1,  0)
DIRS  = [UP, DOWN, LEFT, RIGHT]

# Map legend: 1=wall  0=dot  2=open  3=power-pellet  4=ghost-house(open but blocked for players)
# The ghost house has a clear exit at cols 13-14, row 11 -> row 9 corridor
RAW_MAP = [
"1111111111111111111111111111",  # 0
"1000000000000110000000000001",  # 1
"1011110111110110111110111101",  # 2
"1311110111110110111110111131",  # 3
"1011110111110110111110111101",  # 4
"1000000000000000000000000001",  # 5
"1011110110111111110110111101",  # 6
"1011110110111111110110111101",  # 7
"1000000110000220000110000001",  # 8  <- cols 13-14 open (ghost exit corridor)
"1111110111112002211110111111",  # 9  <- cols 12-15 open
"1111110111112002211110111111",  # 10 <- cols 12-15 open
"1111110110002002200110111111",  # 11 <- cols 11-16 open (ghost door area)
"1111110110044444400110111111",  # 12 <- ghost house top
"1111110110444444440110111111",  # 13 <- ghost house mid
"1111110110444444440110111111",  # 14 <- ghost house mid
"1111110110044444400110111111",  # 15 <- ghost house bottom
"1111110110000000000110111111",  # 16
"1111110110111111110110111111",  # 17
"1000000000000110000000000001",  # 18
"1011110111110110111110111101",  # 19
"1011110111110110111110111101",  # 20
"1300110000000000000000110031",  # 21
"1110110110111111110110110111",  # 22
"1110110110111111110110110111",  # 23
"1000000110000110000110000001",  # 24
"1011111111110110111111111101",  # 25
"1011111111110110111111111101",  # 26
"1000000000000000000000000001",  # 27
"1011110111110110111110111101",  # 28
"1000000000000110000000000001",  # 29
"1111111111111111111111111111",  # 30
]

def parse_map():
    grid = []
    for row_str in RAW_MAP:
        row = []
        for c in row_str:
            if   c == '1': row.append(1)
            elif c == '0': row.append(0)
            elif c == '3': row.append(3)
            elif c == '4': row.append(4)
            else:          row.append(2)  # '2' or space = open
        while len(row) < COLS: row.append(2)
        grid.append(row[:COLS])
    while len(grid) < ROWS:
        grid.append([2]*COLS)
    return grid

def cell_center(cx, cy):
    return (cx * CELL + CELL // 2, cy * CELL + CELL // 2)

# ── Drawing helpers ────────────────────────────────────────────────────────────
def draw_pacman_sprite(surf, x, y, radius, mouth_deg, facing_deg):
    cx, cy = int(x), int(y)
    r = max(radius, 4)
    m = max(1, min(int(mouth_deg), 88))
    pygame.draw.circle(surf, YELLOW, (cx, cy), r)
    # Carve mouth wedge in black
    pts = [(cx, cy)]
    a0, a1 = facing_deg - m, facing_deg + m
    steps = max(10, m // 2)
    for i in range(steps + 1):
        a = math.radians(a0 + (a1 - a0) * i / steps)
        pts.append((cx + r * math.cos(a), cy - r * math.sin(a)))
    if len(pts) >= 3:
        pygame.draw.polygon(surf, BLACK, pts)
    # Eye
    eye_ang = math.radians(facing_deg + 65)
    ex = cx + int(r * 0.5 * math.cos(eye_ang))
    ey = cy - int(r * 0.5 * math.sin(eye_ang))
    pygame.draw.circle(surf, BLACK, (ex, ey), max(2, r // 6))

def draw_walls(surf, grid):
    for ry in range(ROWS):
        for rx in range(COLS):
            if grid[ry][rx] == 1:
                rct = pygame.Rect(rx*CELL, ry*CELL, CELL, CELL)
                pygame.draw.rect(surf, DARK_BLUE, rct)
                pygame.draw.rect(surf, BLUE, rct, 1)

def draw_door(surf, grid):
    # Pink door bar at the ghost house opening (wherever row has 2-open flanked by 4s)
    for rx in range(COLS):
        if grid[11][rx] == 2 and rx in (11,12,13,14,15,16):
            pass  # the opening is free
    # Draw pink line across cols 13-14 at row 11 top
    px1, _ = cell_center(12, 11)
    px2, _ = cell_center(15, 11)
    _, py  = cell_center(13, 11)
    pygame.draw.line(surf, PINK, (px1 - CELL//2, py - CELL//2 + 2),
                                  (px2 + CELL//2, py - CELL//2 + 2), 3)

# ── Pac-Man ────────────────────────────────────────────────────────────────────
class Pacman:
    SPEED = 2.0

    def __init__(self, grid):
        self.grid = grid
        self.reset()

    def reset(self):
        # Confirmed open: col 13, row 27
        self.x        = 13 * CELL + CELL // 2
        self.y        = 27 * CELL + CELL // 2
        self.dir      = LEFT
        self.next_dir = LEFT
        self.mouth    = 30.0
        self.mspeed   = 3.0
        self.alive    = True
        self.death_t  = 0

    @property
    def cell(self):
        return (int(self.x) // CELL, int(self.y) // CELL)

    def _is_wall(self, gx, gy):
        gx = int(gx) % COLS
        gy = int(gy)
        if gy < 0 or gy >= ROWS:
            return True
        return self.grid[gy][gx] == 1  # only walls block pac-man

    def _can_enter_cell(self, cx, cy):
        cx = cx % COLS
        if cy < 0 or cy >= ROWS:
            return False
        v = self.grid[cy][cx]
        return v != 1 and v != 4   # pac-man can't enter ghost house

    def update(self, keys):
        if not self.alive:
            self.death_t += 1
            return

        if keys[pygame.K_LEFT]  or keys[pygame.K_a]: self.next_dir = LEFT
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]: self.next_dir = RIGHT
        if keys[pygame.K_UP]    or keys[pygame.K_w]: self.next_dir = UP
        if keys[pygame.K_DOWN]  or keys[pygame.K_s]: self.next_dir = DOWN

        cx, cy = self.cell
        centre_x = cx * CELL + CELL // 2
        centre_y = cy * CELL + CELL // 2
        near = abs(self.x - centre_x) < self.SPEED + 1 and abs(self.y - centre_y) < self.SPEED + 1

        # Try turning
        if near:
            nd = self.next_dir
            ncx, ncy = cx + nd[0], cy + nd[1]
            if self._can_enter_cell(ncx, ncy):
                self.dir = nd
                if self.dir in (LEFT, RIGHT): self.y = centre_y
                else:                         self.x = centre_x

        # Move or stop at wall
        dcx, dcy = cx + self.dir[0], cy + self.dir[1]
        if near and not self._can_enter_cell(dcx, dcy):
            self.x, self.y = centre_x, centre_y
        else:
            nx = self.x + self.dir[0] * self.SPEED
            ny = self.y + self.dir[1] * self.SPEED
            # pixel-level wall check
            margin = CELL * 0.40
            blocked = False
            for ddx, ddy in [(-1,-1),(1,-1),(-1,1),(1,1)]:
                tx = nx + ddx * margin
                ty = ny + ddy * margin
                if self._is_wall(int(tx) // CELL, int(ty) // CELL):
                    blocked = True
                    break
            if not blocked:
                self.x, self.y = nx, ny
            else:
                self.x, self.y = centre_x, centre_y

        # Tunnel wrap
        if self.x < 0:            self.x = COLS * CELL - 1.0
        if self.x >= COLS * CELL: self.x = 0.0

        # Mouth animation
        self.mouth += self.mspeed
        if self.mouth >= 40: self.mspeed = -3.0
        if self.mouth <= 2:  self.mspeed =  3.0

    def draw(self, surf):
        r = CELL // 2 - 2
        cx, cy = int(self.x), int(self.y)
        if not self.alive:
            progress = min(self.death_t / 50.0, 1.0)
            sr = int(r * (1.0 - progress))
            if sr > 1:
                draw_pacman_sprite(surf, cx, cy, sr, int(progress * 89), 0)
            return
        facing = {RIGHT: 0, UP: 90, LEFT: 180, DOWN: 270}.get(self.dir, 0)
        draw_pacman_sprite(surf, cx, cy, r, int(self.mouth), facing)

# ── Ghost ──────────────────────────────────────────────────────────────────────
SCATTER_TARGETS = [(COLS-2, 0), (1, 0), (COLS-2, ROWS-1), (1, ROWS-1)]
# Ghost exit waypoint: move to this cell to leave the house
GHOST_EXIT = (13, 8)   # confirmed open cell above house

class Ghost:
    SPD_NORMAL = 1.8
    SPD_SCARED = 1.2
    SPD_EATEN  = 3.5

    def __init__(self, idx, grid, color):
        self.idx   = idx
        self.grid  = grid
        self.color = color
        self.reset()

    def reset(self):
        # Place ghosts inside house at confirmed type-4 cells
        starts = [(13,13),(14,13),(13,14),(14,14)]
        sx, sy = starts[self.idx]
        self.x        = sx * CELL + CELL // 2
        self.y        = sy * CELL + CELL // 2
        self.dir      = UP
        self.state    = 'house'
        self.scared_t = 0
        self.house_t  = self.idx * 150   # stagger release
        self.exiting  = False            # True while navigating to exit

    @property
    def cell(self):
        return (int(self.x) // CELL, int(self.y) // CELL)

    def frighten(self):
        if self.state in ('chase', 'scatter'):
            self.state    = 'scared'
            self.scared_t = FPS * 7

    def mark_eaten(self):
        self.state   = 'eaten'
        self.exiting = False

    def _passable(self, gx, gy, allow_house=False):
        gx = gx % COLS
        if not (0 <= gy < ROWS): return False
        v = self.grid[gy][gx]
        if v == 1: return False
        if v == 4 and not allow_house: return False
        return True

    def _bfs(self, start, target, allow_house=False):
        sx, sy = start
        tx, ty = target
        if (sx, sy) == (tx, ty): return None
        visited = {(sx, sy)}
        q = deque([((sx, sy), None)])
        while q:
            (cx, cy), first = q.popleft()
            for d in DIRS:
                nx, ny = (cx + d[0]) % COLS, cy + d[1]
                if (nx, ny) in visited: continue
                if not self._passable(nx, ny, allow_house): continue
                visited.add((nx, ny))
                nf = first or d
                if (nx, ny) == (tx, ty): return nf
                q.append(((nx, ny), nf))
        return None

    def _choose_target(self, pacman):
        px, py = pacman.cell
        if self.state == 'scatter': return SCATTER_TARGETS[self.idx]
        if self.state == 'eaten':   return GHOST_EXIT
        if self.state == 'scared':  return (random.randint(0, COLS-1), random.randint(0, ROWS-1))
        # chase
        if self.idx == 0: return (px, py)
        if self.idx == 1:
            tx = px + pacman.dir[0] * 4
            ty = py + pacman.dir[1] * 4
            return (max(0, min(COLS-1, tx)), max(0, min(ROWS-1, ty)))
        if self.idx == 2:
            return (max(0, min(COLS-1, px - pacman.dir[0]*2)),
                    max(0, min(ROWS-1, py - pacman.dir[1]*2)))
        dx, dy = px - self.cell[0], py - self.cell[1]
        return (px, py) if math.hypot(dx, dy) > 8 else SCATTER_TARGETS[3]

    def update(self, pacman, mode):
        spd = self.SPD_NORMAL
        if self.state == 'scared': spd = self.SPD_SCARED
        if self.state == 'eaten':  spd = self.SPD_EATEN

        # ── House phase: bounce and wait, then exit ──────────────────────────
        if self.state == 'house':
            self.house_t -= 1
            if self.house_t <= 0:
                # Start exiting
                self.exiting = True
                self.state   = mode   # join the game

        if self.exiting:
            # Navigate to exit using house-passable BFS
            d = self._bfs(self.cell, GHOST_EXIT, allow_house=True)
            if d:
                self.dir = d
            # Check if we've reached exit
            ex, ey = GHOST_EXIT
            if abs(self.cell[0]-ex) <= 1 and abs(self.cell[1]-ey) <= 1:
                self.exiting = False

        # ── Scared timer ──────────────────────────────────────────────────────
        if self.state == 'scared':
            self.scared_t -= 1
            if self.scared_t <= 0:
                self.state = mode

        # ── Normal movement: BFS toward target ───────────────────────────────
        if not self.exiting and self.state != 'house':
            cx, cy = self.cell
            snap_x = abs(self.x - (cx * CELL + CELL // 2))
            snap_y = abs(self.y - (cy * CELL + CELL // 2))
            if snap_x < spd + 1 and snap_y < spd + 1:
                self.x = cx * CELL + CELL // 2
                self.y = cy * CELL + CELL // 2
                target = self._choose_target(pacman)
                allow_h = (self.state == 'eaten')
                d = self._bfs(self.cell, target, allow_house=allow_h)
                if d:
                    self.dir = d

        # ── Apply movement ────────────────────────────────────────────────────
        allow_h = self.exiting or self.state in ('house', 'eaten')
        nx = self.x + self.dir[0] * spd
        ny = self.y + self.dir[1] * spd
        ngx = int(nx) // CELL % COLS
        ngy = int(ny) // CELL
        if self._passable(ngx, ngy, allow_house=allow_h):
            self.x = nx % (COLS * CELL)
            self.y = ny

        # Tunnel wrap
        if self.x < 0:            self.x = COLS * CELL - 1.0
        if self.x >= COLS * CELL: self.x = 0.0

        # Respawn check when eaten
        if self.state == 'eaten':
            ex, ey = GHOST_EXIT
            if abs(self.cell[0]-ex) <= 1 and abs(self.cell[1]-ey) <= 1:
                # Teleport into house and reset
                self.x = 13 * CELL + CELL // 2
                self.y = 13 * CELL + CELL // 2
                self.state   = mode
                self.scared_t = 0
                self.exiting  = False
                self.house_t  = 0   # exit immediately

    def draw(self, surf):
        cx, cy = int(self.x), int(self.y)
        r = CELL // 2 - 1

        if self.state == 'eaten':
            for ex_off in (-r//3, r//3):
                ex = cx + ex_off; ey = cy - r // 4
                pygame.draw.circle(surf, WHITE, (ex, ey), r // 3)
                pygame.draw.circle(surf, BLUE,  (ex + self.dir[0], ey + self.dir[1]), r // 5)
            return

        blink = (self.state == 'scared' and
                 self.scared_t < FPS*2 and (self.scared_t // 12) % 2 == 0)
        color = SCARED2_C if blink else (SCARED_C if self.state == 'scared' else self.color)

        # Body
        pygame.draw.circle(surf, color, (cx, cy - r//4), r)
        pygame.draw.rect(surf, color, pygame.Rect(cx-r, cy-r//4, r*2, r+r//2))
        # Wavy skirt
        nw = 3; sw = (r*2) // nw
        pts = [(cx-r, cy+r//2)]
        for i in range(nw):
            x1=cx-r+i*sw; x2=x1+sw//2; x3=x1+sw
            pts += [(x2, cy+r//2+r//4), (x3, cy+r//2)]
        pts += [(cx+r, cy+r), (cx-r, cy+r)]
        pygame.draw.polygon(surf, color, pts)

        if self.state != 'scared':
            for ex_off in (-r//3, r//3):
                ex = cx+ex_off; ey = cy-r//3
                pygame.draw.circle(surf, WHITE, (ex, ey), r//3)
                pygame.draw.circle(surf, DARK_BLUE,
                    (ex+self.dir[0]*2, ey+self.dir[1]*2), r//5)
        else:
            for i in range(-1, 2):
                pygame.draw.circle(surf, WHITE, (cx+i*(r//3), cy-r//6), r//7)

# ── HUD ────────────────────────────────────────────────────────────────────────
def draw_hud(surf, font, score, hi, lives, level):
    by = ROWS * CELL
    pygame.draw.rect(surf, BLACK, (0, by, W, 60))
    surf.blit(font.render(f"SCORE {score:06d}", True, WHITE),  (8, by+4))
    surf.blit(font.render(f"BEST  {hi:06d}",   True, YELLOW), (W//2-65, by+4))
    surf.blit(font.render(f"LV {level}",        True, CYAN),  (W-60, by+4))
    r = 9
    for i in range(lives):
        lx=14+i*26; ly=by+38
        pts=[(lx,ly)]
        for a in range(30, 330, 6):
            rad=math.radians(a)
            pts.append((lx+r*math.cos(rad), ly-r*math.sin(rad)))
        pygame.draw.polygon(surf, YELLOW, pts)

# ── Game ───────────────────────────────────────────────────────────────────────
class Game:
    PHASES = [7, 20, 7, 20, 5, 20, 5, 9999]

    def __init__(self):
        pygame.init()
        self.screen  = pygame.display.set_mode((W, H))
        pygame.display.set_caption("Pac-Man")
        self.clock   = pygame.time.Clock()
        self.font    = pygame.font.SysFont("monospace", 15, bold=True)
        self.bigfont = pygame.font.SysFont("monospace", 38, bold=True)
        self.hi      = 0
        self.new_game()

    def new_game(self):
        self.orig   = parse_map()
        self.grid   = [r[:] for r in self.orig]
        self.score  = 0; self.lives = 3; self.level = 1
        self.pac    = Pacman(self.grid)
        self.ghosts = [Ghost(0,self.grid,RED),  Ghost(1,self.grid,PINK),
                       Ghost(2,self.grid,CYAN), Ghost(3,self.grid,ORANGE)]
        self.mode   = 'scatter'
        self.mode_t = FPS * self.PHASES[0]
        self.phase  = 0
        self.combo  = 0; self.msg = ""; self.msg_t = 0; self.state = 'play'

    def _reset_pos(self):
        self.pac.reset()
        for g in self.ghosts: g.reset()
        self.mode='scatter'; self.mode_t=FPS*self.PHASES[0]; self.phase=0; self.combo=0

    def handle_events(self):
        for e in pygame.event.get():
            if e.type == pygame.QUIT: pygame.quit(); sys.exit()
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE: pygame.quit(); sys.exit()
                if e.key == pygame.K_r: self.new_game()
                if e.key == pygame.K_RETURN and self.state == 'gameover': self.new_game()

    def update(self):
        if self.state == 'dead':
            self.pac.death_t += 1
            if self.pac.death_t > 55:
                self.lives -= 1
                if self.lives <= 0:
                    self.hi = max(self.hi, self.score); self.state = 'gameover'
                else:
                    self._reset_pos(); self.state = 'play'
            return
        if self.state != 'play': return

        keys = pygame.key.get_pressed()
        self.mode_t -= 1
        if self.mode_t <= 0:
            self.phase = (self.phase+1) % len(self.PHASES)
            self.mode  = 'scatter' if self.phase%2==0 else 'chase'
            self.mode_t = int(self.PHASES[self.phase] * FPS)

        self.pac.update(keys)
        for g in self.ghosts: g.update(self.pac, self.mode)

        cx, cy = self.pac.cell
        if 0 <= cy < ROWS and 0 <= cx < COLS:
            t = self.grid[cy][cx]
            if t == 0:
                self.grid[cy][cx] = 2; self.score += 10
            elif t == 3:
                self.grid[cy][cx] = 2; self.score += 50
                self.combo = 0
                for g in self.ghosts: g.frighten()

        for g in self.ghosts:
            if abs(g.x-self.pac.x) < CELL*0.75 and abs(g.y-self.pac.y) < CELL*0.75:
                if g.state == 'scared':
                    g.mark_eaten(); self.combo += 1
                    pts = 200*(2**(self.combo-1))
                    self.score += pts; self.msg = str(pts); self.msg_t = 60
                elif g.state not in ('eaten','house') and not g.exiting and self.pac.alive:
                    self.pac.alive = False; self.state = 'dead'; return

        if sum(1 for row in self.grid for v in row if v in (0,3)) == 0:
            self.level += 1
            self.grid = [r[:] for r in self.orig]
            self._reset_pos()
            self.msg = f"LEVEL {self.level}!"; self.msg_t = 120

        if self.msg_t > 0: self.msg_t -= 1
        self.hi = max(self.hi, self.score)

    def draw(self):
        self.screen.fill(BLACK)
        draw_walls(self.screen, self.grid)
        draw_door(self.screen, self.grid)

        tm = pygame.time.get_ticks()
        for ry in range(ROWS):
            for rx in range(COLS):
                v = self.grid[ry][rx]
                px, py = cell_center(rx, ry)
                if v == 0: pygame.draw.circle(self.screen, DOT_C, (px,py), 3)
                elif v == 3:
                    pr = int(abs(math.sin(tm/300.0))*3+6)
                    pygame.draw.circle(self.screen, POWER_C, (px,py), pr)

        for g in self.ghosts: g.draw(self.screen)
        self.pac.draw(self.screen)

        if self.msg_t > 0:
            s = self.bigfont.render(self.msg, True, YELLOW)
            self.screen.blit(s, (W//2-s.get_width()//2, H//2-40))

        draw_hud(self.screen, self.font, self.score, self.hi, self.lives, self.level)

        if self.state == 'gameover':
            ov = pygame.Surface((W,H), pygame.SRCALPHA); ov.fill((0,0,0,170))
            self.screen.blit(ov, (0,0))
            t1 = self.bigfont.render("GAME  OVER", True, RED)
            t2 = self.font.render("ENTER = new game    R = restart", True, WHITE)
            self.screen.blit(t1, (W//2-t1.get_width()//2, H//2-50))
            self.screen.blit(t2, (W//2-t2.get_width()//2, H//2+10))

        pygame.display.flip()

    def run(self):
        while True:
            self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(FPS)

if __name__ == "__main__":
    Game().run()
