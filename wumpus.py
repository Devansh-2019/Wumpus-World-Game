import pygame
import sys
import random
import math
import time
from collections import deque

pygame.init()
try:
    # 8-bit unsigned mono — matches our bytearray synthesis; no numpy required
    pygame.mixer.init(frequency=44100, size=8, channels=1, buffer=1024)
except Exception:
    pass

# ─── Constants ───────────────────────────────────────────────────────────────
GRID_SIZE   = 6
CELL_SIZE   = 90
PANEL_W     = 280
WIDTH       = GRID_SIZE * CELL_SIZE + PANEL_W
HEIGHT      = GRID_SIZE * CELL_SIZE + 60
FPS         = 60

# Palette
WHITE       = (255, 255, 255)
C_BG        = (10, 12, 20)
C_CELL_DARK = (22, 28, 45)
C_CELL_MID  = (30, 38, 60)
C_VISITED   = (25, 42, 70)
C_SAFE      = (20, 80, 55)
C_DANGER    = (90, 40, 20)
C_WUMPUS    = (120, 20, 30)
C_PIT       = (15, 15, 35)
C_GOLD      = (200, 170, 30)
C_PANEL     = (14, 18, 32)
C_BORDER    = (40, 55, 100)
C_PLAYER    = (80, 180, 255)
C_TEXT      = (200, 215, 255)
C_DIM       = (80,  95, 140)
C_GREEN     = (60, 200, 120)
C_RED       = (220, 60, 60)
C_ORANGE    = (220, 140, 40)
C_PURPLE    = (160, 80, 220)
C_CYAN      = (40, 210, 210)

# Game states
STATE_PLAY   = "play"
STATE_WIN    = "win"
STATE_DEAD   = "dead"
STATE_MENU   = "menu"

# ─── Sound synthesis ─────────────────────────────────────────────────────────
def _make_sound(freq, duration_ms, waveform="sine", volume=0.3):
    """Build a pygame Sound using only stdlib — no numpy required.
    pygame.mixer is initialised with 8-bit unsigned mono @ 44100 Hz."""
    sample_rate = 44100
    n = int(sample_rate * duration_ms / 1000)
    buf = bytearray(n)
    for i in range(n):
        t = i / sample_rate
        if waveform == "sine":
            v = math.sin(2 * math.pi * freq * t)
        elif waveform == "square":
            v = 1.0 if math.sin(2 * math.pi * freq * t) >= 0 else -1.0
        else:                            # noise
            v = random.uniform(-1, 1)
        # short fade-in/out to avoid clicks
        fade = min(1.0, min(i, n - i) / max(1, int(sample_rate * 0.01)))
        val = int(127 + 127 * v * volume * fade)
        buf[i] = max(0, min(255, val))
    return pygame.mixer.Sound(buffer=bytes(buf))

def _make_chord(freqs, duration_ms, volume=0.25):
    sample_rate = 44100
    n = int(sample_rate * duration_ms / 1000)
    raw = [0.0] * n
    for freq in freqs:
        for i in range(n):
            t = i / sample_rate
            fade = min(1.0, min(i, n - i) / max(1, int(sample_rate * 0.05)))
            raw[i] += math.sin(2 * math.pi * freq * t) * fade
    peak = max(abs(v) for v in raw) or 1.0
    buf = bytearray(n)
    for i, v in enumerate(raw):
        buf[i] = max(0, min(255, int(127 + 127 * v / peak * volume)))
    return pygame.mixer.Sound(buffer=bytes(buf))

# Dummy silent sound used when synthesis fails
class _SilentSound:
    def play(self): pass

def _safe_make(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except Exception:
        return _SilentSound()

# Always define every sound symbol so NameError can never occur
SND_MOVE   = _safe_make(_make_sound, 440, 80,  "sine",   0.2)
SND_SAFE   = _safe_make(_make_chord, [523, 659, 784], 300, 0.25)
SND_DANGER = _safe_make(_make_sound, 180, 400, "square", 0.2)
SND_GOLD   = _safe_make(_make_chord, [523, 659, 784, 1047], 600, 0.3)
SND_DEATH  = _safe_make(_make_sound, 80,  800, "square", 0.3)
SND_WIN    = _safe_make(_make_chord, [523, 659, 784, 1047, 1319], 1000, 0.3)
SND_CLICK  = _safe_make(_make_sound, 880,  60, "sine",   0.15)
SND_ARROW  = _safe_make(_make_sound, 660, 150, "square", 0.2)

def play_snd(snd):
    try:
        snd.play()
    except Exception:
        pass

# ─── Fonts ───────────────────────────────────────────────────────────────────
try:
    FONT_TITLE  = pygame.font.SysFont("couriernew", 32, bold=True)
    FONT_BIG    = pygame.font.SysFont("couriernew", 22, bold=True)
    FONT_MED    = pygame.font.SysFont("couriernew", 16)
    FONT_SMALL  = pygame.font.SysFont("couriernew", 13)
    FONT_CELL   = pygame.font.SysFont("couriernew", 12, bold=True)
    FONT_ICON   = pygame.font.SysFont("segoeui",    20, bold=True)
except:
    FONT_TITLE = FONT_BIG = FONT_MED = FONT_SMALL = FONT_CELL = FONT_ICON = pygame.font.SysFont(None, 20)

# ─── Particle system ─────────────────────────────────────────────────────────
class Particle:
    def __init__(self, x, y, color, vx=0, vy=0, life=60, size=4):
        self.x, self.y = float(x), float(y)
        self.vx, self.vy = vx, vy
        self.color = color
        self.life = self.max_life = life
        self.size = size

    def update(self):
        self.x  += self.vx
        self.y  += self.vy
        self.vy += 0.15
        self.life -= 1

    def draw(self, surf):
        alpha = self.life / self.max_life
        r, g, b = self.color
        c = (int(r*alpha), int(g*alpha), int(b*alpha))
        sz = max(1, int(self.size * alpha))
        pygame.draw.circle(surf, c, (int(self.x), int(self.y)), sz)

class ParticleSystem:
    def __init__(self):
        self.particles = []

    def burst(self, x, y, color, n=20, speed=3):
        for _ in range(n):
            a  = random.uniform(0, 2*math.pi)
            sp = random.uniform(0.5, speed)
            self.particles.append(Particle(x, y, color,
                math.cos(a)*sp, math.sin(a)*sp,
                random.randint(30, 80), random.randint(2, 6)))

    def update_draw(self, surf):
        self.particles = [p for p in self.particles if p.life > 0]
        for p in self.particles:
            p.update()
            p.draw(surf)

# ─── AI Knowledge Base ───────────────────────────────────────────────────────
class KnowledgeBase:
    def __init__(self, size):
        self.size = size
        self.reset()

    def reset(self):
        n = self.size
        self.breeze   = {}   # (r,c) -> True/False/None
        self.stench   = {}
        self.visited  = set()
        self.safe     = set()
        self.pit_prob = {}   # (r,c) -> 0..1
        self.wumpus_prob = {}
        self.wumpus_alive = True
        self.wumpus_loc   = None  # known location
        self.frontier  = set()

    def adj(self, r, c):
        for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
            nr, nc = r+dr, c+dc
            if 0 <= nr < self.size and 0 <= nc < self.size:
                yield nr, nc

    def observe(self, r, c, has_breeze, has_stench):
        self.breeze[(r,c)]  = has_breeze
        self.stench[(r,c)]  = has_stench
        self.visited.add((r,c))
        self.safe.add((r,c))
        self._infer()

    def _infer(self):
        changed = True
        while changed:
            changed = False
            for (r,c) in list(self.visited):
                # No breeze → all neighbors safe from pits
                if self.breeze.get((r,c)) == False:
                    for nr,nc in self.adj(r,c):
                        if (nr,nc) not in self.safe:
                            self.safe.add((nr,nc))
                            changed = True
                # No stench → all neighbors safe from wumpus
                if self.stench.get((r,c)) == False:
                    for nr,nc in self.adj(r,c):
                        if (nr,nc) not in self.safe:
                            self.safe.add((nr,nc))
                            changed = True

        # Deduce wumpus location: if stench and exactly one neighbor not safe/visited
        wumpus_candidates = None
        for (r,c) in self.visited:
            if self.stench.get((r,c)) == True and self.wumpus_alive:
                cands = set()
                for nr,nc in self.adj(r,c):
                    if (nr,nc) not in self.safe and (nr,nc) not in self.visited:
                        cands.add((nr,nc))
                if wumpus_candidates is None:
                    wumpus_candidates = cands
                else:
                    wumpus_candidates &= cands
        if wumpus_candidates and len(wumpus_candidates) == 1:
            self.wumpus_loc = list(wumpus_candidates)[0]

        # Compute pit probability heuristic
        self.pit_prob = {}
        self.wumpus_prob = {}
        for r in range(self.size):
            for c in range(self.size):
                if (r,c) in self.safe or (r,c) in self.visited:
                    self.pit_prob[(r,c)] = 0.0
                    self.wumpus_prob[(r,c)] = 0.0
                    continue
                # Count how many visited breezy neighbors point here
                breezy_adj = sum(1 for nr,nc in self.adj(r,c)
                                 if self.breeze.get((nr,nc)) == True)
                non_breezy_adj = sum(1 for nr,nc in self.adj(r,c)
                                     if self.breeze.get((nr,nc)) == False)
                if non_breezy_adj > 0:
                    self.pit_prob[(r,c)] = 0.0
                else:
                    self.pit_prob[(r,c)] = min(1.0, breezy_adj * 0.35)

                stenchy_adj = sum(1 for nr,nc in self.adj(r,c)
                                  if self.stench.get((nr,nc)) == True)
                non_stenchy_adj = sum(1 for nr,nc in self.adj(r,c)
                                      if self.stench.get((nr,nc)) == False)
                if not self.wumpus_alive or non_stenchy_adj > 0:
                    self.wumpus_prob[(r,c)] = 0.0
                else:
                    self.wumpus_prob[(r,c)] = min(1.0, stenchy_adj * 0.4)

        # Update frontier
        self.frontier = set()
        for (r,c) in self.visited:
            for nr,nc in self.adj(r,c):
                if (nr,nc) not in self.visited:
                    self.frontier.add((nr,nc))

    def best_move(self, current):
        cr, cc = current
        # BFS to nearest safe unvisited
        unvisited_safe = [pos for pos in self.safe if pos not in self.visited]
        if not unvisited_safe:
            # Try frontier with lowest danger
            candidates = [(self.danger(r,c), r, c) for r,c in self.frontier]
            candidates.sort()
            if candidates:
                _, r, c = candidates[0]
                return self._path_to(current, (r,c))
            return None
        # Pick closest safe unvisited
        def dist(pos): return abs(pos[0]-cr) + abs(pos[1]-cc)
        target = min(unvisited_safe, key=dist)
        return self._path_to(current, target)

    def _path_to(self, src, dst):
        if src == dst: return None
        q = deque([(src, [])])
        seen = {src}
        while q:
            (r,c), path = q.popleft()
            for nr,nc in self.adj(r,c):
                if (nr,nc) in seen: continue
                seen.add((nr,nc))
                new_path = path + [(nr,nc)]
                if (nr,nc) == dst:
                    return new_path
                # Only traverse safe or visited
                if (nr,nc) in self.safe or (nr,nc) in self.visited:
                    q.append(((nr,nc), new_path))
        return None

    def danger(self, r, c):
        if (r,c) in self.safe: return 0.0
        return self.pit_prob.get((r,c), 0.1) + self.wumpus_prob.get((r,c), 0.1)

    def should_shoot(self, current):
        if not self.wumpus_alive or self.wumpus_loc is None:
            return None
        cr, cc = current
        wr, wc = self.wumpus_loc
        if wr == cr or wc == cc:
            return self.wumpus_loc
        return None

# ─── World generation ────────────────────────────────────────────────────────
def generate_world(size, pit_prob=0.15):
    world = {}
    wumpus_r, wumpus_c = 0, 0
    gold_r,   gold_c   = 0, 0
    start = (size-1, 0)

    # Place wumpus
    while True:
        wr, wc = random.randint(0, size-1), random.randint(0, size-1)
        if (wr, wc) != start and (wr, wc) != (size-1, 1) and (wr, wc) != (size-2, 0):
            wumpus_r, wumpus_c = wr, wc
            break

    # Place gold
    while True:
        gr, gc = random.randint(0, size-1), random.randint(0, size-1)
        if (gr, gc) != start and (gr, gc) != (wumpus_r, wumpus_c):
            gold_r, gold_c = gr, gc
            break

    # Build cells
    for r in range(size):
        for c in range(size):
            has_pit = (r,c) != start and random.random() < pit_prob
            world[(r,c)] = {
                "pit":    has_pit,
                "wumpus": (r == wumpus_r and c == wumpus_c),
                "gold":   (r == gold_r   and c == gold_c),
                "breeze": False,
                "stench": False,
            }

    # Propagate breeze/stench
    for r in range(size):
        for c in range(size):
            if world[(r,c)]["pit"]:
                for nr,nc in _adj(r,c,size):
                    world[(nr,nc)]["breeze"] = True
            if world[(r,c)]["wumpus"]:
                for nr,nc in _adj(r,c,size):
                    world[(nr,nc)]["stench"] = True

    return world, (wumpus_r, wumpus_c), (gold_r, gold_c)

def _adj(r, c, size):
    for dr,dc in [(-1,0),(1,0),(0,-1),(0,1)]:
        nr,nc = r+dr, c+dc
        if 0 <= nr < size and 0 <= nc < size:
            yield nr, nc

# ─── Main Game ───────────────────────────────────────────────────────────────
class WumpusGame:
    def __init__(self):
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("⚔  WUMPUS WORLD  ⚔")
        self.clock  = pygame.time.Clock()
        self.ps     = ParticleSystem()
        self.state  = STATE_MENU
        self.high_score = 0
        # pre-init all game attributes so they always exist even on menu screen
        self.world = {}
        self.player = (GRID_SIZE-1, 0)
        self.kb = KnowledgeBase(GRID_SIZE)
        self.arrows = 1
        self.score = 0
        self.has_gold = False
        self.wumpus_dead = False
        self.wumpus_pos = (0, 0)
        self.gold_pos = (0, 0)
        self.log = []
        self.ai_path = []
        self.ai_mode = False
        self.ai_timer = 0
        self.anim_player = [float(self.player[1]*CELL_SIZE + CELL_SIZE//2),
                            float(self.player[0]*CELL_SIZE + CELL_SIZE//2)]
        self.anim_target = self.anim_player[:]
        self.shake_timer = 0
        self.flash_color = None
        self.flash_timer = 0

    def _new_game(self):
        self.world, self.wumpus_pos, self.gold_pos = generate_world(GRID_SIZE)
        self.player = (GRID_SIZE-1, 0)
        self.kb     = KnowledgeBase(GRID_SIZE)
        self.arrows = 1
        self.score  = 0
        self.has_gold    = False
        self.wumpus_dead = False
        self.log    = ["► New game started", "► You enter the cave..."]
        self.ai_path     = []
        self.ai_mode     = False
        self.ai_timer    = 0
        self.anim_player = [float(self.player[1]*CELL_SIZE + CELL_SIZE//2),
                            float(self.player[0]*CELL_SIZE + CELL_SIZE//2)]
        self.anim_target = self.anim_player[:]
        self.shake_timer = 0
        self.flash_color = None
        self.flash_timer = 0
        self.state  = STATE_PLAY   # set last so _enter_cell sees correct state
        self._enter_cell()

    def _enter_cell(self):
        r, c = self.player
        cell = self.world[(r,c)]
        b = cell["breeze"]
        s = cell["stench"]
        self.kb.observe(r, c, b, s)
        self.score -= 1  # step cost

        msgs = []
        if b:  msgs.append("💨 You feel a breeze!")
        if s:  msgs.append("🦨 You smell a stench!")
        if cell["gold"] and not self.has_gold:
            msgs.append("✨ GOLD found! Press G to grab!")
        if not b and not s:
            msgs.append("✓ This room seems safe.")

        for m in msgs:
            self._log(m)

        if cell["pit"]:
            self._log("💀 You fell into a PIT!")
            self.score -= 1000
            self.state = STATE_DEAD
            self.shake_timer = 30
            self.flash_color = C_RED
            self.flash_timer = 45
            play_snd(SND_DEATH)
            self.ps.burst(*self.anim_player, C_RED, 40, 5)

        elif cell["wumpus"] and not self.wumpus_dead:
            self._log("💀 The WUMPUS devoured you!")
            self.score -= 1000
            self.state = STATE_DEAD
            self.shake_timer = 30
            self.flash_color = C_WUMPUS
            self.flash_timer = 45
            play_snd(SND_DEATH)
            self.ps.burst(*self.anim_player, C_WUMPUS, 40, 5)

        elif b or s:
            play_snd(SND_DANGER)
        else:
            play_snd(SND_SAFE)
            self.ps.burst(*self.anim_player, C_GREEN, 8, 2)

    def _log(self, msg):
        self.log.append(msg)
        if len(self.log) > 12:
            self.log.pop(0)

    def cell_center(self, r, c):
        return (c * CELL_SIZE + CELL_SIZE//2, r * CELL_SIZE + CELL_SIZE//2)

    def move(self, dr, dc):
        if self.state != STATE_PLAY: return
        nr, nc = self.player[0]+dr, self.player[1]+dc
        if 0 <= nr < GRID_SIZE and 0 <= nc < GRID_SIZE:
            self.player = (nr, nc)
            cx, cy = self.cell_center(nr, nc)
            self.anim_target = [float(cx), float(cy)]
            play_snd(SND_MOVE)
            self._enter_cell()

    def shoot(self, dr, dc):
        if self.state != STATE_PLAY or self.arrows <= 0: return
        self.arrows -= 1
        self.score  -= 10
        play_snd(SND_ARROW)
        self._log("🏹 Arrow fired!")
        pr, pc = self.player
        # Trace arrow in direction
        r, c = pr+dr, pc+dc
        while 0 <= r < GRID_SIZE and 0 <= c < GRID_SIZE:
            if self.world[(r,c)]["wumpus"] and not self.wumpus_dead:
                self.wumpus_dead = True
                self.kb.wumpus_alive = False
                self.world[(r,c)]["wumpus"] = False
                self.score += 500
                self._log("🎯 WUMPUS slain! +500")
                play_snd(SND_GOLD)
                self.ps.burst(*self.cell_center(r,c), C_RED, 40, 5)
                # Re-infer after wumpus death
                self.kb._infer()
                return
            r, c = r+dr, c+dc
        self._log("🏹 Arrow missed...")

    def grab_gold(self):
        if self.state != STATE_PLAY: return
        r, c = self.player
        if self.world[(r,c)]["gold"] and not self.has_gold:
            self.has_gold = True
            self.world[(r,c)]["gold"] = False
            self.score += 1000
            self._log("💰 GOLD collected! +1000")
            play_snd(SND_GOLD)
            self.ps.burst(*self.anim_player, C_GOLD, 50, 6)
            self.flash_color = C_GOLD
            self.flash_timer = 30

    def climb_out(self):
        if self.state != STATE_PLAY: return
        if self.player == (GRID_SIZE-1, 0):
            if self.has_gold:
                self.score += 500
                self._log("🏆 Escaped with gold! +500")
            else:
                self._log("🚪 Escaped without gold.")
            if self.score > self.high_score:
                self.high_score = self.score
            play_snd(SND_WIN)
            self.state = STATE_WIN
            self.ps.burst(*self.anim_player, C_GOLD, 80, 7)

    def ai_step(self):
        if self.state != STATE_PLAY: return
        if not self.ai_path:
            # Check if we should shoot
            shot = self.kb.should_shoot(self.player)
            if shot and self.arrows > 0:
                dr = shot[0] - self.player[0]
                dc = shot[1] - self.player[1]
                if dr != 0: dr = dr // abs(dr)
                if dc != 0: dc = dc // abs(dc)
                self.shoot(dr, dc)
                return
            # Grab gold if available
            r, c = self.player
            if self.world[(r,c)]["gold"] and not self.has_gold:
                self.grab_gold()
                return
            # Climb if we have gold at start
            if self.has_gold and self.player == (GRID_SIZE-1, 0):
                self.climb_out()
                return
            # Get best move
            path = self.kb.best_move(self.player)
            if path:
                self.ai_path = path
            else:
                self._log("🤖 AI: No safe path found.")
                self.ai_mode = False
                return
        # Follow path
        if self.ai_path:
            next_pos = self.ai_path.pop(0)
            dr = next_pos[0] - self.player[0]
            dc = next_pos[1] - self.player[1]
            self.move(dr, dc)

    def update(self, dt):
        # Smooth player animation
        tx, ty = self.anim_target
        self.anim_player[0] += (tx - self.anim_player[0]) * 0.25
        self.anim_player[1] += (ty - self.anim_player[1]) * 0.25

        if self.shake_timer > 0: self.shake_timer -= 1
        if self.flash_timer > 0: self.flash_timer -= 1

        # AI stepping
        if self.ai_mode and self.state == STATE_PLAY:
            self.ai_timer += 1
            if self.ai_timer >= 18:
                self.ai_timer = 0
                self.ai_step()

    # ── low-level drawing helpers ──────────────────────────────────────────────
    def _draw_pit(self, surf, cx, cy, size=34):
        """Dramatic spiral vortex: dark gradient rings + rotating purple arms."""
        t = time.time()
        # Gradient rings from edge inward
        for r2, col in [
            (size,      (35,  20,  70)),
            (size-6,    (20,  10,  50)),
            (size-12,   (10,   5,  30)),
            (size-18,   (4,    2,  15)),
            (size-24,   (0,    0,   5)),
            (max(2, size-30), (0, 0, 0)),
        ]:
            if r2 > 0:
                pygame.draw.circle(surf, col, (cx, cy), r2)
        # 3 rotating spiral arms
        arm_surf = pygame.Surface((CELL_SIZE, CELL_SIZE), pygame.SRCALPHA)
        off_x, off_y = cx - CELL_SIZE//2, cy - CELL_SIZE//2
        for arm in range(3):
            base_angle = t * 2.0 + arm * (2 * math.pi / 3)
            pts = []
            for step in range(18):
                frac  = step / 17
                angle = base_angle + frac * math.pi * 1.4
                r2    = int((size - 3) * (1 - frac * 0.75))
                pts.append((cx + int(math.cos(angle) * r2) - off_x,
                            cy + int(math.sin(angle) * r2) - off_y))
            for i in range(len(pts) - 1):
                fade = int(130 * (1 - i / len(pts)))
                pygame.draw.line(arm_surf, (120, 70, 230, fade), pts[i], pts[i+1], 2)
        surf.blit(arm_surf, (off_x, off_y))
        # outer glow + centre
        pygame.draw.circle(surf, (100, 50, 200), (cx, cy), size, 3)
        pygame.draw.circle(surf, (140, 80, 255), (cx, cy), size + 2, 1)
        pygame.draw.circle(surf, (0, 0, 0), (cx, cy), 4)

    def _draw_wumpus(self, surf, cx, cy, size=24):
        """Bold red beast: filled circle body + fangs."""
        # body
        pygame.draw.circle(surf, (180, 20, 20), (cx, cy), size)
        pygame.draw.circle(surf, (220, 60, 60), (cx, cy), size, 3)
        # eyes
        eo = size // 3
        pygame.draw.circle(surf, (255, 220, 0), (cx - eo, cy - eo//2), 5)
        pygame.draw.circle(surf, (255, 220, 0), (cx + eo, cy - eo//2), 5)
        pygame.draw.circle(surf, (0, 0, 0),     (cx - eo, cy - eo//2), 2)
        pygame.draw.circle(surf, (0, 0, 0),     (cx + eo, cy - eo//2), 2)
        # fangs
        fang_w = size // 4
        pygame.draw.polygon(surf, (255, 255, 255), [
            (cx - fang_w,     cy + size//3),
            (cx - fang_w//2,  cy + size//3 + 7),
            (cx,              cy + size//3),
        ])
        pygame.draw.polygon(surf, (255, 255, 255), [
            (cx + fang_w//2,  cy + size//3),
            (cx + fang_w,     cy + size//3 + 7),
            (cx + fang_w*2,   cy + size//3),
        ])

    def _draw_gold(self, surf, cx, cy, size=20):
        """Bright star shape using polygon."""
        t = time.time()
        pulse = 0.85 + 0.15 * math.sin(t * 4)
        outer = int(size * pulse)
        inner = int(size * 0.45 * pulse)
        pts = []
        for i in range(10):
            angle = math.pi / 5 * i - math.pi / 2
            r2 = outer if i % 2 == 0 else inner
            pts.append((cx + int(math.cos(angle) * r2),
                        cy + int(math.sin(angle) * r2)))
        pygame.draw.polygon(surf, (255, 210, 0), pts)
        pygame.draw.polygon(surf, (255, 255, 140), pts, 2)
        # shine dot
        pygame.draw.circle(surf, (255, 255, 200), (cx - outer//4, cy - outer//4), max(2, outer//6))

    def _draw_breeze(self, surf, x, y, cell_size):
        """Full-cell wind effect: multiple animated horizontal wave streaks."""
        t = time.time()
        bsurf = pygame.Surface((cell_size, cell_size), pygame.SRCALPHA)
        # 6 wave lines sweeping across the cell
        for i in range(6):
            wy     = 12 + i * 13
            speed  = 1.5 + i * 0.3
            phase  = t * speed + i * 0.9
            pts    = []
            for px2 in range(0, cell_size + 1, 3):
                wave = int(math.sin(phase + px2 * 0.18) * 4)
                pts.append((px2, wy + wave))
            if len(pts) >= 2:
                alpha = 90 + i * 18
                col   = (40 + i*10, 200 + i*5, 230, alpha)
                pygame.draw.lines(bsurf, col, False, pts, 2)
        # small drifting dots (wind particles)
        for i in range(8):
            phase = (t * 0.8 + i * 0.37) % 1.0
            px2   = int(phase * (cell_size + 10)) - 5
            py2   = 8 + (i * 11) % (cell_size - 16)
            r2    = 2 + (i % 2)
            alpha = int(160 * (1 - abs(phase - 0.5) * 2))
            pygame.draw.circle(bsurf, (100, 220, 255, alpha), (px2, py2), r2)
        surf.blit(bsurf, (x, y))
        # "BREEZE" label at bottom of cell
        lbl = FONT_SMALL.render("BREEZE", True, (60, 210, 240))
        surf.blit(lbl, (x + cell_size//2 - lbl.get_width()//2, y + cell_size - 18))

    def _draw_stench(self, surf, x, y, cell_size):
        """Full-cell toxic stench: bold rising green blobs + diagonal toxic streaks."""
        t = time.time()
        ssurf = pygame.Surface((cell_size, cell_size), pygame.SRCALPHA)

        # ── 1. Diagonal toxic streaks (like breeze but jagged/sickly) ─────────
        for i in range(5):
            speed  = 0.6 + i * 0.15
            phase  = (t * speed + i * 0.55) % 1.0
            # diagonal from bottom-left to top-right, scrolling upward
            start_x = int(phase * (cell_size + 30)) - 15
            pts = []
            for step in range(0, cell_size + 8, 5):
                jitter = int(math.sin(t * 2 + step * 0.25 + i * 1.1) * 5)
                pts.append((start_x + step, cell_size - step + jitter))
            pts = [(px2, py2) for px2, py2 in pts
                   if -5 <= px2 <= cell_size + 5 and -5 <= py2 <= cell_size + 5]
            if len(pts) >= 2:
                alpha = 160 + i * 15
                green = min(255, 170 + i * 12)
                pygame.draw.lines(ssurf, (60, green, 30, alpha), False, pts, 3)

        # ── 2. Large rising blobs (6 independent, clearly visible) ────────────
        blob_seeds = [(7, 0.0), (22, 0.33), (37, 0.66),
                      (52, 0.15), (67, 0.5),  (80, 0.82)]
        for bx, offset in blob_seeds:
            if bx >= cell_size: continue
            phase = (t * 0.55 + offset) % 1.0
            # y rises from bottom (phase=0) to top (phase=1)
            by    = int(cell_size - phase * (cell_size + 20)) + 10
            if by < -10 or by > cell_size + 10: continue
            # wobble size
            sz    = 9 + int(math.sin(t * 1.8 + offset * 6) * 3)
            alpha = min(255, int(220 * math.sin(phase * math.pi) + 20))
            # outer toxic green blob
            pygame.draw.circle(ssurf, (50,  min(255, 190 + int(offset*30)), 20, alpha),
                               (bx, by), sz)
            # inner bright highlight
            pygame.draw.circle(ssurf, (120, 255, 80, alpha // 2),
                               (bx - sz//4, by - sz//4), max(2, sz // 3))
            # rim
            pygame.draw.circle(ssurf, (80, 255, 60, min(255, alpha + 40)),
                               (bx, by), sz, 2)

        # ── 3. Thick toxic mist band at bottom ────────────────────────────────
        for px2 in range(0, cell_size, 1):
            wave   = int(math.sin(t * 1.2 + px2 * 0.12) * 6)
            mist_y = cell_size - 28 + wave
            for dy in range(22):
                a = max(0, int(90 * (1 - dy / 22)))
                py3 = mist_y + dy
                if 0 <= py3 < cell_size:
                    ssurf.set_at((px2, py3), (70, min(255, 180 + dy*2), 40, a))

        surf.blit(ssurf, (x, y))
        # label
        lbl = FONT_SMALL.render("STENCH", True, (100, 240, 80))
        surf.blit(lbl, (x + cell_size//2 - lbl.get_width()//2, y + cell_size - 18))

    def _draw_safe_mark(self, surf, cx, cy):
        """Green check mark."""
        pts = [
            (cx - 10, cy),
            (cx - 4,  cy + 7),
            (cx + 10, cy - 8),
        ]
        pygame.draw.lines(surf, (60, 220, 100), False, pts, 3)

    def _draw_player_icon(self, surf, px, py, has_gold):
        """Bright blue explorer with glow."""
        # glow rings
        for radius in range(22, 6, -5):
            alpha = max(0, 35 - radius)
            glow = pygame.Surface((radius*2, radius*2), pygame.SRCALPHA)
            pygame.draw.circle(glow, (*C_PLAYER, alpha), (radius, radius), radius)
            surf.blit(glow, (px - radius, py - radius))
        # shadow
        shadow_surf = pygame.Surface((28, 10), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow_surf, (0, 0, 0, 70), (0, 0, 28, 10))
        surf.blit(shadow_surf, (px - 14, py + 12))
        # body
        pygame.draw.circle(surf, (50, 140, 230), (px, py), 14)
        pygame.draw.circle(surf, (140, 210, 255), (px, py), 14, 2)
        # visor
        pygame.draw.arc(surf, (200, 240, 255),
                        pygame.Rect(px-8, py-8, 16, 10), 0, math.pi, 2)
        # gold badge
        if has_gold:
            pygame.draw.circle(surf, (255, 210, 0), (px + 10, py - 10), 6)
            pygame.draw.circle(surf, (255, 255, 140), (px + 10, py - 10), 6, 1)

    # ── main cell draw ─────────────────────────────────────────────────────────
    def draw_cell(self, surf, r, c, ox, oy):
        cell      = self.world[(r,c)]
        kb        = self.kb
        visited   = (r,c) in kb.visited
        safe      = (r,c) in kb.safe
        pit_p     = kb.pit_prob.get((r,c), 0.0)
        wump_p    = kb.wumpus_prob.get((r,c), 0.0)
        danger    = pit_p + wump_p
        game_over = self.state in (STATE_WIN, STATE_DEAD)

        x  = ox + c * CELL_SIZE
        y  = oy + r * CELL_SIZE
        cx = x + CELL_SIZE // 2
        cy = y + CELL_SIZE // 2
        rect = pygame.Rect(x, y, CELL_SIZE, CELL_SIZE)

        # ── 1. Background colour ──────────────────────────────────────────────
        if visited:
            base = C_SAFE if safe else (C_DANGER if danger > 0.4 else C_VISITED)
        else:
            base = (18, 50, 38) if safe else C_CELL_DARK
        pygame.draw.rect(surf, base, rect)

        # ── 2. Danger heatmap on unvisited cells ─────────────────────────────
        if not visited and danger > 0:
            ov = pygame.Surface((CELL_SIZE, CELL_SIZE), pygame.SRCALPHA)
            ov.fill((200, 40, 40, int(danger * 130)))
            surf.blit(ov, (x, y))

        # ── 3. Probability bars (left edge = wumpus, right edge = pit) ───────
        if wump_p > 0:
            bh = int((CELL_SIZE - 8) * wump_p)
            pygame.draw.rect(surf, (180, 30, 30),  (x + 2, y + CELL_SIZE - 4 - bh, 5, bh))
        if pit_p > 0:
            bh = int((CELL_SIZE - 8) * pit_p)
            pygame.draw.rect(surf, (60, 60, 180),  (x + CELL_SIZE - 7, y + CELL_SIZE - 4 - bh, 5, bh))

        # ── 4. Clue icons on visited cells (full cell fill) ───────────────────
        if visited:
            has_b = cell["breeze"]
            has_s = cell["stench"]
            if has_b:
                self._draw_breeze(surf, x, y, CELL_SIZE)
            if has_s:
                self._draw_stench(surf, x, y, CELL_SIZE)
            if not has_b and not has_s:
                self._draw_safe_mark(surf, cx, cy)

        # ── 5. Entity icons (pit / wumpus / gold) — drawn on top of clues ─────
        reveal = visited or game_over
        if reveal:
            if cell["pit"]:
                self._draw_pit(surf, cx, cy - 4)
                lbl = FONT_SMALL.render("PIT", True, (180, 150, 255))
                surf.blit(lbl, (cx - lbl.get_width()//2, y + 4))

            if cell["wumpus"] and not self.wumpus_dead:
                self._draw_wumpus(surf, cx, cy - 4)
                lbl = FONT_SMALL.render("WUMPUS", True, (255, 120, 120))
                surf.blit(lbl, (cx - lbl.get_width()//2, y + 4))

            elif cell["wumpus"] and self.wumpus_dead:
                pygame.draw.line(surf, (140, 30, 30), (cx-14, cy-14), (cx+14, cy+14), 4)
                pygame.draw.line(surf, (140, 30, 30), (cx+14, cy-14), (cx-14, cy+14), 4)
                lbl = FONT_SMALL.render("DEAD", True, (160, 60, 60))
                surf.blit(lbl, (cx - lbl.get_width()//2, y + 4))

            if cell["gold"]:
                self._draw_gold(surf, cx, cy - 4)
                lbl = FONT_SMALL.render("GOLD", True, (255, 235, 80))
                surf.blit(lbl, (cx - lbl.get_width()//2, y + 4))

        # ── 6. Fog of war ────────────────────────────────────────────────────
        if not visited and not game_over:
            fog = pygame.Surface((CELL_SIZE, CELL_SIZE), pygame.SRCALPHA)
            fog.fill((0, 0, 0, 150 if not safe else 70))
            surf.blit(fog, (x, y))

        # ── 7. AI path highlight ──────────────────────────────────────────────
        if self.ai_mode and (r,c) in self.ai_path:
            hl = pygame.Surface((CELL_SIZE, CELL_SIZE), pygame.SRCALPHA)
            hl.fill((80, 180, 255, 45))
            surf.blit(hl, (x, y))

        # ── 8. Wumpus known-location warning ─────────────────────────────────
        if self.kb.wumpus_loc == (r,c) and self.kb.wumpus_alive and not visited:
            hl = pygame.Surface((CELL_SIZE, CELL_SIZE), pygame.SRCALPHA)
            hl.fill((220, 40, 40, 55))
            surf.blit(hl, (x, y))
            # pulsing border
            pulse_w = 2 + int(abs(math.sin(time.time()*3)) * 2)
            pygame.draw.rect(surf, (220, 60, 60), rect, pulse_w)

        # ── 9. Cell border ────────────────────────────────────────────────────
        border_col = C_PLAYER if (r,c) == self.player else (C_DIM if (r,c) in kb.frontier else C_BORDER)
        pygame.draw.rect(surf, border_col, rect, 1)

        # ── 10. Start cell marker ─────────────────────────────────────────────
        if (r,c) == (GRID_SIZE-1, 0):
            lbl = FONT_SMALL.render("START", True, C_CYAN)
            surf.blit(lbl, (x + 2, y + 2))

        # ── 11. Coordinates ───────────────────────────────────────────────────
        coord = FONT_SMALL.render(f"{r},{c}", True, (C_DIM[0]//2, C_DIM[1]//2, C_DIM[2]//2))
        surf.blit(coord, (x + CELL_SIZE - 24, y + CELL_SIZE - 15))

    def draw_player(self, surf, ox, oy):
        px = int(self.anim_player[0]) + ox
        py = int(self.anim_player[1]) + oy
        self._draw_player_icon(surf, px, py, self.has_gold)

    def draw_panel(self, surf):
        ox = GRID_SIZE * CELL_SIZE
        panel_h = HEIGHT
        panel = pygame.Rect(ox, 0, PANEL_W, panel_h)
        pygame.draw.rect(surf, C_PANEL, panel)
        pygame.draw.line(surf, C_BORDER, (ox, 0), (ox, panel_h), 2)

        # Clip drawing to panel so nothing overflows
        surf.set_clip(pygame.Rect(ox, 0, PANEL_W, panel_h - 2))

        y = 10
        def header(text, col=C_TEXT):
            nonlocal y
            t = FONT_MED.render(text, True, col)
            surf.blit(t, (ox + 10, y))
            y += 22

        def row(label, val, col=C_TEXT):
            nonlocal y
            t1 = FONT_SMALL.render(label, True, C_DIM)
            t2 = FONT_SMALL.render(str(val), True, col)
            surf.blit(t1, (ox + 10, y))
            surf.blit(t2, (ox + 110, y))
            y += 16

        def divider():
            nonlocal y
            pygame.draw.line(surf, C_BORDER, (ox+6, y+2), (ox+PANEL_W-6, y+2), 1)
            y += 8

        # ── Stats ─────────────────────────────────────────────────────────────
        header("WUMPUS WORLD", C_GOLD)
        divider()
        row("Score:",   self.score,  C_GREEN if self.score >= 0 else C_RED)
        row("Best:",    self.high_score, C_GOLD)
        row("Arrows:",  str(self.arrows) + " left", C_ORANGE)
        row("Gold:",    "CARRYING!" if self.has_gold else "not found",
                        C_GOLD if self.has_gold else C_DIM)
        row("Wumpus:",  "DEAD" if self.wumpus_dead else "ALIVE",
                        C_GREEN if self.wumpus_dead else C_RED)
        row("Pos:",     f"({self.player[0]},{self.player[1]})", C_CYAN)
        row("Visited:", f"{len(self.kb.visited)}/{GRID_SIZE**2}", C_TEXT)

        # ── AI ────────────────────────────────────────────────────────────────
        divider()
        ai_col = C_GREEN if self.ai_mode else C_DIM
        header("AI SOLVER  " + ("ON" if self.ai_mode else "OFF  [TAB]"), ai_col)
        if self.kb.wumpus_loc:
            row("W-loc:", str(self.kb.wumpus_loc), C_RED)

        # ── Log ───────────────────────────────────────────────────────────────
        divider()
        header("LOG", C_DIM)
        for msg in self.log[-5:]:
            t = FONT_SMALL.render(msg[:34], True, C_TEXT)
            surf.blit(t, (ox + 8, y))
            y += 14

        # ── Legend ────────────────────────────────────────────────────────────
        divider()
        header("LEGEND", C_DIM)
        legend = [
            ((180, 30, 30),   "Wumpus  (red circle)"),
            ((80,  50, 180),  "Pit     (dark vortex)"),
            ((220, 190, 20),  "Gold    (yellow star)"),
            ((40,  200, 220), "Breeze  (cyan waves)"),
            ((60,  220, 60),  "Stench  (green blobs)"),
            ((60,  210, 100), "Safe    (green check)"),
        ]
        for dot_col, txt in legend:
            pygame.draw.circle(surf, dot_col, (ox + 16, y + 6), 5)
            t3 = FONT_SMALL.render(txt, True, C_TEXT)
            surf.blit(t3, (ox + 26, y))
            y += 14

        # ── Controls ──────────────────────────────────────────────────────────
        divider()
        header("CONTROLS", C_TEXT)
        controls = [
            ("WASD / Arrows", "Move"),
            ("G",             "Grab gold"),
            ("E",             "Escape cave"),
            ("F + Arrow",     "Shoot arrow"),
            ("TAB",           "Toggle AI"),
            ("R",             "New game"),
            ("ESC",           "Menu"),
        ]
        for key, act in controls:
            t1 = FONT_SMALL.render(f"[{key}]", True, C_ORANGE)
            t2 = FONT_SMALL.render(act,        True, C_TEXT)
            surf.blit(t1, (ox + 8,  y))
            surf.blit(t2, (ox + 118, y))
            y += 14

        surf.set_clip(None)

    def draw_overlay(self, surf):
        if self.state == STATE_WIN:
            self._draw_endscreen(surf, "✦ VICTORY ✦", C_GOLD,
                                 f"Score: {self.score}  |  Best: {self.high_score}",
                                 "Press R to play again")
        elif self.state == STATE_DEAD:
            self._draw_endscreen(surf, "✦ YOU DIED ✦", C_RED,
                                 f"Score: {self.score}",
                                 "Press R to try again")

    def _draw_endscreen(self, surf, title, col, sub, hint):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        surf.blit(overlay, (0,0))
        cx = (GRID_SIZE * CELL_SIZE) // 2
        cy = HEIGHT // 2

        # Box
        bw, bh = 360, 180
        bx, by = cx - bw//2, cy - bh//2
        pygame.draw.rect(surf, C_PANEL, (bx, by, bw, bh), border_radius=12)
        pygame.draw.rect(surf, col,     (bx, by, bw, bh), 3, border_radius=12)

        t1 = FONT_TITLE.render(title, True, col)
        surf.blit(t1, (cx - t1.get_width()//2, by + 20))

        t2 = FONT_MED.render(sub, True, C_TEXT)
        surf.blit(t2, (cx - t2.get_width()//2, by + 70))

        t3 = FONT_MED.render(hint, True, C_DIM)
        surf.blit(t3, (cx - t3.get_width()//2, by + 120))

    def draw_menu(self, surf):
        surf.fill(C_BG)
        cx = WIDTH // 2
        t = time.time()

        # Animated title
        for i, ch in enumerate("WUMPUS WORLD"):
            y_off = int(math.sin(t * 2 + i * 0.5) * 6)
            col = [C_GOLD, C_RED, C_ORANGE][i % 3]
            letter = FONT_TITLE.render(ch, True, col)
            surf.blit(letter, (cx - 180 + i * 30, 100 + y_off))

        lines = [
            ("⚔  Hunt the Wumpus. Grab the gold. Escape alive.", C_TEXT, FONT_MED, 180),
            ("",                                                  C_DIM,  FONT_MED, 200),
            ("You are an adventurer in a dark cave.",             C_DIM,  FONT_SMALL,220),
            ("Sense breezes (pits nearby) and stenches (Wumpus nearby).", C_DIM, FONT_SMALL, 240),
            ("Use logic to survive.",                             C_DIM,  FONT_SMALL,260),
            ("",                                                  C_DIM,  FONT_MED, 280),
            ("Press  ENTER  to start",                            C_GREEN, FONT_BIG, 320),
            ("Press  H  for hints overlay",                       C_DIM,  FONT_SMALL, 360),
        ]
        for text, col, font, y in lines:
            t2 = font.render(text, True, col)
            surf.blit(t2, (cx - t2.get_width()//2, y))

        # Decorative grid preview
        for i in range(4):
            for j in range(4):
                col2 = C_CELL_DARK if (i+j)%2==0 else C_CELL_MID
                pygame.draw.rect(surf, col2, (cx + 180 + j*20, 200 + i*20, 19, 19))
        pygame.draw.circle(surf, C_PLAYER, (cx + 190, 278), 7)

    def draw(self):
        if self.state == STATE_MENU:
            self.draw_menu(self.screen)
            self.ps.update_draw(self.screen)
            pygame.display.flip()
            return

        ox, oy = 0, 0
        # Shake
        if self.shake_timer > 0:
            ox = random.randint(-4, 4)
            oy = random.randint(-4, 4)

        # Background
        self.screen.fill(C_BG)

        # Flash
        if self.flash_timer > 0 and self.flash_color:
            alpha = int(self.flash_timer / 45 * 100)
            fl = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            fl.fill((*self.flash_color, alpha))
            self.screen.blit(fl, (0, 0))

        # Grid
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                self.draw_cell(self.screen, r, c, ox, oy)

        # Player
        self.draw_player(self.screen, ox, oy)

        # Grid border
        gw = GRID_SIZE * CELL_SIZE
        pygame.draw.rect(self.screen, C_BORDER, (ox, oy, gw, gw), 2)

        # Status bar bottom
        bar = pygame.Rect(0, GRID_SIZE*CELL_SIZE, gw, 60)
        pygame.draw.rect(self.screen, C_PANEL, bar)
        pygame.draw.line(self.screen, C_BORDER, (0, GRID_SIZE*CELL_SIZE), (gw, GRID_SIZE*CELL_SIZE), 1)
        status = f"Pos ({self.player[0]},{self.player[1]})  Score {self.score}  Visited {len(self.kb.visited)}/{GRID_SIZE**2}  {'[AI ON]' if self.ai_mode else ''}  {'[AIM ARROW TO SHOOT]' if getattr(self, 'shooting_mode', False) else ''}"
        t = FONT_MED.render(status, True, C_TEXT)
        self.screen.blit(t, (10, GRID_SIZE*CELL_SIZE + 20))

        # Panel
        self.draw_panel(self.screen)

        # Particles
        self.ps.update_draw(self.screen)

        # End overlays
        self.draw_overlay(self.screen)

        pygame.display.flip()

    def handle_shoot_key(self, key):
        dirs = {
            pygame.K_UP:    (-1, 0),
            pygame.K_DOWN:  ( 1, 0),
            pygame.K_LEFT:  ( 0,-1),
            pygame.K_RIGHT: ( 0, 1),
        }
        if key in dirs:
            self.shoot(*dirs[key])

    def run(self):
        self.shooting_mode = False

        while True:
            dt = self.clock.tick(FPS)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit(); sys.exit()

                elif event.type == pygame.KEYDOWN:
                    key = event.key

                    if self.state == STATE_MENU:
                        if key == pygame.K_RETURN:
                            play_snd(SND_CLICK)
                            self._new_game()

                    elif self.state in (STATE_WIN, STATE_DEAD):
                        if key == pygame.K_r:
                            play_snd(SND_CLICK)
                            self._new_game()
                        elif key == pygame.K_ESCAPE:
                            self.state = STATE_MENU

                    elif self.state == STATE_PLAY:
                        if key == pygame.K_r:
                            play_snd(SND_CLICK)
                            self._new_game()
                        elif key == pygame.K_ESCAPE:
                            self.state = STATE_MENU
                            self.shooting_mode = False
                        elif key == pygame.K_TAB:
                            self.ai_mode = not self.ai_mode
                            play_snd(SND_CLICK)
                            self._log(f"🤖 AI {'enabled' if self.ai_mode else 'disabled'}")
                        elif key == pygame.K_g:
                            self.grab_gold()
                        elif key == pygame.K_e:
                            self.climb_out()
                        elif key == pygame.K_f:
                            self.shooting_mode = True
                            self._log("🏹 Aim! Press arrow key to shoot.")
                        elif self.shooting_mode:
                            # consume any key as the shoot direction
                            self.handle_shoot_key(key)
                            self.shooting_mode = False
                        else:
                            # Movement
                            move_map = {
                                pygame.K_w: (-1, 0), pygame.K_UP:    (-1, 0),
                                pygame.K_s: ( 1, 0), pygame.K_DOWN:  ( 1, 0),
                                pygame.K_a: ( 0,-1), pygame.K_LEFT:  ( 0,-1),
                                pygame.K_d: ( 0, 1), pygame.K_RIGHT: ( 0, 1),
                            }
                            if key in move_map:
                                self.move(*move_map[key])

            self.update(dt)
            self.draw()


if __name__ == "__main__":
    WumpusGame().run()