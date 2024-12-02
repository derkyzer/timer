import pygame
import win32gui
import win32con
import win32api
import math
import time
import ctypes
from ctypes import wintypes, Structure, sizeof, POINTER, byref

class FLASHWINFO(Structure):
    _fields_ = [
        ("cbSize", ctypes.c_uint),
        ("hwnd", ctypes.c_void_p),
        ("dwFlags", ctypes.c_uint),
        ("uCount", ctypes.c_uint),
        ("dwTimeout", ctypes.c_uint)
    ]

class CircularWindow:
    def __init__(self, size=400, title="Circular Window"):
        pygame.init()
        self.size = size
        
        # Create the window
        self.screen = pygame.display.set_mode((size, size), pygame.NOFRAME)
        pygame.display.set_caption(title)
        
        # Create circle surface with transparency
        self.surface = pygame.Surface((size, size), pygame.SRCALPHA)
        
        # Get the window handle
        self.hwnd = win32gui.GetForegroundWindow()
        
        # Set window properties - removed WS_EX_TRANSPARENT
        win_style = win32gui.GetWindowLong(self.hwnd, win32con.GWL_EXSTYLE)
        win32gui.SetWindowLong(self.hwnd, win32con.GWL_EXSTYLE, 
                             win_style | win32con.WS_EX_LAYERED)
        
        # Create region for circular shape
        self.create_circular_region()
        
        # Set window to be transparent
        win32gui.SetLayeredWindowAttributes(self.hwnd, win32api.RGB(0,0,0), 0, win32con.LWA_COLORKEY)
        
        # Center the window on screen
        user32 = win32api.GetModuleHandle("user32")
        screen_width = win32api.GetSystemMetrics(0)
        screen_height = win32api.GetSystemMetrics(1)
        win32gui.SetWindowPos(self.hwnd, 
                            win32con.HWND_TOPMOST,
                            (screen_width - size) // 2,
                            (screen_height - size) // 2,
                            size, size,
                            win32con.SWP_SHOWWINDOW)

        # Window dragging state
        self.dragging = False
        self.drag_offset = None
        
        # Closing animation state
        self.escape_start = None
        self.escape_held = False
        self.escape_duration = 1.5  # Shortened from 2.0 to 1.5 seconds
        self.close_surface = pygame.Surface((size, size), pygame.SRCALPHA)
        
        # Focus state
        self.has_focus = True

        # Size interpolation
        self.max_radius = size//2
        self.min_radius = size//5
        self.current_radius = self.max_radius
        self.target_radius = self.max_radius
        self.size_transition_speed = 8.0
        self.expanded = True

    def create_circular_region(self):
        """Create circular region for the window"""
        region = win32gui.CreateRoundRectRgn(0, 0, self.size, self.size, self.size, self.size)
        win32gui.SetWindowRgn(self.hwnd, region, True)

    def draw_closing_animation(self):
        if not self.escape_held or self.escape_start is None:
            return
            
        progress = min(1.0, (time.time() - self.escape_start) / self.escape_duration)
        
        # Clear the close surface
        self.close_surface.fill((0,0,0,0))
        
        # Draw the arc using current_radius instead of fixed size
        center = (self.size//2, self.size//2)
        radius = self.current_radius - 4  # Adjust radius to be slightly smaller than window
        
        start_angle = -math.pi/2  # Start from top
        end_angle = start_angle + (2 * math.pi * progress)
        
        # Draw the arc with anti-aliasing
        points = []
        for angle in range(int(math.degrees(start_angle)), int(math.degrees(end_angle)), 2):
            rad = math.radians(angle)
            x = center[0] + radius * math.cos(rad)
            y = center[1] + radius * math.sin(rad)
            points.append((x, y))
            
        if len(points) > 1:
            pygame.draw.lines(self.close_surface, (255, 80, 80, 255), False, points, 6)  # Increased thickness
        
        # Blend the closing animation
        self.surface.blit(self.close_surface, (0, 0))

    def get_cursor_pos(self):
        """Get the current cursor position using Win32 API"""
        point = wintypes.POINT()
        ctypes.windll.user32.GetCursorPos(ctypes.byref(point))
        return point.x, point.y

    def update_window_pos(self):
        if not self.dragging or self.drag_offset is None:
            return
            
        # Get current cursor position
        cursor_x, cursor_y = self.get_cursor_pos()
        
        # Calculate new window position based on cursor and initial offset
        new_x = cursor_x - self.drag_offset[0]
        new_y = cursor_y - self.drag_offset[1]
        
        # Update window position
        win32gui.SetWindowPos(self.hwnd, 0, int(new_x), int(new_y), 0, 0, 
                             win32con.SWP_NOSIZE | win32con.SWP_NOZORDER)

    def lerp(self, start, end, t):
        """Linear interpolation between two values"""
        return start + (end - start) * t

    def update_size(self):
        """Update current radius with smooth interpolation"""
        if abs(self.current_radius - self.target_radius) > 0.1:
            dt = 1/60  # Assuming 60 FPS
            self.current_radius = self.lerp(
                self.current_radius,
                self.target_radius,
                1 - math.exp(-self.size_transition_speed * dt)
            )

    def handle_window_click(self, pos):
        """Handle window expansion/collapse on click. Returns True if click was handled."""
        if not self.expanded:
            center = (self.size//2, self.size//2)
            if math.dist(pos, center) <= self.current_radius:
                # Only expand if clicked in the center area (1/3 of radius)
                if math.dist(pos, center) <= self.current_radius/3:
                    self.expanded = True
                    self.target_radius = self.max_radius
                    return True
        return False

    def process_parent_events(self, events):
        """Process basic window events. Returns False if window should close."""
        # Check if window has focus
        self.has_focus = self.hwnd == win32gui.GetForegroundWindow()
        
        # Update size based on focus
        if not self.has_focus and self.expanded:
            self.expanded = False
            self.target_radius = self.min_radius
        
        for event in events:
            if event.type == pygame.QUIT:
                return False
                
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if not self.escape_held:
                        self.escape_start = time.time()
                        self.escape_held = True
                    
            elif event.type == pygame.KEYUP:
                if event.key == pygame.K_ESCAPE:
                    self.escape_held = False
                    self.escape_start = None
                    
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left click
                    # Handle window expansion first
                    if self.handle_window_click(event.pos):
                        continue
                        
                    # If not handled by expansion, handle dragging
                    # Check if click is within the current window radius
                    center = (self.size//2, self.size//2)
                    if math.dist(event.pos, center) <= self.current_radius:
                        win_rect = win32gui.GetWindowRect(self.hwnd)
                        cursor_x, cursor_y = self.get_cursor_pos()
                        self.drag_offset = (cursor_x - win_rect[0], cursor_y - win_rect[1])
                        self.dragging = True
                    
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:  # Left click release
                    self.dragging = False
                    self.drag_offset = None
                    
            elif event.type == pygame.MOUSEMOTION:
                if self.dragging:
                    self.update_window_pos()
        
        # Check if escape has been held long enough
        if self.escape_held and self.escape_start is not None:
            if time.time() - self.escape_start >= self.escape_duration:
                return False
        
        return True

    def handle_events(self):
        """Handle basic window events. Returns False if window should close."""
        return self.process_parent_events(pygame.event.get())

    def update(self):
        """Update the display"""
        pygame.display.flip()

    def quit(self):
        """Clean up pygame"""
        pygame.quit()

    def flash_taskbar(self):
        """Flash the taskbar icon"""
        flash_info = FLASHWINFO()
        flash_info.cbSize = sizeof(FLASHWINFO)
        flash_info.hwnd = self.hwnd
        flash_info.dwFlags = win32con.FLASHW_ALL | win32con.FLASHW_TIMERNOFG
        flash_info.uCount = 3
        flash_info.dwTimeout = 0
        try:
            user32 = ctypes.windll.user32
            user32.FlashWindowEx(byref(flash_info))
        except Exception as e:
            print(f"Failed to flash taskbar: {e}")
