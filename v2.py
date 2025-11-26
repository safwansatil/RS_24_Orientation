import tkinter as tk
from tkinter import ttk
import serial
import serial.tools.list_ports
import threading
import math
import time

class LEDGameGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("LED Memory Game")
        self.root.attributes('-fullscreen', True)
        self.root.configure(bg='#0a0a0a')
        
        # Game state
        self.current_round = 0
        self.game_active = False
        self.game_paused = False
        self.score = 0
        self.bulb_colors = ["#FF3B3B", "#3B8BFF", "#FFD93B", "#3BFF6B", "#B83BFF", "#FFFFFF"]
        self.bulb_names = ["red", "blue", "yellow", "green", "purple", "white"]
        self.blinking = False
        
        # Serial connection
        self.ser = None
        self.serial_thread = None
        self.serial_running = False
        
        self.setup_gui()
        self.connect_serial()
        self.setup_keyboard_bindings()
        
        self.root.bind('<Escape>', lambda e: self.root.attributes('-fullscreen', False))
        
    def setup_gui(self):
        # Main container
        self.canvas = tk.Canvas(self.root, bg='#0a0a0a', highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # Round indicator - small, top right
        self.round_text = self.canvas.create_text(
            0, 25, text="R1", 
            font=("SF Pro Display", 20, "bold"),
            fill="#ffffff", tags="round", anchor="ne"
        )
        
        # Score display - top left
        self.score_text = self.canvas.create_text(
            30, 25, text="Score: 0", 
            font=("SF Pro Display", 20, "bold"),
            fill="#ffffff", tags="score", anchor="nw"
        )
        
        # Status text (subtle, centered)
        self.status_text = self.canvas.create_text(
            0, 0, text="Ready", 
            font=("SF Pro Display", 16),
            fill="#ffffff", tags="status"
        )
        
        # Start button
        self.start_btn = self.canvas.create_rectangle(
            0, 0, 0, 0, fill="#1a1a1a", outline="#333333", width=2, tags="start_btn"
        )
        self.start_btn_text = self.canvas.create_text(
            0, 0, text="START", font=("SF Pro Display", 14, "bold"),
            fill="#ffffff", tags="start_btn_text"
        )
        
        # Restart button
        self.restart_btn = self.canvas.create_rectangle(
            0, 0, 0, 0, fill="#1a1a1a", outline="#333333", width=2, tags="restart_btn"
        )
        self.restart_btn_text = self.canvas.create_text(
            0, 0, text="⟳", font=("SF Pro Display", 18),
            fill="#ffffff", tags="restart_btn_text"
        )
        
        # Stop/Pause button
        self.stop_btn = self.canvas.create_rectangle(
            0, 0, 0, 0, fill="#1a1a1a", outline="#333333", width=2, tags="stop_btn"
        )
        self.stop_btn_text = self.canvas.create_text(
            0, 0, text="⏸️", font=("SF Pro Display", 14),
            fill="#ffffff", tags="stop_btn_text"
        )
        
        self.bulb_items = []
        self.glow_items = []
        
        self.canvas.bind('<Configure>', self.draw_bulbs)
        self.canvas.tag_bind("start_btn", "<Button-1>", lambda e: self.start_game())
        self.canvas.tag_bind("start_btn_text", "<Button-1>", lambda e: self.start_game())
        self.canvas.tag_bind("restart_btn", "<Button-1>", lambda e: self.restart_game())
        self.canvas.tag_bind("restart_btn_text", "<Button-1>", lambda e: self.restart_game())
        self.canvas.tag_bind("stop_btn", "<Button-1>", lambda e: self.toggle_pause())
        self.canvas.tag_bind("stop_btn_text", "<Button-1>", lambda e: self.toggle_pause())
        
        # Hover effects
        self.canvas.tag_bind("start_btn", "<Enter>", lambda e: self.hover_button("start", True))
        self.canvas.tag_bind("start_btn", "<Leave>", lambda e: self.hover_button("start", False))
        self.canvas.tag_bind("start_btn_text", "<Enter>", lambda e: self.hover_button("start", True))
        self.canvas.tag_bind("start_btn_text", "<Leave>", lambda e: self.hover_button("start", False))
        self.canvas.tag_bind("restart_btn", "<Enter>", lambda e: self.hover_button("restart", True))
        self.canvas.tag_bind("restart_btn", "<Leave>", lambda e: self.hover_button("restart", False))
        self.canvas.tag_bind("restart_btn_text", "<Enter>", lambda e: self.hover_button("restart", True))
        self.canvas.tag_bind("restart_btn_text", "<Leave>", lambda e: self.hover_button("restart", False))
        self.canvas.tag_bind("stop_btn", "<Enter>", lambda e: self.hover_button("stop", True))
        self.canvas.tag_bind("stop_btn", "<Leave>", lambda e: self.hover_button("stop", False))
        self.canvas.tag_bind("stop_btn_text", "<Enter>", lambda e: self.hover_button("stop", True))
        self.canvas.tag_bind("stop_btn_text", "<Leave>", lambda e: self.hover_button("stop", False))
    
    def draw_bulbs(self, event=None):
        if not event:
            return
            
        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()
        center_x = width // 2
        center_y = height // 2
        
        # Round indicator - top right corner
        self.canvas.coords(self.round_text, width - 30, 25)
        
        # Score display - top left
        self.canvas.coords(self.score_text, 30, 25)
        
        # Status text - top center
        self.canvas.coords(self.status_text, center_x, 30)
        
        # Start button - bottom left
        btn_width = 100
        btn_height = 40
        btn_x = center_x - btn_width - 60
        btn_y = height - 80
        self.canvas.coords(self.start_btn, btn_x, btn_y, btn_x + btn_width, btn_y + btn_height)
        self.canvas.coords(self.start_btn_text, btn_x + btn_width // 2, btn_y + btn_height // 2)
        
        # Stop button - bottom center
        stop_btn_x = center_x - btn_width // 2
        self.canvas.coords(self.stop_btn, stop_btn_x, btn_y, stop_btn_x + btn_width, btn_y + btn_height)
        self.canvas.coords(self.stop_btn_text, center_x, btn_y + btn_height // 2)
        
        # Restart button - bottom right
        restart_btn_x = center_x + 60
        self.canvas.coords(self.restart_btn, restart_btn_x, btn_y, restart_btn_x + btn_width, btn_y + btn_height)
        self.canvas.coords(self.restart_btn_text, restart_btn_x + btn_width // 2, btn_y + btn_height // 2)
        
        # Clear existing bulbs
        for item in self.bulb_items + self.glow_items:
            self.canvas.delete(item)
        self.bulb_items.clear()
        self.glow_items.clear()
        
        # Calculate layout
        radius = min(width, height) * 0.32
        bulb_size = min(width, height) * 0.085
        
        # Draw hexagon of bulbs
        for i in range(6):
            angle = 2 * math.pi * i / 6 - math.pi / 6
            x = center_x + radius * math.cos(angle)
            y = center_y + radius * math.sin(angle)
            
            # Outer glow (invisible by default)
            glow = self.canvas.create_oval(
                x - bulb_size * 1.5, y - bulb_size * 1.5,
                x + bulb_size * 1.5, y + bulb_size * 1.5,
                fill='#0a0a0a', outline="", state='hidden',
                tags=f"glow_{i}"
            )
            self.glow_items.append(glow)
            
            # Bulb circle (dark when off)
            bulb = self.canvas.create_oval(
                x - bulb_size, y - bulb_size,
                x + bulb_size, y + bulb_size,
                fill='#1a1a1a', outline='#333333', width=2,
                tags=f"bulb_{i}"
            )
            self.bulb_items.append(bulb)
            
            # Number label
            self.canvas.create_text(
                x, y, text=str(i + 1),
                font=("SF Pro Display", int(bulb_size * 0.8), "bold"),
                fill="#444444", tags=f"text_{i}"
            )
    
    def setup_keyboard_bindings(self):
        for i in range(1, 7):
            self.root.bind(str(i), lambda e, num=i: self.send_input(num))
        
        self.root.bind('<space>', lambda e: self.start_game())
        self.root.bind('<r>', lambda e: self.restart_game())
        self.root.bind('<p>', lambda e: self.toggle_pause())
    
    def toggle_pause(self):
        if not self.game_active:
            return
            
        if self.ser and self.ser.is_open:
            self.ser.write(b"stop\n")
            # Note: The actual pause state will be updated when we receive serial confirmation
    
    def send_input(self, number):
        if self.ser and self.ser.is_open and self.game_active and not self.game_paused:
            try:
                self.ser.write(f"{number}\n".encode())
                self.quick_pulse(number - 1)
            except Exception as e:
                print(f"Error: {e}")
    
    def update_score(self, new_score):
        self.score = new_score
        self.canvas.itemconfig(self.score_text, text=f"Score: {self.score}")
    
    def quick_pulse(self, idx):
        """Quick visual feedback on keypress"""
        self.canvas.itemconfig(self.bulb_items[idx], fill=self.bulb_colors[idx], outline=self.bulb_colors[idx])
        self.root.after(150, lambda: self.deactivate_bulb(idx))
    
    def connect_serial(self):
        try:
            self.ser = serial.Serial('COM7', 9600, timeout=1)
            self.serial_running = True
            self.serial_thread = threading.Thread(target=self.read_serial, daemon=True)
            self.serial_thread.start()
            self.update_status("Connected")
        except:
            self.try_alternative_ports()
    
    def try_alternative_ports(self):
        ports = serial.tools.list_ports.comports()
        for port in ports:
            try:
                self.ser = serial.Serial(port.device, 9600, timeout=1)
                self.serial_running = True
                self.serial_thread = threading.Thread(target=self.read_serial, daemon=True)
                self.serial_thread.start()
                self.update_status("Connected")
                return
            except:
                continue
        self.update_status("No device found")
    
    def read_serial(self):
        while self.serial_running and self.ser and self.ser.is_open:
            try:
                line = self.ser.readline().decode('utf-8').strip()
                if line:
                    self.process_serial_message(line)
            except:
                time.sleep(0.1)
    
    def process_serial_message(self, msg):
        self.root.after(0, lambda: self.handle_serial_message(msg))
    
    def handle_serial_message(self, msg):
        print(f"Serial: {msg}")  # Debug print
        
        # Handle score updates
        if "Score:" in msg:
            try:
                if "Final Score:" in msg:
                    score_str = msg.split("Final Score:")[1].strip()
                else:
                    score_str = msg.split("Score:")[1].strip()
                # Extract just the number (in case there's additional text)
                score_value = int(''.join(filter(str.isdigit, score_str.split()[0])))
                self.update_score(score_value)
            except ValueError as e:
                print(f"Error parsing score: {e}")
        
        if "ROUND" in msg and "=====" in msg:
            try:
                round_num = int(msg.split("ROUND")[1].split("=")[0].strip())
                self.current_round = round_num
                self.update_round(round_num)
                self.update_status("Watch...")
            except:
                pass
        
        elif "GAME_LOST" in msg:
            self.game_lost()
        
        elif "ROUND_WON" in msg:
            self.round_won()
        
        elif "GAME_WON" in msg:
            self.game_won()
        
        elif "Enter the sequence" in msg:
            self.update_status("Your turn")
            self.game_active = True
            self.game_paused = False
            self.canvas.itemconfig(self.stop_btn_text, text="⏸️")
            # Show stop button
            self.canvas.itemconfig(self.stop_btn, state='normal')
            self.canvas.itemconfig(self.stop_btn_text, state='normal')
        
        elif "GAME PAUSED" in msg:
            self.game_paused = True
            self.update_status("Paused")
            self.canvas.itemconfig(self.stop_btn_text, text="▶️")
        
        elif "GAME RESUMED" in msg:
            self.game_paused = False
            self.update_status("Resumed")
            self.canvas.itemconfig(self.stop_btn_text, text="⏸️")
        
        elif "LED" in msg and "[ON]" in msg and "[OFF]" not in msg:
            try:
                led_num = int(msg.split("LED")[1].split("[ON]")[0].strip()) - 1
                if 0 <= led_num < 6:
                    self.activate_bulb(led_num)
            except:
                pass
        
        elif "LED" in msg and "[OFF]" in msg:
            try:
                led_num = int(msg.split("LED")[1].split("[OFF]")[0].strip()) - 1
                if 0 <= led_num < 6:
                    self.deactivate_bulb(led_num)
            except:
                pass
    
    def activate_bulb(self, idx):
        """Light up bulb with glow effect"""
        color = self.bulb_colors[idx]
        self.canvas.itemconfig(self.bulb_items[idx], fill=color, outline=color, width=3)
        self.canvas.itemconfig(self.glow_items[idx], fill=self.get_glow_color(idx), state='normal')
    
    def deactivate_bulb(self, idx):
        """Turn off bulb"""
        self.canvas.itemconfig(self.bulb_items[idx], fill='#1a1a1a', outline='#333333', width=2)
        self.canvas.itemconfig(self.glow_items[idx], state='hidden')
    
    def get_glow_color(self, idx):
        """Get semi-transparent glow color"""
        glow_map = {
            0: "#FF3B3B40", 1: "#3B8BFF40", 2: "#FFD93B40",
            3: "#3BFF6B40", 4: "#B83BFF40", 5: "#FFFFFF40"
        }
        return glow_map.get(idx, "#FFFFFF40")
    
    def hover_button(self, btn_type, entering):
        """Handle button hover effects"""
        if btn_type == "start":
            if entering:
                self.canvas.itemconfig(self.start_btn, fill="#2a2a2a", outline="#555555")
            else:
                self.canvas.itemconfig(self.start_btn, fill="#1a1a1a", outline="#333333")
        elif btn_type == "restart":
            if entering:
                self.canvas.itemconfig(self.restart_btn, fill="#2a2a2a", outline="#555555")
                self.canvas.itemconfig(self.restart_btn_text, fill="#ffffff")
            else:
                self.canvas.itemconfig(self.restart_btn, fill="#1a1a1a", outline="#333333")
                self.canvas.itemconfig(self.restart_btn_text, fill="#888888")
        elif btn_type == "stop":
            if entering:
                self.canvas.itemconfig(self.stop_btn, fill="#2a2a2a", outline="#555555")
            else:
                self.canvas.itemconfig(self.stop_btn, fill="#1a1a1a", outline="#333333")
    
    def update_round(self, num):
        self.canvas.itemconfig(self.round_text, text=f"R{num}")
    
    def update_status(self, text):
        self.canvas.itemconfig(self.status_text, text=text)
    
    def start_game(self):
        if self.ser and self.ser.is_open:
            self.ser.write(b"start\n")
            self.update_status("Starting...")
            self.game_active = True
            self.game_paused = False
            self.score = 0
            self.update_score(0)
            # Hide start button during game
            self.canvas.itemconfig(self.start_btn, state='hidden')
            self.canvas.itemconfig(self.start_btn_text, state='hidden')
            # Show stop button
            self.canvas.itemconfig(self.stop_btn, state='normal')
            self.canvas.itemconfig(self.stop_btn_text, state='normal')
    
    def restart_game(self):
        if self.ser and self.ser.is_open:
            self.ser.write(b"restart\n")
            self.update_status("Ready")
            self.reset_bulbs()
            self.game_active = False
            self.game_paused = False
            self.current_round = 0
            self.score = 0
            self.update_score(0)
            self.update_round(0)
            # Show start button again
            self.canvas.itemconfig(self.start_btn, state='normal')
            self.canvas.itemconfig(self.start_btn_text, state='normal')
            # Hide stop button
            self.canvas.itemconfig(self.stop_btn, state='hidden')
            self.canvas.itemconfig(self.stop_btn_text, state='hidden')
        else:
            self.update_status("Not connected")
    
    def reset_bulbs(self):
        for i in range(6):
            self.deactivate_bulb(i)
        self.blinking = False
    
    def game_lost(self):
        self.update_status("Game Over")
        self.game_active = False
        self.game_paused = False
        self.blink_all_failure()
        # Show start button again
        self.canvas.itemconfig(self.start_btn, state='normal')
        self.canvas.itemconfig(self.start_btn_text, state='normal')
        # Hide stop button
        self.canvas.itemconfig(self.stop_btn, state='hidden')
        self.canvas.itemconfig(self.stop_btn_text, state='hidden')
    
    def round_won(self):
        self.update_status("Nice!")
        self.flash_all_success()
    
    def game_won(self):
        self.update_status("You Won!")
        self.game_active = False
        self.game_paused = False
        self.victory_animation()
        # Show start button again after animation
        self.root.after(2000, lambda: (
            self.canvas.itemconfig(self.start_btn, state='normal'),
            self.canvas.itemconfig(self.start_btn_text, state='normal'),
            self.canvas.itemconfig(self.stop_btn, state='hidden'),
            self.canvas.itemconfig(self.stop_btn_text, state='hidden')
        ))
    
    def blink_all_failure(self):
        """Blink all bulbs with failure color (#0B1E24)"""
        self.blinking = True
        self._blink_cycle(0, "#DADF93")  # failure color
    
    def flash_all_success(self):
        """Flash all bulbs with success color (#F27E17)"""
        for i in range(6):
            self.canvas.itemconfig(self.bulb_items[i], fill='#F27E17', outline='#F27E17')
        self.root.after(800, self.reset_bulbs)
    
    def victory_animation(self):
        """Rainbow cycle animation with success colors"""
        def cycle(count):
            if count >= 18:
                self.reset_bulbs()
                return
            idx = count % 6
            for i in range(6):
                if i == idx:
                    self.canvas.itemconfig(self.bulb_items[i], fill=self.bulb_colors[i])
                else:
                    self.canvas.itemconfig(self.bulb_items[i], fill='#1a1a1a')
            self.root.after(100, lambda: cycle(count + 1))
        cycle(0)
    
    def _blink_cycle(self, count, color):
        if count >= 6:
            self.reset_bulbs()
            return
        
        if count % 2 == 0:
            for i in range(6):
                self.canvas.itemconfig(self.bulb_items[i], fill=color, outline=color)
        else:
            for i in range(6):
                self.canvas.itemconfig(self.bulb_items[i], fill='#1a1a1a', outline='#333333')
        
        self.root.after(300, lambda: self._blink_cycle(count + 1, color))
    
    def on_closing(self):
        self.serial_running = False
        if self.ser and self.ser.is_open:
            self.ser.close()
        self.root.destroy()

def main():
    root = tk.Tk()
    app = LEDGameGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()