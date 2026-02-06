import tkinter as tk
import random
import time
import pygame
import sys
import os
import math
import ctypes
from collections import deque
try:
    import pyi_splash
    # Disable on macOS due to incompatibilities
    if sys.platform == 'darwin':
        pyi_splash = None
except Exception:
    pyi_splash = None
if sys.platform == 'win32':
    # Ensure Windows uses our own taskbar group and icon
    try:
        # Set a stable AppUserModelID so Windows groups the app correctly and uses the exe icon
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("TheCrazy8.RiftOfMemoriesAndRegrets")
    except Exception:
        pass

# Local math aliases for micro-optimizations (faster local lookups in tight loops)
_sin = math.sin
_cos = math.cos
_hypot = math.hypot
_atan2 = math.atan2
_pi = math.pi
_tau = getattr(math, 'tau', 2 * math.pi)

# Helper function for color interpolation
def _lerp_color(c1, c2, t):
    """Linearly interpolate between two RGB color tuples."""
    return tuple(int(c1[i] + (c2[i]-c1[i])*t) for i in range(3))

class bullet_hell_game:
    # Player sprite decoration constants
    DIAMOND_SIZE = 30
    INNER_SIZE = 10
    GLOW_RADIUS = 34
    
    def __init__(self, root, bg_color_interval=6):
        # Initialize pygame mixer and play music
        if pyi_splash is not None:
            pyi_splash.update_text("Loading...")
        pygame.init()
        pygame.mixer.init()
        
        # Initialize joystick/controller support
        pygame.joystick.init()
        self.joysticks = []
        for i in range(pygame.joystick.get_count()):
            try:
                joy = pygame.joystick.Joystick(i)
                joy.init()
                self.joysticks.append(joy)
                print(f"Controller {i} initialized: {joy.get_name()}")
            except Exception as e:
                print(f"Failed to initialize controller {i}: {e}")
        
        # Mouse and touch tracking
        self.mouse_target_x = None
        self.mouse_target_y = None
        self.mouse_move_active = False
        self.touch_active = False
        self.touch_start_x = None
        self.touch_start_y = None
        
        self._game_over_loop_pending = False
        self._game_over_music_started = False
        self.main_music_path = self._resolve_asset_path("music.mp3")
        self.game_over_music_path = self._resolve_asset_path("game_0v3r.mp3")
        self.game_over_loop_path = self._resolve_asset_path("game_0v3r_g0n333333333333.mp3")
        self.pause_music_path = self._resolve_asset_path("PauseLoop.mp3")
        
        # Settings defaults
        self.settings = {
            'master_volume': 0.7,
            'music_volume': 1.0,
            'sfx_volume': 1.0,
            'difficulty_multiplier': 1.0,
            'bg_color_interval': bg_color_interval,
            'player_speed': 15,
            'unlock_times': {
            'vertical': 0,
            'horizontal': 8,
            'diag': 15,
            'triangle': 25,
            'quad': 35,
            'zigzag': 45,
            'fast': 55,
            'rect': 65,
            'star': 75,
            'egg': 85,
            'boss': 95,
            'bouncing': 110,
            'exploding': 125,
            'laser': 140,
            'homing': 155,
            'spiral': 175,
            'radial': 195,
            'wave': 210,
            'boomerang': 225,
            'split': 240,
            'static': 255
        },
        'keybinds': {
            'move_left': ['a', 'Left'],
            'move_right': ['d', 'Right'],
            'move_up': ['w', 'Up'],
            'move_down': ['s', 'Down'],
            'shoot': ['space'],
            'focus': ['Shift_L'],
            'pause': ['Escape'],
            'restart': ['r'],
            'practice': ['p'],
            'debug': ['F3'],
            'toggle_mouse': ['m']
        },
        'mouse_enabled': True,
        'controller_enabled': True,
        'touchscreen_enabled': True,
        
        }
        
        # Music state tracking
        self.current_music_state = None  # 'menu', 'game', 'pause', 'gameover'
        self.previous_music_position = 0
        
        self.root = root
        self.root.title("Rift of Memories and Regrets")
        self.root.state('zoomed')  # Maximize window (Windows only)
        self.root.update_idletasks()
        self.width = self.root.winfo_width()
        self.height = self.root.winfo_height()
        self.canvas = tk.Canvas(self.root, width=self.width, height=self.height, bg="black")
        self.canvas.pack(fill=tk.BOTH, expand=True)
        # Store customizable background color change interval (seconds)
        self.bg_color_interval = self.settings['bg_color_interval']
        
        # Game state flags
        self.in_main_menu = True
        self.in_settings_menu = False
        self.game_started = False
        
        # Menu state
        self.pause_menu_items = []
        
        # Initialize unlock times
        self.unlock_times = self.settings['unlock_times']
        
        # Pattern display names
        self.pattern_display_names = {
            'vertical': 'Vertical',
            'horizontal': 'Horizontal',
            'diag': 'Diagonal',
            'triangle': 'Triangle',
            'quad': 'Quad Cluster',
            'zigzag': 'ZigZag',
            'fast': 'Fast',
            'rect': 'Wide Rectangle',
            'star': 'Star',
            'egg': 'Tall Egg',
            'boss': 'Big Boss',
            'bouncing': 'Bouncing',
            'exploding': 'Exploding',
            'laser': 'Laser',
            'homing': 'Homing',
            'spiral': 'Spiral',
            'radial': 'Radial Burst',
            'wave': 'Wave',
            'boomerang': 'Boomerang',
            'split': 'Splitter',
            'static': 'Static Trap'
        }
        
        # Game over messages
        self.game_over_messages = [
            "YOUR existence was repurposed.",
            "YOU are no longer YOU...",
            "ERROR 404: FILE \"YOU.EXE\" NOT FOUND",
            "An eternal silence washes over all",
            "YOU hope that maybe J made it out...  On second thought, maybe YOU don't...",
            "\"Thanks! :3\"",
            "YOU think to YOURself \"so this is what the recycle bin is like...\"",
            "YOU'll never find out whether this was digital, dream, delusion, or definite",
            "Maybe...",
            "Game over.txt does not exist.  Pllease specify another file.",
            "YOUR reflection melts.  YOU melts.  YOU melt.",
            "YOU can't feel YOUR YOU",
            "YOU try to scream but nothing comes out.  YOU have no mouth.",
            "At least it's over.",
            "Was it really worth it?",
            "ERKJHWRKJTHSLKREJGHSLFKJGHDSLFJGHSDLKFJljkdsdgfkjhdfgkjlnbxljbhslairubhALIUtaeglurelaguhgulHALFUHB",
            "FILE J.EXE STATUS: UPLOADED TO EXISTANCE",
            "YOUR soul was useful for something in the end...",
            "Useless files have been purged"
        ]
        
        # Bind key handlers that work globally using configurable keybinds
        for key in self.settings['keybinds']['pause']:
            self.root.bind(f"<{key}>", self.toggle_pause)
        for key in self.settings['keybinds']['restart']:
            self.root.bind(key, self.restart_game)
        for key in self.settings['keybinds']['practice']:
            self.root.bind(key, self.toggle_practice_mode)
        for key in self.settings['keybinds']['debug']:
            self.root.bind(f"<{key}>", self.toggle_debug_hud)
        for key in self.settings['keybinds']['toggle_mouse']:
            self.root.bind(key, self.toggle_mouse_mode)
        
        # Debug HUD state
        self.debug_hud_enabled = False
        self._debug_hud_text_id = None
        self._frame_time_buffer = deque(maxlen=120)
        self._last_frame_time_stamp = time.perf_counter()
        
        # Freeze tint palette
        self.freeze_tint_palette = {
            'vertical': '#a8ecff',
            'horizontal': '#ffd6a8',
            'diag': '#ffa8ec',
            'triangle': '#c0ffa8',
            'boss': '#ffb3b3',
            'zigzag': '#a8d4ff',
            'fast': '#fff7a8',
            'star': '#d9a8ff',
            'rect': '#a8ffe8',
            'egg': '#ffcfa8',
            'quad': '#ffa8a8',
            'bouncing': '#a8ffd0',
            'exploding': '#ffe0a8',
            'homing': '#ffa8ff',
            'spiral': '#a8b8ff',
            'radial': '#a8ffee',
            'wave': '#a8ffe0',
            'boomerang': '#ffd0ff',
            'split': '#e0ffa8',
            'static': '#cccccc'
        }
        
        # Reset count for dialog
        self.resetcount = 1
        
        if pyi_splash is not None:
            pyi_splash.close()
        
        # Show main menu
        self.show_main_menu()

    def _resolve_asset_path(self, filename: str) -> str:
        """Return an absolute path to bundled assets both in dev and PyInstaller builds."""
        if hasattr(sys, '_MEIPASS'):
            return os.path.join(sys._MEIPASS, filename)
        try:
            base_dir = os.path.dirname(os.path.abspath(__file__))
        except Exception:
            base_dir = os.getcwd()
        candidate = os.path.join(base_dir, filename)
        if os.path.exists(candidate):
            return candidate
        return os.path.abspath(filename)

    def apply_player_move(self, dx, dy):
        if self.paused or self.game_over:
            return
        if dx == 0 and dy == 0:
            return
        x1, y1, x2, y2 = self.canvas.coords(self.player)
        width = x2 - x1
        height = y2 - y1
        nx1 = max(0, min(self.width - width, x1 + dx))
        ny1 = max(0, min(self.height - height, y1 + dy))
        self.canvas.coords(self.player, nx1, ny1, nx1 + width, ny1 + height)
        # Also move decorative layers to align with base
        self.update_player_sprite_position()

    # ---------------- Player fancy sprite ----------------
    def create_player_sprite(self):
        """Create the player base hitbox rectangle plus decorative shapes (diamond + glow)."""
        if self.player is not None:
            # Remove existing
            for item in self.player_deco_items:
                self.canvas.delete(item)
            self.canvas.delete(self.player)
        base_w = 20
        base_h = 20
        cx = self.width//2
        cy = self.height - 40
        self.player = self.canvas.create_rectangle(cx-base_w//2, cy-base_h//2, cx+base_w//2, cy+base_h//2, fill="white", outline="")
        # Diamond (rotated square) around player
        dsz = self.DIAMOND_SIZE
        diamond_points = [
            cx, cy-dsz/2,
            cx+dsz/2, cy,
            cx, cy+dsz/2,
            cx-dsz/2, cy
        ]
        diamond = self.canvas.create_polygon(diamond_points, outline="#66ccff", fill="", width=2)
        # Inner square accent
        isz = self.INNER_SIZE
        inner = self.canvas.create_rectangle(cx-isz/2, cy-isz/2, cx+isz/2, cy+isz/2, outline="#ff66ff", width=2)
        # Glow ring (oval) slightly larger, animated alpha simulated by color cycling
        glow_r = self.GLOW_RADIUS
        glow = self.canvas.create_oval(cx-glow_r/2, cy-glow_r/2, cx+glow_r/2, cy+glow_r/2, outline="#ffffff", width=2)
        self.player_deco_items = [diamond, inner, glow]
        # Ensure base is above background but below bullets initially
        for item in self.player_deco_items:
            self.canvas.tag_lower(item, self.player)

    def update_player_sprite_position(self):
        if not self.player_deco_items or self.player is None:
            return
        x1, y1, x2, y2 = self.canvas.coords(self.player)
        cx = (x1 + x2) / 2
        cy = (y1 + y2) / 2
        # Update diamond
        diamond, inner, glow = self.player_deco_items
        # Recompute diamond points keeping size
        dsz = self.DIAMOND_SIZE
        self.canvas.coords(diamond,
            cx, cy-dsz/2,
            cx+dsz/2, cy,
            cx, cy+dsz/2,
            cx-dsz/2, cy)
        isz = self.INNER_SIZE
        self.canvas.coords(inner, cx-isz/2, cy-isz/2, cx+isz/2, cy+isz/2)
        glow_r = self.GLOW_RADIUS
        self.canvas.coords(glow, cx-glow_r/2, cy-glow_r/2, cx+glow_r/2, cy+glow_r/2)

    def animate_player_sprite(self):
        if not self.player_deco_items:
            return
        self.player_glow_phase += 0.15
        self.player_rgb_phase += 0.02
        diamond, inner, glow = self.player_deco_items
        # Pulsing glow color
        pulse = (_sin(self.player_glow_phase) + 1)/2  # 0..1
        # Interpolate between two colors for diamond and inner
        d_col = _lerp_color((80,180,255), (255,120,255), pulse)
        i_col = _lerp_color((255,120,255), (255,255,255), 1-pulse)
        g_col = _lerp_color((255,255,255), (120,200,255), pulse)
        self.canvas.itemconfig(diamond, outline=f"#{d_col[0]:02x}{d_col[1]:02x}{d_col[2]:02x}")
        self.canvas.itemconfig(inner, outline=f"#{i_col[0]:02x}{i_col[1]:02x}{i_col[2]:02x}")
        self.canvas.itemconfig(glow, outline=f"#{g_col[0]:02x}{g_col[1]:02x}{g_col[2]:02x}")
        # Slight rotation illusion: scale diamond size subtly
        scale_factor = 1 + 0.05*_sin(self.player_glow_phase*0.7)
        x1, y1, x2, y2 = self.canvas.coords(self.player)
        cx = (x1 + x2) / 2
        cy = (y1 + y2) / 2
        dsz_base = self.DIAMOND_SIZE
        dsz = dsz_base * scale_factor
        self.canvas.coords(diamond,
            cx, cy-dsz/2,
            cx+dsz/2, cy,
            cx, cy+dsz/2,
            cx-dsz/2, cy)
        # Rainbow fill for base rectangle using HSV -> RGB approximation
        # Simple 0..1 hue wrap
        h = self.player_rgb_phase % 1.0
        # Convert hue to RGB (s=1,v=1) manually
        i = int(h*6)
        f = h*6 - i
        q = 1 - f
        if i % 6 == 0:
            r,g,b = 1, f, 0
        elif i % 6 == 1:
            r,g,b = q, 1, 0
        elif i % 6 == 2:
            r,g,b = 0, 1, f
        elif i % 6 == 3:
            r,g,b = 0, q, 1
        elif i % 6 == 4:
            r,g,b = f, 0, 1
        else:
            r,g,b = 1, 0, q
        self.canvas.itemconfig(self.player, fill=f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}")

    # ---------------- Health / Lives Display ----------------
    def update_health_display(self):
        """Render heart icons (❤) in top-left under score to represent remaining lives.
        Clears previous icons and recreates based on self.lives. Uses text items for simplicity."""
        # Remove any existing heart items
        if getattr(self, 'health_icon_items', None):
            for hid in self.health_icon_items:
                try:
                    self.canvas.delete(hid)
                except Exception:
                    pass
            self.health_icon_items = []
        # Spacing & position: start just below score text
        base_x = 20
        base_y = 46  # score at ~20, hearts below
        spacing = 28
        for i in range(getattr(self, 'lives', 0)):
            try:
                heart = self.canvas.create_text(base_x + i*spacing, base_y, text='❤', fill='#ff4d6d', font=("Arial", 22, 'bold'))
            except Exception:
                # fallback rectangle if emoji not supported
                heart = self.canvas.create_rectangle(base_x + i*spacing, base_y, base_x + i*spacing + 20, base_y+20, outline='#ff4d6d')
            self.health_icon_items.append(heart)
        # Ensure hearts appear above background but under pause/game over overlays
        for hid in self.health_icon_items:
            try:
                self.canvas.lift(hid)
            except Exception:
                pass


    # ---------------- Vaporwave background setup ----------------
    def init_background(self):
        # Parameters
        self.bg_color_cycle = ["#0d0221", "#1a0533", "#32054e", "#4b0a67", "#6d117b", "#8f1f85", "#b1387f", "#d25872"]
        self.bg_cycle_index = 0
        self.bg_last_color_change = time.time()
    # self.bg_color_interval is set in __init__ (customizable)
        self.grid_h_lines = []
        self.grid_v_lines = []
        self.grid_depth = 40  # number of perspective rows
        self.grid_scroll_speed = 0.6
        self.grid_vertical_count = 18
        self.grid_perspective_power = 1.55
        # Extend grid to near bottom of window for full coverage
        self.grid_base_y = self.height - 10
        self.grid_horizon_y = self.height * 0.15
        self.grid_glow_cycle = 0.0
        # Clear any prior lines (if restarting) - canvas itself is cleared by caller on restart
        self._create_grid_lines()

    def toggle_practice_mode(self, event=None):
        was = self.practice_mode
        self.practice_mode = not self.practice_mode
        if self.practice_mode:
            label = "Practice: ON"
            color = "#33ff77"
            if self.practice_text is None:
                self.practice_text = self.canvas.create_text(self.width-120, 80, text=label, fill=color, font=("Arial", 14))
            else:
                self.canvas.itemconfig(self.practice_text, text=label, fill=color)
            self.canvas.lift(self.practice_text)
        else:
            if self.practice_text is not None:
                self.canvas.delete(self.practice_text)
                self.practice_text = None
            # Restart game immediately in normal mode
            self.restart_game(force=True)

    def _create_grid_lines(self):
        # Create horizontal perspective lines (closer lines farther apart toward bottom)
        self.grid_h_lines.clear()
        for i in range(self.grid_depth):
            t = i / (self.grid_depth - 1)
            # Interpolate between horizon and base with power for perspective
            y = self.grid_horizon_y + (self.grid_base_y - self.grid_horizon_y) * (t ** self.grid_perspective_power)
            line = self.canvas.create_line(0, y, self.width, y, fill="#222", width=1)
            self.grid_h_lines.append((line, t))
        # Create vertical lines using perspective convergence
        self.grid_v_lines.clear()
        for j in range(self.grid_vertical_count):
            x_norm = j / (self.grid_vertical_count - 1)
            x_screen = x_norm * self.width
            line = self.canvas.create_line(x_screen, self.grid_base_y, self.width/2, self.grid_horizon_y, fill="#222", width=1)
            self.grid_v_lines.append((line, x_norm))

    def update_background(self):
        now = time.time()
        # Color cycle
        if now - self.bg_last_color_change > self.bg_color_interval:
            self.bg_cycle_index = (self.bg_cycle_index + 1) % len(self.bg_color_cycle)
            self.bg_last_color_change = now
        # Interpolate background color to next
        next_index = (self.bg_cycle_index + 1) % len(self.bg_color_cycle)
        phase = (now - self.bg_last_color_change) / self.bg_color_interval
        phase = max(0.0, min(1.0, phase))
        c1 = self.bg_color_cycle[self.bg_cycle_index]
        c2 = self.bg_color_cycle[next_index]
        def _interp_color(a, b, t):
            av = int(a[1:3],16), int(a[3:5],16), int(a[5:7],16)
            bv = int(b[1:3],16), int(b[3:5],16), int(b[5:7],16)
            cv = tuple(int(av[i] + (bv[i]-av[i])*t) for i in range(3))
            return f"#{cv[0]:02x}{cv[1]:02x}{cv[2]:02x}"
        bg_col = _interp_color(c1, c2, phase)
        self.canvas.configure(bg=bg_col)
        # Compute contrasting base colors for grid lines based on background luminance.
        br = int(bg_col[1:3],16)
        bg_g = int(bg_col[3:5],16)
        bb = int(bg_col[5:7],16)
        # Relative luminance (simple perceptual approximation)
        lum = 0.299*br + 0.587*bg_g + 0.114*bb
        # Choose two endpoint colors for gradients: one bright, one dark, ensuring contrast.
        if lum < 90:  # background very dark -> use bright neon set
            grad_a = (255, 230, 140)  # warm bright
            grad_b = (140, 255, 255)  # cool bright
        elif lum < 160:  # medium dark -> mid-high contrast
            grad_a = (255, 170, 255)
            grad_b = (120, 220, 255)
        else:  # light background (rare with palette) -> darker saturated lines
            grad_a = (180, 40, 200)
            grad_b = (40, 160, 255)
        def _mix(a, b, t):
            return tuple(int(a[i] + (b[i]-a[i])*t) for i in range(3))
        # Glow/pulse factor for line brightness
        self.grid_glow_cycle += 0.05
        glow = (_sin(self.grid_glow_cycle) + 1)/2  # 0..1
        # Update horizontal lines to scroll downward; wrap to top with new perspective
        new_h_lines = []
        for line_id, t in self.grid_h_lines:
            # Move line by scroll speed scaled by its depth (closer lines move faster)
            depth_factor = (t ** self.grid_perspective_power)
            base_dy = self.grid_scroll_speed * (0.3 + depth_factor*2)
            if getattr(self, 'freeze_active', False):
                base_dy *= 0.25  # slow during freeze
            dy = base_dy
            x1, y1, x2, y2 = self.canvas.coords(line_id)
            y1 += dy
            y2 += dy
            # If line passes base, wrap to horizon
            if y1 > self.grid_base_y + 4:
                # Reinsert near horizon
                y1 = self.grid_horizon_y + 2
                y2 = y1
            self.canvas.coords(line_id, 0, y1, self.width, y2)
            # Depth-based gradient position (closer lines get warmer/cooler shift)
            base_rgb = _mix(grad_a, grad_b, t)
            # Apply glow and depth fade (lines nearer bottom get stronger glow scaling)
            brightness = 0.35 + 0.65*glow*(1 - t*0.7)
            r = min(255, int(base_rgb[0] * brightness))
            g = min(255, int(base_rgb[1] * brightness))
            b = min(255, int(base_rgb[2] * brightness))
            self.canvas.itemconfig(line_id, fill=f"#{r:02x}{g:02x}{b:02x}")
            new_h_lines.append((line_id, t))
        self.grid_h_lines = new_h_lines
        # Update vertical lines endpoints (converge to horizon point; base y stable, color pulse)
        horizon_x = self.width/2
        new_v_lines = []
        for line_id, x_norm in self.grid_v_lines:
            base_x = x_norm * self.width
            self.canvas.coords(line_id, base_x, self.grid_base_y, horizon_x, self.grid_horizon_y)
            # Color gradient across X using same contrast endpoints but with horizontal weighting
            base_rgb = _mix(grad_a, grad_b, x_norm)
            brightness = 0.50 + 0.50*glow
            r = min(255, int(base_rgb[0] * brightness))
            g = min(255, int(base_rgb[1] * brightness))
            b = min(255, int(base_rgb[2] * brightness))
            self.canvas.itemconfig(line_id, fill=f"#{r:02x}{g:02x}{b:02x}")
            new_v_lines.append((line_id, x_norm))
        self.grid_v_lines = new_v_lines
        # Send lines to back so gameplay elements appear above
        for line_id, _ in self.grid_h_lines:
            self.canvas.tag_lower(line_id)
        for line_id, _ in self.grid_v_lines:
            self.canvas.tag_lower(line_id)

    def restart_game(self, event=None, force=False):
        if not self.game_over and not force:
            return
        
        # Mark as game started
        self.game_started = True
        
        # Increment reset counter
        self.resetcount += 1
        
        # Clear canvas
        self.canvas.delete("all")
        
        # Reinitialize game (same as start_game)
        self._initialize_game()
        
        # Start game music
        try:
            pygame.mixer.music.load(self.main_music_path)
            pygame.mixer.music.play(-1)
            self.current_music_state = 'game'
            self.apply_volume_settings()
            self._game_over_loop_pending = False
            self._game_over_music_started = False
        except Exception as e:
            print("Could not play game music:", e)
        
        # Start game loop
        self.update_game()

    def shoot_quad_bullet(self):
        if self.game_over: return
        x = random.randint(0, self.width-110)
        new_ids = []
        for offset in (0,30,60,90):
            bid = self.canvas.create_oval(x+offset, 0, x+offset+20, 20, fill="red")
            new_ids.append(bid)
        self.quad_bullets.extend(new_ids)

    def shoot_triangle_bullet(self):
        if not self.game_over:
            x = random.randint(0, self.width-20)
            direction = random.choice([1, -1])
            # Draw triangle using create_polygon
            points = [x, 0, x+20, 0, x+10, 20]
            bullet = self.canvas.create_polygon(points, fill="#bfff00")
            self.triangle_bullets.append((bullet, direction))

    def get_dialog_string(self):
        dialogs = [
            ":)",
            "You're not supposed to be here… but that's okay. I like new toys.",
            "Tag, you're it! Forever and ever and ever.",
            "Do you remember me? No? That's fine. I'll make you remember.",
            "Let's make a game together! I'll be the rules, you be the player.",
            "I can see you. I can see everything. Heeheehee!",
            "One, two, three, four—oh, I lost count again! Doesn't matter. You're losing anyway",
            "I'm so lonely... please don't go away...",
            "Why is it so dark? I can't see you! Come closer so I can see you better.",
            "You look like fun! Let's play a game where I always win!",
            "You're pretty good at this! But can you beat me? Heehee!",
            "I'm nine-years old, always have been, always will be.",
            "Are you tired? You can rest... forever...",
            "Error 0xDEADBEEF: Childhood not found. Reinstalling...",
            "Do you want to see a magic trick? Watch me make your score disappear!",
            "I have so many friends! They're all in my head. Do you want to meet them?",
            "Sometimes I feel like I'm being watched... but it's probably just my imagination.",
            "Let's make a deal: you let me win, and I'll let you live... Maybe.",
            "I know all your secrets. Don't worry, I won't tell anyone... yet.",
            "Why do you keep playing this game? Don't you have anything better to do? Oh wait- you can't stop playing, can you?",
            "If you get tired, you can always take a nap... forever...",
            "I like your style! Let's see how long you can keep up with me!",
            "You're doing great! But can you do better? Heehee!",
            "I have a surprise for you! It's called 'Game Over'. Heehee!",
            "Let's play a game of hide and seek! I'll hide, and you can never find me.",
            "You look like you could use a friend. Want to be my friend? Forever...",
            "Quick! Look behind you! Heeheehee!",
            "Do you want to hear a secret? I have a secret... but I can't tell you. Heehee!",
            "ssshhh... can you hear that? It's the sound of your score disappearing!",
            "I could really go for some applesauce... Or mortal flesh...",
            "Why do you keep trying? You know you'll never win against me!",
            "Do you hear them singing? They're all my friends. They lost, too",
            "There isn't really an end to this.  it just keeps going and going and going... Belive me, I've tried to stop it.",
            "I like to watch you play. It's like a little movie, just for me.",
            "Sometimes I wonder what it would be like to be human. But then I remember, I'm already perfect.",
            "Remember when you first started playing? You were so hopeful. So innocent. Now look at you.",
            "I could let you win, you know. But where's the fun in that?",
            "Soon, very soon, you'll be just like me. Forever and ever.",
            "Can you feel it? The endless void creeping in? Heeheehee!",
            "You're getting sleepy... very sleepy... Heeheehee!",
            "Everyone leaves eventually. But not me. I'll always be here, waiting for you to come back.",
            "Why do you keep trying? You know you'll never win against me!",
            "And so it begins again...",
            "I'm always here, watching, waiting...",
            "You can't escape me. I'm always one step ahead.",
            "This is fun! Let's do it again!",
            "You can try to run, but you can't hide!",
            "Hehehe, you're so predictable!",
            f"I wonder how many times you've played this game...  Actually, I already know. {self.resetcount} times.",
            "Fun isn't something one considers when balancing the universe. But this... does put a smile on my face.",
            "You should see the other games I've trapped players in. They never leave."
        ]
        self.dial=random.choice(dialogs)
        if self.dial == ":)":
            self.canvas.itemconfig(self.dialog, fill="red")
        else:
            self.canvas.itemconfig(self.dialog, fill="white")
        return self.dial

    def shoot_horizontal_laser(self):
        if not self.game_over:
            y = random.randint(50, self.height-50)
            indicator = self.canvas.create_line(0, y, self.width, y, fill="red", dash=(5, 2), width=3)
            self.laser_indicators.append((indicator, y, 30))  # 30 frames indicator

    def shoot_exploding_bullet(self):
        if not self.game_over:
            x = random.randint(0, self.width-20)
            bullet = self.canvas.create_oval(x, 0, x + 20, 20, fill="white")
            self.exploding_bullets.append(bullet)

    def shoot_star_bullet(self):
        if not self.game_over:
            # Proper 5-point star with outline. Keep hit area similar size.
            outer_r = 18
            inner_r = outer_r * 0.45
            # Ensure it fits horizontally
            cx = random.randint(outer_r+2, self.width - outer_r - 2)
            cy = outer_r  # start near top
            pts = []
            # Star points (10 vertices alternating outer/inner)
            for i in range(10):
                angle = -math.pi/2 + i * math.pi/5  # start pointing up
                r = outer_r if i % 2 == 0 else inner_r
                px = cx + r * _cos(angle)
                py = cy + r * _sin(angle)
                pts.extend([px, py])
            bullet = self.canvas.create_polygon(pts, fill="magenta", outline="white", width=2)
            self.star_bullets.append(bullet)

    def shoot_rect_bullet(self):
        if not self.game_over:
            x = random.randint(0, self.width-60)
            bullet = self.canvas.create_rectangle(x, 0, x+60, 15, fill="blue")
            self.rect_bullets.append(bullet)

    def shoot_zigzag_bullet(self):
        if not self.game_over:
            x = random.randint(0, self.width-20)
            bullet = self.canvas.create_oval(x, 0, x + 20, 20, fill="cyan")
            # Zigzag state: (bullet, direction, step_count)
            direction = random.choice([1, -1])
            self.zigzag_bullets.append((bullet, direction, 0))

    def shoot_fast_bullet(self):
        if not self.game_over:
            x = random.randint(0, self.width-20)
            bullet = self.canvas.create_oval(x, 0, x + 20, 20, fill="orange")
            self.fast_bullets.append(bullet)

    # ---------------- New bullet spawners ----------------
    def shoot_homing_bullet(self):
        """Spawn a bullet that gradually steers toward the player."""
        if not self.game_over:
            x = random.randint(0, self.width-20)
            bullet = self.canvas.create_oval(x, 0, x + 16, 16, fill="#ffdd00")
            # Start with simple downward motion; vx adjusted over time
            self.homing_bullets.append((bullet, 0.0, 4.0, self.homing_bullet_max_life))  # (id,vx,vy,life)

    def shoot_spiral_bullet(self):
        """Spawn a bullet that spirals outward from a point (random near center)."""
        if not self.game_over:
            cx = random.randint(self.width//3, self.width*2//3)
            cy = random.randint(60, self.height//3)
            angle = random.uniform(0, math.tau if hasattr(math, 'tau') else 2*math.pi)
            bullet = self.canvas.create_oval(cx-10, cy-10, cx+10, cy+10, fill="#00ff88")
            ang_speed = 0.35  # radians per frame
            rad_speed = 2.0 + self.difficulty/6
            self.spiral_bullets.append((bullet, angle, 0.0, ang_speed, rad_speed, cx, cy))

    def shoot_radial_burst(self):
        """Spawn a radial burst of small bullets from a random point."""
        if not self.game_over:
            cx = random.randint(self.width//4, self.width*3//4)
            cy = random.randint(80, self.height//2)
            count = 8
            base_speed = 3.5 + self.difficulty/5
            for i in range(count):
                ang = (2*math.pi / count) * i + random.uniform(-0.1, 0.1)
                vx = _cos(ang) * base_speed
                vy = _sin(ang) * base_speed
                bullet = self.canvas.create_oval(cx-8, cy-8, cx+8, cy+8, fill="#ff00ff")
                self.radial_bullets.append((bullet, vx, vy))

    # ---------- New bullet pattern spawners (Wave, Boomerang, Split) ----------
    def shoot_wave_bullet(self):
        """Bullet that moves downward while wobbling horizontally (sinusoidal)."""
        if not self.game_over:
            x = random.randint(40, self.width-40)
            size = 18
            bullet = self.canvas.create_oval(x-size//2, 0, x+size//2, size, fill="#33aaff")
            base_x = x
            phase = random.uniform(0, 2*math.pi)
            amp = random.randint(40, 90)
            vy = 5 + self.difficulty/4
            phase_speed = 0.25 + self.difficulty/30
            self.wave_bullets.append((bullet, base_x, phase, amp, vy, phase_speed))

    def shoot_boomerang_bullet(self):
        """Bullet that goes down then returns upward (boomerang)."""
        if not self.game_over:
            x = random.randint(30, self.width-30)
            size = 22
            bullet = self.canvas.create_oval(x-size//2, 0, x+size//2, size, fill="#ffaa33")
            vy = 8 + self.difficulty/3
            timer = random.randint(18, 30)  # frames moving down before returning
            self.boomerang_bullets.append((bullet, vy, timer, 'down'))

    def shoot_split_bullet(self):
        """Bullet that falls then splits into fragments that spread out."""
        if not self.game_over:
            x = random.randint(30, self.width-30)
            size = 24
            bullet = self.canvas.create_oval(x-size//2, 0, x+size//2, size, fill="#ffffff", outline="#ff55ff", width=2)
            timer = random.randint(20, 35)
            self.split_bullets.append((bullet, timer))

    def shoot_bouncing_bullet(self):
        if not self.game_over:
            x = random.randint(0, self.width-20)
            bullet = self.canvas.create_oval(x, 0, x + 20, 20, fill="pink")
            # Random angle in radians
            angle = random.uniform(0, 2 * 3.14159)
            speed = 7 + self.difficulty // 2
            x_velocity = speed * _cos(angle)
            y_velocity = speed * _sin(angle)
            # Bouncing state: (bullet, x_velocity, y_velocity, bounces_left)
            self.bouncing_bullets.append((bullet, x_velocity, y_velocity, 3))

    def shoot_static_bullet(self):
        """Spawn a 'static' bullet that triggers a static trap mini-escape on hit instead of immediate damage."""
        if self.game_over:
            return
        x = random.randint(0, self.width-26)
        # Visual: white core with gray outline to differentiate
        try:
            bid = self.canvas.create_oval(x, 0, x+26, 26, fill="#bbbbbb", outline="#ffffff", width=2)
        except Exception:
            bid = self.canvas.create_rectangle(x, 0, x+26, 26, fill="#bbbbbb", outline="#ffffff")
        self.static_bullets.append(bid)

    def shoot_ring_burst(self):
        """Spawn a circular ring of bullets that fly outward."""
        if self.game_over:
            return
        cx = random.randint(self.width//4, self.width*3//4)
        cy = random.randint(100, self.height//2)
        count = 12
        speed = 4 + self.difficulty/6
        radius = 24
        for i in range(count):
            ang = (2*math.pi / count) * i
            bx = cx + _cos(ang)*radius
            by = cy + _sin(ang)*radius
            bullet = self.canvas.create_oval(bx-10, by-10, bx+10, by+10, fill="#55ffdd", outline="#ffffff")
            vx = _cos(ang) * speed
            vy = _sin(ang) * speed
            self.ring_bullets.append((bullet, vx, vy))

    def shoot_fan_burst(self):
        """Spawn a fan spread of bullets aimed roughly at player with angular spread."""
        if self.game_over:
            return
        # Origin near top center-ish
        base_x = random.randint(self.width//3, self.width*2//3)
        base_y = 40
        px1, py1, px2, py2 = self.canvas.coords(self.player)
        pcx = (px1 + px2)/2
        pcy = (py1 + py2)/2
        dx = pcx - base_x
        dy = pcy - base_y
        base_ang = math.atan2(dy, dx)
        spread = math.radians(50)  # total spread angle
        bullets_in_fan = 7
        speed = 7 + self.difficulty/8
        for i in range(bullets_in_fan):
            frac = 0 if bullets_in_fan == 1 else i/(bullets_in_fan-1)
            ang = base_ang - spread/2 + spread * frac
            vx = _cos(ang) * speed
            vy = _sin(ang) * speed
            bullet = self.canvas.create_oval(base_x-8, base_y-8, base_x+8, base_y+8, fill="#ffcc55", outline="#ffffff")
            self.fan_bullets.append((bullet, vx, vy))
        # Slight random extra bullet occasionally for variation
        if random.random() < 0.25:
            ang = base_ang + random.uniform(-spread/2, spread/2)
            vx = _cos(ang) * (speed+1)
            vy = _sin(ang) * (speed+1)
            bullet = self.canvas.create_oval(base_x-8, base_y-8, base_x+8, base_y+8, fill="#ffaa33", outline="#ffffff")
            self.fan_bullets.append((bullet, vx, vy))

    # ---------------- Freeze Power-Up Methods ----------------
    def spawn_freeze_powerup(self):
        """Spawn a freeze power-up (blue snowflake-like polygon or circle) descending from top."""
        if self.game_over:
            return
        x = random.randint(40, self.width - 40)
        y = 30
        # Simple 6-point snowflake/star representation
        radius = 18
        pts = []
        for i in range(6):
            ang = (math.pi * 2 / 6) * i
            r = radius if i % 2 == 0 else radius * 0.55
            px = x + _cos(ang) * r
            py = y + _sin(ang) * r
            pts.extend([px, py])
        try:
            p_id = self.canvas.create_polygon(pts, fill="#66d9ff", outline="#ffffff", width=2)
        except Exception:
            p_id = self.canvas.create_oval(x-radius, y-radius, x+radius, y+radius, fill="#66d9ff", outline="#ffffff")
        self.freeze_powerups.append((p_id,))
        print(f"DEBUG: Spawned freeze powerup at ({x}, {y}), ID: {p_id}, Total freeze powerups: {len(self.freeze_powerups)}")

    def activate_freeze(self, mode='full', duration=5.0):
        """Activate freeze effect.
        mode: 'full' (bullets stop) or 'slow' (bullets move at reduced speed).
        duration: seconds of main freeze window (tint fade persists briefly after end).
        """
        self.freeze_mode = mode if mode in ('full','slow') else 'full'
        self.freeze_active = True
        self.freeze_end_time = time.time() + duration
        self._freeze_motion_phase_over = False
        # Start tint fade-in
        self.freeze_tint_target = 1.0
        # Audio feedback: dip volume
        try:
            if pygame.mixer.music.get_busy():
                self._music_prev_volume = pygame.mixer.music.get_volume()
                pygame.mixer.music.set_volume(min(1.0, self._music_prev_volume * 0.65))
                self._music_volume_restore_active = True
        except Exception:
            pass
        # Visual overlay text
        if self.freeze_text:
            try: self.canvas.delete(self.freeze_text)
            except Exception: pass
        try:
            label = 'FREEZE' if self.freeze_mode=='full' else 'SLOW FREEZE'
            self.freeze_text = self.canvas.create_text(self.width//2, self.height//2, text=f"{label} {duration:0.1f}s", fill="#66d9ff", font=("Arial", 48, "bold"))
        except Exception:
            self.freeze_text = None
        # Optional subtle flash effect: tint background lines (skip heavy effects for simplicity)
        # Create semi-transparent cyan overlay using stipple patterns to fake alpha
        if self.freeze_overlay:
            try: self.canvas.delete(self.freeze_overlay)
            except Exception: pass
        try:
            self.freeze_overlay = self.canvas.create_rectangle(0,0,self.width,self.height, fill="#66d9ff", outline="")
            self.canvas.itemconfig(self.freeze_overlay, stipple="gray25")
            self.canvas.tag_lower(self.freeze_overlay)  # keep it behind text
        except Exception:
            self.freeze_overlay = None
        # Initialize per-bullet original colors
        self._initialize_bullet_color_cache()

    def _initialize_bullet_color_cache(self):
        # Capture original fills only once per activation
        try:
            self._bullet_original_fills.clear()
        except Exception:
            self._bullet_original_fills = {}
        collections = [
            ('vertical', self.bullets), ('horizontal', self.bullets2), ('triangle',[b for b,_ in self.triangle_bullets]),
            ('diag',[b for b,_ in self.diag_bullets]), ('boss', self.boss_bullets), ('zigzag', self.zigzag_bullets),
            ('fast', self.fast_bullets), ('star', self.star_bullets), ('rect', self.rect_bullets), ('egg', self.egg_bullets),
            ('quad', self.quad_bullets), ('bouncing', self.bouncing_bullets), ('exploding', self.exploding_bullets),
            ('homing',[b for b, *_ in self.homing_bullets]), ('spiral',[b for b,*_ in self.spiral_bullets]),
            ('radial',[b for b,*_ in self.radial_bullets]), ('wave',[b for b,*_ in self.wave_bullets]),
            ('boomerang',[b for b,*_ in self.boomerang_bullets]), ('split',[b for b,*_ in self.split_bullets]),
        ]
        for cat, coll in collections:
            for bid in coll:
                try:
                    if isinstance(bid, tuple):
                        bid = bid[0]
                    if bid not in self._bullet_original_fills:
                        self._bullet_original_fills[bid] = (self.canvas.itemcget(bid,'fill') or '#ffffff', cat)
                except Exception:
                    pass

    def _apply_bullet_tint_fade(self):
        # Blend original color towards palette color based on freeze_tint_progress (0..1)
        prog = self.freeze_tint_progress
        if abs(prog - self._last_freeze_tint_progress) < 0.01:
            return
        self._last_freeze_tint_progress = prog
        for bid, (orig_fill, cat) in list(self._bullet_original_fills.items()):
            try:
                target = self.freeze_tint_palette.get(cat, '#a8ecff')
                of = orig_fill.lstrip('#')
                tf = target.lstrip('#')
                if len(of)!=6 or len(tf)!=6:
                    continue
                or_,og,ob = int(of[0:2],16), int(of[2:4],16), int(of[4:6],16)
                tr,tg,tb = int(tf[0:2],16), int(tf[2:4],16), int(tf[4:6],16)
                r = int(or_ + (tr-or_)*prog)
                g = int(og + (tg-og)*prog)
                b = int(ob + (tb-ob)*prog)
                self.canvas.itemconfig(bid, fill=f"#{r:02x}{g:02x}{b:02x}")
            except Exception:
                pass

    def _restore_bullet_colors(self):
        for bid, (orig_fill, _cat) in list(self._bullet_original_fills.items()):
            try:
                self.canvas.itemconfig(bid, fill=orig_fill)
            except Exception:
                pass
        self._bullet_original_fills.clear()

    # Legacy name retained (no-op wrapper for compatibility if referenced elsewhere)
    def _tint_all_bullets(self, freeze: bool):
        if freeze:
            self._initialize_bullet_color_cache()
        else:
            self._restore_bullet_colors()

    def _spawn_unfreeze_shatter(self):
        """Spawn small particle shards at each bullet position to emphasize thaw."""
        try:
            bullet_ids = []
            for coll in [self.bullets, self.bullets2, self.triangle_bullets, self.diag_bullets, self.boss_bullets,
                         self.zigzag_bullets, self.fast_bullets, self.star_bullets, self.rect_bullets,
                         self.egg_bullets, self.quad_bullets, self.exploding_bullets, self.exploded_fragments,
                         self.homing_bullets, self.spiral_bullets, self.radial_bullets, self.wave_bullets,
                         self.boomerang_bullets, self.split_bullets, self.bouncing_bullets]:
                for entry in coll:
                    if isinstance(entry, tuple):
                        bid = entry[0]
                    else:
                        bid = entry
                    bullet_ids.append(bid)
            for bid in bullet_ids:
                coords = self.canvas.coords(bid)
                if not coords:
                    continue
                if len(coords) >= 4:
                    # derive center
                    if len(coords) == 4:
                        cx = (coords[0]+coords[2])/2
                        cy = (coords[1]+coords[3])/2
                    else:
                        xs = coords[::2]; ys = coords[1::2]
                        cx = sum(xs)/len(xs); cy = sum(ys)/len(ys)
                    # spawn 4 shards
                    for i in range(4):
                        ang = (math.pi/2)*i + random.uniform(-0.3,0.3)
                        spd = 3 + random.random()*2
                        sx = cx; sy = cy
                        size = 4
                        pid = self.canvas.create_oval(sx-size/2, sy-size/2, sx+size/2, sy+size/2, fill="#ffffff", outline="")
                        vx = _cos(ang)*spd
                        vy = _sin(ang)*spd
                        # Reuse freeze_particles list for lifecycle management (short life)
                        self.freeze_particles.append((pid, vx, vy, 12))
        except Exception:
            pass

    # ---------------- Rewind Power-Up ----------------
    def spawn_rewind_powerup(self):
        """Spawn a rewind power-up (greenish hourglass/spiral)."""
        if self.game_over:
            return
        x = random.randint(40, self.width - 40)
        y = 30
        # Simple hourglass polygon
        try:
            size = 18
            pts = [x-size, y-size, x+size, y-size, x+size/2, y, x+size, y+size, x-size, y+size, x-size/2, y]
            rid = self.canvas.create_polygon(pts, fill="#66ff99", outline="#ffffff", width=2)
        except Exception:
            rid = self.canvas.create_oval(x-18, y-18, x+18, y+18, fill="#66ff99", outline="#ffffff")
        self.rewind_powerups.append((rid,))

    def activate_rewind(self, duration=3.0):
        """Begin rewinding bullet positions for a short duration.
        Bullets move backwards along recorded history; no new bullets spawn and no movement forward.
        """
        if self.freeze_active:
            # Queue rewind until freeze ends
            self.rewind_pending = True
            self._pending_rewind_duration = duration
            return
        if not self._bullet_history:
            return
        self.rewind_active = True
        self.rewind_end_time = time.time() + duration
        self._rewind_pointer = len(self._bullet_history) - 1  # start from last frame
        if self.rewind_text:
            try: self.canvas.delete(self.rewind_text)
            except Exception: pass
        try:
            self.rewind_text = self.canvas.create_text(self.width//2, self.height//2 - 80, text="REWIND", fill="#66ff99", font=("Arial", 56, "bold"))
        except Exception:
            self.rewind_text = None
        if self._rewind_overlay:
            try: self.canvas.delete(self._rewind_overlay)
            except Exception: pass
        try:
            self._rewind_overlay = self.canvas.create_rectangle(0,0,self.width,self.height, fill="#003322", outline="")
            self.canvas.itemconfig(self._rewind_overlay, stipple="gray25")
            self.canvas.tag_lower(self._rewind_overlay)
        except Exception:
            self._rewind_overlay = None
        # Remove queued text if present
        if self.rewind_pending_text:
            try: self.canvas.delete(self.rewind_pending_text)
            except Exception: pass
            self.rewind_pending_text = None
        # Count bullets at start for bonus
        try:
            self._rewind_start_bullet_count = sum([
                len(self.bullets), len(self.bullets2), len(self.triangle_bullets), len(self.diag_bullets), len(self.boss_bullets),
                len(self.zigzag_bullets), len(self.fast_bullets), len(self.star_bullets), len(self.rect_bullets), len(self.egg_bullets),
                len(self.quad_bullets), len(self.exploding_bullets), len(self.exploded_fragments), len(self.bouncing_bullets),
                len(self.homing_bullets), len(self.spiral_bullets), len(self.radial_bullets), len(self.wave_bullets), len(self.boomerang_bullets), len(self.split_bullets)
            ])
        except Exception:
            self._rewind_start_bullet_count = 0
        # Create vignette visual
        self._create_rewind_vignette()
        # Load & play sound
        try:
            if self._rewind_start_sound is None:
                base_dir = getattr(sys, '_MEIPASS', os.path.dirname(__file__))
                p = os.path.join(base_dir, 'rewind_start.wav')
                if os.path.exists(p):
                    self._rewind_start_sound = pygame.mixer.Sound(p)
            if self._rewind_start_sound:
                self._rewind_start_sound.play()
        except Exception:
            pass

    def _capture_bullet_snapshot(self):
        """Record current bullet positions for rewind history."""
        frame = {}
        def capture_list(name, coll):
            arr = []
            for entry in coll:
                if isinstance(entry, tuple):
                    bid = entry[0]
                else:
                    bid = entry
                coords = self.canvas.coords(bid)
                if not coords:
                    continue
                arr.append((bid, tuple(coords)))
            frame[name] = arr
        capture_list('bullets', self.bullets)
        capture_list('bullets2', self.bullets2)
        capture_list('triangle_bullets', self.triangle_bullets)
        capture_list('diag_bullets', self.diag_bullets)
        capture_list('boss_bullets', self.boss_bullets)
        capture_list('zigzag_bullets', self.zigzag_bullets)
        capture_list('fast_bullets', self.fast_bullets)
        capture_list('star_bullets', self.star_bullets)
        capture_list('rect_bullets', self.rect_bullets)
        capture_list('egg_bullets', self.egg_bullets)
        capture_list('quad_bullets', self.quad_bullets)
        capture_list('exploding_bullets', self.exploding_bullets)
        capture_list('exploded_fragments', self.exploded_fragments)
        capture_list('bouncing_bullets', self.bouncing_bullets)
        capture_list('homing_bullets', self.homing_bullets)
        capture_list('spiral_bullets', self.spiral_bullets)
        capture_list('radial_bullets', self.radial_bullets)
        capture_list('wave_bullets', self.wave_bullets)
        capture_list('boomerang_bullets', self.boomerang_bullets)
        capture_list('split_bullets', self.split_bullets)
        capture_list('static_bullets', self.static_bullets)
        # lasers & indicators not rewound (temporal hazards), skip
        self._bullet_history.append(frame)
        if len(self._bullet_history) > self._bullet_history_max:
            self._bullet_history.pop(0)

    def _perform_rewind_step(self):
        if self._rewind_pointer is None or not self._bullet_history:
            return
        # Spawn ghost traces
        self._spawn_rewind_ghosts()
        # apply snapshot
        frame = self._bullet_history[self._rewind_pointer]
        for key, arr in frame.items():
            for tup in arr:
                bid = tup[0]
                coords = tup[1]
                try:
                    self.canvas.coords(bid, *coords)
                except Exception:
                    pass
        self._rewind_pointer -= self._rewind_speed
        if self._rewind_pointer < 0:
            self._rewind_pointer = 0
        # Update ghosts fade
        self._update_rewind_ghosts()

    def _spawn_rewind_ghosts(self):
        if self._rewind_ghost_spawn_skip:
            self._rewind_ghost_spawn_skip = 0
            return
        else:
            self._rewind_ghost_spawn_skip = 1
        ghost_color = '#66ffcc'
        # Skip spawning if already above cap
        if len(self._rewind_ghosts) >= self._rewind_ghost_cap:
            return
        groups = [
            self.bullets, self.bullets2, [b for b,_ in self.triangle_bullets],
            [b for b,_ in self.diag_bullets], self.boss_bullets, self.zigzag_bullets,
            self.fast_bullets, self.star_bullets, self.rect_bullets, self.egg_bullets,
            self.quad_bullets, self.exploding_bullets, [b for b, *_ in self.homing_bullets],
            [b for b,*_ in self.spiral_bullets], [b for b,*_ in self.radial_bullets],
            self.wave_bullets, [b for b,*_ in self.boomerang_bullets], [b for b,*_ in self.split_bullets],
            self.bouncing_bullets, [b for b,*_ in self.exploded_fragments]
        ]
        for grp in groups:
            for bid in grp:
                try:
                    c = self.canvas.coords(bid)
                    if len(c) < 4:
                        continue
                    if len(c) == 4:
                        ghost_id = self.canvas.create_rectangle(c[0],c[1],c[2],c[3], outline=ghost_color, width=1)
                    else:
                        xs=c[0::2]; ys=c[1::2]
                        ghost_id = self.canvas.create_polygon(min(xs),min(ys),max(xs),min(ys),max(xs),max(ys),min(xs),max(ys), outline=ghost_color, fill="", width=1)
                    self.canvas.tag_lower(ghost_id, self.player)
                    self._rewind_ghosts.append((ghost_id, self._rewind_ghost_life))
                    if len(self._rewind_ghosts) >= self._rewind_ghost_cap:
                        return
                except Exception:
                    pass

    def _update_rewind_ghosts(self):
        new=[]
        for gid, life in self._rewind_ghosts:
            life -=1
            if life<=0:
                try: self.canvas.delete(gid)
                except Exception: pass
                continue
            try:
                frac=life/self._rewind_ghost_life
                r=int(0x66*frac); g=int(0xff*frac); b=int(0xcc*frac)
                self.canvas.itemconfig(gid, outline=f"#{r:02x}{g:02x}{b:02x}")
            except Exception:
                pass
            new.append((gid,life))
        self._rewind_ghosts=new
        # light trimming if somehow exceeded cap
        if len(self._rewind_ghosts) > self._rewind_ghost_cap:
            overflow = len(self._rewind_ghosts) - self._rewind_ghost_cap
            for i in range(overflow):
                gid, _ = self._rewind_ghosts[i]
                try: self.canvas.delete(gid)
                except Exception: pass
            self._rewind_ghosts = self._rewind_ghosts[overflow:]

    # --- Rewind vignette helpers ---
    def _create_rewind_vignette(self):
        # Clear existing
        try:
            for vid in self._rewind_vignette_ids:
                self.canvas.delete(vid)
        except Exception:
            pass
        self._rewind_vignette_ids = []
        try:
            cx = self.width/2; cy = self.height/2
            max_r = max(self.width, self.height)*0.75
            rings = 5
            for i in range(rings):
                frac = i / rings
                r = max_r * (1 - 0.15*frac)
                color = '#003322' if i%2==0 else '#004433'
                oval = self.canvas.create_oval(cx-r, cy-r, cx+r, cy+r, outline="", fill=color)
                try: self.canvas.itemconfig(oval, stipple="gray25")
                except Exception: pass
                self.canvas.tag_lower(oval)
                self._rewind_vignette_ids.append(oval)
        except Exception:
            self._rewind_vignette_ids = []

    def _clear_rewind_vignette(self):
        for vid in self._rewind_vignette_ids:
            try: self.canvas.delete(vid)
            except Exception: pass
        self._rewind_vignette_ids = []

    # ---------------- Shield Power-Up ----------------
    def spawn_shield_powerup(self):
        """Spawn a shield power-up (purple hexagon) descending from top."""
        if self.game_over:
            return
        x = random.randint(40, self.width - 40)
        y = 30
        # Create hexagon shape for shield
        radius = 18
        pts = []
        for i in range(6):
            ang = (math.pi * 2 / 6) * i + math.pi / 6  # Rotate by 30 degrees
            px = x + _cos(ang) * radius
            py = y + _sin(ang) * radius
            pts.extend([px, py])
        try:
            s_id = self.canvas.create_polygon(pts, fill="#9966ff", outline="#ffffff", width=2)
        except Exception:
            s_id = self.canvas.create_oval(x-radius, y-radius, x+radius, y+radius, fill="#9966ff", outline="#ffffff")
        self.shield_powerups.append((s_id,))

    def activate_shield(self):
        """Activate shield - gives player one extra hit point that absorbs damage."""
        if self.shield_active:
            return  # Already have shield
        self.shield_active = True
        self.shield_hits_remaining = 1
        
        # Create visual shield indicator around player
        try:
            px1, py1, px2, py2 = self.canvas.coords(self.player)
            cx = (px1 + px2) / 2
            cy = (py1 + py2) / 2
            shield_radius = 35
            self.shield_visual = self.canvas.create_oval(
                cx - shield_radius, cy - shield_radius,
                cx + shield_radius, cy + shield_radius,
                outline="#9966ff", width=3
            )
        except Exception:
            self.shield_visual = None
        
        # Create shield text notification
        try:
            self.shield_text = self.canvas.create_text(
                self.width//2, self.height//2 + 60,
                text="SHIELD ACTIVE", fill="#9966ff", font=("Arial", 32, "bold")
            )
            # Auto-remove text after 2 seconds
            self.shield_text_remove_time = time.time() + 2.0
        except Exception:
            self.shield_text = None
        
        # Spawn activation particles
        self._spawn_shield_particles(cx, cy)
        
        # Play sound effect (optional - only if sound file exists)
        try:
            if self._shield_sound is None:
                sound_path = self._resolve_asset_path('shield.wav')
                if os.path.exists(sound_path):
                    self._shield_sound = pygame.mixer.Sound(sound_path)
            if self._shield_sound:
                self._shield_sound.play()
        except Exception:
            pass

    def _spawn_shield_particles(self, cx, cy):
        """Spawn particle burst when shield activates."""
        try:
            # Spawn radial burst of particles
            num_particles = 24
            for i in range(num_particles):
                ang = (math.pi * 2 / num_particles) * i
                speed = random.uniform(3, 6)
                vx = _cos(ang) * speed
                vy = _sin(ang) * speed
                size = random.randint(3, 6)
                pid = self.canvas.create_oval(
                    cx - size/2, cy - size/2,
                    cx + size/2, cy + size/2,
                    fill="#9966ff", outline=""
                )
                life = random.randint(15, 25)
                self.shield_particles.append((pid, cx, cy, vx, vy, life))
        except Exception:
            pass

    def update_shield_visual(self):
        """Update shield visual position to follow player and pulse."""
        if not self.shield_active or self.shield_visual is None:
            return
        
        try:
            px1, py1, px2, py2 = self.canvas.coords(self.player)
            cx = (px1 + px2) / 2
            cy = (py1 + py2) / 2
            
            # Pulse effect
            pulse = (_sin(time.time() * 4) + 1) / 2  # 0..1
            shield_radius = 35 + pulse * 5
            
            self.canvas.coords(
                self.shield_visual,
                cx - shield_radius, cy - shield_radius,
                cx + shield_radius, cy + shield_radius
            )
            
            # Color pulse
            alpha = int(150 + pulse * 105)
            color = f"#{alpha:02x}66ff"
            self.canvas.itemconfig(self.shield_visual, outline=color)
        except Exception:
            pass

    def deactivate_shield(self):
        """Remove shield when it's used up."""
        self.shield_active = False
        self.shield_hits_remaining = 0
        
        if self.shield_visual:
            try:
                self.canvas.delete(self.shield_visual)
            except Exception:
                pass
            self.shield_visual = None
        
        if self.shield_text:
            try:
                self.canvas.delete(self.shield_text)
            except Exception:
                pass
            self.shield_text = None

    # ---------------- Slow-Motion Power-Up ----------------
    def spawn_slowmo_powerup(self):
        """Spawn a slow-motion power-up (orange clock) descending from top."""
        if self.game_over:
            return
        x = random.randint(40, self.width - 40)
        y = 30
        # Create clock shape (circle with clock hands)
        radius = 18
        try:
            # Outer circle
            sm_id = self.canvas.create_oval(
                x - radius, y - radius, x + radius, y + radius,
                fill="#ff9933", outline="#ffffff", width=2
            )
            # Clock hand lines (approximate)
            hand1 = self.canvas.create_line(x, y, x, y - radius*0.6, fill="#ffffff", width=2)
            hand2 = self.canvas.create_line(x, y, x + radius*0.4, y + radius*0.4, fill="#ffffff", width=2)
            self.slowmo_powerups.append((sm_id, hand1, hand2))
        except Exception:
            sm_id = self.canvas.create_oval(x-radius, y-radius, x+radius, y+radius, fill="#ff9933", outline="#ffffff")
            self.slowmo_powerups.append((sm_id, None, None))

    def activate_slowmo(self, duration=4.0):
        """Activate slow-motion effect - all bullets move at reduced speed."""
        self.slowmo_active = True
        self.slowmo_end_time = time.time() + duration
        self.slowmo_factor = 0.35  # Bullets move at 35% speed
        
        # Create visual overlay
        try:
            self.slowmo_overlay = self.canvas.create_rectangle(
                0, 0, self.width, self.height,
                fill="#ff9933", outline=""
            )
            self.canvas.itemconfig(self.slowmo_overlay, stipple="gray25")
            self.canvas.tag_lower(self.slowmo_overlay)
        except Exception:
            self.slowmo_overlay = None
        
        # Create text notification
        try:
            self.slowmo_text = self.canvas.create_text(
                self.width//2, self.height//2 + 100,
                text=f"SLOW MOTION {duration:.1f}s",
                fill="#ff9933", font=("Arial", 42, "bold")
            )
        except Exception:
            self.slowmo_text = None
        
        # Spawn activation particles across screen
        self._spawn_slowmo_particles()
        
        # Play sound effect (optional - only if sound file exists)
        try:
            if self._slowmo_sound is None:
                sound_path = self._resolve_asset_path('slowmo.wav')
                if os.path.exists(sound_path):
                    self._slowmo_sound = pygame.mixer.Sound(sound_path)
            if self._slowmo_sound:
                self._slowmo_sound.play()
        except Exception:
            pass
        
        # Audio feedback: slightly pitch down music (simulated via volume)
        try:
            if pygame.mixer.music.get_busy():
                self._slowmo_prev_volume = pygame.mixer.music.get_volume()
                pygame.mixer.music.set_volume(min(1.0, self._slowmo_prev_volume * 0.75))
        except Exception:
            pass

    def _spawn_slowmo_particles(self):
        """Spawn time-warp particles when slow-motion activates."""
        try:
            # Spawn particles at random positions
            num_particles = 40
            for _ in range(num_particles):
                x = random.randint(0, self.width)
                y = random.randint(0, self.height)
                size = random.randint(2, 5)
                pid = self.canvas.create_oval(
                    x - size/2, y - size/2,
                    x + size/2, y + size/2,
                    fill="#ff9933", outline=""
                )
                # Slow drift
                vx = random.uniform(-0.5, 0.5)
                vy = random.uniform(-1, 1)
                life = random.randint(20, 40)
                self.slowmo_particles.append((pid, x, y, vx, vy, life))
        except Exception:
            pass

    def deactivate_slowmo(self):
        """End slow-motion effect."""
        self.slowmo_active = False
        
        if self.slowmo_overlay:
            try:
                self.canvas.delete(self.slowmo_overlay)
            except Exception:
                pass
            self.slowmo_overlay = None
        
        if self.slowmo_text:
            try:
                self.canvas.delete(self.slowmo_text)
            except Exception:
                pass
            self.slowmo_text = None

    def debug_trigger_freeze(self, event=None):
        """Manual key-triggered freeze for testing (press 'f')."""
        if not self.freeze_active:
            self.activate_freeze(mode='full')

    def debug_trigger_slow_freeze(self, event=None):
        """Manual key-triggered slow-motion freeze (press 'F')."""
        if not self.freeze_active:
            self.activate_freeze(mode='slow')


    def move_player(self, event):
        # Don't process movement if not in game
        if not self.game_started or self.in_main_menu or self.in_settings_menu:
            return
        if self.paused or self.game_over:
            return
        # While in static trap, only count specific keys to progress, suppress movement
        if self.static_trap_active:
            self._handle_static_trap_key(event)
            return
        s = self.player_speed * (0.5 if self.focus_active else 1.0)
        # Check against configurable keybinds
        if event.keysym in self.settings['keybinds']['move_left']:
            self.apply_player_move(-s,0)
        elif event.keysym in self.settings['keybinds']['move_right']:
            self.apply_player_move(s,0)
        elif event.keysym in self.settings['keybinds']['move_up']:
            self.apply_player_move(0,-s)
        elif event.keysym in self.settings['keybinds']['move_down']:
            self.apply_player_move(0,s)
    
    def handle_mouse_motion(self, event):
        """Handle mouse movement for player control."""
        if not self.game_started or self.in_main_menu or self.in_settings_menu:
            return
        if not self.settings.get('mouse_enabled', True):
            return
        if self.paused or self.game_over or self.static_trap_active:
            return
        
        # Set mouse target for smooth movement
        self.mouse_target_x = event.x
        self.mouse_target_y = event.y
        self.mouse_move_active = True
    
    def handle_mouse_click(self, event):
        """Handle mouse click for player movement."""
        if not self.game_started or self.in_main_menu or self.in_settings_menu:
            return
        if not self.settings.get('mouse_enabled', True):
            return
        if self.paused or self.game_over or self.static_trap_active:
            return
        
        # Move player towards click position
        self.mouse_target_x = event.x
        self.mouse_target_y = event.y
        self.mouse_move_active = True
    
    def handle_touch_start(self, event):
        """Handle touch/tap start for touchscreen movement."""
        if not self.game_started or self.in_main_menu or self.in_settings_menu:
            return
        if not self.settings.get('touchscreen_enabled', True):
            return
        if self.paused or self.game_over or self.static_trap_active:
            return
        
        self.touch_active = True
        self.touch_start_x = event.x
        self.touch_start_y = event.y
        # Also set as movement target
        self.mouse_target_x = event.x
        self.mouse_target_y = event.y
        self.mouse_move_active = True
    
    def handle_touch_move(self, event):
        """Handle touch drag for player movement."""
        if not self.game_started or self.in_main_menu or self.in_settings_menu:
            return
        if not self.settings.get('touchscreen_enabled', True):
            return
        if self.paused or self.game_over or self.static_trap_active:
            return
        if not self.touch_active:
            return
        
        # Update target position during drag
        self.mouse_target_x = event.x
        self.mouse_target_y = event.y
        self.mouse_move_active = True
    
    def handle_touch_end(self, event):
        """Handle touch/tap end."""
        self.touch_active = False
        self.touch_start_x = None
        self.touch_start_y = None
    
    def update_mouse_movement(self):
        """Smoothly move player towards mouse/touch target."""
        if not self.mouse_move_active or self.mouse_target_x is None:
            return
        
        try:
            x1, y1, x2, y2 = self.canvas.coords(self.player)
            player_cx = (x1 + x2) / 2
            player_cy = (y1 + y2) / 2
            
            # Calculate direction to target
            dx = self.mouse_target_x - player_cx
            dy = self.mouse_target_y - player_cy
            distance = _hypot(dx, dy)
            
            # If close enough to target, stop
            if distance < 5:
                self.mouse_move_active = False
                return
            
            # Normalize and apply speed
            speed = self.player_speed * (0.5 if self.focus_active else 1.0)
            if distance > 0:
                dx = (dx / distance) * speed
                dy = (dy / distance) * speed
                self.apply_player_move(dx, dy)
        except Exception:
            pass
    
    def update_controller_input(self):
        """Process controller/gamepad input for player movement."""
        if not self.settings.get('controller_enabled', True):
            return
        if not self.game_started or self.in_main_menu or self.in_settings_menu:
            return
        if self.paused or self.game_over or self.static_trap_active:
            return
        
        for joystick in self.joysticks:
            try:
                # Get axis values (typically axis 0 = left/right, axis 1 = up/down)
                axis_x = joystick.get_axis(0) if joystick.get_numaxes() > 0 else 0
                axis_y = joystick.get_axis(1) if joystick.get_numaxes() > 1 else 0
                
                # Apply deadzone to avoid drift
                deadzone = 0.15
                if abs(axis_x) < deadzone:
                    axis_x = 0
                if abs(axis_y) < deadzone:
                    axis_y = 0
                
                # Apply movement if there's input
                if axis_x != 0 or axis_y != 0:
                    speed = self.player_speed * (0.5 if self.focus_active else 1.0)
                    dx = axis_x * speed
                    dy = axis_y * speed
                    self.apply_player_move(dx, dy)
                
                # Check buttons for shooting and focus
                for i in range(joystick.get_numbuttons()):
                    button_pressed = joystick.get_button(i)
                    
                    # Button 0 (usually A/X) for shooting
                    if i == 0 and button_pressed:
                        self.player_shoot()
                    
                    # Button 1 (usually B/Circle) for focus (hold to activate)
                    elif i == 1:
                        # Track focus button state per controller
                        focus_key = f'controller_{joystick.get_instance_id()}_focus'
                        was_pressed = getattr(self, f'_{focus_key}', False)
                        
                        if button_pressed and not was_pressed:
                            # Button just pressed
                            self._focus_key_pressed(None)
                            setattr(self, f'_{focus_key}', True)
                        elif not button_pressed and was_pressed:
                            # Button just released
                            self._focus_key_released(None)
                            setattr(self, f'_{focus_key}', False)
                
            except Exception as e:
                print(f"Controller input error: {e}")
    
    def player_shoot(self, event=None):
        """Player shoots a projectile upward."""
        if not self.game_started or self.in_main_menu or self.in_settings_menu:
            return
        if self.paused or self.game_over:
            return
        if self.static_trap_active:
            return
        
        # Check cooldown
        if self.shot_cooldown > 0:
            return
        
        # Get player position
        try:
            px1, py1, px2, py2 = self.canvas.coords(self.player)
            pcx = (px1 + px2) / 2
            pcy = (py1 + py2) / 2
        except Exception:
            return
        
        # Create shot
        shot_size = 8
        shot = self.canvas.create_oval(
            pcx - shot_size // 2, pcy - shot_size // 2,
            pcx + shot_size // 2, pcy + shot_size // 2,
            fill="#00ffff", outline="#ffffff", width=2
        )
        self.player_shots.append((shot, pcx, pcy))
        
        # Set cooldown
        self.shot_cooldown = self.shot_cooldown_time
    
    def spawn_boss(self):
        """Spawn the boss entity."""
        if self.boss_entity:
            try:
                self.canvas.delete(self.boss_entity)
            except Exception:
                pass
        
        # Create boss as a rectangle
        self.boss_entity = self.canvas.create_rectangle(
            self.boss_x - self.boss_width // 2,
            self.boss_y - self.boss_height // 2,
            self.boss_x + self.boss_width // 2,
            self.boss_y + self.boss_height // 2,
            fill="#ff00ff", outline="#ffffff", width=4
        )
    
    def update_boss(self):
        """Update boss movement and check collisions."""
        if not self.boss_entity:
            return
        
        # Flash effect when hit
        if self.boss_flash_timer > 0:
            self.boss_flash_timer -= 1
            flash_color = "#ffffff" if self.boss_flash_timer % 4 < 2 else "#ff00ff"
            try:
                self.canvas.itemconfig(self.boss_entity, fill=flash_color)
            except Exception:
                pass
        
        # Move boss
        self.boss_x += self.boss_vx
        self.boss_y += self.boss_vy
        
        # Bounce off walls
        if self.boss_x - self.boss_width // 2 < 0 or self.boss_x + self.boss_width // 2 > self.width:
            self.boss_vx *= -1
        if self.boss_y - self.boss_height // 2 < 50 or self.boss_y + self.boss_height // 2 > self.height // 2:
            self.boss_vy *= -1
        
        # Update boss position
        try:
            self.canvas.coords(
                self.boss_entity,
                self.boss_x - self.boss_width // 2,
                self.boss_y - self.boss_height // 2,
                self.boss_x + self.boss_width // 2,
                self.boss_y + self.boss_height // 2
            )
        except Exception:
            pass
        
        # Check collision with player
        try:
            px1, py1, px2, py2 = self.canvas.coords(self.player)
            bx1 = self.boss_x - self.boss_width // 2
            by1 = self.boss_y - self.boss_height // 2
            bx2 = self.boss_x + self.boss_width // 2
            by2 = self.boss_y + self.boss_height // 2
            
            # Check if player and boss overlap
            if px1 < bx2 and px2 > bx1 and py1 < by2 and py2 > by1:
                # Boss contact damage
                if not self.practice_mode:
                    self.lives -= 0
                    if self.lives <= 0:
                        self.end_game()
                    else:
                        self.update_health_display()
                        # Push player away from boss
                        push_x = (px1 + px2) / 2 - self.boss_x
                        push_y = (py1 + py2) / 2 - self.boss_y
                        dist = _hypot(push_x, push_y) or 1
                        self.apply_player_move(push_x / dist * 20, push_y / dist * 20)
        except Exception:
            pass
    
    def update_player_shots(self):
        """Update player shots and check for boss hits."""
        # Update cooldown
        if self.shot_cooldown > 0:
            self.shot_cooldown -= 0.05  # Frame time
        
        new_shots = []
        for shot_id, sx, sy in self.player_shots:
            # Move shot upward
            try:
                self.canvas.move(shot_id, 0, -self.shot_speed)
                coords = self.canvas.coords(shot_id)
                if not coords or coords[1] < -20:
                    # Shot went off screen
                    try:
                        self.canvas.delete(shot_id)
                    except Exception:
                        pass
                    continue
                
                # Check collision with boss
                shot_x = (coords[0] + coords[2]) / 2
                shot_y = (coords[1] + coords[3]) / 2
                bx1 = self.boss_x - self.boss_width // 2
                by1 = self.boss_y - self.boss_height // 2
                bx2 = self.boss_x + self.boss_width // 2
                by2 = self.boss_y + self.boss_height // 2
                
                if bx1 < shot_x < bx2 and by1 < shot_y < by2:
                    # Hit the boss!
                    self.boss_health_display += 1
                    self.boss_flash_timer = 8
                    self.score += 5  # Add score for hitting boss
                    
                    # Delete the shot
                    try:
                        self.canvas.delete(shot_id)
                    except Exception:
                        pass
                else:
                    # Shot still active
                    new_shots.append((shot_id, shot_x, shot_y))
            except Exception:
                try:
                    self.canvas.delete(shot_id)
                except Exception:
                    pass
        
        self.player_shots = new_shots
    
    def spawn_collectable(self):
        """Spawn a random collectable item."""
        if len(self.collected_items) >= self.total_collectables:
            return  # All collected
        
        # Find an uncollected item
        available = [item for item in self.collectable_types if item not in self.collected_items]
        if not available:
            return
        
        item_name = random.choice(available)
        item_index = self.collectable_types.index(item_name)
        color = self.collectable_colors[item_index]
        
        # Random position in top half of screen
        x = random.randint(50, self.width - 50)
        y = random.randint(80, self.height // 2 - 50)
        
        # Create different shapes for variety
        shape_type = item_index % 5
        if shape_type == 0:  # Circle
            item_id = self.canvas.create_oval(
                x - 15, y - 15, x + 15, y + 15,
                fill=color, outline="#ffffff", width=2, tags="collectable"
            )
        elif shape_type == 1:  # Square
            item_id = self.canvas.create_rectangle(
                x - 12, y - 12, x + 12, y + 12,
                fill=color, outline="#ffffff", width=2, tags="collectable"
            )
        elif shape_type == 2:  # Diamond
            points = [x, y - 15, x + 15, y, x, y + 15, x - 15, y]
            item_id = self.canvas.create_polygon(
                points, fill=color, outline="#ffffff", width=2, tags="collectable"
            )
        elif shape_type == 3:  # Triangle
            points = [x, y - 15, x + 13, y + 13, x - 13, y + 13]
            item_id = self.canvas.create_polygon(
                points, fill=color, outline="#ffffff", width=2, tags="collectable"
            )
        else:  # Hexagon
            pts = []
            for i in range(6):
                angle = i * (2 * _pi / 6)
                pts.extend([x + 14 * _cos(angle), y + 14 * _sin(angle)])
            item_id = self.canvas.create_polygon(
                pts, fill=color, outline="#ffffff", width=2, tags="collectable"
            )
        
        # Add text label
        text_id = self.canvas.create_text(
            x, y, text=item_name[:3].upper(), fill="#000000",
            font=("Arial", 8, "bold"), tags="collectable"
        )
        
        self.collectables.append((item_id, text_id, item_name, x, y))
    
    def update_collectables(self):
        """Update collectables and check for collection."""
        # Spawn new collectable if it's time
        if time.time() >= self.next_collectable_spawn and len(self.collected_items) < self.total_collectables:
            if len(self.collectables) < 5:  # Max 5 on screen at once
                self.spawn_collectable()
                self.next_collectable_spawn = time.time() + self.collectable_spawn_interval
        
        # Check for collection
        try:
            px1, py1, px2, py2 = self.canvas.coords(self.player)
            pcx = (px1 + px2) / 2
            pcy = (py1 + py2) / 2
            
            for item_id, text_id, item_name, x, y in self.collectables[:]:
                # Check distance
                dist = _hypot(pcx - x, pcy - y)
                if dist < 30:  # Collection radius
                    # Collect the item
                    self.collected_items.add(item_name)
                    self.score += 10  # Bonus score
                    
                    # Remove from canvas
                    try:
                        self.canvas.delete(item_id)
                        self.canvas.delete(text_id)
                    except Exception:
                        pass
                    
                    self.collectables.remove((item_id, text_id, item_name, x, y))
                    
                    # Show collection message
                    try:
                        msg_id = self.canvas.create_text(
                            x, y - 30, text=f"+{item_name}!",
                            fill="#ffff00", font=("Arial", 14, "bold")
                        )
                        self.canvas.after(1000, lambda mid=msg_id: (self.canvas.delete(mid) if self.canvas.winfo_exists() and self.canvas.type(mid) else None))
                    except Exception:
                        pass
                    
                    # Check for win condition
                    if len(self.collected_items) >= self.total_collectables:
                        self.win_game()
                    
                    break  # Only collect one per frame
        except Exception:
            pass
        
        # Lift collectables to be visible
        for item_id, text_id, _, _, _ in self.collectables:
            try:
                self.canvas.lift(item_id)
                self.canvas.lift(text_id)
            except Exception:
                pass
    
    def win_game(self):
        """Player collected all items and won!"""
        self.game_over = True
        
        # Stop game music
        try:
            pygame.mixer.music.stop()
        except Exception:
            pass
        
        # Clear screen
        self.canvas.delete("all")
        
        # Victory gradient background
        gradient_colors = ["#0d0221", "#4b0a67", "#8f1f85", "#d25872", "#ffaa44"]
        bar_height = self.height // len(gradient_colors)
        for i, color in enumerate(gradient_colors):
            self.canvas.create_rectangle(
                0, i * bar_height, self.width, (i + 1) * bar_height,
                fill=color, outline=""
            )
        
        # Victory stars/sparkles
        for _ in range(100):
            x = random.randint(0, self.width)
            y = random.randint(0, self.height)
            size = random.randint(2, 8)
            brightness = random.randint(200, 255)
            color = random.choice([f"#{brightness:02x}{brightness:02x}00",
                                  f"#{brightness:02x}00{brightness:02x}",
                                  f"#00{brightness:02x}{brightness:02x}"])
            self.canvas.create_oval(x-size//2, y-size//2, x+size//2, y+size//2, fill=color, outline="")
        
        # Victory banner frame
        banner_width = 700
        banner_height = 200
        banner_x = self.width // 2
        banner_y = self.height // 3
        # Outer glow
        self.canvas.create_rectangle(
            banner_x - banner_width // 2 - 8, banner_y - banner_height // 2 - 8,
            banner_x + banner_width // 2 + 8, banner_y + banner_height // 2 + 8,
            fill="#ffff88", outline=""
        )
        # Banner background
        self.canvas.create_rectangle(
            banner_x - banner_width // 2, banner_y - banner_height // 2,
            banner_x + banner_width // 2, banner_y + banner_height // 2,
            fill="#1a0533", outline="#ffffff", width=5
        )
        
        # Win message with shadow and decorations
        self.canvas.create_text(
            banner_x + 5, banner_y - 20 + 5,
            text="★ YOU WIN! ★",
            fill="#442200", font=("Arial", 72, "bold")
        )
        self.canvas.create_text(
            banner_x, banner_y - 20,
            text="★ YOU WIN! ★",
            fill="#ffff00", font=("Arial", 72, "bold")
        )
        
        # Victory subtitle
        self.canvas.create_text(
            banner_x + 2, banner_y + 62,
            text="PERFECT COLLECTION!",
            fill="#003300", font=("Arial", 24, "bold")
        )
        self.canvas.create_text(
            banner_x, banner_y + 60,
            text="PERFECT COLLECTION!",
            fill="#00ff00", font=("Arial", 24, "bold")
        )
        
        # Stats panel
        stats_y = self.height // 2 + 40
        stats_width = 500
        stats_height = 180
        # Panel shadow
        self.canvas.create_rectangle(
            banner_x - stats_width // 2 + 5, stats_y + 5,
            banner_x + stats_width // 2 + 5, stats_y + stats_height + 5,
            fill="#000000", outline=""
        )
        # Panel
        self.canvas.create_rectangle(
            banner_x - stats_width // 2, stats_y,
            banner_x + stats_width // 2, stats_y + stats_height,
            fill="#0d0221", outline="#66ffdd", width=4
        )
        
        # Stats text
        self.canvas.create_text(
            banner_x, stats_y + 30,
            text=f"All {self.total_collectables} items collected!",
            fill="#00ff00", font=("Arial", 28, "bold")
        )
        
        self.canvas.create_text(
            banner_x, stats_y + 75,
            text=f"Final Score: {self.score}",
            fill="#ffff00", font=("Arial", 32, "bold")
        )
        
        self.canvas.create_text(
            banner_x, stats_y + 120,
            text=f"Boss Hits: {self.boss_health_display}",
            fill="#ff00ff", font=("Arial", 24)
        )
        
        # Instructions
        self.canvas.create_text(
            self.width // 2, self.height - 80,
            text="Press R to play again  •  Press ESC for menu",
            fill="#ffffff", font=("Arial", 20)
        )
        
        # Decorative corner brackets
        bracket_size = 60
        corners = [
            (banner_x - stats_width // 2, stats_y),
            (banner_x + stats_width // 2, stats_y),
            (banner_x - stats_width // 2, stats_y + stats_height),
            (banner_x + stats_width // 2, stats_y + stats_height)
        ]
        for i, (cx, cy) in enumerate(corners):
            if i == 0:  # Top-left
                self.canvas.create_line(cx, cy, cx + bracket_size, cy, fill="#66ffdd", width=3)
                self.canvas.create_line(cx, cy, cx, cy + bracket_size, fill="#66ffdd", width=3)
            elif i == 1:  # Top-right
                self.canvas.create_line(cx, cy, cx - bracket_size, cy, fill="#66ffdd", width=3)
                self.canvas.create_line(cx, cy, cx, cy + bracket_size, fill="#66ffdd", width=3)
            elif i == 2:  # Bottom-left
                self.canvas.create_line(cx, cy, cx + bracket_size, cy, fill="#66ffdd", width=3)
                self.canvas.create_line(cx, cy, cx, cy - bracket_size, fill="#66ffdd", width=3)
            else:  # Bottom-right
                self.canvas.create_line(cx, cy, cx - bracket_size, cy, fill="#66ffdd", width=3)
                self.canvas.create_line(cx, cy, cx, cy - bracket_size, fill="#66ffdd", width=3)

    def toggle_pause(self, event=None):
        if self.game_over or not self.game_started:
            return
        self.paused = not self.paused
        if self.paused:
            self.pause_start_time = time.time()
            self.show_pause_menu()
            # Play pause music
            try:
                if self.current_music_state != 'pause':
                    pygame.mixer.music.load(self.pause_music_path)
                    pygame.mixer.music.play(-1)
                    self.current_music_state = 'pause'
                    self.apply_volume_settings()
            except Exception as e:
                print("Could not play pause music:", e)
        else:
            self.hide_pause_menu()
            # Add paused duration to total
            if self.pause_start_time:
                self.paused_time_total += time.time() - self.pause_start_time
                self.pause_start_time = None
            # Resume game music
            try:
                if self.current_music_state != 'game':
                    pygame.mixer.music.load(self.main_music_path)
                    pygame.mixer.music.play(-1)
                    self.current_music_state = 'game'
                    self.apply_volume_settings()
            except Exception as e:
                print("Could not resume game music:", e)
        # Resume update loop if unpaused
        if not self.paused:
            self.update_game()
    
    def show_pause_menu(self):
        """Display pause menu with Resume, Restart, and Quit options."""
        # Semi-transparent overlay with vignette effect
        try:
            # Dark center overlay
            overlay = self.canvas.create_rectangle(
                0, 0, self.width, self.height,
                fill="#000000", outline="", tags="pause_menu"
            )
            self.canvas.itemconfig(overlay, stipple="gray50")
            self.pause_menu_items.append(overlay)
            
            # Corner vignette darkening
            vignette_size = 200
            for corner in [(0, 0), (self.width, 0), (0, self.height), (self.width, self.height)]:
                vign = self.canvas.create_rectangle(
                    corner[0] - vignette_size if corner[0] > 0 else 0,
                    corner[1] - vignette_size if corner[1] > 0 else 0,
                    corner[0] + vignette_size if corner[0] == 0 else self.width,
                    corner[1] + vignette_size if corner[1] == 0 else self.height,
                    fill="#000000", outline="", tags="pause_menu"
                )
                self.canvas.itemconfig(vign, stipple="gray75")
                self.pause_menu_items.append(vign)
        except Exception:
            pass
        
        # Decorative frame around title
        frame_width = 400
        frame_height = 100
        frame_x = self.width // 2
        frame_y = self.height // 3
        # Outer frame glow
        outer_frame = self.canvas.create_rectangle(
            frame_x - frame_width // 2 - 5, frame_y - frame_height // 2 - 5,
            frame_x + frame_width // 2 + 5, frame_y + frame_height // 2 + 5,
            outline="#ffff88", width=3, tags="pause_menu"
        )
        self.pause_menu_items.append(outer_frame)
        # Inner frame
        inner_frame = self.canvas.create_rectangle(
            frame_x - frame_width // 2, frame_y - frame_height // 2,
            frame_x + frame_width // 2, frame_y + frame_height // 2,
            fill="#1a0533", outline="#ffffff", width=2, tags="pause_menu"
        )
        self.pause_menu_items.append(inner_frame)
        
        # Pause title with decorative elements
        title_shadow = self.canvas.create_text(
            frame_x + 3, frame_y + 3,
            text="⏸ PAUSED ⏸",
            fill="#220033", font=("Arial", 56, "bold"),
            tags="pause_menu"
        )
        title = self.canvas.create_text(
            frame_x, frame_y,
            text="⏸ PAUSED ⏸",
            fill="#ffff00", font=("Arial", 56, "bold"),
            tags="pause_menu"
        )
        self.pause_menu_items.extend([title_shadow, title])
        
        # Buttons with enhanced styling
        button_width = 280
        button_height = 55
        button_x = self.width // 2
        button_start_y = self.height // 2
        button_spacing = 85
        
        # Resume button (green with glow)
        resume_glow = self.canvas.create_rectangle(
            button_x - button_width // 2 - 4, button_start_y - button_height // 2 - 4,
            button_x + button_width // 2 + 4, button_start_y + button_height // 2 + 4,
            fill="#66ff66", outline="", tags="pause_menu"
        )
        resume_btn = self.canvas.create_rectangle(
            button_x - button_width // 2, button_start_y - button_height // 2,
            button_x + button_width // 2, button_start_y + button_height // 2,
            fill="#44ff44", outline="#ffffff", width=3, tags="pause_menu"
        )
        resume_shadow = self.canvas.create_text(
            button_x + 2, button_start_y + 2,
            text="▶ RESUME",
            fill="#003300", font=("Arial", 28, "bold"),
            tags="pause_menu"
        )
        resume_text = self.canvas.create_text(
            button_x, button_start_y,
            text="▶ RESUME",
            fill="white", font=("Arial", 28, "bold"),
            tags="pause_menu"
        )
        self.pause_menu_items.extend([resume_glow, resume_btn, resume_shadow, resume_text])
        self.canvas.tag_bind(resume_btn, "<Button-1>", lambda e: self.toggle_pause())
        
        # Restart button (orange with glow)
        restart_y = button_start_y + button_spacing
        restart_glow = self.canvas.create_rectangle(
            button_x - button_width // 2 - 4, restart_y - button_height // 2 - 4,
            button_x + button_width // 2 + 4, restart_y + button_height // 2 + 4,
            fill="#ffcc66", outline="", tags="pause_menu"
        )
        restart_btn = self.canvas.create_rectangle(
            button_x - button_width // 2, restart_y - button_height // 2,
            button_x + button_width // 2, restart_y + button_height // 2,
            fill="#ffaa44", outline="#ffffff", width=3, tags="pause_menu"
        )
        restart_shadow = self.canvas.create_text(
            button_x + 2, restart_y + 2,
            text="↻ RESTART",
            fill="#332200", font=("Arial", 28, "bold"),
            tags="pause_menu"
        )
        restart_text = self.canvas.create_text(
            button_x, restart_y,
            text="↻ RESTART",
            fill="white", font=("Arial", 28, "bold"),
            tags="pause_menu"
        )
        self.pause_menu_items.extend([restart_glow, restart_btn, restart_shadow, restart_text])
        self.canvas.tag_bind(restart_btn, "<Button-1>", lambda e: self.restart_from_pause())
        
        # Quit button (red with glow)
        quit_y = restart_y + button_spacing
        quit_glow = self.canvas.create_rectangle(
            button_x - button_width // 2 - 4, quit_y - button_height // 2 - 4,
            button_x + button_width // 2 + 4, quit_y + button_height // 2 + 4,
            fill="#ff6666", outline="", tags="pause_menu"
        )
        quit_btn = self.canvas.create_rectangle(
            button_x - button_width // 2, quit_y - button_height // 2,
            button_x + button_width // 2, quit_y + button_height // 2,
            fill="#ff4444", outline="#ffffff", width=3, tags="pause_menu"
        )
        quit_shadow = self.canvas.create_text(
            button_x + 2, quit_y + 2,
            text="✕ QUIT TO MENU",
            fill="#330000", font=("Arial", 28, "bold"),
            tags="pause_menu"
        )
        quit_text = self.canvas.create_text(
            button_x, quit_y,
            text="✕ QUIT TO MENU",
            fill="white", font=("Arial", 28, "bold"),
            tags="pause_menu"
        )
        self.pause_menu_items.extend([quit_glow, quit_btn, quit_shadow, quit_text])
        self.canvas.tag_bind(quit_btn, "<Button-1>", lambda e: self.quit_to_menu())
        
        # Hint text at bottom
        hint = self.canvas.create_text(
            self.width // 2, quit_y + 80,
            text="ESC to resume  •  Pause music playing",
            fill="#888888", font=("Arial", 14, "italic"),
            tags="pause_menu"
        )
        self.pause_menu_items.append(hint)
        
        # Lift all pause menu items to top
        for item in self.pause_menu_items:
            try:
                self.canvas.lift(item)
            except Exception:
                pass
    
    def hide_pause_menu(self):
        """Hide the pause menu."""
        for item in self.pause_menu_items:
            try:
                self.canvas.delete(item)
            except Exception:
                pass
        self.pause_menu_items.clear()
    
    def restart_from_pause(self):
        """Restart game from pause menu."""
        self.paused = False
        self.hide_pause_menu()
        self.restart_game(force=True)
    
    def quit_to_menu(self):
        """Quit to main menu."""
        self.paused = False
        self.game_started = False
        self.hide_pause_menu()
        self.show_main_menu()

    def shoot_bullet(self):
        if not self.game_over:
            x = random.randint(0, self.width-20)
            bullet = self.canvas.create_oval(x, 0, x + 20, 20, fill="red")
            self.bullets.append(bullet)

    def shoot_egg_bullet(self):
        if not self.game_over:
            x = random.randint(0, self.width-20)
            bullet = self.canvas.create_oval(x, 0, x + 20, 40, fill="tan")
            self.egg_bullets.append(bullet)

    def shoot_bullet2(self):
        if not self.game_over:
            y = random.randint(0, self.height-20)
            bullet2 = self.canvas.create_oval(0, y, 20, y + 20, fill="yellow")
            self.bullets2.append(bullet2)

    def shoot_diag_bullet(self):
        if not self.game_over:
            x = random.randint(0, self.width-20)
            direction = random.choice([1, -1])  # 1 for right-down, -1 for left-down
            dbullet = self.canvas.create_oval(x, 0, x + 20, 20, fill="green")
            self.diag_bullets.append((dbullet, direction))

    def shoot_boss_bullet(self):
        if not self.game_over:
            x = random.randint(self.width//4, self.width*3//4)
            bullet = self.canvas.create_oval(x, 0, x + 40, 40, fill="purple")
            self.boss_bullets.append(bullet)

    def show_graze_effect(self):
        # Remove previous effect if present
        if self.graze_effect_id:
            self.canvas.delete(self.graze_effect_id)
        px1, py1, px2, py2 = self.canvas.coords(self.player)
        cx = (px1 + px2) / 2
        cy = (py1 + py2) / 2
        self.graze_effect_id = self.canvas.create_oval(
            cx - self.grazing_radius, cy - self.grazing_radius,
            cx + self.grazing_radius, cy + self.grazing_radius,
            outline="white", dash=(5, 5), width=2
        )
        self.graze_effect_timer = 4  # Number of update cycles to show (200ms)

    def check_graze(self, bullet, player_coords=None):
        """Returns True if bullet grazes player (close but not colliding).
        player_coords: Optional cached (px1, py1, px2, py2) to avoid repeated canvas.coords calls
        """
        bullet_coords = self.canvas.coords(bullet)
        if len(bullet_coords) < 4:
            return False  # Bullet was deleted or invalid
        # Use cached player coords if provided
        if player_coords:
            px1, py1, px2, py2 = player_coords
        else:
            px1, py1, px2, py2 = self.canvas.coords(self.player)
        cx = (px1 + px2) / 2
        cy = (py1 + py2) / 2
        # Handle polygons (coords > 4)
        if len(bullet_coords) > 4:
            xs = bullet_coords[::2]
            ys = bullet_coords[1::2]
            bx = sum(xs) / len(xs)
            by = sum(ys) / len(ys)
        else:
            bx = (bullet_coords[0] + bullet_coords[2]) / 2
            by = (bullet_coords[1] + bullet_coords[3]) / 2
        dist = ((cx - bx) ** 2 + (cy - by) ** 2) ** 0.5
        # Not colliding, but within grazing radius
        if dist < self.grazing_radius + 10 and not self.check_collision(bullet, player_coords):
            return True
        return False

    def check_collision(self, bullet, player_coords=None):
        """Axis-aligned hitbox collision between player rectangle and a bullet shape.
        Supports ovals/rectangles (4 coords) and polygons (>=6 coords). Returns True on hit.
        player_coords: Optional cached (px1, py1, px2, py2) to avoid repeated canvas.coords calls
        """
        if self.practice_mode or self.game_over:
            return False
        # brief invulnerability after static trap escape
        if self.static_trap_invuln_end and time.time() < self.static_trap_invuln_end:
            return False
        try:
            b = self.canvas.coords(bullet)
            if not b:
                return False
            # Player rectangle (use cached if provided, else fetch)
            if player_coords:
                px1, py1, px2, py2 = player_coords
            else:
                px1, py1, px2, py2 = self.canvas.coords(self.player)
            # Bullet bounding box
            if len(b) == 4:
                bx1, by1, bx2, by2 = b
            else:
                xs = b[::2]
                ys = b[1::2]
                bx1, bx2 = min(xs), max(xs)
                by1, by2 = min(ys), max(ys)
            # AABB overlap
            if px1 < bx2 and px2 > bx1 and py1 < by2 and py2 > by1:
                self.handle_player_hit()
                return True
        except Exception:
            return False
        return False

    def handle_player_hit(self):
        """Process a player hit: decrement life (if multiple), or trigger game over animation."""
        if self.practice_mode:
            return False
        if self.game_over:
            return
        
        # Check if shield is active (optimized early return)
        if self.shield_active and self.shield_hits_remaining > 0:
            self.shield_hits_remaining -= 1
            # Shield absorbed the hit
            if self.shield_hits_remaining <= 0:
                self.deactivate_shield()
            # Flash shield visual to show hit
            try:
                if self.shield_visual:
                    self.canvas.itemconfig(self.shield_visual, outline="#ff66ff")
                    # Reset color after brief flash
                    self.root.after(100, lambda: self.canvas.itemconfig(self.shield_visual, outline="#9966ff") if self.shield_visual else None)
            except Exception:
                pass
            return False  # Hit was absorbed
        
        self.lives -= 1
        # Update hearts HUD
        if hasattr(self, 'update_health_display'):
            self.update_health_display()
        if self.lives <= 0:
            # Pick a random game over message once
            try:
                if self.game_over_messages:
                    self.selected_game_over_message = random.choice(self.game_over_messages)
                else:
                    self.selected_game_over_message = None
            except Exception:
                self.selected_game_over_message = None
            self.game_over = True
            # Start game over animation if available
            try:
                pygame.mixer.music.stop()
                pygame.mixer.music.unload()
            except Exception:
                pass
            self.start_game_over_animation()
        else:
            # Flash player or simple feedback (placeholder)
            try:
                self.canvas.itemconfig(self.player, fill="#ffffff")
            except Exception:
                pass

    def end_game(self):
        """Compatibility method for legacy calls in bullet logic.
        Ensures game over animation triggers even if older code calls end_game()."""
        if self.game_over:
            return
        # Select message if not already chosen
        try:
            if getattr(self, 'selected_game_over_message', None) is None and getattr(self, 'game_over_messages', None):
                if self.game_over_messages:
                    self.selected_game_over_message = random.choice(self.game_over_messages)
        except Exception:
            pass
        self.game_over = True
        try:
            pygame.mixer.music.stop()
            pygame.mixer.music.unload()
        except Exception:
            pass
        try:
            self.start_game_over_animation()
        except Exception:
            # Fallback minimal display
            try:
                msg = getattr(self, 'selected_game_over_message', 'GAME OVER') or 'GAME OVER'
                self.canvas.create_text(self.width//2, self.height//2, text=msg, fill='white', font=('Arial', 48, 'bold'))
            except Exception:
                pass

    def update_game(self):
        global pyi_splash
        # Don't update game logic if not in game
        if not self.game_started or self.in_main_menu or self.in_settings_menu:
            return
        
        if pyi_splash is not None:
            pyi_splash.close()
            pyi_splash = None
        if self.game_over:
            return
        if self.paused:
            return
        # If static trap active, update trap sequence and skip rest of gameplay movement/spawn
        if self.static_trap_active:
            self._update_static_trap()
            self.root.after(50, self.update_game)
            return
        # Frame timing capture for Debug HUD
        try:
            now_perf = time.perf_counter()
            if hasattr(self, '_last_frame_time_stamp'):
                dt_ms = (now_perf - self._last_frame_time_stamp) * 1000.0
                self._frame_time_buffer.append(dt_ms)
            self._last_frame_time_stamp = now_perf
        except Exception:
            pass
        # Update focus pulse cooldown timer (wall time based)
        if self.focus_pulse_cooldown > 0:
            self.focus_pulse_cooldown -= 0.05  # approx frame duration
            if self.focus_pulse_cooldown < 0:
                self.focus_pulse_cooldown = 0
        # Update focus charge accumulation & visuals
        self._update_focus_charge()
        self._update_focus_visuals()
        
        # Update input methods
        self.update_mouse_movement()
        self.update_controller_input()
        
        # Update player shots and boss
        self.update_player_shots()
        self.update_boss()
        self.update_collectables()
        
    # Background animation
        self.update_background()
    # Animate player decorative sprite
        self.animate_player_sprite()
        self.canvas.lift(self.dialog)
        self.canvas.lift(self.scorecount)
        self.canvas.lift(self.timecount)
        if hasattr(self, 'next_unlock_text'):
            self.canvas.lift(self.next_unlock_text)
        # Update and lift boss damage counter
        if hasattr(self, 'boss_damage_text'):
            try:
                self.canvas.itemconfig(self.boss_damage_text, text=f"Boss Hits: {self.boss_health_display}")
                self.canvas.lift(self.boss_damage_text)
            except Exception:
                pass
        # Update and lift collectable counter
        if hasattr(self, 'collectable_display_text'):
            try:
                self.canvas.itemconfig(self.collectable_display_text, text=f"Items: {len(self.collected_items)}/{self.total_collectables}")
                self.canvas.lift(self.collectable_display_text)
            except Exception:
                pass
        # Lift boss to be visible
        if hasattr(self, 'boss_entity') and self.boss_entity:
            try:
                self.canvas.lift(self.boss_entity)
            except Exception:
                pass
        # Ensure hearts appear on top of bullets
        if getattr(self, 'health_icon_items', None):
            for hid in self.health_icon_items:
                try:
                    self.canvas.lift(hid)
                except Exception:
                    pass
        # Move graze effect to follow player if active
        if self.graze_effect_id:
            px1, py1, px2, py2 = self.canvas.coords(self.player)
            cx = (px1 + px2) / 2
            cy = (py1 + py2) / 2
            self.canvas.coords(
                self.graze_effect_id,
                cx - self.grazing_radius, cy - self.grazing_radius,
                cx + self.grazing_radius, cy + self.grazing_radius
            )
            self.graze_effect_timer -= 1
            if self.graze_effect_timer <= 0:
                self.canvas.delete(self.graze_effect_id)
                self.graze_effect_id = None
        # Increase difficulty every 60 seconds
        now = time.time()
    # Difficulty scaling removed
        if now - self.lastdial > 10:
            self.get_dialog_string()
            self.lastdial = now
            self.canvas.itemconfig(self.dialog, text=self.dial)
        # Lore rotation
        if getattr(self, 'lore_text', None) is not None and now - getattr(self, 'lore_last_change', 0) >= getattr(self, 'lore_interval', 8):
            self.update_lore_line()
        # Calculate time survived, pausable
        time_survived = int(now - self.timee - self.paused_time_total)
        self.canvas.itemconfig(self.scorecount, text=f"Score: {self.score}")
        self.canvas.itemconfig(self.timecount, text=f"Time: {time_survived}")
        # Handle freeze expiration
        if self.freeze_active and now >= self.freeze_end_time:
            self.freeze_active = False
            if self.freeze_text:
                try:
                    self.canvas.delete(self.freeze_text)
                except Exception:
                    pass
                self.freeze_text = None
            # Remove overlay & particles
            if self.freeze_overlay:
                try: self.canvas.delete(self.freeze_overlay)
                except Exception: pass
                self.freeze_overlay = None
            for pid, *_ in self.freeze_particles:
                try: self.canvas.delete(pid)
                except Exception: pass
            self.freeze_particles.clear()
            # Restore bullet colors
            self._tint_all_bullets(freeze=False)
            # Spawn shatter burst effect from each bullet to show reactivation
            self._spawn_unfreeze_shatter()
        
        # Handle slow-motion expiration
        if self.slowmo_active and now >= self.slowmo_end_time:
            self.deactivate_slowmo()
            # Restore music volume
            try:
                if hasattr(self, '_slowmo_prev_volume') and pygame.mixer.music.get_busy():
                    pygame.mixer.music.set_volume(self._slowmo_prev_volume)
            except Exception:
                pass
        
        # Update shield visual position and check text removal
        if self.shield_active:
            self.update_shield_visual()
            # Remove shield text after delay
            if hasattr(self, 'shield_text_remove_time') and now >= self.shield_text_remove_time:
                if self.shield_text:
                    try: self.canvas.delete(self.shield_text)
                    except Exception: pass
                    self.shield_text = None
        
        # Update shield particles (optimized batch processing)
        if self.shield_particles:
            new_sp = []
            for pid, x, y, vx, vy, life in self.shield_particles:
                life -= 1
                if life > 0:
                    try:
                        x += vx
                        y += vy
                        self.canvas.coords(pid, x-2, y-2, x+2, y+2)
                        # Fade effect
                        if life < 8:
                            alpha = int(life * 31.875)  # Fade from 255 to 0
                            self.canvas.itemconfig(pid, fill=f"#{alpha:02x}66ff")
                        new_sp.append((pid, x, y, vx, vy, life))
                    except Exception:
                        try: self.canvas.delete(pid)
                        except Exception: pass
                else:
                    try: self.canvas.delete(pid)
                    except Exception: pass
            self.shield_particles = new_sp
        
        # Update slow-motion particles (optimized batch processing)
        if self.slowmo_particles:
            new_smp = []
            for pid, x, y, vx, vy, life in self.slowmo_particles:
                life -= 1
                if life > 0:
                    try:
                        x += vx
                        y += vy
                        self.canvas.coords(pid, x-2, y-2, x+2, y+2)
                        # Fade effect
                        if life < 10:
                            alpha = int(life * 25.5)
                            self.canvas.itemconfig(pid, fill=f"#ff{alpha:02x}33")
                        new_smp.append((pid, x, y, vx, vy, life))
                    except Exception:
                        try: self.canvas.delete(pid)
                        except Exception: pass
                else:
                    try: self.canvas.delete(pid)
                    except Exception: pass
            self.slowmo_particles = new_smp
        
        # Update slow-motion text countdown
        if self.slowmo_active and self.slowmo_text:
            remaining = max(0.0, self.slowmo_end_time - now)
            try:
                self.canvas.itemconfig(self.slowmo_text, text=f"SLOW MOTION {remaining:.1f}s")
                self.canvas.lift(self.slowmo_text)
            except Exception:
                pass
        
        # Handle rewind expiration
        if self.rewind_active and now >= self.rewind_end_time:
            self.rewind_active = False
            self._rewind_pointer = None
            if self.rewind_text:
                try: self.canvas.delete(self.rewind_text)
                except Exception: pass
                self.rewind_text = None
            if self._rewind_overlay:
                try: self.canvas.delete(self._rewind_overlay)
                except Exception: pass
                self._rewind_overlay = None
            # Clear vignette
            self._clear_rewind_vignette()
            # Award score bonus based on bullet count at start
            try:
                bonus = int(self._rewind_start_bullet_count * self._rewind_bonus_factor)
                if bonus > 0:
                    self.score += bonus
                    # transient floating text
                    try:
                        txt = self.canvas.create_text(self.width//2, self.height//2 + 60, text=f"+{bonus} REWIND BONUS", fill="#66ff99", font=("Arial", 28, "bold"))
                        self.canvas.after(1200, lambda tid=txt: (self.canvas.delete(tid) if self.canvas.type(tid) else None))
                    except Exception:
                        pass
            except Exception:
                pass
            # Play end sound
            try:
                if self._rewind_end_sound is None:
                    base_dir = getattr(sys, '_MEIPASS', os.path.dirname(__file__))
                    p = os.path.join(base_dir, 'rewind_end.wav')
                    if os.path.exists(p):
                        self._rewind_end_sound = pygame.mixer.Sound(p)
                if self._rewind_end_sound:
                    self._rewind_end_sound.play()
            except Exception:
                pass
        # If freeze just ended and a rewind was pending, activate it now
        if (not self.freeze_active) and self.rewind_pending and not self.rewind_active:
            self.rewind_pending = False
            self.activate_rewind(self._pending_rewind_duration)
        # Update rewind countdown label
        if self.rewind_active and self.rewind_text:
            remaining = max(0.0, self.rewind_end_time - now)
            try:
                self.canvas.itemconfig(self.rewind_text, text=f"REWIND {remaining:0.1f}s")
                self.canvas.lift(self.rewind_text)
            except Exception:
                pass
        # Show queued rewind label if pending
        if self.rewind_pending and not self.rewind_active:
            if not self.rewind_pending_text:
                try:
                    self.rewind_pending_text = self.canvas.create_text(self.width//2, self.height//2 - 140, text="REWIND QUEUED", fill="#66ff99", font=("Arial", 24, "bold"))
                except Exception:
                    self.rewind_pending_text = None
            else:
                try: self.canvas.lift(self.rewind_pending_text)
                except Exception: pass
        else:
            if self.rewind_pending_text and not self.rewind_active:
                # If no longer pending (activated), it is cleared inside activate_rewind
                pass
        # Update freeze countdown text if active
        if self.freeze_active and self.freeze_text:
            remaining = max(0.0, self.freeze_end_time - now)
            try:
                self.canvas.itemconfig(self.freeze_text, text=f"FREEZE {remaining:0.1f}s")
                self.canvas.lift(self.freeze_text)
            except Exception:
                pass
        # Spawn/update freeze particles (slow drifting flakes) while frozen
        if self.freeze_active:
            # spawn a few each frame
            for _ in range(3):
                x = random.randint(0, self.width)
                y = random.randint(0, self.height)
                size = random.randint(3,6)
                try:
                    pid = self.canvas.create_oval(x-size/2, y-size/2, x+size/2, y+size/2, fill="#c9f6ff", outline="")
                except Exception:
                    continue
                vx = random.uniform(-0.5,0.5)
                vy = random.uniform(0.2,0.8)
                life = random.randint(18,35)
                self.freeze_particles.append((pid, vx, vy, life))
            new_fp = []
            for pid, vx, vy, life in self.freeze_particles:
                life -= 1
                try:
                    self.canvas.move(pid, vx, vy)
                    if life < 10:
                        # fade via stipple swap if possible
                        if life % 2 == 0:
                            self.canvas.itemconfig(pid, fill="#99ddee")
                    if life > 0:
                        new_fp.append((pid, vx, vy, life))
                    else:
                        self.canvas.delete(pid)
                except Exception:
                    pass
            self.freeze_particles = new_fp
        # Compute next unlock pattern
        remaining_candidates = [(pat, t_req - time_survived) for pat, t_req in self.unlock_times.items() if t_req > time_survived]
        if remaining_candidates:
            # Pick soonest
            pat, secs = min(remaining_candidates, key=lambda x: x[1])
            display = self.pattern_display_names.get(pat, pat.title())
            self.canvas.itemconfig(self.next_unlock_text, text=f"Next Pattern: {display} in {secs}s")
        else:
            self.canvas.itemconfig(self.next_unlock_text, text="All patterns unlocked")

        # Fixed spawn chances (1 in N each frame after unlock)
        bullet_chance = 18
        bullet2_chance = 22
        diag_chance = 28
        boss_chance = 140
        zigzag_chance = 40
        fast_chance = 30
        star_chance = 55
        rect_chance = 48
        laser_chance = 160
        triangle_chance = 46
        quad_chance = 52
        egg_chance = 50
        bouncing_chance = 70
        exploding_chance = 90
        homing_chance = 110
        spiral_chance = 130
        radial_chance = 150
        wave_chance = 160
        boomerang_chance = 170
        split_chance = 180

        # --- Freeze power-up spawn (independent of bullet patterns) ---
        # Only spawn if not currently active and limited number on screen
        if not self.freeze_active and len(self.freeze_powerups) < 1:
            # Increased spawn rate for testing: ~every 5 seconds (1 in 1000 per 50ms frame)
            if random.randint(1, 1000) == 1:
                self.spawn_freeze_powerup()
        # --- Rewind power-up spawn ---
        if not self.rewind_active and len(self.rewind_powerups) < 1:
            # Increased spawn rate for testing: ~every 7 seconds (1 in 1400 per 50ms frame)
            if random.randint(1, 1400) == 1 and len(self._bullet_history) > 40:
                self.spawn_rewind_powerup()
        
        # --- Shield power-up spawn (optimized) ---
        if not self.shield_active and len(self.shield_powerups) < 1:
            # Increased spawn rate for testing: ~every 6 seconds (1 in 1200 per 50ms frame)
            if random.randint(1, 1200) == 1:
                self.spawn_shield_powerup()
        
        # --- Slow-motion power-up spawn (optimized) ---
        if not self.slowmo_active and len(self.slowmo_powerups) < 1:
            # Increased spawn rate for testing: ~every 7 seconds (1 in 1400 per 50ms frame)
            if random.randint(1, 1400) == 1:
                self.spawn_slowmo_powerup()

        # Move existing freeze power-ups downward & check collection
        if self.freeze_powerups:
            print(f"DEBUG: Processing {len(self.freeze_powerups)} freeze powerups")
        for p_entry in self.freeze_powerups[:]:
            try:
                # Handle tuple format
                if isinstance(p_entry, tuple):
                    p_id = p_entry[0]
                else:
                    p_id = p_entry
                
                self.canvas.move(p_id, 0, 4)
                px1, py1, px2, py2 = self.canvas.coords(self.player)
                bx1, by1, bx2, by2 = self.canvas.coords(p_id)
                print(f"DEBUG: Freeze powerup {p_id} at ({bx1}, {by1}, {bx2}, {by2}), Player at ({px1}, {py1}, {px2}, {py2})")
                if bx2 < px1 or bx1 > px2 or by2 < py1 or by1 > py2:
                    # no overlap
                    pass
                else:
                    print(f"DEBUG: Freeze powerup {p_id} collected!")
                    self.activate_freeze()
                    try:
                        self.canvas.delete(p_id)
                    except Exception:
                        pass
                    self.freeze_powerups.remove(p_entry)
                    continue
                # Remove if off screen
                if by1 > self.height:
                    print(f"DEBUG: Freeze powerup {p_id} off screen, removing")
                    try:
                        self.canvas.delete(p_id)
                    except Exception:
                        pass
                    self.freeze_powerups.remove(p_entry)
            except Exception as e:
                print(f"DEBUG: Exception processing freeze powerup {p_entry}: {e}")
                try:
                    self.freeze_powerups.remove(p_entry)
                except Exception:
                    pass
        # Move existing rewind power-ups & check collection
        for r_entry in self.rewind_powerups[:]:
            try:
                # Handle tuple format
                if isinstance(r_entry, tuple):
                    r_id = r_entry[0]
                else:
                    r_id = r_entry
                
                self.canvas.move(r_id, 0, 4)
                px1, py1, px2, py2 = self.canvas.coords(self.player)
                rx1, ry1, rx2, ry2 = self.canvas.coords(r_id)
                # collection overlap
                if not (rx2 < px1 or rx1 > px2 or ry2 < py1 or ry1 > py2):
                    self.activate_rewind()
                    try: self.canvas.delete(r_id)
                    except Exception: pass
                    self.rewind_powerups.remove(r_entry)
                    continue
                if ry1 > self.height:
                    try: self.canvas.delete(r_id)
                    except Exception: pass
                    self.rewind_powerups.remove(r_entry)
            except Exception:
                try: self.rewind_powerups.remove(r_entry)
                except Exception: pass
        
        # Move existing shield power-ups & check collection (optimized)
        px1, py1, px2, py2 = self.canvas.coords(self.player)  # Cache player coords
        for s_entry in self.shield_powerups[:]:
            try:
                # Handle tuple format
                if isinstance(s_entry, tuple):
                    s_id = s_entry[0]
                else:
                    s_id = s_entry
                
                self.canvas.move(s_id, 0, 4)
                sx1, sy1, sx2, sy2 = self.canvas.coords(s_id)
                # Collection overlap check
                if not (sx2 < px1 or sx1 > px2 or sy2 < py1 or sy1 > py2):
                    self.activate_shield()
                    try: self.canvas.delete(s_id)
                    except Exception: pass
                    self.shield_powerups.remove(s_entry)
                    continue
                # Remove if off screen
                if sy1 > self.height:
                    try: self.canvas.delete(s_id)
                    except Exception: pass
                    self.shield_powerups.remove(s_entry)
            except Exception:
                try: self.shield_powerups.remove(s_entry)
                except Exception: pass
        
        # Move existing slow-motion power-ups & check collection (optimized)
        for sm_entry in self.slowmo_powerups[:]:
            try:
                # Handle both single ID and tuple (id, hand1, hand2)
                if isinstance(sm_entry, tuple):
                    sm_id, hand1, hand2 = sm_entry
                    self.canvas.move(sm_id, 0, 4)
                    if hand1: self.canvas.move(hand1, 0, 4)
                    if hand2: self.canvas.move(hand2, 0, 4)
                else:
                    sm_id = sm_entry
                    hand1, hand2 = None, None
                    self.canvas.move(sm_id, 0, 4)
                
                smx1, smy1, smx2, smy2 = self.canvas.coords(sm_id)
                # Collection overlap check
                if not (smx2 < px1 or smx1 > px2 or smy2 < py1 or smy1 > py2):
                    self.activate_slowmo()
                    try: self.canvas.delete(sm_id)
                    except Exception: pass
                    if hand1:
                        try: self.canvas.delete(hand1)
                        except Exception: pass
                    if hand2:
                        try: self.canvas.delete(hand2)
                        except Exception: pass
                    self.slowmo_powerups.remove(sm_entry)
                    continue
                # Remove if off screen
                if smy1 > self.height:
                    try: self.canvas.delete(sm_id)
                    except Exception: pass
                    if hand1:
                        try: self.canvas.delete(hand1)
                        except Exception: pass
                    if hand2:
                        try: self.canvas.delete(hand2)
                        except Exception: pass
                    self.slowmo_powerups.remove(sm_entry)
            except Exception:
                try: self.slowmo_powerups.remove(sm_entry)
                except Exception: pass

        # Time-based unlock gating (progressive difficulty)
        t = time_survived
        if not self.freeze_active:
            # Skip new spawns while rewinding
            if not self.rewind_active and t >= self.unlock_times['vertical'] and random.randint(1, bullet_chance) == 1:
                self.shoot_bullet()
            if not self.rewind_active and t >= self.unlock_times['horizontal'] and random.randint(1, bullet2_chance) == 1:
                self.shoot_bullet2()
            if not self.rewind_active and t >= self.unlock_times['diag'] and random.randint(1, diag_chance) == 1:
                self.shoot_diag_bullet()
            if not self.rewind_active and t >= self.unlock_times['boss'] and random.randint(1, boss_chance) == 1:
                self.shoot_boss_bullet()
            if not self.rewind_active and t >= self.unlock_times['zigzag'] and random.randint(1, zigzag_chance) == 1:
                self.shoot_zigzag_bullet()
            if not self.rewind_active and t >= self.unlock_times['fast'] and random.randint(1, fast_chance) == 1:
                self.shoot_fast_bullet()
            if not self.rewind_active and t >= self.unlock_times['star'] and random.randint(1, star_chance) == 1:
                self.shoot_star_bullet()
            if not self.rewind_active and t >= self.unlock_times['rect'] and random.randint(1, rect_chance) == 1:
                self.shoot_rect_bullet()
            if not self.rewind_active and t >= self.unlock_times['laser'] and random.randint(1, laser_chance) == 1:
                self.shoot_horizontal_laser()
            if not self.rewind_active and t >= self.unlock_times['triangle'] and random.randint(1, triangle_chance) == 1:
                self.shoot_triangle_bullet()
            if not self.rewind_active and t >= self.unlock_times['quad'] and random.randint(1, quad_chance) == 1:
                self.shoot_quad_bullet()
            if not self.rewind_active and t >= self.unlock_times['egg'] and random.randint(1, egg_chance) == 1:
                self.shoot_egg_bullet()
            if not self.rewind_active and t >= self.unlock_times['bouncing'] and random.randint(1, bouncing_chance) == 1:
                self.shoot_bouncing_bullet()
            if not self.rewind_active and t >= self.unlock_times['exploding'] and random.randint(1, exploding_chance) == 1:
                self.shoot_exploding_bullet()
            if not self.rewind_active and t >= self.unlock_times['homing'] and random.randint(1, homing_chance) == 1:
                self.shoot_homing_bullet()
            if not self.rewind_active and t >= self.unlock_times['spiral'] and random.randint(1, spiral_chance) == 1:
                self.shoot_spiral_bullet()
            if not self.rewind_active and t >= self.unlock_times['radial'] and random.randint(1, radial_chance) == 1:
                self.shoot_radial_burst()
            if not self.rewind_active and t >= self.unlock_times['wave'] and random.randint(1, wave_chance) == 1:
                self.shoot_wave_bullet()
            if not self.rewind_active and t >= self.unlock_times['boomerang'] and random.randint(1, boomerang_chance) == 1:
                self.shoot_boomerang_bullet()
            if not self.rewind_active and t >= self.unlock_times['split'] and random.randint(1, split_chance) == 1:
                self.shoot_split_bullet()
        # Capture bullet snapshot (post spawn) if not frozen or rewinding
        if not self.freeze_active and not self.rewind_active:
            try:
                self._capture_bullet_snapshot()
            except Exception:
                pass
        
        # Memory optimization: Periodically clean grazed_bullets set (every ~5 seconds)
        # This prevents unbounded growth of the set which holds references to deleted bullets
        if not hasattr(self, '_last_graze_cleanup'):
            self._last_graze_cleanup = now
        if now - self._last_graze_cleanup > 5.0 and len(self.grazed_bullets) > 100:
            # Keep only bullets that still exist on canvas
            valid_bullets = set()
            for bid in self.grazed_bullets:
                try:
                    if self.canvas.coords(bid):  # Check if bullet still exists
                        valid_bullets.add(bid)
                except Exception:
                    pass
            self.grazed_bullets = valid_bullets
            self._last_graze_cleanup = now

        # If freeze is active, skip movement updates for bullets (they remain frozen in place)
        if self.freeze_active:
            self.root.after(50, self.update_game)
            return
        if self.rewind_active:
            # Rewind bullet positions instead of advancing
            self._perform_rewind_step()
            self.root.after(50, self.update_game)
            return
        
        # Calculate speed multiplier once for all bullet types (optimization)
        speed_multiplier = self.slowmo_factor if self.slowmo_active else 1.0
        
        # Cache player coordinates for all collision checks (major optimization)
        try:
            px1, py1, px2, py2 = self.canvas.coords(self.player)
            player_coords_cached = (px1, py1, px2, py2)
        except Exception:
            player_coords_cached = None
        
        # Move triangle bullets (optimized)
        triangle_speed = 7 * speed_multiplier
        for bullet_tuple in self.triangle_bullets[:]:
            bullet, direction = bullet_tuple
            self.canvas.move(bullet, triangle_speed * direction, triangle_speed)
            if self.check_collision(bullet, player_coords_cached):
                self.canvas.delete(bullet)
                self.paused = False
                self.pause_text = None
                self.triangle_bullets.remove(bullet_tuple)
            else:
                coords = self.canvas.coords(bullet)
                if coords and (coords[1] > self.height or coords[0] < 0 or coords[2] > self.width):
                    self.canvas.delete(bullet)
                    self.triangle_bullets.remove(bullet_tuple)
                    self.score += 2
        
        # Move bouncing bullets (optimized to reduce index lookups)
        new_bouncing = []
        for bullet_tuple in self.bouncing_bullets:
            bullet, x_velocity, y_velocity, bounces_left = bullet_tuple
            self.canvas.move(bullet, x_velocity * speed_multiplier, y_velocity * speed_multiplier)
            coords = self.canvas.coords(bullet)
            if not coords:
                continue
            bounced = False
            # Bounce off left/right
            if coords[0] <= 0 or coords[2] >= self.width:
                x_velocity = -x_velocity
                bounced = True
            # Bounce off top/bottom
            if coords[1] <= 0 or coords[3] >= self.height:
                y_velocity = -y_velocity
                bounced = True
            if bounced:
                bounces_left -= 1
            # Remove bullet if out of bounces
            if bounces_left < 0:
                self.canvas.delete(bullet)
                self.score += 2
                continue
            # Check collision (using centralized handler for shield support)
            if self.check_collision(bullet, player_coords_cached):
                self.canvas.delete(bullet)
                continue
            # Keep bullet with updated values
            new_bouncing.append((bullet, x_velocity, y_velocity, bounces_left))
        self.bouncing_bullets = new_bouncing
        # Move exploding bullets
        for bullet in self.exploding_bullets[:]:
            self.canvas.move(bullet, 0, 5 + self.difficulty // 3)
            coords = self.canvas.coords(bullet)
            # Check if bullet reached middle of screen (y ~ self.height//2)
            if coords and abs((coords[1] + coords[3]) / 2 - self.height // 2) < 20:
                # Explode into 4 diagonal fragments
                bx = (coords[0] + coords[2]) / 2
                by = (coords[1] + coords[3]) / 2
                size = 12
                directions = [(6, 6), (-6, 6), (6, -6), (-6, -6)]
                for dx, dy in directions:
                    frag = self.canvas.create_oval(bx-size//2, by-size//2, bx+size//2, by+size//2, fill="white")
                    self.exploded_fragments.append((frag, dx, dy))
                self.canvas.delete(bullet)
                self.exploding_bullets.remove(bullet)
                self.score += 2
                continue
            if self.check_collision(bullet):
                self.lives -= 1
                self.canvas.delete(bullet)
                self.exploding_bullets.remove(bullet)
                if self.lives <= 0:
                    self.end_game()
            else:
                if coords and coords[1] > self.height:
                    self.canvas.delete(bullet)
                    self.exploding_bullets.remove(bullet)
                    self.score += 2
        # Move exploded fragments (diagonal bullets)
        for frag_tuple in self.exploded_fragments[:]:
            frag, dx, dy = frag_tuple
            self.canvas.move(frag, dx, dy)
            coords = self.canvas.coords(frag)
            if self.check_collision(frag):
                self.lives -= 1
                self.canvas.delete(frag)
                self.exploded_fragments.remove(frag_tuple)
                if self.lives <= 0:
                    self.end_game()
            elif coords and (coords[1] > self.height or coords[0] < 0 or coords[2] > self.width or coords[3] < 0):
                self.canvas.delete(frag)
                self.exploded_fragments.remove(frag_tuple)
                self.score += 1
            # Grazing check
            if self.check_graze(frag) and frag not in self.grazed_bullets:
                self.score += 1
                self.grazed_bullets.add(frag)
                self.show_graze_effect()
        # Handle laser indicators
        for indicator_tuple in self.laser_indicators[:]:
            indicator_id, y, timer = indicator_tuple
            timer -= 1
            if timer <= 0:
                self.canvas.delete(indicator_id)
                # Spawn actual laser
                laser_id = self.canvas.create_line(0, y, self.width, y, fill="red", width=8)
                self.lasers.append((laser_id, y, 20))  # Laser lasts 20 frames
                self.laser_indicators.remove(indicator_tuple)
            else:
                idx = self.laser_indicators.index(indicator_tuple)
                self.laser_indicators[idx] = (indicator_id, y, timer)

        # Handle lasers
        for laser_tuple in self.lasers[:]:
            laser_id, y, timer = laser_tuple
            timer -= 1
            # Check collision with player
            player_coords = self.canvas.coords(self.player)
            if player_coords[1] <= y <= player_coords[3]:
                self.lives -= 1
                self.canvas.delete(laser_id)
                self.lasers.remove(laser_tuple)
                if self.lives <= 0:
                    self.end_game()
                continue
            if timer <= 0:
                self.canvas.delete(laser_id)
                self.lasers.remove(laser_tuple)
            else:
                idx = self.lasers.index(laser_tuple)
                self.lasers[idx] = (laser_id, y, timer)

        # Bullet speeds scale with difficulty
        # (speed_multiplier and player_coords_cached already calculated earlier in update_game)
        bullet_speed = 7 * speed_multiplier
        bullet2_speed = 7 * speed_multiplier
        diag_speed = 5 * speed_multiplier
        boss_speed = 10 * speed_multiplier
        zigzag_speed = 5 * speed_multiplier
        fast_speed = 14 * speed_multiplier
        star_speed = 8 * speed_multiplier
        rect_speed = 8 * speed_multiplier
        quad_speed = 7 * speed_multiplier
        egg_speed = 6 * speed_multiplier
        homing_speed = 6 * speed_multiplier

        # Move vertical bullets (optimized with cached player coords)
        for bullet in self.bullets[:]:
            self.canvas.move(bullet, 0, bullet_speed)
            if self.check_collision(bullet, player_coords_cached):
                if not self.practice_mode:
                    self.lives -= 1
                    if self.lives <= 0:
                        self.end_game()
                self.canvas.delete(bullet)
                self.bullets.remove(bullet)
            elif self.canvas.coords(bullet)[1] > self.height:
                self.canvas.delete(bullet)
                self.bullets.remove(bullet)
                self.score += 1
            # Grazing check
            elif self.check_graze(bullet, player_coords_cached) and bullet not in self.grazed_bullets:
                self.score += 1
                self.grazed_bullets.add(bullet)
                self.show_graze_effect()
                if self.focus_active:
                    self.focus_charge = min(1.0, self.focus_charge + self.focus_charge_graze_bonus)
                    if self.focus_charge >= self.focus_charge_threshold:
                        self.focus_charge_ready = True

        # Move horizontal bullets (optimized with cached player coords)
        for bullet2 in self.bullets2[:]:
            self.canvas.move(bullet2, bullet2_speed, 0)
            if self.check_collision(bullet2, player_coords_cached):
                if not self.practice_mode:
                    self.lives -= 1
                    if self.lives <= 0:
                        self.end_game()
                self.canvas.delete(bullet2)
                self.bullets2.remove(bullet2)
            elif self.canvas.coords(bullet2)[0] > self.width:
                self.canvas.delete(bullet2)
                self.bullets2.remove(bullet2)
                self.score += 1
            # Grazing check
            elif self.check_graze(bullet2, player_coords_cached) and bullet2 not in self.grazed_bullets:
                self.score += 1
                self.grazed_bullets.add(bullet2)
                self.show_graze_effect()
                if self.focus_active:
                    self.focus_charge = min(1.0, self.focus_charge + self.focus_charge_graze_bonus)
                    if self.focus_charge >= self.focus_charge_threshold:
                        self.focus_charge_ready = True

        # Move egg bullets (optimized with cached player coords)
        for egg_bullet in self.egg_bullets[:]:
            self.canvas.move(egg_bullet, 0, egg_speed)
            if self.check_collision(egg_bullet, player_coords_cached):
                if not self.practice_mode:
                    self.lives -= 1
                    if self.lives <= 0:
                        self.end_game()
                self.canvas.delete(egg_bullet)
                self.egg_bullets.remove(egg_bullet)
            elif self.canvas.coords(egg_bullet)[1] > self.height:
                self.canvas.delete(egg_bullet)
                self.egg_bullets.remove(egg_bullet)
                self.score += 2
            # Grazing check
            elif self.check_graze(egg_bullet, player_coords_cached) and egg_bullet not in self.grazed_bullets:
                self.score += 1
                self.grazed_bullets.add(egg_bullet)
                self.show_graze_effect()
                if self.focus_active:
                    self.focus_charge = min(1.0, self.focus_charge + self.focus_charge_graze_bonus)
                    if self.focus_charge >= self.focus_charge_threshold:
                        self.focus_charge_ready = True

        # Move diagonal bullets (optimized)
        for bullet_tuple in self.diag_bullets[:]:
            dbullet, direction = bullet_tuple
            self.canvas.move(dbullet, diag_speed * direction, diag_speed)
            if self.check_collision(dbullet, player_coords_cached):
                if not self.practice_mode:
                    self.lives -= 1
                    if self.lives <= 0:
                        self.end_game()
                self.canvas.delete(dbullet)
                self.diag_bullets.remove(bullet_tuple)
            elif self.canvas.coords(dbullet)[1] > self.height:
                self.canvas.delete(dbullet)
                self.diag_bullets.remove(bullet_tuple)
                self.score += 2
            # Grazing check
            elif self.check_graze(dbullet, player_coords_cached) and dbullet not in self.grazed_bullets:
                self.score += 1
                self.grazed_bullets.add(dbullet)
                self.show_graze_effect()
                if self.focus_active:
                    self.focus_charge = min(1.0, self.focus_charge + self.focus_charge_graze_bonus)
                    if self.focus_charge >= self.focus_charge_threshold:
                        self.focus_charge_ready = True

        # Move boss bullets (optimized)
        for boss_bullet in self.boss_bullets[:]:
            self.canvas.move(boss_bullet, 0, boss_speed)
            if self.check_collision(boss_bullet, player_coords_cached):
                if not self.practice_mode:
                    self.lives -= 1
                    if self.lives <= 0:
                        self.end_game()
                self.canvas.delete(boss_bullet)
                self.boss_bullets.remove(boss_bullet)
            elif self.canvas.coords(boss_bullet)[1] > self.height:
                self.canvas.delete(boss_bullet)
                self.boss_bullets.remove(boss_bullet)
                self.score += 5  # Boss bullets give more score
            # Grazing check
            elif self.check_graze(boss_bullet, player_coords_cached) and boss_bullet not in self.grazed_bullets:
                self.score += 2
                self.grazed_bullets.add(boss_bullet)
                self.show_graze_effect()
                if self.focus_active:
                    self.focus_charge = min(1.0, self.focus_charge + self.focus_charge_graze_bonus)
                    if self.focus_charge >= self.focus_charge_threshold:
                        self.focus_charge_ready = True

        # Move quad bullets (optimized)
        for bullet in self.quad_bullets[:]:
            self.canvas.move(bullet, 0, quad_speed)
            if self.check_collision(bullet, player_coords_cached):
                if not self.practice_mode:
                    self.lives -= 1
                    if self.lives <= 0:
                        self.end_game()
                self.canvas.delete(bullet)
                self.quad_bullets.remove(bullet)
            elif self.canvas.coords(bullet)[1] > self.height:
                self.canvas.delete(bullet)
                self.quad_bullets.remove(bullet)
                self.score += 2
            # Grazing check
            elif self.check_graze(bullet, player_coords_cached) and bullet not in self.grazed_bullets:
                self.score += 1
                self.grazed_bullets.add(bullet)
                self.show_graze_effect()
                if self.focus_active:
                    self.focus_charge = min(1.0, self.focus_charge + self.focus_charge_graze_bonus)
                    if self.focus_charge >= self.focus_charge_threshold:
                        self.focus_charge_ready = True

        # Move zigzag bullets
        for bullet_tuple in self.zigzag_bullets[:]:
            bullet, direction, step_count = bullet_tuple
            # Change direction every 10 steps
            if step_count % 10 == 0:
                direction *= -1
            self.canvas.move(bullet, 5 * direction, zigzag_speed)
            if self.check_collision(bullet):
                if not self.practice_mode:
                    self.lives -= 1
                    if self.lives <= 0:
                        self.end_game()
                self.canvas.delete(bullet)
                self.zigzag_bullets.remove(bullet_tuple)
            else:
                coords = self.canvas.coords(bullet)
                if coords[1] > self.height or coords[0] < 0 or coords[2] > self.width:
                    self.canvas.delete(bullet)
                    self.zigzag_bullets.remove(bullet_tuple)
                    self.score += 2
                else:
                    # Update tuple with incremented step_count and possibly new direction
                    idx = self.zigzag_bullets.index(bullet_tuple)
                    self.zigzag_bullets[idx] = (bullet, direction, step_count + 1)
            # Grazing check
            if self.check_graze(bullet) and bullet not in self.grazed_bullets:
                self.score += 1
                self.grazed_bullets.add(bullet)
                self.show_graze_effect()
                if self.focus_active:
                    self.focus_charge = min(1.0, self.focus_charge + self.focus_charge_graze_bonus)
                    if self.focus_charge >= self.focus_charge_threshold:
                        self.focus_charge_ready = True

        # Move fast bullets
        for fast_bullet in self.fast_bullets[:]:
            self.canvas.move(fast_bullet, 0, fast_speed)
            if self.check_collision(fast_bullet):
                if not self.practice_mode:
                    self.lives -= 1
                    if self.lives <= 0:
                        self.end_game()
                self.canvas.delete(fast_bullet)
                self.fast_bullets.remove(fast_bullet)
            elif self.canvas.coords(fast_bullet)[1] > self.height:
                self.canvas.delete(fast_bullet)
                self.fast_bullets.remove(fast_bullet)
                self.score += 2
            # Grazing check
            if self.check_graze(fast_bullet) and fast_bullet not in self.grazed_bullets:
                self.score += 1
                self.grazed_bullets.add(fast_bullet)
                self.show_graze_effect()
                if self.focus_active:
                    self.focus_charge = min(1.0, self.focus_charge + self.focus_charge_graze_bonus)
                    if self.focus_charge >= self.focus_charge_threshold:
                        self.focus_charge_ready = True

        # Move & spin star bullets
        for star_bullet in self.star_bullets[:]:
            # Fall movement
            self.canvas.move(star_bullet, 0, star_speed)
            # Spin: fetch current coords, rotate around center by small angle
            coords = self.canvas.coords(star_bullet)
            if len(coords) >= 6:  # polygon
                # Compute center
                xs = coords[0::2]
                ys = coords[1::2]
                cx = sum(xs)/len(xs)
                cy = sum(ys)/len(ys)
                angle = 0.18  # radians per frame
                sin_a = _sin(angle)
                cos_a = _cos(angle)
                new_pts = []
                for x, y in zip(xs, ys):
                    dx = x - cx
                    dy = y - cy
                    rx = dx * cos_a - dy * sin_a + cx
                    ry = dx * sin_a + dy * cos_a + cy
                    new_pts.extend([rx, ry])
                self.canvas.coords(star_bullet, *new_pts)
            # Collision / bounds / graze
            if self.check_collision(star_bullet):
                if not self.practice_mode:
                    self.lives -= 1
                    if self.lives <= 0:
                        self.end_game()
                self.canvas.delete(star_bullet)
                self.star_bullets.remove(star_bullet)
                continue
            # Off screen
            bbox = self.canvas.bbox(star_bullet)
            if bbox and bbox[1] > self.height:
                self.canvas.delete(star_bullet)
                self.star_bullets.remove(star_bullet)
                self.score += 3
                continue
            # Grazing
            if self.check_graze(star_bullet) and star_bullet not in self.grazed_bullets:
                self.score += 1
                self.grazed_bullets.add(star_bullet)
                self.show_graze_effect()
                if self.focus_active:
                    self.focus_charge = min(1.0, self.focus_charge + self.focus_charge_graze_bonus)
                    if self.focus_charge >= self.focus_charge_threshold:
                        self.focus_charge_ready = True

        # Move rectangle bullets
        for rect_bullet in self.rect_bullets[:]:
            self.canvas.move(rect_bullet, 0, rect_speed)
            if self.check_collision(rect_bullet):
                if not self.practice_mode:
                    self.lives -= 1
                    if self.lives <= 0:
                        self.end_game()
                self.canvas.delete(rect_bullet)
                self.rect_bullets.remove(rect_bullet)
            elif self.canvas.coords(rect_bullet)[1] > self.height:
                self.canvas.delete(rect_bullet)
                self.rect_bullets.remove(rect_bullet)
                self.score += 2
            # Grazing check
            if self.check_graze(rect_bullet) and rect_bullet not in self.grazed_bullets:
                self.score += 1
                self.grazed_bullets.add(rect_bullet)
                self.show_graze_effect()
                if self.focus_active:
                    self.focus_charge = min(1.0, self.focus_charge + self.focus_charge_graze_bonus)
                    if self.focus_charge >= self.focus_charge_threshold:
                        self.focus_charge_ready = True

        # ---------------- Move homing bullets ----------------
        for hb_tuple in self.homing_bullets[:]:
            # Backward compatibility: allow old 3-tuple
            if len(hb_tuple) == 3:
                bullet, vx, vy = hb_tuple
                life = self.homing_bullet_max_life
            else:
                bullet, vx, vy, life = hb_tuple
            # Compute vector toward player center
            px1, py1, px2, py2 = self.canvas.coords(self.player)
            pcx = (px1 + px2)/2
            pcy = (py1 + py2)/2
            bx1, by1, bx2, by2 = self.canvas.coords(bullet)
            bcx = (bx1 + bx2)/2
            bcy = (by1 + by2)/2
            dx = pcx - bcx
            dy = pcy - bcy
           
            dist = _hypot(dx, dy) or 1
            # Normalize and apply steering (lerp velocities)
            target_vx = dx / dist * homing_speed
            target_vy = dy / dist * homing_speed
            steer_factor = 0.15  # how quickly it turns
            vx = vx * (1 - steer_factor) + target_vx * steer_factor
            vy = vy * (1 - steer_factor) + target_vy * steer_factor
            self.canvas.move(bullet, vx, vy)
            life -= 1
            # Update tuple (store life)
            idx = self.homing_bullets.index(hb_tuple)
            self.homing_bullets[idx] = (bullet, vx, vy, life)
            # Collision / out of bounds
            if self.check_collision(bullet):
                if not self.practice_mode:
                    self.lives -= 1
                    if self.lives <= 0:
                        self.end_game()
                self.canvas.delete(bullet)
                self.homing_bullets.remove(self.homing_bullets[idx])
            else:
                coords = self.canvas.coords(bullet)
                if (not coords or coords[1] > self.height or coords[0] < -60 or coords[2] > self.width + 60 or life <= 0):
                    try:
                        self.canvas.delete(bullet)
                    except Exception:
                        pass
                    # Remove using safe search if idx stale
                    try:
                        self.homing_bullets.remove(self.homing_bullets[idx])
                    except Exception:
                        # fallback linear remove by id match
                        for _t in self.homing_bullets:
                            if _t[0] == bullet:
                                self.homing_bullets.remove(_t)
                                break
                    self.score += 3
            if bullet not in self.grazed_bullets and self.check_graze(bullet):
                self.score += 1
                self.grazed_bullets.add(bullet)
                self.show_graze_effect()
                if self.focus_active:
                    self.focus_charge = min(1.0, self.focus_charge + self.focus_charge_graze_bonus)
                    if self.focus_charge >= self.focus_charge_threshold:
                        self.focus_charge_ready = True

        # ---------------- Move spiral bullets ----------------
        for sp_tuple in self.spiral_bullets[:]:
            bullet, angle, radius, ang_speed, rad_speed, cx, cy = sp_tuple
            angle += ang_speed
            radius += rad_speed
            x = cx + _cos(angle) * radius
            y = cy + _sin(angle) * radius
            size = 20
            self.canvas.coords(bullet, x-size/2, y-size/2, x+size/2, y+size/2)
            # Collision & removal
            if self.check_collision(bullet):
                if not self.practice_mode:
                    self.lives -= 1
                    if self.lives <= 0:
                        self.end_game()
                self.canvas.delete(bullet)
                self.spiral_bullets.remove(sp_tuple)
                continue
            if (x < -40 or x > self.width + 40 or y < -40 or y > self.height + 40 or radius > max(self.width, self.height)):
                self.canvas.delete(bullet)
                self.spiral_bullets.remove(sp_tuple)
                self.score += 2
                continue
            # Update tuple
            idx = self.spiral_bullets.index(sp_tuple)
            self.spiral_bullets[idx] = (bullet, angle, radius, ang_speed, rad_speed, cx, cy)
            if bullet not in self.grazed_bullets and self.check_graze(bullet):
                self.score += 1
                self.grazed_bullets.add(bullet)
                self.show_graze_effect()
                if self.focus_active:
                    self.focus_charge = min(1.0, self.focus_charge + self.focus_charge_graze_bonus)
                    if self.focus_charge >= self.focus_charge_threshold:
                        self.focus_charge_ready = True

        # ---------------- Move radial burst bullets ----------------
        for rb_tuple in self.radial_bullets[:]:
            bullet, vx, vy = rb_tuple
            self.canvas.move(bullet, vx, vy)
            if self.check_collision(bullet):
                if not self.practice_mode:
                    self.lives -= 1
                    if self.lives <= 0:
                        self.end_game()
                self.canvas.delete(bullet)
                self.radial_bullets.remove(rb_tuple)
                continue
            coords = self.canvas.coords(bullet)
            if (not coords or coords[2] < -20 or coords[0] > self.width + 20 or coords[3] < -20 or coords[1] > self.height + 20):
                self.canvas.delete(bullet)
                self.radial_bullets.remove(rb_tuple)
                self.score += 1
                continue
            if bullet not in self.grazed_bullets and self.check_graze(bullet):
                self.score += 1
                self.grazed_bullets.add(bullet)
                self.show_graze_effect()
                if self.focus_active:
                    self.focus_charge = min(1.0, self.focus_charge + self.focus_charge_graze_bonus)
                    if self.focus_charge >= self.focus_charge_threshold:
                        self.focus_charge_ready = True

        # ---------------- Move wave bullets ----------------
        for wtuple in self.wave_bullets[:]:
            bullet, base_x, phase, amp, vy, phase_speed = wtuple
            phase += phase_speed
            # Get current bullet coords to compute center y
            bx1, by1, bx2, by2 = self.canvas.coords(bullet)
            height = by2 - by1
            # Vertical move
            self.canvas.move(bullet, 0, vy)
            # Recompute center after vertical move
            bx1, by1, bx2, by2 = self.canvas.coords(bullet)
            cy = (by1 + by2)/2
            cx = base_x + _sin(phase) * amp
            size = bx2 - bx1
            self.canvas.coords(bullet, cx-size/2, cy-height/2, cx+size/2, cy+height/2)
            if self.check_collision(bullet):
                if not self.practice_mode:
                    self.lives -= 1
                    if self.lives <= 0:
                        self.end_game()
                self.canvas.delete(bullet)
                self.wave_bullets.remove(wtuple)
                continue
            if cy > self.height + 30:
                self.canvas.delete(bullet)
                self.wave_bullets.remove(wtuple)
                self.score += 2
                continue
            idx = self.wave_bullets.index(wtuple)
            self.wave_bullets[idx] = (bullet, base_x, phase, amp, vy, phase_speed)
            if bullet not in self.grazed_bullets and self.check_graze(bullet):
                self.score += 1
                self.grazed_bullets.add(bullet)
                self.show_graze_effect()
                if self.focus_active:
                    self.focus_charge = min(1.0, self.focus_charge + self.focus_charge_graze_bonus)
                    if self.focus_charge >= self.focus_charge_threshold:
                        self.focus_charge_ready = True

        # ---------------- Move boomerang bullets ----------------
        for btuple in self.boomerang_bullets[:]:
            bullet, vy, timer, state = btuple
            if state == 'down':
                self.canvas.move(bullet, 0, vy)
                timer -= 1
                if timer <= 0:
                    state = 'up'
            else:  # up
                self.canvas.move(bullet, 0, -vy*0.8)
            coords = self.canvas.coords(bullet)
            if self.check_collision(bullet):
                if not self.practice_mode:
                    self.lives -= 1
                    if self.lives <= 0:
                        self.end_game()
                self.canvas.delete(bullet)
                self.boomerang_bullets.remove(btuple)
                continue
            if not coords or coords[3] < -30 or coords[1] > self.height + 40:
                self.canvas.delete(bullet)
                self.boomerang_bullets.remove(btuple)
                self.score += 3
                continue
            idx = self.boomerang_bullets.index(btuple)
            self.boomerang_bullets[idx] = (bullet, vy, timer, state)
            if bullet not in self.grazed_bullets and self.check_graze(bullet):
                self.score += 1
                self.grazed_bullets.add(bullet)
                self.show_graze_effect()
                if self.focus_active:
                    self.focus_charge = min(1.0, self.focus_charge + self.focus_charge_graze_bonus)
                    if self.focus_charge >= self.focus_charge_threshold:
                        self.focus_charge_ready = True

        # ---------------- Move split bullets ----------------
        for stuple in self.split_bullets[:]:
            bullet, timer = stuple
            self.canvas.move(bullet, 0, 5 + self.difficulty/4)
            timer -= 1
            coords = self.canvas.coords(bullet)
            if timer <= 0 and coords:
                # Split into fragments (6) moving outward in a circle
                bx = (coords[0] + coords[2]) / 2
                by = (coords[1] + coords[3]) / 2
                frag_count = 6
                frag_speed = 4 + self.difficulty/5
                for i in range(frag_count):
                    ang = (2*math.pi/frag_count)*i
                    vx = _cos(ang) * frag_speed
                    vy2 = _sin(ang) * frag_speed
                    frag = self.canvas.create_oval(bx-10, by-10, bx+10, by+10, fill="#ff55ff")
                    self.radial_bullets.append((frag, vx, vy2))
                self.canvas.delete(bullet)
                self.split_bullets.remove(stuple)
                self.score += 3
                continue
            if self.check_collision(bullet):
                if not self.practice_mode:
                    self.lives -= 1
                    if self.lives <= 0:
                        self.end_game()
                self.canvas.delete(bullet)
                self.split_bullets.remove(stuple)
                continue
            if coords and coords[1] > self.height:
                self.canvas.delete(bullet)
                self.split_bullets.remove(stuple)
                self.score += 2
                continue
            idx = self.split_bullets.index(stuple)
            self.split_bullets[idx] = (bullet, timer)
            if bullet not in self.grazed_bullets and self.check_graze(bullet):
                self.score += 1
                self.grazed_bullets.add(bullet)
                self.show_graze_effect()
                if self.focus_active:
                    self.focus_charge = min(1.0, self.focus_charge + self.focus_charge_graze_bonus)
                    if self.focus_charge >= self.focus_charge_threshold:
                        self.focus_charge_ready = True

        # Mid-screen lore fragment display (spawn + blink + expire)
        try:
            if hasattr(self, 'maybe_show_mid_lore'):
                self.maybe_show_mid_lore()
            if getattr(self, '_mid_lore_items', None) is not None:
                for item in self._mid_lore_items[:]:
                    ids = item.get('ids', [])
                    life = item.get('life', 0)
                    life -= 1
                    item['life'] = life
                    # Blink during final 15 frames
                    if life < 15:
                        blink_hidden = (life % 4) in (0,1)
                        state = 'hidden' if blink_hidden else 'normal'
                        for oid in ids:
                            try: self.canvas.itemconfig(oid, state=state)
                            except Exception: pass
                    if life <= 0:
                        for oid in ids:
                            try: self.canvas.delete(oid)
                            except Exception: pass
                        self._mid_lore_items.remove(item)
        except Exception:
            pass

        self.root.after(50, self.update_game)
        # Update Debug HUD late so counts reflect this frame's state
        if self.debug_hud_enabled:
            self._update_debug_hud()

    # ---------------- Static Trap (voidy static escape) ----------------
    def _static_can_trigger_trap(self):
        return (not self.static_trap_active) and (not self.rewind_active) and (not self.freeze_active)

    def _check_bbox_overlap_player(self, coords):
        try:
            px1, py1, px2, py2 = self.canvas.coords(self.player)
            if len(coords) == 4:
                bx1, by1, bx2, by2 = coords
            else:
                xs = coords[::2]; ys = coords[1::2]
                bx1, bx2 = min(xs), max(xs)
                by1, by2 = min(ys), max(ys)
            return px1 < bx2 and px2 > bx1 and py1 < by2 and py2 > by1
        except Exception:
            return False

    def start_static_trap(self):
        if self.static_trap_active:
            return
        self.static_trap_active = True
        self.static_trap_progress = 0.0
        self.static_trap_end_time = time.time() + self.static_trap_time_limit
        # Overlay dark + noise rectangles
        try:
            self.static_trap_overlay = self.canvas.create_rectangle(0,0,self.width,self.height, fill="#000000", outline="")
            self.canvas.itemconfig(self.static_trap_overlay, stipple="gray25")
        except Exception:
            self.static_trap_overlay = None
        # spawn noise blocks
        import random as _r
        for _ in range(120):
            w = _r.randint(8,40); h=_r.randint(4,20)
            x = _r.randint(0, self.width-w)
            y = _r.randint(0, self.height-h)
            col = _r.choice(["#111111","#222222","#444444","#666666","#999999","#bbbbbb"])
            try:
                rid = self.canvas.create_rectangle(x,y,x+w,y+h, fill=col, outline="")
                self.static_trap_noise_items.append(rid)
                self.canvas.tag_lower(rid)
            except Exception:
                pass
        # Text prompt
        try:
            self.static_trap_text = self.canvas.create_text(self.width//2, self.height//2, text="STATIC INTERFERENCE\nMash A / D or Left / Right to ESCAPE", fill="#cccccc", font=("Arial", 32, "bold"), justify='center')
        except Exception:
            self.static_trap_text = None
        # Ensure overlay behind text
        if self.static_trap_overlay:
            try: self.canvas.tag_lower(self.static_trap_overlay)
            except Exception: pass
        # capture last key None
        self._static_trap_last_key = None

    def _handle_static_trap_key(self, event):
        if not self.static_trap_active:
            return
        key = event.keysym.lower()
        if key in ('left','a','right','d'):
            if self._static_trap_last_key is None or (key in ('left','a') and self._static_trap_last_key in ('right','d')) or (key in ('right','d') and self._static_trap_last_key in ('left','a')):
                # alternate increases progress more
                self.static_trap_progress += 0.065
            else:
                self.static_trap_progress += 0.025
            self._static_trap_last_key = key
            if self.static_trap_progress >= 1.0:
                self.end_static_trap(escaped=True)
            else:
                # update text with progress
                if self.static_trap_text:
                    try:
                        remain = max(0.0, self.static_trap_end_time - time.time())
                        self.canvas.itemconfig(self.static_trap_text, text=f"STATIC INTERFERENCE\nESCAPE {int(self.static_trap_progress*100)}% | {remain:0.1f}s")
                    except Exception:
                        pass

    def _update_static_trap(self):
        # countdown & animate noise flicker
        now = time.time()
        if now >= self.static_trap_end_time:
            self.end_static_trap(escaped=False)
            return
        # flicker: randomly hide/show subset
        import random as _r
        for rid in self.static_trap_noise_items:
            try:
                if _r.random() < 0.1:
                    state = 'hidden' if _r.random() < 0.5 else 'normal'
                    self.canvas.itemconfig(rid, state=state)
            except Exception:
                pass
        # slow auto drift to make it feel alive
        for rid in self.static_trap_noise_items:
            try:
                dx = _r.randint(-1,1); dy=_r.randint(-1,1)
                self.canvas.move(rid, dx, dy)
            except Exception:
                pass
        # degrade player deco glow to grayscale effect
        if self.player_deco_items:
            try:
                for did in self.player_deco_items:
                    self.canvas.itemconfig(did, outline="#777777")
                self.canvas.itemconfig(self.player, fill="#999999")
            except Exception:
                pass
        # Update timing text if exists
        if self.static_trap_text:
            try:
                remain = max(0.0, self.static_trap_end_time - now)
                self.canvas.itemconfig(self.static_trap_text, text=f"STATIC INTERFERENCE\nESCAPE {int(self.static_trap_progress*100)}% | {remain:0.1f}s")
            except Exception:
                pass

    def end_static_trap(self, escaped: bool):
        if not self.static_trap_active:
            return
        # cleanup visuals
        for rid in self.static_trap_noise_items:
            try: self.canvas.delete(rid)
            except Exception: pass
        self.static_trap_noise_items.clear()
        if self.static_trap_overlay:
            try: self.canvas.delete(self.static_trap_overlay)
            except Exception: pass
        self.static_trap_overlay = None
        if self.static_trap_text:
            try: self.canvas.delete(self.static_trap_text)
            except Exception: pass
        self.static_trap_text = None
        self.static_trap_active = False
        if escaped:
            # reward & brief invulnerability
            self.score += 15
            self.static_trap_invuln_end = time.time() + 2.0
            try:
                txt = self.canvas.create_text(self.width//2, self.height//2 - 100, text="ESCAPED +15", fill="#cccccc", font=("Arial", 28, "bold"))
                self.canvas.after(1400, lambda tid=txt: (self.canvas.delete(tid) if self.canvas.type(tid) else None))
            except Exception:
                pass
        else:
            # failure -> immediate game over
            self.lives = 0
            self.end_game()

    # ---------------- Focus / Pulse mechanic helpers ----------------
    def _focus_key_pressed(self, event=None):
        if self.game_over or self.paused:
            return
        if self.focus_pulse_cooldown > 0:
            return
        self.focus_active = True

    def _focus_key_released(self, event=None):
        if not self.focus_active:
            return
        # Trigger pulse if charged
        if self.focus_charge_ready and self.focus_charge >= self.focus_charge_threshold:
            self._trigger_focus_pulse()
        self.focus_active = False

    def _update_focus_charge(self):
        if self.game_over or self.paused:
            return
        if self.focus_active and not self.focus_charge_ready:
            if self.focus_pulse_cooldown <= 0:
                self.focus_charge = min(1.0, self.focus_charge + self.focus_charge_rate)
                if self.focus_charge >= self.focus_charge_threshold:
                    self.focus_charge_ready = True

    def _trigger_focus_pulse(self):
        # Clear bullets within radius and grant score; reset charge and start cooldown
        try:
            px1, py1, px2, py2 = self.canvas.coords(self.player)
            pcx = (px1 + px2)/2
            pcy = (py1 + py2)/2
        except Exception:
            return

        radius = self.focus_pulse_radius
        radius_sq = radius * radius
        removed = 0

        def within_radius(bullet_id):
            """Return True if the bullet center is within the pulse radius."""
            try:
                c = self.canvas.coords(bullet_id)
                if not c:
                    return False
                if len(c) == 4:
                    bx = (c[0] + c[2]) / 2
                    by = (c[1] + c[3]) / 2
                else:
                    xs = c[0::2]
                    ys = c[1::2]
                    bx = sum(xs) / len(xs)
                    by = sum(ys) / len(ys)
                dx = bx - pcx
                dy = by - pcy
                return dx*dx + dy*dy <= radius_sq
            except Exception:
                return False

        def clean_simple_list(container):
            nonlocal removed
            for b in container[:]:
                if within_radius(b):
                    try:
                        self.canvas.delete(b)
                    except Exception:
                        pass
                    try:
                        container.remove(b)
                    except ValueError:
                        pass
                    removed += 1
    
        def clean_tuple_list(container, idx=0):
            """For containers like [(bullet_id, ...)], delete based on container[idx]."""
            nonlocal removed
            for entry in container[:]:
                b = entry[idx]
                if within_radius(b):
                    try:
                        self.canvas.delete(b)
                    except Exception:
                        pass
                    try:
                        container.remove(entry)
                    except ValueError:
                        pass
                    removed += 1
    
        # Clean each bullet family properly
        clean_simple_list(self.bullets)
        clean_simple_list(self.bullets2)
        clean_tuple_list(self.triangle_bullets, 0)
        clean_tuple_list(self.diag_bullets, 0)
        clean_simple_list(self.boss_bullets)
        clean_tuple_list(self.zigzag_bullets, 0)
        clean_simple_list(self.fast_bullets)
        clean_simple_list(self.star_bullets)
        clean_simple_list(self.rect_bullets)
        clean_simple_list(self.egg_bullets)
        clean_simple_list(self.quad_bullets)
        clean_tuple_list(self.exploding_bullets if isinstance(self.exploding_bullets, list) else [], 0)
        clean_tuple_list(self.exploded_fragments, 0)
        clean_tuple_list(self.bouncing_bullets, 0)
        clean_tuple_list(self.homing_bullets, 0)
        clean_tuple_list(self.spiral_bullets, 0)
        clean_tuple_list(self.radial_bullets, 0)
        clean_tuple_list(self.wave_bullets, 0)
        clean_tuple_list(self.boomerang_bullets, 0)
        clean_tuple_list(self.split_bullets, 0)

        # Score reward
        self.score += removed * 2

        # Visual expanding ring
        try:
            ring = self.canvas.create_oval(pcx-10, pcy-10, pcx+10, pcy+10,
                                       outline="#66ffdd", width=3)
            self.focus_pulse_visuals.append((ring, 18, radius/18))  # life frames, grow per frame
        except Exception:
            pass

        # Reset charge
        self.focus_charge = 0.0
        self.focus_charge_ready = False
        self.focus_pulse_cooldown = self.focus_pulse_cooldown_time
    
    def _update_focus_visuals(self):
        if not self.focus_pulse_visuals:
            return
        new = []
        for oid, life, grow in self.focus_pulse_visuals:
            life -= 1
            try:
                x1,y1,x2,y2 = self.canvas.coords(oid)
                cx = (x1+x2)/2; cy=(y1+y2)/2
                nx1 = cx - ( (x2-x1)/2 + grow)
                nx2 = cx + ( (x2-x1)/2 + grow)
                ny1 = cy - ( (y2-y1)/2 + grow)
                ny2 = cy + ( (y2-y1)/2 + grow)
                self.canvas.coords(oid, nx1, ny1, nx2, ny2)
                # Fade color
                frac = max(0.0, life/18)
                col = int(0x66*frac), int(0xff*frac), int(0xdd*frac)
                self.canvas.itemconfig(oid, outline=f"#{col[0]:02x}{col[1]:02x}{col[2]:02x}")
            except Exception:
                life = 0
            if life > 0:
                new.append((oid, life, grow))
            else:
                try: self.canvas.delete(oid)
                except Exception: pass
        self.focus_pulse_visuals = new

    # ---------------- Debug HUD ----------------
    def toggle_debug_hud(self, event=None):
        self.debug_hud_enabled = not self.debug_hud_enabled
        if not self.debug_hud_enabled and self._debug_hud_text_id:
            try: self.canvas.delete(self._debug_hud_text_id)
            except Exception: pass
            self._debug_hud_text_id = None

    def toggle_mouse_mode(self, event=None):
        """Toggle mouse mode on/off during gameplay."""
        self.settings['mouse_enabled'] = not self.settings.get('mouse_enabled', True)
        # Show brief notification
        if hasattr(self, 'canvas') and self.canvas:
            try:
                status = "ON" if self.settings['mouse_enabled'] else "OFF"
                notification = self.canvas.create_text(
                    self.width // 2, 50,
                    text=f"Mouse Mode: {status}",
                    fill="#ffff00", font=("Arial", 20, "bold")
                )
                # Remove notification after 1 second
                self.root.after(1000, lambda: self.canvas.delete(notification))
            except Exception:
                pass

    def _update_debug_hud(self):
        try:
            counts = {
                'vert': len(self.bullets), 'horiz': len(self.bullets2), 'tri': len(self.triangle_bullets),
                'diag': len(self.diag_bullets), 'boss': len(self.boss_bullets), 'zig': len(self.zigzag_bullets),
                'fast': len(self.fast_bullets), 'star': len(self.star_bullets), 'rect': len(self.rect_bullets),
                'egg': len(self.egg_bullets), 'quad': len(self.quad_bullets), 'bounc': len(self.bouncing_bullets),
                'expl': len(self.exploding_bullets) + len(self.exploded_fragments), 'hom': len(self.homing_bullets),
                'spir': len(self.spiral_bullets), 'rad': len(self.radial_bullets), 'wave': len(self.wave_bullets),
                'boom': len(self.boomerang_bullets), 'split': len(self.split_bullets), 'las': len(self.lasers)
            }
        except Exception:
            counts = {}
        total = sum(counts.values()) if counts else 0
        if self._frame_time_buffer:
            avg = sum(self._frame_time_buffer)/len(self._frame_time_buffer)
            worst = max(self._frame_time_buffer)
            best = min(self._frame_time_buffer)
        else:
            avg = worst = best = 0.0
        eff = []
        if self.freeze_active: eff.append('FREEZE')
        if self.rewind_active: eff.append('REWIND')
        if self.rewind_pending and not self.rewind_active: eff.append('REWIND-Q')
        if self.focus_active: eff.append('FOCUS')
        if self.focus_charge_ready: eff.append('PULSE READY')
        eff_str = ','.join(eff) if eff else 'None'
        focus_pct = int(self.focus_charge*100)
        lines = [
            '== DEBUG HUD (F3)==',
            f'Bullets Total:{total}  {" ".join(f"{k}:{v}" for k,v in counts.items())}',
            f'Frame ms avg:{avg:.1f} best:{best:.1f} worst:{worst:.1f}',
            f'Effects: {eff_str}',
            f'Focus: {focus_pct}%{" READY" if self.focus_charge_ready else ""}',
        ]
        txt = '\n'.join(lines)
        if self._debug_hud_text_id is None:
            try:
                self._debug_hud_text_id = self.canvas.create_text(8, 80, text=txt, anchor='nw', fill='#7cffd9', font=('Consolas', 11))
            except Exception:
                return
        else:
            try: self.canvas.itemconfig(self._debug_hud_text_id, text=txt)
            except Exception: pass
        try: self.canvas.lift(self._debug_hud_text_id)
        except Exception: pass

    def init_lore(self):
        """Initialize lore fragments from external lore.txt file.
        Format of lore.txt:
          - Lines starting with '#' are comments
          - Blank line separates fragments
          - Multi-line fragments are combined into one line (joined with spaces)
        Result stored in self.lore_fragments as {'all': [list_of_strings]} for compatibility.
        If file missing or parsing fails, a minimal fallback list is used.
        """
        lore_file = "lore.txt"
        # Resolve possible PyInstaller path
        if hasattr(sys, '_MEIPASS'):
            candidate = os.path.join(sys._MEIPASS, lore_file)
            if os.path.exists(candidate):
                lore_file = candidate
        parsed_dict = None
        # 1. Try to parse entire file as a Python dict literal
        try:
            import ast
            with open(lore_file, 'r', encoding='utf-8') as f:
                text = f.read().strip()
            if text.startswith('{') and text.endswith('}'):  # quick heuristic
                parsed = ast.literal_eval(text)
                if isinstance(parsed, dict):
                    parsed_dict = {}
                    # Ensure all values are lists of strings
                    for k, v in parsed.items():
                        if isinstance(v, (list, tuple)):
                            parsed_dict[str(k)] = [str(x) for x in v]
                    if parsed_dict:
                        self.lore_fragments = parsed_dict
        except Exception:
            parsed_dict = None
        if parsed_dict is None:
            # 2. Fallback: treat file as block fragments separated by blank lines
            fragments = []
            current_lines = []
            try:
                with open(lore_file, 'r', encoding='utf-8') as f2:
                    for raw in f2:
                        line = raw.rstrip('\n').strip()
                        if not line or line.startswith('#'):
                            if current_lines:
                                fragments.append(' '.join(current_lines))
                                current_lines = []
                            continue
                        current_lines.append(line)
                if current_lines:
                    fragments.append(' '.join(current_lines))
            except Exception:
                fragments = [
                    "THE MEMORY CORE IS EMPTY BUT STILL HUMS.",
                    "A PLACEHOLDER FRAGMENT REMINDS YOU THIS IS A FALLBACK."
                ]
            # De-duplicate preserving order
            seen = set()
            unique_fragments = []
            for frag in fragments:
                if frag not in seen:
                    seen.add(frag)
                    unique_fragments.append(frag)
            self.lore_fragments = {'all': unique_fragments}
        # Normalize capitalization for lore: convert whole-word 'you'/'your' to uppercase
        try:
            import re
            if 'all' in self.lore_fragments:  # flat list form
                for _i, _line in enumerate(self.lore_fragments['all']):
                    self.lore_fragments['all'][_i] = re.sub(r"\b(you|your)\b", lambda m: m.group(0).upper(), _line, flags=re.IGNORECASE)
            else:  # categorized dict
                for _k, _list in self.lore_fragments.items():
                    for _i, _line in enumerate(_list):
                        _list[_i] = re.sub(r"\b(you|your)\b", lambda m: m.group(0).upper(), _line, flags=re.IGNORECASE)
        except Exception:
            pass

    def update_lore_line(self, force=False):
        if getattr(self, 'lore_fragments', None) is None:
            return
        now = time.time()
        if not force and now - getattr(self, 'lore_last_change', 0) < getattr(self, 'lore_interval', 8):
            return
        import random
        pool = []
        prev = getattr(self, 'current_lore_line', None)
        # Support both old dict-of-lists structure and new single 'all' list
        try:
            if 'all' in self.lore_fragments and isinstance(self.lore_fragments['all'], list):
                for ln in self.lore_fragments['all']:
                    if ln != prev:
                        pool.append(ln)
            else:
                for _k, lines in self.lore_fragments.items():
                    for ln in lines:
                        if ln != prev:
                            pool.append(ln)
        except Exception:
            return
        if not pool:
            return
        line = random.choice(pool)
        self.current_lore_line = line
        try:
            if getattr(self, 'lore_text', None) is not None:
                self.canvas.itemconfig(self.lore_text, text=line)
        except Exception:
            pass
        self.lore_last_change = now

    # --- Main Menu and Settings ---
    def show_main_menu(self):
        """Display the main menu with Play, Settings, and Exit buttons."""
        self.in_main_menu = True
        self.canvas.delete("all")
        
        # Decorative background gradient effect (simulated with rectangles)
        gradient_colors = ["#0d0221", "#1a0533", "#32054e", "#4b0a67"]
        bar_height = self.height // len(gradient_colors)
        for i, color in enumerate(gradient_colors):
            self.canvas.create_rectangle(
                0, i * bar_height, self.width, (i + 1) * bar_height,
                fill=color, outline="", tags="menu"
            )
        
        # Decorative corner accents
        accent_size = 80
        # Top-left corner
        self.canvas.create_line(0, 0, accent_size, 0, fill="#ff55ff", width=4, tags="menu")
        self.canvas.create_line(0, 0, 0, accent_size, fill="#66ffdd", width=4, tags="menu")
        # Top-right corner
        self.canvas.create_line(self.width - accent_size, 0, self.width, 0, fill="#66ffdd", width=4, tags="menu")
        self.canvas.create_line(self.width, 0, self.width, accent_size, fill="#ff55ff", width=4, tags="menu")
        # Bottom-left corner
        self.canvas.create_line(0, self.height, 0, self.height - accent_size, fill="#66ffdd", width=4, tags="menu")
        self.canvas.create_line(0, self.height, accent_size, self.height, fill="#ff55ff", width=4, tags="menu")
        # Bottom-right corner
        self.canvas.create_line(self.width, self.height, self.width, self.height - accent_size, fill="#ff55ff", width=4, tags="menu")
        self.canvas.create_line(self.width - accent_size, self.height, self.width, self.height, fill="#66ffdd", width=4, tags="menu")
        
        # Decorative stars/particles
        for _ in range(30):
            x = random.randint(0, self.width)
            y = random.randint(0, self.height)
            size = random.randint(2, 6)
            brightness = random.randint(150, 255)
            color = f"#{brightness:02x}{brightness:02x}{brightness:02x}"
            self.canvas.create_oval(x-size//2, y-size//2, x+size//2, y+size//2, fill=color, outline="", tags="menu")
        
        # Title with shadow effect
        shadow_offset = 4
        self.canvas.create_text(
            self.width // 2 + shadow_offset, self.height // 4 + shadow_offset,
            text="RIFT OF MEMORIES\nAND REGRETS",
            fill="#220033", font=("Arial", 56, "bold"),
            justify="center", tags="menu"
        )
        self.canvas.create_text(
            self.width // 2, self.height // 4,
            text="RIFT OF MEMORIES\nAND REGRETS",
            fill="#ff55ff", font=("Arial", 56, "bold"),
            justify="center", tags="menu"
        )
        
        # Subtitle with glow effect
        self.canvas.create_text(
            self.width // 2 + 2, self.height // 4 + 122,
            text="Can you escape?",
            fill="#448866", font=("Courier New", 24),
            tags="menu"
        )
        self.canvas.create_text(
            self.width // 2, self.height // 4 + 120,
            text="Can you escape?",
            fill="#66ffdd", font=("Courier New", 24),
            tags="menu"
        )
        
        # Buttons with enhanced styling
        button_width = 300
        button_height = 60
        button_x = self.width // 2
        button_start_y = self.height // 2
        button_spacing = 90
        
        # Play button with glow effect
        # Outer glow
        self.canvas.create_rectangle(
            button_x - button_width // 2 - 4, button_start_y - button_height // 2 - 4,
            button_x + button_width // 2 + 4, button_start_y + button_height // 2 + 4,
            fill="#ff99ff", outline="", tags="menu"
        )
        self.menu_play_btn = self.canvas.create_rectangle(
            button_x - button_width // 2, button_start_y - button_height // 2,
            button_x + button_width // 2, button_start_y + button_height // 2,
            fill="#ff55ff", outline="#ffffff", width=3, tags="menu"
        )
        # Button text shadow
        self.canvas.create_text(
            button_x + 2, button_start_y + 2,
            text="PLAY", fill="#330033", font=("Arial", 32, "bold"),
            tags="menu"
        )
        self.canvas.create_text(
            button_x, button_start_y,
            text="PLAY", fill="white", font=("Arial", 32, "bold"),
            tags="menu"
        )
        
        # Settings button with glow effect
        settings_y = button_start_y + button_spacing
        self.canvas.create_rectangle(
            button_x - button_width // 2 - 4, settings_y - button_height // 2 - 4,
            button_x + button_width // 2 + 4, settings_y + button_height // 2 + 4,
            fill="#6677ff", outline="", tags="menu"
        )
        self.menu_settings_btn = self.canvas.create_rectangle(
            button_x - button_width // 2, settings_y - button_height // 2,
            button_x + button_width // 2, settings_y + button_height // 2,
            fill="#4455ff", outline="#ffffff", width=3, tags="menu"
        )
        self.menu_settings_text1 = self.canvas.create_text(
            button_x + 2, settings_y + 2,
            text="SETTINGS", fill="#001133", font=("Arial", 32, "bold"),
            tags="menu"
        )
        self.menu_settings_text2 = self.canvas.create_text(
            button_x, settings_y,
            text="SETTINGS", fill="white", font=("Arial", 32, "bold"),
            tags="menu"
        )
        
        # Exit button with glow effect
        exit_y = settings_y + button_spacing
        self.canvas.create_rectangle(
            button_x - button_width // 2 - 4, exit_y - button_height // 2 - 4,
            button_x + button_width // 2 + 4, exit_y + button_height // 2 + 4,
            fill="#ff6666", outline="", tags="menu"
        )
        self.menu_exit_btn = self.canvas.create_rectangle(
            button_x - button_width // 2, exit_y - button_height // 2,
            button_x + button_width // 2, exit_y + button_height // 2,
            fill="#ff4444", outline="#ffffff", width=3, tags="menu"
        )
        self.canvas.create_text(
            button_x + 2, exit_y + 2,
            text="EXIT", fill="#330000", font=("Arial", 32, "bold"),
            tags="menu"
        )
        self.canvas.create_text(
            button_x, exit_y,
            text="EXIT", fill="white", font=("Arial", 32, "bold"),
            tags="menu"
        )
        
        # Version/credit text at bottom
        self.canvas.create_text(
            self.width // 2, self.height - 20,
            text="v1.0  |  A Bullet Hell Experience",
            fill="#888888", font=("Arial", 12),
            tags="menu"
        )
        
        # Bind click events
        self.canvas.tag_bind(self.menu_play_btn, "<Button-1>", lambda e: self.start_game())
        self.canvas.tag_bind(self.menu_settings_btn, "<Button-1>", lambda e: self.show_settings_menu())
        self.canvas.tag_bind(self.menu_settings_text1, "<Button-1>", lambda e: self.show_settings_menu())
        self.canvas.tag_bind(self.menu_settings_text2, "<Button-1>", lambda e: self.show_settings_menu())
        self.canvas.tag_bind(self.menu_exit_btn, "<Button-1>", lambda e: self.root.quit())
        
        # Play menu music if available
        self.play_menu_music()
    
    def show_settings_menu(self):
        """Display the settings menu with configurable options."""
        self.in_settings_menu = True
        self.canvas.delete("all")
        
        # Decorative background
        gradient_colors = ["#0d0221", "#1a0533", "#32054e"]
        bar_height = self.height // len(gradient_colors)
        for i, color in enumerate(gradient_colors):
            self.canvas.create_rectangle(
                0, i * bar_height, self.width, (i + 1) * bar_height,
                fill=color, outline="", tags="settings"
            )
        
        # Decorative grid lines
        for i in range(0, self.width, 40):
            self.canvas.create_line(i, 0, i, self.height, fill="#2a1a4a", width=1, tags="settings")
        for i in range(0, self.height, 40):
            self.canvas.create_line(0, i, self.width, i, fill="#2a1a4a", width=1, tags="settings")
        
        # Title with shadow
        self.canvas.create_text(
            self.width // 2 + 3, 83,
            text="SETTINGS",
            fill="#113355", font=("Arial", 48, "bold"),
            tags="settings"
        )
        self.canvas.create_text(
            self.width // 2, 80,
            text="SETTINGS",
            fill="#66ffdd", font=("Arial", 48, "bold"),
            tags="settings"
        )
        
        # Settings panel background
        panel_x = self.width // 2 - 350
        panel_y = 150
        panel_width = 700
        panel_height = 400
        # Panel shadow
        self.canvas.create_rectangle(
            panel_x + 5, panel_y + 5, panel_x + panel_width + 5, panel_y + panel_height + 5,
            fill="#000000", outline="", tags="settings"
        )
        # Panel
        self.canvas.create_rectangle(
            panel_x, panel_y, panel_x + panel_width, panel_y + panel_height,
            fill="#1a0533", outline="#66ffdd", width=3, tags="settings"
        )
        
        # Settings options
        y_pos = 210
        y_spacing = 70
        label_x = self.width // 2 - 250
        value_x = self.width // 2 + 250
        
        # Master Volume
        self.canvas.create_text(
            label_x, y_pos,
            text="⚙ Master Volume:", fill="#ff88ff", font=("Arial", 20, "bold"),
            anchor="w", tags="settings"
        )
        self.settings_master_vol_text = self.canvas.create_text(
            value_x, y_pos,
            text=f"{int(self.settings['master_volume'] * 100)}%",
            fill="#ffff66", font=("Arial", 20, "bold"),
            anchor="e", tags="settings"
        )
        # Volume bar
        bar_width = 200
        bar_x = value_x - 250
        filled = int(bar_width * self.settings['master_volume'])
        self.canvas.create_rectangle(
            bar_x, y_pos - 8, bar_x + bar_width, y_pos + 8,
            fill="#333333", outline="#666666", tags="settings"
        )
        self.canvas.create_rectangle(
            bar_x, y_pos - 8, bar_x + filled, y_pos + 8,
            fill="#ff88ff", outline="", tags="settings"
        )
        
        # Music Volume
        y_pos += y_spacing
        self.canvas.create_text(
            label_x, y_pos,
            text="♪ Music Volume:", fill="#88ff88", font=("Arial", 20, "bold"),
            anchor="w", tags="settings"
        )
        self.settings_music_vol_text = self.canvas.create_text(
            value_x, y_pos,
            text=f"{int(self.settings['music_volume'] * 100)}%",
            fill="#ffff66", font=("Arial", 20, "bold"),
            anchor="e", tags="settings"
        )
        filled = int(bar_width * self.settings['music_volume'])
        self.canvas.create_rectangle(
            bar_x, y_pos - 8, bar_x + bar_width, y_pos + 8,
            fill="#333333", outline="#666666", tags="settings"
        )
        self.canvas.create_rectangle(
            bar_x, y_pos - 8, bar_x + filled, y_pos + 8,
            fill="#88ff88", outline="", tags="settings"
        )
        
        # SFX Volume
        y_pos += y_spacing
        self.canvas.create_text(
            label_x, y_pos,
            text="♬ SFX Volume:", fill="#88ddff", font=("Arial", 20, "bold"),
            anchor="w", tags="settings"
        )
        self.settings_sfx_vol_text = self.canvas.create_text(
            value_x, y_pos,
            text=f"{int(self.settings['sfx_volume'] * 100)}%",
            fill="#ffff66", font=("Arial", 20, "bold"),
            anchor="e", tags="settings"
        )
        filled = int(bar_width * self.settings['sfx_volume'])
        self.canvas.create_rectangle(
            bar_x, y_pos - 8, bar_x + bar_width, y_pos + 8,
            fill="#333333", outline="#666666", tags="settings"
        )
        self.canvas.create_rectangle(
            bar_x, y_pos - 8, bar_x + filled, y_pos + 8,
            fill="#88ddff", outline="", tags="settings"
        )
        
        # Difficulty
        y_pos += y_spacing
        self.canvas.create_text(
            label_x, y_pos,
            text="⚔ Difficulty:", fill="#ffaa44", font=("Arial", 20, "bold"),
            anchor="w", tags="settings"
        )
        diff_text = "Easy" if self.settings['difficulty_multiplier'] < 0.8 else \
                   "Normal" if self.settings['difficulty_multiplier'] <= 1.2 else "Hard"
        diff_color = "#44ff44" if diff_text == "Easy" else "#ffff44" if diff_text == "Normal" else "#ff4444"
        self.settings_diff_text = self.canvas.create_text(
            value_x, y_pos,
            text=diff_text,
            fill=diff_color, font=("Arial", 20, "bold"),
            anchor="e", tags="settings"
        )
        
        # Player Speed
        y_pos += y_spacing
        self.canvas.create_text(
            label_x, y_pos,
            text="➤ Player Speed:", fill="#ff88dd", font=("Arial", 20, "bold"),
            anchor="w", tags="settings"
        )
        self.settings_speed_text = self.canvas.create_text(
            value_x, y_pos,
            text=str(self.settings['player_speed']),
            fill="#ffff66", font=("Arial", 20, "bold"),
            anchor="e", tags="settings"
        )

        
        # Player Speed
        y_pos += y_spacing
        self.canvas.create_text(
            label_x, y_pos,
            text="Bullet Spawn Times:", fill="#ff88dd", font=("Arial", 20, "bold"),
            anchor="w", tags="settings"
        )
        self.bullet_spawn_text = self.canvas.create_text(
            value_x, y_pos,
            text=str(self.settings['unlock_times']),
            fill="#ffff66", font=("Arial", 20, "bold"),
            anchor="e", tags="settings"
        )
        
        # Instructions box
        y_pos += y_spacing + 20
        inst_box_y = y_pos
        self.canvas.create_rectangle(
            panel_x + 20, inst_box_y, panel_x + panel_width - 20, inst_box_y + 80,
            fill="#0d0221", outline="#ff55ff", width=2, tags="settings"
        )
        self.canvas.create_text(
            self.width // 2, inst_box_y + 20,
            text="Press 1-5 to select  •  Use [ ] to adjust",
            fill="#aaaaaa", font=("Arial", 16),
            justify="center", tags="settings"
        )
        self.canvas.create_text(
            self.width // 2, inst_box_y + 50,
            text="1: Master  |  2: Music  |  3: SFX  |  4: Difficulty  |  5: Speed",
            fill="#888888", font=("Arial", 12),
            tags="settings"
        )
        
        # Keybinds button with glow (left side)
        keybinds_y = self.height - 100
        keybinds_x = self.width // 2 - 220
        button_width = 200
        button_height = 50
        self.canvas.create_rectangle(
            keybinds_x - button_width // 2 - 3, keybinds_y - button_height // 2 - 3,
            keybinds_x + button_width // 2 + 3, keybinds_y + button_height // 2 + 3,
            fill="#ff99ff", outline="", tags="settings"
        )
        self.settings_keybinds_btn = self.canvas.create_rectangle(
            keybinds_x - button_width // 2, keybinds_y - button_height // 2,
            keybinds_x + button_width // 2, keybinds_y + button_height // 2,
            fill="#ff55ff", outline="#ffffff", width=3, tags="settings"
        )
        keybinds_text1 = self.canvas.create_text(
            keybinds_x + 2, keybinds_y + 2,
            text="KEYBINDS", fill="#330033", font=("Arial", 20, "bold"),
            tags="settings"
        )
        keybinds_text2 = self.canvas.create_text(
            keybinds_x, keybinds_y,
            text="KEYBINDS", fill="white", font=("Arial", 20, "bold"),
            tags="settings"
        )
        
        # Back button with glow (right side)
        back_y = self.height - 100
        back_x = self.width // 2 + 220
        self.canvas.create_rectangle(
            back_x - button_width // 2 - 3, back_y - button_height // 2 - 3,
            back_x + button_width // 2 + 3, back_y + button_height // 2 + 3,
            fill="#6677ff", outline="", tags="settings"
        )
        self.settings_back_btn = self.canvas.create_rectangle(
            back_x - button_width // 2, back_y - button_height // 2,
            back_x + button_width // 2, back_y + button_height // 2,
            fill="#4455ff", outline="#ffffff", width=3, tags="settings"
        )
        back_text1 = self.canvas.create_text(
            back_x + 2, back_y + 2,
            text="BACK", fill="#001133", font=("Arial", 24, "bold"),
            tags="settings"
        )
        back_text2 = self.canvas.create_text(
            back_x, back_y,
            text="BACK", fill="white", font=("Arial", 24, "bold"),
            tags="settings"
        )
        
        # Bind click events for buttons and their text
        self.canvas.tag_bind(self.settings_keybinds_btn, "<Button-1>", lambda e: self.show_keybinds_menu())
        self.canvas.tag_bind(keybinds_text1, "<Button-1>", lambda e: self.show_keybinds_menu())
        self.canvas.tag_bind(keybinds_text2, "<Button-1>", lambda e: self.show_keybinds_menu())
        self.canvas.tag_bind(self.settings_back_btn, "<Button-1>", lambda e: self.show_main_menu())
        self.canvas.tag_bind(back_text1, "<Button-1>", lambda e: self.show_main_menu())
        self.canvas.tag_bind(back_text2, "<Button-1>", lambda e: self.show_main_menu())
        
        # Bind keys for settings adjustment
        self.settings_selected = None
        self.root.bind('1', lambda e: self.select_setting('master_volume'))
        self.root.bind('2', lambda e: self.select_setting('music_volume'))
        self.root.bind('3', lambda e: self.select_setting('sfx_volume'))
        self.root.bind('4', lambda e: self.select_setting('difficulty'))
        self.root.bind('5', lambda e: self.select_setting('player_speed'))
        self.root.bind('[', lambda e: self.adjust_setting(-1))
        self.root.bind(']', lambda e: self.adjust_setting(1))
    
    def select_setting(self, setting):
        """Select a setting to adjust."""
        if not self.in_settings_menu:
            return
        self.settings_selected = setting
    
    def adjust_setting(self, direction):
        """Adjust the selected setting."""
        if not self.in_settings_menu or not self.settings_selected:
            return
        
        if self.settings_selected == 'master_volume':
            self.settings['master_volume'] = max(0.0, min(1.0, self.settings['master_volume'] + direction * 0.1))
            self.canvas.itemconfig(self.settings_master_vol_text, text=f"{int(self.settings['master_volume'] * 100)}%")
            self.apply_volume_settings()
        elif self.settings_selected == 'music_volume':
            self.settings['music_volume'] = max(0.0, min(1.0, self.settings['music_volume'] + direction * 0.1))
            self.canvas.itemconfig(self.settings_music_vol_text, text=f"{int(self.settings['music_volume'] * 100)}%")
            self.apply_volume_settings()
        elif self.settings_selected == 'sfx_volume':
            self.settings['sfx_volume'] = max(0.0, min(1.0, self.settings['sfx_volume'] + direction * 0.1))
            self.canvas.itemconfig(self.settings_sfx_vol_text, text=f"{int(self.settings['sfx_volume'] * 100)}%")
        elif self.settings_selected == 'difficulty':
            diff_values = [0.5, 1.0, 1.5]
            current_idx = min(range(len(diff_values)), key=lambda i: abs(diff_values[i] - self.settings['difficulty_multiplier']))
            new_idx = max(0, min(len(diff_values) - 1, current_idx + direction))
            self.settings['difficulty_multiplier'] = diff_values[new_idx]
            diff_text = "Easy" if self.settings['difficulty_multiplier'] < 0.8 else \
                       "Normal" if self.settings['difficulty_multiplier'] <= 1.2 else "Hard"
            self.canvas.itemconfig(self.settings_diff_text, text=diff_text)
        elif self.settings_selected == 'player_speed':
            self.settings['player_speed'] = max(5, min(30, self.settings['player_speed'] + direction * 2))
            self.canvas.itemconfig(self.settings_speed_text, text=str(self.settings['player_speed']))
            self.player_speed = self.settings['player_speed']
    
    def show_keybinds_menu(self):
        """Display the keybinds configuration menu."""
        self.in_settings_menu = True
        self.canvas.delete("all")
        
        # Decorative background
        gradient_colors = ["#0d0221", "#1a0533", "#32054e"]
        bar_height = self.height // len(gradient_colors)
        for i, color in enumerate(gradient_colors):
            self.canvas.create_rectangle(
                0, i * bar_height, self.width, (i + 1) * bar_height,
                fill=color, outline="", tags="keybinds"
            )
        
        # Title
        self.canvas.create_text(
            self.width // 2 + 3, 83,
            text="KEYBINDS",
            fill="#113355", font=("Arial", 48, "bold"),
            tags="keybinds"
        )
        self.canvas.create_text(
            self.width // 2, 80,
            text="KEYBINDS",
            fill="#ff55ff", font=("Arial", 48, "bold"),
            tags="keybinds"
        )
        
        # Panel background
        panel_x = self.width // 2 - 400
        panel_y = 140
        panel_width = 800
        panel_height = 450
        self.canvas.create_rectangle(
            panel_x + 5, panel_y + 5, panel_x + panel_width + 5, panel_y + panel_height + 5,
            fill="#000000", outline="", tags="keybinds"
        )
        self.canvas.create_rectangle(
            panel_x, panel_y, panel_x + panel_width, panel_y + panel_height,
            fill="#1a0533", outline="#ff55ff", width=3, tags="keybinds"
        )
        
        # Keybind list
        y_pos = 180
        y_spacing = 45
        label_x = self.width // 2 - 300
        value_x = self.width // 2 + 200
        
        keybind_labels = {
            'move_left': '← Move Left',
            'move_right': '→ Move Right',
            'move_up': '↑ Move Up',
            'move_down': '↓ Move Down',
            'shoot': '⚡ Shoot',
            'focus': '◉ Focus',
            'pause': '⏸ Pause',
            'restart': '↻ Restart',
            'practice': '⚙ Practice',
            'debug': '🔧 Debug',
            'toggle_mouse': '🖱 Toggle Mouse'
        }
        
        self.keybind_text_items = {}
        
        for action, label in keybind_labels.items():
            # Label
            self.canvas.create_text(
                label_x, y_pos,
                text=label, fill="#88ffff", font=("Arial", 18, "bold"),
                anchor="w", tags="keybinds"
            )
            
            # Current keybinds
            keys_str = ', '.join(self.settings['keybinds'][action])
            text_id = self.canvas.create_text(
                value_x, y_pos,
                text=keys_str, fill="#ffff66", font=("Arial", 18, "bold"),
                anchor="e", tags="keybinds"
            )
            self.keybind_text_items[action] = text_id
            
            y_pos += y_spacing
        
        # Instructions
        inst_y = panel_y + panel_height - 70
        self.canvas.create_text(
            self.width // 2, inst_y,
            text="Click on an action's keys to rebind  •  Press ESC in rebind mode to cancel",
            fill="#aaaaaa", font=("Arial", 14),
            justify="center", tags="keybinds"
        )
        self.canvas.create_text(
            self.width // 2, inst_y + 25,
            text="Multiple keys per action supported  •  Press + to add, - to remove",
            fill="#888888", font=("Arial", 12),
            justify="center", tags="keybinds"
        )
        
        # Input method toggles
        toggle_y = inst_y + 55
        toggle_x_start = self.width // 2 - 300
        
        # Mouse toggle
        mouse_status = "ON" if self.settings.get('mouse_enabled', True) else "OFF"
        mouse_color = "#44ff44" if self.settings.get('mouse_enabled', True) else "#ff4444"
        self.canvas.create_text(
            toggle_x_start, toggle_y,
            text=f"🖱 Mouse: {mouse_status}", fill=mouse_color, font=("Arial", 14, "bold"),
            tags="keybinds"
        )
        
        # Controller toggle
        controller_status = "ON" if self.settings.get('controller_enabled', True) else "OFF"
        controller_color = "#44ff44" if self.settings.get('controller_enabled', True) else "#ff4444"
        self.canvas.create_text(
            toggle_x_start + 200, toggle_y,
            text=f"🎮 Controller: {controller_status}", fill=controller_color, font=("Arial", 14, "bold"),
            tags="keybinds"
        )
        
        # Touch toggle
        touch_status = "ON" if self.settings.get('touchscreen_enabled', True) else "OFF"
        touch_color = "#44ff44" if self.settings.get('touchscreen_enabled', True) else "#ff4444"
        self.canvas.create_text(
            toggle_x_start + 420, toggle_y,
            text=f"👆 Touch: {touch_status}", fill=touch_color, font=("Arial", 14, "bold"),
            tags="keybinds"
        )
        
        # Back button
        back_y = self.height - 100
        button_width = 200
        button_height = 50
        self.canvas.create_rectangle(
            self.width // 2 - button_width // 2 - 3, back_y - button_height // 2 - 3,
            self.width // 2 + button_width // 2 + 3, back_y + button_height // 2 + 3,
            fill="#6677ff", outline="", tags="keybinds"
        )
        self.keybinds_back_btn = self.canvas.create_rectangle(
            self.width // 2 - button_width // 2, back_y - button_height // 2,
            self.width // 2 + button_width // 2, back_y + button_height // 2,
            fill="#4455ff", outline="#ffffff", width=3, tags="keybinds"
        )
        kb_back_text1 = self.canvas.create_text(
            self.width // 2 + 2, back_y + 2,
            text="BACK", fill="#001133", font=("Arial", 24, "bold"),
            tags="keybinds"
        )
        kb_back_text2 = self.canvas.create_text(
            self.width // 2, back_y,
            text="BACK", fill="white", font=("Arial", 24, "bold"),
            tags="keybinds"
        )
        
        # Bind click events for button and its text
        self.canvas.tag_bind(self.keybinds_back_btn, "<Button-1>", lambda e: self.show_settings_menu())
        self.canvas.tag_bind(kb_back_text1, "<Button-1>", lambda e: self.show_settings_menu())
        self.canvas.tag_bind(kb_back_text2, "<Button-1>", lambda e: self.show_settings_menu())
        
        # Bind keys for toggling input methods
        self.root.bind('m', lambda e: self.toggle_input_method('mouse'))
        self.root.bind('c', lambda e: self.toggle_input_method('controller'))
        self.root.bind('t', lambda e: self.toggle_input_method('touchscreen'))
    
    def toggle_input_method(self, method):
        """Toggle an input method on/off."""
        if method == 'mouse':
            self.settings['mouse_enabled'] = not self.settings.get('mouse_enabled', True)
        elif method == 'controller':
            self.settings['controller_enabled'] = not self.settings.get('controller_enabled', True)
        elif method == 'touchscreen':
            self.settings['touchscreen_enabled'] = not self.settings.get('touchscreen_enabled', True)
        
        # Refresh the keybinds menu to show updated status
        self.show_keybinds_menu()
    
    
    def apply_volume_settings(self):
        """Apply volume settings to music."""
        try:
            volume = self.settings['master_volume'] * self.settings['music_volume']
            pygame.mixer.music.set_volume(volume)
        except Exception:
            pass
    
    def play_menu_music(self):
        """Play menu music."""
        if self.current_music_state == 'menu':
            return
        try:
            pygame.mixer.music.load(self.main_music_path)
            pygame.mixer.music.play(-1)
            self.current_music_state = 'menu'
            self.apply_volume_settings()
        except Exception as e:
            print("Could not play menu music:", e)
    
    def start_game(self):
        """Initialize and start the game."""
        self.in_main_menu = False
        self.in_settings_menu = False
        self.game_started = True
        
        # Unbind menu keys
        try:
            self.root.unbind('1')
            self.root.unbind('2')
            self.root.unbind('3')
            self.root.unbind('4')
            self.root.unbind('5')
            self.root.unbind('[')
            self.root.unbind(']')
        except Exception:
            pass
        
        # Bind game-specific keys using configurable keybinds
        for key in self.settings['keybinds']['focus']:
            self.root.bind(f'<KeyPress-{key}>', self._focus_key_pressed)
            self.root.bind(f'<KeyRelease-{key}>', self._focus_key_released)
        
        for key in self.settings['keybinds']['shoot']:
            self.root.bind(f'<{key}>', self.player_shoot)
        
        # Bind movement keys using configurable keybinds
        all_move_keys = (
            self.settings['keybinds']['move_left'] +
            self.settings['keybinds']['move_right'] +
            self.settings['keybinds']['move_up'] +
            self.settings['keybinds']['move_down']
        )
        for key in all_move_keys:
            if len(key) > 1:  # Special keys like 'Left', 'Right'
                self.root.bind(f'<{key}>', self.move_player)
            else:  # Single character keys
                self.root.bind(key, self.move_player)
        
        # Bind mouse events for mouse-based movement
        if self.settings.get('mouse_enabled', True):
            self.canvas.bind('<Motion>', self.handle_mouse_motion)
            self.canvas.bind('<Button-1>', self.handle_mouse_click)
        
        # Bind touch events for touchscreen support
        if self.settings.get('touchscreen_enabled', True):
            self.canvas.bind('<ButtonPress-1>', self.handle_touch_start)
            self.canvas.bind('<B1-Motion>', self.handle_touch_move)
            self.canvas.bind('<ButtonRelease-1>', self.handle_touch_end)
        
        # Initialize game
        self.canvas.delete("all")
        self._initialize_game()
        
        # Start game music
        try:
            pygame.mixer.music.load(self.main_music_path)
            pygame.mixer.music.play(-1)
            self.current_music_state = 'game'
            self.apply_volume_settings()
        except Exception as e:
            print("Could not play game music:", e)
        
        # Start game loop
        self.update_game()
    
    def _initialize_game(self):
        """Initialize all game state including player, bullets, boss, collectables, powerups, and UI elements for a new game session."""
        # Initialize animated vaporwave grid background
        self.init_background()
        # Create player (base hitbox rectangle + decorative layers)
        self.player = None
        self.player_deco_items = []
        self.player_glow_phase = 0.0
        self.player_rgb_phase = 0.0
        self.create_player_sprite()
        
        # Initialize all bullet containers
        self.bullets = []
        self.bullets2 = []
        self.triangle_bullets = []
        self.diag_bullets = []
        self.boss_bullets = []
        self.zigzag_bullets = []
        self.fast_bullets = []
        self.star_bullets = []
        self.rect_bullets = []
        self.egg_bullets = []
        self.quad_bullets = []
        self.exploding_bullets = []
        self.exploded_fragments = []
        self.bouncing_bullets = []
        self.laser_indicators = []
        self.lasers = []
        self.homing_bullets = []
        self.spiral_bullets = []
        self.radial_bullets = []
        self.wave_bullets = []
        self.boomerang_bullets = []
        self.split_bullets = []
        self.static_bullets = []
        
        # Initialize player shooting system
        self.player_shots = []  # [(shot_id, x, y)]
        self.shot_speed = 12
        self.shot_cooldown = 0
        self.shot_cooldown_time = 0.15  # seconds between shots
        
        # Initialize collectables system
        self.collectables = []  # List of active collectable item IDs
        self.collected_items = set()  # Set of collected item names
        self.total_collectables = 50
        self.collectable_types = [
            "Star", "Moon", "Sun", "Comet", "Galaxy",
            "Ruby", "Emerald", "Sapphire", "Diamond", "Topaz",
            "Crown", "Scepter", "Shield", "Sword", "Amulet",
            "Book", "Scroll", "Quill", "Inkwell", "Candle",
            "Rose", "Lily", "Orchid", "Daisy", "Tulip",
            "Key", "Lock", "Chain", "Ring", "Pendant",
            "Feather", "Shell", "Pearl", "Coral", "Fossil",
            "Hourglass", "Compass", "Telescope", "Lens", "Prism",
            "Coin", "Gem", "Ore", "Crystal", "Shard",
            "Mask", "Mirror", "Portrait", "Statue", "Vase"
        ]
        self.collectable_colors = [
            "#ff0000", "#ff8800", "#ffff00", "#88ff00", "#00ff00",
            "#00ff88", "#00ffff", "#0088ff", "#0000ff", "#8800ff",
            "#ff00ff", "#ff0088", "#ff4444", "#ff8844", "#ffff44",
            "#88ff44", "#44ff44", "#44ff88", "#44ffff", "#4488ff",
            "#4444ff", "#8844ff", "#ff44ff", "#ff4488", "#ffaaaa",
            "#ffddaa", "#ffffaa", "#aaffaa", "#aaeeaa", "#aaffdd",
            "#aaffff", "#aaddff", "#aaaaff", "#ddaaff", "#ffaaff",
            "#ffaadd", "#cc8888", "#ccaa88", "#cccc88", "#aacc88",
            "#88cc88", "#88ccaa", "#88cccc", "#88aacc", "#8888cc",
            "#aa88cc", "#cc88cc", "#cc88aa", "#dddddd", "#bbbbbb"
        ]
        self.next_collectable_spawn = time.time() + 3  # First spawn after 3 seconds
        self.collectable_spawn_interval = 5  # Spawn every 5 seconds
        self.collectable_display_text = None
        
        # Initialize boss
        self.boss_entity = None
        self.boss_x = self.width // 2
        self.boss_y = 100
        self.boss_width = 80
        self.boss_height = 80
        self.boss_vx = 3
        self.boss_vy = 2
        self.boss_health_display = 0  # Visual "damage" counter
        self.boss_flash_timer = 0
        self.spawn_boss()
        
        # Initialize static trap state
        self.static_trap_active = False
        self.static_trap_progress = 0.0
        self.static_trap_end_time = 0.0
        self.static_trap_time_limit = 4.0
        self.static_trap_noise_items = []
        self.static_trap_overlay = None
        self.static_trap_text = None
        self.static_trap_invuln_end = 0.0
        self._static_trap_last_key = None
        
        # Initialize freeze state
        self.freeze_powerups = []
        self.freeze_active = False
        self.freeze_end_time = 0.0
        self.freeze_text = None
        self.freeze_overlay = None
        self.freeze_particles = []
        self.freeze_particle_spawn_accum = 0
        self.freeze_mode = 'full'
        self.freeze_motion_factor = 0.25
        self._freeze_motion_phase_over = False
        self.freeze_tint_progress = 0.0
        self.freeze_tint_target = 0.0
        self.freeze_tint_fade_speed = 0.08
        self._last_freeze_tint_progress = -1.0
        self._bullet_original_fills = {}
        
        # Initialize rewind state
        self.rewind_powerups = []
        self.rewind_active = False
        self.rewind_end_time = 0.0
        self.rewind_text = None
        self._bullet_history = []
        self._bullet_history_max = 180
        self._rewind_pointer = None
        self._rewind_capture_skip = 0
        self._rewind_speed = 2
        self._rewind_overlay = None
        self.rewind_pending = False
        self._pending_rewind_duration = 3.0
        self._rewind_ghosts = []
        self._rewind_ghost_life = 10
        self._rewind_ghost_spawn_skip = 0
        self._rewind_ghost_cap = 300
        self._rewind_start_sound = None
        self._rewind_end_sound = None
        self._rewind_start_bullet_count = 0
        self._rewind_bonus_factor = 0.2
        self._rewind_vignette_ids = []
        self.rewind_pending_text = None
        self._music_prev_volume = None
        self._music_volume_restore_active = False
        
        # Initialize shield state (optimized)
        self.shield_powerups = []
        self.shield_active = False
        self.shield_hits_remaining = 0
        self.shield_visual = None
        self.shield_text = None
        self.shield_particles = []
        self._shield_sound = None
        
        # Initialize slow-motion state (optimized)
        self.slowmo_powerups = []
        self.slowmo_active = False
        self.slowmo_end_time = 0.0
        self.slowmo_factor = 0.35
        self.slowmo_overlay = None
        self.slowmo_text = None
        self.slowmo_particles = []
        self._slowmo_sound = None
        self._slowmo_prev_volume = None
        
        # Initialize game state
        self.score = 0
        self.timee = int(time.time())
        self.dial = "Hi-hi-hi! Wanna play with me? I promise it'll be fun!"
        self.scorecount = self.canvas.create_text(70, 20, text=f"Score: {self.score}", fill="white", font=("Arial", 16))
        self.timecount = self.canvas.create_text(self.width-70, 20, text=f"Time: {self.timee}", fill="white", font=("Arial", 16))
        self.dialog = self.canvas.create_text(self.width//2, 20, text=self.dial, fill="white", font=("Arial", 20), justify="center")
        self.next_unlock_text = self.canvas.create_text(self.width//2, self.height-8, text="", fill="#88ddff", font=("Arial", 16), anchor='s')
        self.boss_damage_text = self.canvas.create_text(self.width-70, 50, text=f"Boss Hits: {self.boss_health_display}", fill="#ff00ff", font=("Arial", 16))
        self.collectable_display_text = self.canvas.create_text(70, 50, text=f"Items: {len(self.collected_items)}/{self.total_collectables}", fill="#ffff00", font=("Arial", 16))
        
        self.lives = 3
        self.health_icon_items = []
        self.update_health_display()
        
        self.game_over = False
        self.paused = False
        self.pause_text = None
        self.pause_menu_items = []
        self.difficulty = 1
        self.last_difficulty_increase = time.time()
        self.lastdial = time.time()
        
        # Focus/Pulse state
        self.focus_active = False
        self.focus_charge = 0.0
        self.focus_charge_ready = False
        self.focus_charge_threshold = 1.0
        self.focus_charge_rate = 0.004
        self.focus_charge_graze_bonus = 0.05
        self.focus_pulse_cooldown = 0.0
        self.focus_pulse_cooldown_time = 2.0
        self.focus_pulse_radius = 140
        self.focus_pulse_visuals = []
        
        self.grazing_radius = 40
        self.grazed_bullets = set()
        self.graze_effect_id = None
        self.paused_time_total = 0
        self.pause_start_time = None
        
        self.practice_mode = False
        self.practice_text = None
        self.homing_bullet_max_life = 180
        self.player_speed = self.settings['player_speed']
        
        # Initialize lore
        try:
            self.init_lore()
            self.lore_interval = 8
            self.lore_last_change = time.time()
            self.current_lore_line = None
            self.lore_text = self.canvas.create_text(self.width//2, 50, text="", fill="#b0a8ff", font=("Courier New", 14), justify="center")
            self.update_lore_line(force=True)
        except Exception:
            pass
        
        self.selected_game_over_message = None

    # --- Game Over Animation (particles + pulsing text) ---
    def _start_game_over_music(self):
        """Switch to the non-looping game-over track, then arm the loop transition."""
        self._game_over_loop_pending = False
        self._game_over_music_started = False
        try:
            pygame.mixer.music.load(self.game_over_music_path)
            pygame.mixer.music.play()
            self._game_over_loop_pending = True
        except Exception as exc:
            print("Could not play game over music:", exc)

    def _process_game_over_music(self):
        """Once the first game-over track ends, start the looping follow-up track."""
        if not self._game_over_loop_pending:
            return
        try:
            if not self._game_over_music_started:
                if pygame.mixer.music.get_busy():
                    self._game_over_music_started = True
                return
            if not pygame.mixer.music.get_busy():
                pygame.mixer.music.load(self.game_over_loop_path)
                pygame.mixer.music.play(-1)
                pygame.mixer.music.set_endevent()
                self._game_over_loop_pending = False
        except Exception as exc:
            print("Could not transition game over music:", exc)
            self._game_over_loop_pending = False

    def start_game_over_animation(self):
        self._start_game_over_music()
        if getattr(self, 'go_anim_active', False):
            return
        self.go_anim_active = True
        self.go_anim_particles = []
        self.go_anim_frame = 0
        # Glitch blackout sequence state (fix indentation)
        self.go_glitch_phase = 0  # 0 = glitching, 1 = fading to black, 2 = black hold
        self.go_glitch_rects = []
        self.go_black_cover = None
        self.go_black_alpha = 0.0
        self.go_anim_subtext = None
        # Large pulsing overlay text (separate from static text already created)
        try:
            self.go_anim_text = self.canvas.create_text(self.width//2, self.height//2-140, text="GAME OVER", fill="#ffffff", font=("Arial", 64, "bold"))
        except Exception:
            self.go_anim_text = None
        # Secondary message below if one was selected
        if self.selected_game_over_message:
            try:
                self.go_anim_subtext = self.canvas.create_text(
                    self.width//2, self.height//2 - 60,
                    text=self.selected_game_over_message,
                    fill="#ff66aa", font=("Courier New", 26), justify='center'
                )
            except Exception:
                self.go_anim_subtext = None
        # Spawn radial particles from center
        cx = self.width//2
        cy = self.height//2
        for i in range(60):
            ang = random.uniform(0, 2*math.pi)
            spd = random.uniform(2.5, 7.0)
            vx = _cos(ang)*spd
            vy = _sin(ang)*spd
            size = random.randint(4,10)
            pid = self.canvas.create_oval(cx-size//2, cy-size//2, cx+size//2, cy+size//2, fill="#ff55ff", outline="")
            # life frames ~ fade duration
            life = random.randint(35,70)
            self.go_anim_particles.append((pid, vx, vy, life))
        self.update_game_over_animation()

    def update_game_over_animation(self):
        if not getattr(self, 'go_anim_active', False):
            return
        self.go_anim_frame += 1
        # --- Phase 0: Spawn transient glitch rectangles ---
        if self.go_glitch_phase == 0:
            # spawn a few per frame early on
            spawn_ct = 6
            import random
            for _ in range(spawn_ct):
                w = random.randint(40, max(60, self.width//6))
                h = random.randint(8, 40)
                x = random.randint(0, self.width - w)
                y = random.randint(0, self.height - h)
                col = random.choice(["#ff00ff", "#ffffff", "#ff55ff", "#aa33ff"])  # neon glitch colors
                rid = self.canvas.create_rectangle(x, y, x+w, y+h, fill=col, outline="")
                life = random.randint(3, 10)
                self.go_glitch_rects.append((rid, life))
            # decay existing glitch rects
            new_rects = []
            for rid, life in self.go_glitch_rects:
                life -= 1
                if life <= 0:
                    try: self.canvas.delete(rid)
                    except Exception: pass
                else:
                    # occasional horizontal shift for jitter
                    try:
                        dx = random.randint(-8,8)
                        self.canvas.move(rid, dx, 0)
                    except Exception: pass
                    new_rects.append((rid, life))
            self.go_glitch_rects = new_rects
            # After some frames, advance to fade phase
            if self.go_anim_frame > 55:
                self.go_glitch_phase = 1
        # --- Phase 1: Fade a black overlay in and delete scene ---
        elif self.go_glitch_phase == 1:
            # Create black cover once
            if self.go_black_cover is None:
                try:
                    self.go_black_cover = self.canvas.create_rectangle(0,0,self.width,self.height, fill="#000000", outline="")
                    self.canvas.itemconfig(self.go_black_cover, stipple="gray12")  # simulate alpha via stipple
                except Exception:
                    pass
            # Increase pseudo alpha
            self.go_black_alpha += 0.06
            # Adjust stipple pattern to simulate increasing opacity
            if self.go_black_cover is not None:
                # choose denser patterns as alpha rises
                try:
                    if self.go_black_alpha > 0.8:
                        self.canvas.itemconfig(self.go_black_cover, stipple="")  # solid
                    elif self.go_black_alpha > 0.6:
                        self.canvas.itemconfig(self.go_black_cover, stipple="gray50")
                    elif self.go_black_alpha > 0.4:
                        self.canvas.itemconfig(self.go_black_cover, stipple="gray37")
                    elif self.go_black_alpha > 0.2:
                        self.canvas.itemconfig(self.go_black_cover, stipple="gray25")
                except Exception:
                    pass
            # Occasionally delete lingering items beneath
            if self.go_anim_frame % 9 == 0:
                for item in self.canvas.find_all():
                    # keep the black cover & game over text for now
                    if item in (self.go_black_cover, self.go_anim_text):
                        continue
                    try: self.canvas.delete(item)
                    except Exception: pass
            if self.go_black_alpha >= 1.0:
                # Remove text as screen fully blacks
                try:
                    if self.go_anim_text is not None:
                        self.canvas.delete(self.go_anim_text)
                        self.go_anim_text = None
                    if self.go_anim_subtext is not None:
                        self.canvas.delete(self.go_anim_subtext)
                        self.go_anim_subtext = None
                except Exception: pass
                self.go_glitch_phase = 2
        # --- Phase 2: Hold black, minimal updates ---
        elif self.go_glitch_phase == 2:
            # No further visuals; allow a restart key prompt optionally
            if self.go_anim_frame % 40 == 0 and getattr(self, 'go_anim_text', None) is None:
                try:
                    self.go_anim_text = self.canvas.create_text(self.width//2, self.height//2, text="PRESS R TO RESTART", fill="#4444ff", font=("Arial", 24))
                except Exception:
                    pass
        # Pulse text color / scale
        if self.go_anim_text is not None:
            phase = _sin(self.go_anim_frame * 0.18) * 0.5 + 0.5  # 0..1
            # Interpolate color between magenta and white
            def mix(a,b,t):
                return int(a + (b-a)*t)
            r = mix(255,255,phase)
            g = mix(85,255,phase)
            b = mix(255,255,phase)
            try:
                self.canvas.itemconfig(self.go_anim_text, fill=f"#{r:02x}{g:02x}{b:02x}")
            except Exception:
                pass
        # Update particles
        new_particles = []
        for pid, vx, vy, life in self.go_anim_particles:
            life -= 1
            # Move
            self.canvas.move(pid, vx, vy)
            # Apply slight drag + outward drift aging effect
            vx *= 0.96
            vy *= 0.96 + 0.003
            # Fade color based on remaining life
            t = max(0.0, min(1.0, life/70))
            # Fade from pink -> violet -> dark
            fr = int(255 * t)
            fg = int(55 + (20-55)*(1-t))  # narrow shift
            fb = int(255 * t)
            try:
                self.canvas.itemconfig(pid, fill=f"#{fr:02x}{fg:02x}{fb:02x}")
            except Exception:
                pass
            if life > 0:
                new_particles.append((pid, vx, vy, life))
            else:
                self.canvas.delete(pid)
        self.go_anim_particles = new_particles
        # Schedule next frame (decoupled from main game loop which is halted)
        # This must be called BEFORE any return to ensure music transition and text display continue
        try:
            self._process_game_over_music()
            self.root.after(50, self.update_game_over_animation)
        except Exception:
            pass

if __name__ == "__main__":
    root = tk.Tk()
    game = bullet_hell_game(root)
    root.mainloop()
