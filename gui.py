# simon_says_simple.py,
# DONT USE THIS FOR NOW
import tkinter as tk
from tkinter import ttk
import threading
import queue
import time

# Try to import serial
try:
    import serial
    import serial.tools.list_ports
    HAS_PYSERIAL = True
except ImportError:
    HAS_PYSERIAL = False

# Constants
BAUD_RATE = 9600
DEFAULT_PORT = "COM7"

class SerialManager(threading.Thread):
    def __init__(self, port, incoming_queue, outgoing_queue):
        super().__init__(daemon=True)
        self.port = port
        self.in_q = incoming_queue
        self.out_q = outgoing_queue
        self.running = True
        self.serial_conn = None

    def run(self):
        try:
            self.serial_conn = serial.Serial(self.port, BAUD_RATE, timeout=0.1)
            time.sleep(2)
            self.in_q.put("CONNECTED")
        except Exception as e:
            self.in_q.put(f"ERROR: {e}")
            return

        buffer = ""
        while self.running:
            try:
                if self.serial_conn and self.serial_conn.in_waiting:
                    data = self.serial_conn.read(self.serial_conn.in_waiting)
                    text = data.decode('utf-8', errors='ignore')
                    buffer += text
                    
                    while '\n' in buffer:
                        line, buffer = buffer.split('\n', 1)
                        self.in_q.put(line.strip())
            except Exception as e:
                self.in_q.put(f"READ_ERROR: {e}")
                break

            try:
                command = self.out_q.get_nowait()
                if command and self.serial_conn:
                    self.serial_conn.write((command + '\n').encode('utf-8'))
            except queue.Empty:
                pass
            except Exception as e:
                self.in_q.put(f"WRITE_ERROR: {e}")

            time.sleep(0.01)

    def stop(self):
        self.running = False
        if self.serial_conn:
            self.serial_conn.close()

class SimonGame(tk.Tk):
    def __init__(self):
        super().__init__()
        
        self.title("Simon Says Game")
        self.geometry("600x500")
        self.configure(bg='black')
        
        # Game state
        self.connected = False
        self.game_active = False
        
        # Serial communication
        self.serial_in = queue.Queue()
        self.serial_out = queue.Queue()
        self.serial_thread = None
        
        # Colors
        self.colors = ['red', 'blue', 'purple', 'green', 'yellow', 'white']
        self.dark_colors = ['darkred', 'darkblue', 'darkviolet', 'darkgreen', 'darkgoldenrod', 'gray']
        
        self.setup_ui()
        self.check_serial()

    def setup_ui(self):
        # Title
        title = tk.Label(self, text="SIMON SAYS", font=('Arial', 24, 'bold'), 
                        bg='black', fg='white')
        title.pack(pady=10)
        
        # Status
        self.status = tk.Label(self, text="Click Connect then Start Game", 
                              font=('Arial', 12), bg='black', fg='yellow')
        self.status.pack(pady=5)
        
        # Bulbs frame
        bulbs_frame = tk.Frame(self, bg='black')
        bulbs_frame.pack(pady=20)
        
        self.bulbs = []
        for i in range(6):
            bulb = tk.Canvas(bulbs_frame, width=80, height=80, bg='black', highlightthickness=0)
            bulb.grid(row=i//3, column=i%3, padx=10, pady=10)
            
            # Draw circle
            circle = bulb.create_oval(10, 10, 70, 70, fill=self.dark_colors[i], outline='white', width=2)
            self.bulbs.append({'canvas': bulb, 'circle': circle, 'color': i})
            
            # Number label
            label = tk.Label(bulbs_frame, text=str(i+1), font=('Arial', 12, 'bold'),
                           bg='black', fg='white')
            label.grid(row=i//3, column=i%3, pady=(85, 0))
            
            # Click binding
            bulb.bind('<Button-1>', lambda e, idx=i: self.bulb_clicked(idx))
        
        # Control buttons
        controls = tk.Frame(self, bg='black')
        controls.pack(pady=20)
        
        self.connect_btn = tk.Button(controls, text="Connect", command=self.connect_arduino,
                                   font=('Arial', 12), width=10)
        self.connect_btn.grid(row=0, column=0, padx=5)
        
        self.start_btn = tk.Button(controls, text="Start Game", command=self.start_game,
                                 font=('Arial', 12), width=10)
        self.start_btn.grid(row=0, column=1, padx=5)
        
        self.restart_btn = tk.Button(controls, text="Restart", command=self.restart_game,
                                   font=('Arial', 12), width=10)
        self.restart_btn.grid(row=0, column=2, padx=5)
        
        quit_btn = tk.Button(controls, text="Quit", command=self.quit_game,
                           font=('Arial', 12), width=10, bg='red', fg='white')
        quit_btn.grid(row=0, column=3, padx=5)
        
        # Round info
        self.round_info = tk.Label(self, text="Rounds: 7 bulbs, 13 bulbs, 17 bulbs", 
                                  font=('Arial', 10), bg='black', fg='white')
        self.round_info.pack(pady=5)
        
        # Score
        self.score_label = tk.Label(self, text="Score: 0/3", font=('Arial', 12, 'bold'),
                                  bg='black', fg='white')
        self.score_label.pack(pady=5)

    def connect_arduino(self):
        if not HAS_PYSERIAL:
            self.status.config(text="PySerial not available - simulation mode")
            self.connected = False
            return
            
        try:
            ports = list(serial.tools.list_ports.comports())
            port_to_use = DEFAULT_PORT
            
            if not any(p.device == DEFAULT_PORT for p in ports) and ports:
                port_to_use = ports[0].device
                
            self.serial_thread = SerialManager(port_to_use, self.serial_in, self.serial_out)
            self.serial_thread.start()
            self.status.config(text=f"Connecting to {port_to_use}...")
            self.connect_btn.config(state='disabled')
            
        except Exception as e:
            self.status.config(text=f"Connection failed: {e}")

    def start_game(self):
        if self.connected:
            self.serial_out.put("start")
        else:
            self.status.config(text="Game started - simulation mode")
            self.game_active = True

    def restart_game(self):
        if self.connected:
            self.serial_out.put("start")
        else:
            self.status.config(text="Game restarted - simulation mode")
            self.game_active = True

    def bulb_clicked(self, bulb_index):
        if not self.game_active:
            return
            
        self.flash_bulb(bulb_index)
        
        if self.connected:
            self.serial_out.put(str(bulb_index + 1))

    def flash_bulb(self, bulb_index, duration=300):
        bulb = self.bulbs[bulb_index]
        bulb['canvas'].itemconfig(bulb['circle'], fill=self.colors[bulb_index])
        self.after(duration, lambda: bulb['canvas'].itemconfig(bulb['circle'], fill=self.dark_colors[bulb_index]))

    def check_serial(self):
        try:
            while True:
                message = self.serial_in.get_nowait()
                self.handle_serial_message(message)
        except queue.Empty:
            pass
            
        self.after(100, self.check_serial)

    def handle_serial_message(self, message):
        if message == "CONNECTED":
            self.connected = True
            self.status.config(text="Connected! Click Start Game")
            
        elif "ERROR" in message:
            self.status.config(text=f"Error: {message}")
            
        elif "CONGRATULATIONS" in message or "GAME_WON" in message:
            self.status.config(text="YOU WON THE GAME! 🎉")
            self.flash_all_bulbs(5)
            
        elif "GAME OVER" in message or "GAME_LOST" in message:
            self.status.config(text="Game Over - You lost!")
            self.blink_all_bulbs(3)
            
        elif "ROUND WON" in message:
            self.status.config(text="Round Won! ✅")
            self.update_score()
            
        elif "ROUND LOST" in message:
            self.status.config(text="Round Lost! ❌")
            self.update_score()
            
        elif "START" in message:
            self.game_active = True
            self.status.config(text="Game started! Watch the LEDs and repeat!")
            
        elif "LED" in message and "ON" in message:
            for i in range(6):
                if str(i+1) in message:
                    self.flash_bulb(i, 800)

    def flash_all_bulbs(self, times):
        def flash(count=0):
            if count >= times * 2:
                return
            if count % 2 == 0:
                for i in range(6):
                    self.bulbs[i]['canvas'].itemconfig(self.bulbs[i]['circle'], fill=self.colors[i])
            else:
                for i in range(6):
                    self.bulbs[i]['canvas'].itemconfig(self.bulbs[i]['circle'], fill=self.dark_colors[i])
            self.after(200, lambda: flash(count + 1))
        flash()

    def blink_all_bulbs(self, times):
        def blink(count=0):
            if count >= times:
                return
            for i in range(6):
                self.bulbs[i]['canvas'].itemconfig(self.bulbs[i]['circle'], fill='red')
            self.after(200, lambda: [self.bulbs[i]['canvas'].itemconfig(self.bulbs[i]['circle'], fill=self.dark_colors[i]) for i in range(6)])
            self.after(400, lambda: blink(count + 1))
        blink()

    def update_score(self):
        # Simple score tracking - you can enhance this by parsing actual scores
        current_text = self.score_label.cget("text")
        if "Score:" in current_text:
            try:
                score = int(current_text.split(":")[1].split("/")[0]) + 1
                self.score_label.config(text=f"Score: {score}/3")
            except:
                self.score_label.config(text="Score: 1/3")
        else:
            self.score_label.config(text="Score: 1/3")

    def quit_game(self):
        if self.serial_thread:
            self.serial_thread.stop()
        self.destroy()

if __name__ == "__main__":
    game = SimonGame()
    game.mainloop()