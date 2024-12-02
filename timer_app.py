from circular_window import CircularWindow
import pygame
import time
import argparse
import win32gui
import colorsys
import math

def lerp_color(color1, color2, t):
    """Linearly interpolate between two colors"""
    return tuple(int(a + (b - a) * t) for a, b in zip(color1, color2))

def lerp(start, end, t):
    """Linear interpolation between two values"""
    return start + (end - start) * t

def get_brightness(color):
    """Get perceived brightness of a color (0-255)"""
    # Using perceived brightness formula: (0.299*R + 0.587*G + 0.114*B)
    return int(0.299 * color[0] + 0.587 * color[1] + 0.114 * color[2])

class TimerWindow(CircularWindow):
    def __init__(self, size=400, initial_minutes=5, autostart=False, bg_color=(0, 120, 255), description=None):
        super().__init__(size, "Timer")
        
        # Initialize fonts
        pygame.font.init()
        self.font = pygame.font.SysFont('Arial', size//5)
        self.button_font = pygame.font.SysFont('Arial', size//16)
        self.desc_font = pygame.font.SysFont('Arial', size//10)
        
        # Colors
        self.BLACK = (0, 0, 0, 255)
        self.WHITE = (255, 255, 255, 255)
        self.GRAY = (128, 128, 128, 255)
        self.RED = (255, 60, 60, 255)
        self.bg_color = tuple(list(bg_color) + [255])  # Add alpha channel
        
        # Timer state
        self.seconds = max(60, min(5400, initial_minutes * 60))  # Between 1 and 90 minutes
        self.running = autostart
        self.last_update = time.time()
        self.finished = False
        self.flash_time = 0
        self.flash_interval = 0.5
        self.description = description
        
        # Store original button positions
        center_x = size//2
        btn_width = size//4
        btn_height = size//12
        self.original_buttons = {
            'start': pygame.Rect(center_x - btn_width//2, size*0.7, btn_width, btn_height),
            'reset': pygame.Rect(center_x - btn_width//2, size*0.82, btn_width, btn_height),
            'up': pygame.Rect(size*0.75, size//2 - btn_height//2, btn_height, btn_height),
            'down': pygame.Rect(size*0.2, size//2 - btn_height//2, btn_height, btn_height)
        }
        self.buttons = self.original_buttons.copy()
        
        # Click handling state
        self.click_handled = False

    def format_time(self):
        minutes = self.seconds // 60
        secs = self.seconds % 60
        return f"{minutes:02d}:{secs:02d}"

    def draw(self):
        # Update size interpolation from parent class
        self.update_size()
        
        # Clear surface
        self.surface.fill((0,0,0,0))
        
        # Calculate current background color
        current_bg = self.bg_color
        if self.finished:
            t = (math.sin(time.time() * 4) + 1) / 2  # Oscillate between 0 and 1
            current_bg = lerp_color(self.bg_color[:3], self.RED[:3], t) + (255,)
        
        # Determine text color based on background brightness
        bg_brightness = get_brightness(current_bg)
        text_color = self.BLACK if bg_brightness > 128 else self.WHITE
        
        # Calculate size ratio for scaling elements
        size_ratio = self.current_radius / self.max_radius
        center = (self.size//2, self.size//2)
        
        # Draw main circle
        pygame.draw.circle(self.surface, current_bg, center, int(self.current_radius))
        
        # Draw time with consistent size in mini mode
        if self.expanded:
            font_size = int(self.size//5 * size_ratio)
        else:
            font_size = self.size//8  # Keep time text size consistent in mini mode
        
        time_font = pygame.font.SysFont('Arial', max(12, font_size))
        time_text = time_font.render(self.format_time(), True, text_color)
        time_rect = time_text.get_rect(center=(center[0], center[1] - font_size//2 if self.expanded else center[1]))
        self.surface.blit(time_text, time_rect)
        
        if self.expanded:
            # Draw description if provided
            if self.description:
                desc_font_size = int(self.size//10 * size_ratio)
                desc_font = pygame.font.SysFont('Arial', max(10, desc_font_size))
                desc_text = desc_font.render(self.description, True, text_color)
                desc_rect = desc_text.get_rect(center=(center[0], center[1]))
                self.surface.blit(desc_text, desc_rect)
            
            # Draw buttons
            btn_positions = {
                'start': (center[0], center[1] + self.current_radius * 0.4),
                'reset': (center[0], center[1] + self.current_radius * 0.6),
                'up': (center[0] + self.current_radius * 0.5, center[1]),
                'down': (center[0] - self.current_radius * 0.5, center[1])
            }
            
            for btn_name, original_rect in self.original_buttons.items():
                color = self.GRAY
                text = btn_name.upper()
                if btn_name == 'start':
                    text = 'STOP' if self.running else 'START'
                elif btn_name == 'up':
                    text = '+'
                elif btn_name == 'down':
                    text = '-'
                
                # Scale and position buttons
                scaled_rect = pygame.Rect(
                    0, 0,
                    original_rect.width * size_ratio,
                    original_rect.height * size_ratio
                )
                scaled_rect.center = btn_positions[btn_name]
                
                pygame.draw.rect(self.surface, color, scaled_rect, border_radius=int(scaled_rect.height//2))
                btn_font_size = int(self.size//16 * size_ratio)
                btn_font = pygame.font.SysFont('Arial', max(8, btn_font_size))
                btn_text = btn_font.render(text, True, text_color)
                btn_text_rect = btn_text.get_rect(center=scaled_rect.center)
                self.surface.blit(btn_text, btn_text_rect)
                
                # Update button rect for click detection
                self.buttons[btn_name] = scaled_rect
        
        # Draw closing animation if needed
        self.draw_closing_animation()
        
        # Update display
        self.screen.fill(self.BLACK)
        self.surface.set_alpha(255)
        self.screen.blit(self.surface, (0,0))
        self.update()

    def handle_button_click(self, pos):
        """Handle button clicks in expanded mode. Returns True if click was handled."""
        if not self.expanded:
            return False
            
        for btn_name, btn_rect in self.buttons.items():
            if btn_rect.collidepoint(pos):
                if btn_name == 'start':
                    self.running = not self.running
                    self.last_update = time.time()
                    if self.finished:  # Reset finished state when starting again
                        self.finished = False
                elif btn_name == 'reset':
                    self.seconds = 300
                    self.running = False
                    self.finished = False
                elif btn_name == 'up' and not self.running:
                    self.seconds = min(5400, self.seconds + 60)  # Max 90 minutes
                elif btn_name == 'down' and not self.running:
                    self.seconds = max(60, self.seconds - 60)  # Min 1 minute
                return True
        return False

    def handle_events(self):
        events = pygame.event.get()
        
        # Reset click handled state
        self.click_handled = False
        
        # Handle timer-specific events first
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left click
                    # Check for button clicks first
                    if self.handle_button_click(event.pos):
                        self.click_handled = True
                elif event.button in (4, 5) and not self.running and self.expanded:  # Mouse wheel
                    direction = 1 if event.button == 4 else -1
                    self.seconds = max(60, min(5400, self.seconds + 60 * direction))
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN and not self.running:  # Enter key resets when not running
                    self.seconds = 300
                    self.finished = False
        
        # Then pass remaining events to parent class
        # Only start dragging if we haven't handled the click
        if not self.click_handled:
            return super().process_parent_events(events)
        return True

    def update_timer(self):
        if self.running:
            current_time = time.time()
            elapsed = current_time - self.last_update
            if elapsed >= 1.0:
                self.seconds = max(0, self.seconds - int(elapsed))
                self.last_update = current_time
                if self.seconds == 0:
                    self.running = False
                    self.finished = True
                    self.flash_taskbar()  # Flash taskbar when timer finishes

def main():
    parser = argparse.ArgumentParser(description='Circular Timer')
    parser.add_argument('-m', '--minutes', type=int, default=5,
                      help='Initial minutes (default: 5)')
    parser.add_argument('-s', '--start', action='store_true',
                      help='Start timer immediately')
    parser.add_argument('-c', '--color', type=str, default='0,120,255',
                      help='Background color as R,G,B (default: 0,120,255)')
    parser.add_argument('-d', '--description', type=str,
                      help='Text description to display under the timer')
    args = parser.parse_args()

    # Parse background color
    try:
        bg_color = tuple(map(int, args.color.split(',')))
        if len(bg_color) != 3 or not all(0 <= x <= 255 for x in bg_color):
            raise ValueError
    except ValueError:
        print("Invalid color format. Using default color.")
        bg_color = (0, 120, 255)

    timer = TimerWindow(400, args.minutes, args.start, bg_color, args.description)
    running = True
    
    while running:
        timer.update_timer()
        timer.draw()
        running = timer.handle_events()
    
    timer.quit()

if __name__ == "__main__":
    main()
