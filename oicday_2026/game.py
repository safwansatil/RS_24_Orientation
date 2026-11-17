"""Fullscreen reaction game for an Arduino or two keyboard players."""
import random
import tkinter as tk
from pathlib import Path
from time import perf_counter_ns
from tkinter import ttk

from PIL import Image, ImageSequence, ImageTk

from connection import Board, available_ports
from match import Match, ROUND_LIMIT


ROOT = Path(__file__).resolve().parent
INK = "#141421"
PAPER = "#f6f2e5"
RED = "#e72841"
SCREEN = "#e2edba"
PLAYER = ("#ffe04b", "#42b8fb")
KEYS = {"a": 1, "l": 2}


class Game:
    def __init__(self, root):
        self.root = root
        root.title("Reaction Duel | OIC Day 2026")
        root.geometry("1120x735")
        root.minsize(780, 530)
        self.board = None
        self.connected = False
        self.mode = "keyboard"
        self.notice = "A and L are the player buttons."
        self.show_controls = False
        self.match = None
        self.token = 0
        self.held = set()
        self.key_releases = {}
        self.presses = {}
        self.cue_at = 0
        self.timers = set()
        self.frame = 0
        self.actor = 0
        self.sprite_items = []
        self.scale = 0
        self.offset = (0, 0)
        self.images = []
        self.actions = {}
        self.sources = []
        for filename in ("bolt.gif", "skip.gif"):
            with Image.open(ROOT / "art" / filename) as gif:
                self.sources.append([(frame.convert("RGBA"), frame.info.get("duration", 40))
                                     for frame in ImageSequence.Iterator(gif)])

        self.canvas = tk.Canvas(root, bg=INK, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.names = [tk.StringVar(value=value) for value in ("Player 1", "Player 2")]
        self.entries = [tk.Entry(self.canvas, textvariable=value, justify="center", relief="flat",
                                 bg=PAPER, fg=INK, highlightthickness=0)
                        for value in self.names]
        self.port = ttk.Combobox(self.canvas, state="readonly")
        self.refresh_ports()

        self.canvas.bind("<Configure>", self.draw)
        self.canvas.bind("<Button-1>", self.click_button)
        self.canvas.bind("<Motion>", self.hover_button)
        root.bind("<KeyPress>", self.key_down)
        root.bind("<KeyRelease>", self.key_up)
        root.bind("<FocusOut>", self.lost_focus)
        root.bind("<F11>", lambda _: root.attributes("-fullscreen", not root.attributes("-fullscreen")))
        root.bind("<Escape>", lambda _: root.attributes("-fullscreen", False))
        root.protocol("WM_DELETE_WINDOW", self.close)
        self.poll_board()

    def refresh_ports(self):
        ports = available_ports()
        selected = self.port.get()
        self.port.configure(values=ports)
        self.port.set(selected if selected in ports else (ports[0] if ports else ""))

    def keyboard_mode(self):
        if self.board:
            self.board.close()
            self.board = None
        self.connected = False
        self.mode = "keyboard"
        self.notice = "A and L are the player buttons."
        self.draw()

    def connect(self):
        if self.board:
            return
        if not self.port.get():
            self.refresh_ports()
        if not self.port.get():
            self.notice = "No serial port found. Plug in the Arduino and refresh."
        else:
            self.mode = "board"
            self.notice = f"Looking for Reaction Duel on {self.port.get()}…"
            self.board = Board(self.port.get())
        self.draw()

    def poll_board(self):
        if self.board:
            while not self.board.inbox.empty():
                kind, data = self.board.inbox.get_nowait()
                if kind == "line":
                    self.receive(data)
                elif kind == "connected":
                    self.connected = True
                    self.notice = f"Arduino ready on {data}. Use the physical buttons."
                    self.draw()
                else:
                    self.board.close()
                    self.board = None
                    self.connected = False
                    self.reset_match()
                    self.show_controls = True
                    self.notice = f"Connection lost: {data}" if len(data) < 82 else "Could not open the port. Close Serial Monitor and reconnect."
                    self.draw()
                    break
        self.root.after(15, self.poll_board)

    def later(self, delay, callback):
        def run():
            self.timers.discard(handle)
            callback()

        handle = self.root.after(delay, run)
        self.timers.add(handle)
        return handle

    def start_match(self):
        if self.mode == "board" and not self.connected:
            return
        names = tuple(value.get().strip()[:20] or f"Player {i}" for i, value in enumerate(self.names, 1))
        self.match = Match(names)
        self.canvas.focus_set()
        self.arm()

    def arm(self):
        self.token += 1
        self.match.arm(self.token)
        self.presses.clear()
        self.frame = 0
        self.actor = 0
        if self.mode == "board":
            self.board.send(f"ARM,{self.token}")
        else:
            self.wait_for_keys()
        self.draw()

    def wait_for_keys(self):
        if not self.held:
            self.receive(f"WAIT,{self.token}")
            self.later(random.randint(2000, 5000), self.keyboard_cue)

    def keyboard_cue(self):
        if self.match.phase == "wait" and not self.presses:
            self.cue_at = perf_counter_ns()
            self.receive(f"GO,{self.token}")
            self.later(3004, self.keyboard_timeout)

    def keyboard_timeout(self):
        if self.match.phase == "go" and not self.presses:
            self.receive(f"RESULT,{self.token},MISS,0,0")

    def key_down(self, event):
        key = event.keysym.lower()
        if key not in KEYS or self.mode != "keyboard" or not self.match:
            return
        if key in self.key_releases:
            self.root.after_cancel(self.key_releases.pop(key))
        if key in self.held:
            return "break"
        self.held.add(key)
        now = perf_counter_ns()
        if self.match.phase == "wait" or (self.match.phase == "go" and now - self.cue_at <= 3_000_000_000):
            if not self.presses:
                self.later(5, self.keyboard_result)
            self.presses.setdefault(KEYS[key], now)
        return "break"

    def key_up(self, event):
        key = event.keysym.lower()
        if key in self.held and key not in self.key_releases:
            self.key_releases[key] = self.root.after(8, lambda: self.release_key(key))
            return "break"

    def release_key(self, key):
        self.key_releases.pop(key, None)
        self.held.discard(key)
        if self.match and self.match.phase == "release" and self.mode == "keyboard":
            self.wait_for_keys()

    def lost_focus(self, event):
        if event.widget in (self.canvas, self.root) and self.match and self.mode == "keyboard":
            for handle in self.key_releases.values():
                self.root.after_cancel(handle)
            self.key_releases.clear()
            self.held.clear()
            if self.match.phase == "release":
                self.wait_for_keys()

    def keyboard_result(self):
        player = min(self.presses, key=self.presses.get)
        first = self.presses[player]
        tied = len(self.presses) == 2 and max(self.presses.values()) - first <= 2_000_000
        if self.match.phase == "wait":
            self.receive(f"RESULT,{self.token},EARLY,{0 if tied else player},0")
        elif tied:
            self.receive(f"RESULT,{self.token},TIE,0,0")
        else:
            self.receive(f"RESULT,{self.token},WIN,{player},{(first - self.cue_at) // 1_000_000}")

    def receive(self, line):
        if not self.match or not self.match.receive(line):
            return
        if self.match.phase in {"result", "finished"}:
            self.cancel_timers()
            self.actor = self.match.winner if self.match.phase == "finished" else (
                self.match.player if self.match.outcome == "WIN" else 0
            )
            if self.actor:
                self.later(25, self.animate)
            if self.match.phase == "result":
                self.later(1600, self.arm)
        self.draw()

    def animate(self):
        self.frame += 1
        index = self.actor - 1
        self.canvas.itemconfigure(self.sprite_items[index], image=self.images[index][self.frame])
        if self.frame + 1 < len(self.sources[index]):
            self.later(self.sources[index][self.frame][1], self.animate)

    def cancel_timers(self):
        for handle in self.timers:
            self.root.after_cancel(handle)
        self.timers.clear()

    def reset_match(self):
        self.cancel_timers()
        if self.match and self.board and self.connected:
            self.board.send("CANCEL")
        self.match = None
        self.draw()

    def close(self):
        if self.board:
            self.board.close()
        self.root.destroy()

    def coords(self, *points):
        return [point * self.scale + self.offset[i % 2] for i, point in enumerate(points)]

    def rect(self, x, y, w, h, fill, outline="", width=1, tags=()):
        return self.canvas.create_rectangle(*self.coords(x, y, x + w, y + h), fill=fill,
                                            outline=outline, width=max(1, width * self.scale), tags=tags)

    def text(self, x, y, content, size, fill=INK, anchor="center", bold=True, tags=(), family="Arial", max_width=None):
        points = max(1, round(size * self.scale))
        weight = "bold" if bold else "normal"
        item = self.canvas.create_text(*self.coords(x, y), text=content, fill=fill, anchor=anchor,
                                       font=(family, points, weight), tags=tags)
        if max_width and content:
            left, _, right, _ = self.canvas.bbox(item)
            while right - left > max_width * self.scale and points > 1:
                points -= 1
                self.canvas.itemconfigure(item, font=(family, points, weight))
                left, _, right, _ = self.canvas.bbox(item)
        return item

    def rounded(self, x, y, w, h, r, fill, tags=()):
        return self.canvas.create_polygon(*self.coords(
            x + r, y, x + w - r, y, x + w, y, x + w, y + r,
            x + w, y + h - r, x + w, y + h, x + w - r, y + h,
            x + r, y + h, x, y + h, x, y + h - r, x, y + r, x, y,
        ), smooth=True, splinesteps=16, fill=fill, tags=tags)

    def button(self, x, y, w, label, action, *, fill=PAPER, enabled=True):
        tag = f"button-{x}-{y}"
        self.rounded(x, y + 7, w, 42, 11, INK)
        self.rounded(x, y, w, 42, 11, fill if enabled else "#df9e9e", tag)
        self.text(x + w / 2, y + 20, label, 12, tags=tag, family="Arial Black")
        if enabled:
            self.actions[tag] = action

    def current_action(self):
        return next((self.actions[tag] for tag in self.canvas.gettags("current") if tag in self.actions), None)

    def click_button(self, _):
        action = self.current_action()
        if action:
            action()

    def hover_button(self, _):
        self.canvas.configure(cursor="hand2" if self.current_action() else "")

    def widget(self, x, y, width, height, widget):
        self.canvas.create_window(*self.coords(x, y), window=widget,
                                  width=int(width * self.scale), height=int(height * self.scale))

    def toggle_controls(self):
        self.show_controls = not self.show_controls
        self.draw()

    def draw(self, _=None):
        canvas = self.canvas
        width, height = canvas.winfo_width(), canvas.winfo_height()
        if width < 10 or height < 10:
            return
        scale = min(width / 1040, height / 680)
        self.offset = ((width - 1040 * scale) / 2, (height - 680 * scale) / 2)
        if scale != self.scale:
            self.scale = scale
            size = (round(224 * scale), round(200 * scale))
            self.images = [[ImageTk.PhotoImage(frame.resize(size, Image.Resampling.LANCZOS))
                            for frame, _ in frames] for frames in self.sources]
            for entry in self.entries:
                entry.configure(font=("Arial", max(10, round(14 * scale)), "bold"))
        self.actions.clear()
        canvas.delete("all")
        canvas.configure(cursor="")
        self.rect(0, 0, 1040, 680, RED)
        self.text(61, 76, "REACTION DUEL", 42, INK, anchor="w", family="Arial Black")
        self.text(58, 69, "REACTION DUEL", 42, PAPER, anchor="w", family="Arial Black")
        self.draw_rounds()

        live = self.match and self.match.phase == "go"
        self.rounded(52, 132, 936, 419, 44, "#9f192f")
        self.rounded(52, 123, 936, 418, 44, INK)
        self.rounded(68, 139, 904, 380, 31, "#354428")
        self.rounded(73, 144, 894, 370, 26, "#ceef9b" if live else SCREEN)
        for x in range(100, 958, 19):
            for y in (416, 430, 444):
                self.rect(x, y, 2, 2, "#a9bd80")
        self.rect(105, 452, 830, 2, "#a9bd80")

        self.sprite_items.clear()
        self.draw_player(0, 234)
        self.draw_player(1, 806)
        self.draw_signal()
        self.draw_controls()

    def draw_rounds(self):
        match = self.match
        completed = match.rounds if match else []
        caption = "7 ROUND CONTEST" if not match else f"ROUND {match.number} / {ROUND_LIMIT}"
        self.text(983, 53, caption, 10, PAPER, anchor="e", family="Arial Black")
        for index in range(ROUND_LIMIT):
            x = 775 + index * 31
            self.rounded(x, 72, 24, 20, 5, INK)
            if index < len(completed):
                player = completed[index]
                if player:
                    self.rounded(x + 3, 75, 18, 14, 4, PLAYER[player - 1])
                else:
                    self.rect(x + 7, 81, 10, 2, PAPER)
            elif match and index == match.number - 1:
                self.rounded(x + 5, 77, 14, 10, 3, PAPER)

    def draw_controls(self):
        if self.match:
            self.button(53, 580, 112, "SETUP", self.reset_match)
            if self.match.phase == "finished":
                self.button(412, 574, 216, "PLAY AGAIN", self.start_match, fill=PLAYER[0])
            return

        self.button(53, 580, 112, "DONE" if self.show_controls else "INPUT", self.toggle_controls)
        if self.show_controls:
            self.button(181, 580, 102, "KEYBOARD", self.keyboard_mode, fill=PLAYER[0] if self.mode == "keyboard" else PAPER)
            self.widget(344, 601, 96, 27, self.port)
            self.button(404, 580, 38, "↻", lambda: (self.refresh_ports(), self.draw()))
            self.button(453, 580, 113, "USB", self.connect, fill=PLAYER[1], enabled=not self.board)
            self.text(55, 649, self.notice, 11, PAPER, anchor="w", max_width=875)
            start_x = 770
        else:
            start_x = 412
        self.button(start_x, 574, 216, "START", self.start_match, fill=PLAYER[0], enabled=self.mode == "keyboard" or self.connected)

    def draw_player(self, index, center):
        match = self.match
        color = PLAYER[index]
        frame = self.frame if match and self.actor == index + 1 else 0
        sprite = self.canvas.create_image(*self.coords(center, 350), image=self.images[index][frame])
        self.sprite_items.append(sprite)
        score = match.scores[index] if match else 0
        self.text(center, 216, str(score), 48, family="Arial Black")
        if match:
            self.text(center, 481, match.names[index], 16, max_width=237, family="Arial Black")
        else:
            self.rounded(center - 107, 466, 214, 34, 8, PAPER)
            self.widget(center, 483, 192, 26, self.entries[index])
        if self.mode == "keyboard":
            x = center - 120 if index == 0 else center + 91
            self.rounded(x, 172, 29, 28, 5, INK)
            self.rounded(x, 169, 29, 26, 5, color)
            self.text(x + 14.5, 182, ("A", "L")[index], 12, family="Arial Black")

    def draw_signal(self):
        match = self.match
        phase = match.phase if match else "setup"
        headline, detail, color = {
            "setup": ("VS", "", INK),
            "release": ("RELEASE", "", INK),
            "wait": ("WAIT…", "", INK),
            "go": ("GO!", "", "#267a35"),
        }.get(phase, ("", "", INK))
        if phase in {"finished", "result"}:
            if phase == "finished":
                headline = "WINNER" if match.winner else "DRAW"
                detail = match.names[match.winner - 1] if match.winner else ""
            elif match.outcome == "WIN":
                headline = f"{match.elapsed} ms"
                detail = f"+1  {match.names[match.player - 1]}"
            elif match.outcome == "EARLY":
                headline = "TOO SOON"
                detail = match.names[match.player - 1] if match.player else "Both players"
            elif match.outcome == "TIE":
                headline = "TIE"
            else:
                headline = "TIME UP"
        self.text(520, 323 if not detail else 311, headline, 62 if phase in {"setup", "go"} else 36,
                  color, family="Arial Black", max_width=312)
        if detail:
            self.text(520, 366, detail, 14, max_width=266, family="Arial Black")


def main():
    root = tk.Tk()
    Game(root)
    root.mainloop()


if __name__ == "__main__":
    main()
