# =============================================================================
# client.py — Minesweeper LAN Multiplayer Client
# =============================================================================
# Run this on BOTH computers (including the one running server.py).
# The host enters their own IP (or "localhost"). The guest enters the host's IP.
#
# How to run:
#   python3 client.py
# =============================================================================
# Line 1-963 Generated with Claude, prompt: "Build a simple Python LAN multiplayer Minesweeper project for a school presentation.
#
# Use:
#
# - Python
#
# - Tkinter for GUI
#
# - socket for LAN communication
#
# - threading for receiving messages
#
# - json for network messages
#
# The project should have three game modes:
#
# 1. Classic Mode
#
# - Two players compete on the same Minesweeper board.
#
# - Both players can reveal cells and place flags.
#
# - Revealing a safe cell gives +1 point.
#
# - Clicking a mine makes that player lose.
#
# - If all safe cells are revealed, the player with the higher score wins.
#
# 2. Co-op Role Mode
#
# - Two players solve the same board together.
#
# - Player 1 can only reveal cells.
#
# - Player 2 can only place or remove flags.
#
# - They win together if all safe cells are revealed.
#
# - They lose together if a mine is clicked.
#
# 3. Sabotage Mode
#
# - Two players each have their own Minesweeper board.
#
# - Each player has 3 sabotage chances.
#
# - When a player uses sabotage, the game randomly places a wrong flag on the opponent’s board.
#
# - The sabotage should only place a flag on an unrevealed cell.
#
# - The opponent can remove the wrong flag manually.
#
# - Clicking a mine still causes a loss.
#
# - The player who survives longer or reveals more safe cells wins.
#
# Networking design:
#
# - Use a server-authoritative model.
#
# - One computer hosts the game as the server.
#
# - The other computer joins as the client.
#
# - The server generates the board and controls the official game state.
#
# - The client sends actions to the server.
#
# - The server updates the game state and sends the new state back.
#
# - Use JSON messages with a "type" field, such as:
#
#   - "mode_select"
#
#   - "move"
#
#   - "flag"
#
#   - "sabotage"
#
#   - "state"
#
#   - "game_over"
#
# Implementation requirements:
#
# *  Make the code beginner-friendly and readable.
#
# *  Add comments explaining important parts.
#
# *   explain the code in a beginner-friendly way for a classroom presentation."
import tkinter as tk
from tkinter import messagebox
import socket
import threading
import json

# ─── Must match the server's port ─────────────────────────────────────────────
PORT = 5555

# ─── Classic Windows Minesweeper color palette ────────────────────────────────
BG          = "#c0c0c0"   # The classic Windows gray used everywhere
CELL_UP     = "#c0c0c0"   # Unrevealed cell — same gray, raised relief makes it 3D
CELL_DOWN   = "#bdbdbd"   # Revealed cell — slightly darker gray, sunken
LED_BG      = "#000000"   # LED display background (black)
LED_FG      = "#ff0000"   # LED display digits (red)
BORDER_DARK = "#808080"   # Dark edge of 3D border
BORDER_LITE = "#ffffff"   # Light edge of 3D border

# ─── Classic Minesweeper number colors ────────────────────────────────────────
NUMBER_COLORS = {
    1: "#0000ff",  # blue
    2: "#007b00",  # dark green
    3: "#ff0000",  # red
    4: "#00007b",  # dark blue
    5: "#7b0000",  # dark red
    6: "#007b7b",  # teal
    7: "#000000",  # black
    8: "#7b7b7b",  # gray
}

# ─── Smiley face states ────────────────────────────────────────────────────────
FACE_IDLE = "🙂"
FACE_WIN  = "😎"
FACE_LOSE = "😵"


# =============================================================================
# Cell-drawing helpers — draw directly onto a tk.Canvas for pixel-perfect
# Windows-style bevels. macOS Tkinter's built-in relief="raised" is too soft;
# drawing manually gives the sharp white/gray edges of the original game.
# =============================================================================

def draw_raised_cell(canvas, size, text="", text_color="black", font=None):
    """
    Draw an unrevealed (raised) cell on a Canvas.

    Classic Windows bevel:
      • Top  + left  edges → 2 px white  (#ffffff)  — the "light" face
      • 1 px of lighter gray (#dfdfdf) just inside the white
      • Bottom + right edges → 2 px gray (#808080) — the "shadow" face
    This makes the cell look like it's popping up out of the board.
    """
    canvas.delete("all")

    # Main background
    canvas.create_rectangle(0, 0, size, size, fill="#c0c0c0", outline="")

    # Outer highlight — white, 2 px on top and left
    canvas.create_rectangle(0, 0, size, 2,    fill="#ffffff", outline="")
    canvas.create_rectangle(0, 0, 2,    size, fill="#ffffff", outline="")

    # Inner highlight — lighter gray, 1 px just inside the white
    canvas.create_rectangle(2, 2, size, 3,    fill="#dfdfdf", outline="")
    canvas.create_rectangle(2, 2, 3,    size, fill="#dfdfdf", outline="")

    # Outer shadow — dark gray, 2 px on bottom and right
    canvas.create_rectangle(0, size - 2, size, size, fill="#808080", outline="")
    canvas.create_rectangle(size - 2, 0, size, size, fill="#808080", outline="")

    if text:
        canvas.create_text(size // 2, size // 2, text=text,
                           fill=text_color, font=font or ("Arial", 12, "bold"))


def draw_sunken_cell(canvas, size, text="", text_color="black", font=None,
                     bg="#bdbdbd"):
    """
    Draw a revealed (sunken/flat) cell on a Canvas.

    A thin 1-px dark border on the top and left edges creates the illusion
    that the cell has been pressed inward, just like the original game.
    """
    canvas.delete("all")

    canvas.create_rectangle(0, 0, size, size, fill=bg, outline="")

    # Thin shadow on top and left only
    canvas.create_rectangle(0, 0, size, 1, fill="#808080", outline="")
    canvas.create_rectangle(0, 0, 1, size, fill="#808080", outline="")

    if text:
        canvas.create_text(size // 2, size // 2, text=text,
                           fill=text_color, font=font or ("Arial", 12, "bold"))


# =============================================================================
# NetworkClient — handles all socket communication in a background thread
# =============================================================================
class NetworkClient:
    """
    Manages the TCP connection to the server.
    Messages are received in a background thread so the GUI never freezes.
    Each complete JSON line triggers the on_message callback.
    """
#_ = for this class only
#constructor
#on_message = idc what u wanna do with the data, so when u call me import a function wowwwwwww im so smart mark is so smart

    def __init__(self, host, port, on_message):
        self.host = host
        self.port = port
        self.on_message = on_message  # called whenever a full message arrives, callback function
        self.sock = None
        self._running = False
        self.buffer = ""  # holds partial recv data between calls
#   socket.AF_INET = IPv4, socket.SOCK_STREAM = TCP
    def connect(self):
        """Try to connect to the server. Returns True on success."""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.host, self.port))
            self._running = True
            return True
        except Exception as e:
            print(f"Connection failed: {e}")
            return False

#daemon = close together
    def start_receive_loop(self):
        """Start the background thread that listens for messages from the server."""
        t = threading.Thread(target=self._receive_loop, daemon=True)
        t.start()

    def _receive_loop(self):
        """
        Continuously receive data. Data arrives as newline-delimited JSON.
        We accumulate bytes and process one complete line at a time.
        """
        while self._running:
            try:
                data = self.sock.recv(4096).decode("utf-8") #4096 bytes
                if not data:
                    break
                self.buffer += data
                while "\n" in self.buffer:
                    line, self.buffer = self.buffer.split("\n", 1)
                    line = line.strip()
                    if line:
                        try:
                            msg = json.loads(line)    #JSON string to Python dict
                            self.on_message(msg)
                        except json.JSONDecodeError:
                            print(f"Bad JSON: {line}")
            except Exception as e:
                print(f"Receive error: {e}")
                break
        self.on_message({"type": "disconnect"})

    def send(self, payload):
        """Send a dict to the server as a JSON line."""
        try:
            self.sock.sendall((json.dumps(payload) + "\n").encode("utf-8"))
        except Exception as e:
            print(f"Send error: {e}")

    def disconnect(self):
        self._running = False
        if self.sock:
            self.sock.close()


# =============================================================================
# LedDisplay — the classic red-on-black digit counter (mine count / timer)
# =============================================================================
class LedDisplay(tk.Frame):   #inherit Frame
    """
    Looks like the classic Minesweeper LED panels.
    Shows up to 3 digits in red on a black background.
    """

    def __init__(self, parent, digits=3):
        super().__init__(parent, bg=LED_BG, bd=1, relief="sunken") #Create itself
        self._digits = digits
        self._label = tk.Label(
            self,
            text="0" * digits,
            font=("Courier New", 22, "bold"),
            bg=LED_BG,
            fg=LED_FG,
            padx=4, pady=2,
            width=digits,
        )
        self._label.pack()

    def set(self, value):
        """Update the displayed number (clamped to fit the digit count)."""
        max_val = 10 ** self._digits - 1
        value = max(0, min(value, max_val))  #0～max
        self._label.config(text=str(value).rjust(self._digits, "0"))


# =============================================================================
# ConnectScreen — enter the server IP and connect
# =============================================================================
class ConnectScreen(tk.Frame):
    """First screen: ask for the server's IP address."""

    def __init__(self, app):
        super().__init__(app, bg=BG)
        self.app = app

        # ── Outer raised panel ─────────────────────────────────────────────
        panel = tk.Frame(self, bg=BG, relief="raised", bd=3)
        panel.pack(padx=30, pady=30)

        tk.Label(
            panel, text="Minesweeper", font=("Arial", 18, "bold"),
            bg=BG, fg="black"
        ).pack(pady=(18, 4))

        tk.Label(
            panel, text="Multiplayer", font=("Arial", 12),
            bg=BG, fg="#444444"
        ).pack(pady=(0, 16))

        # Separator line (classic HR look)
        tk.Frame(panel, bg=BORDER_DARK, height=2).pack(fill="x", padx=10, pady=4)

        tk.Label(
            panel, text="Server IP address:", font=("Arial", 11),
            bg=BG, fg="black"
        ).pack(pady=(10, 2))

        self.ip_var = tk.StringVar(value="localhost")
        entry = tk.Entry(
            panel, textvariable=self.ip_var,
            font=("Arial", 13), width=18, justify="center",
            relief="sunken", bd=2
        )
        entry.pack(pady=6)
        entry.bind("<Return>", lambda e: self._connect())

        tk.Button(
            panel, text="Connect",
            font=("Arial", 11, "bold"),
            bg=BG, fg="black",
            relief="raised", bd=3,
            padx=20, pady=4,
            command=self._connect,
            activebackground="#a0a0a0"
        ).pack(pady=10)

        self.status_label = tk.Label(
            panel, text="", font=("Arial", 10),
            bg=BG, fg="#222222", wraplength=260
        )
        self.status_label.pack(pady=(0, 8))

        tk.Frame(panel, bg=BORDER_DARK, height=2).pack(fill="x", padx=10, pady=4)

        tk.Label(
            panel,
            text="Tip: Host runs server.py first,\nthen connects to 'localhost'.",
            font=("Arial", 9), fg="#555555", bg=BG, justify="center"
        ).pack(pady=(4, 14))

    def _connect(self):
        host = self.ip_var.get().strip()
        if not host:
            return
        self.status_label.config(text="Connecting…")
        self.app.after(50, lambda: self.app.connect(host))


# =============================================================================
# LobbyScreen — mode selection before the game starts
# =============================================================================
class LobbyScreen(tk.Frame):
    """Waiting room shown after connecting — game starts automatically once both players join."""

    def __init__(self, app, mode=None, difficulty=None, local_ip=None):
        super().__init__(app, bg=BG)
        self.app = app

        panel = tk.Frame(self, bg=BG, relief="raised", bd=3)
        panel.pack(padx=30, pady=30)

        tk.Label(
            panel, text="Minesweeper", font=("Arial", 18, "bold"),
            bg=BG, fg="black"
        ).pack(pady=(18, 4))

        tk.Label(
            panel, text="Multiplayer", font=("Arial", 12),
            bg=BG, fg="#444444"
        ).pack(pady=(0, 12))

        tk.Frame(panel, bg=BORDER_DARK, height=2).pack(fill="x", padx=10, pady=4)

        mode_names = {"classic": "Classic (Race)", "coop": "Co-op", "sabotage": "Sabotage"}
        mode_str   = mode_names.get(mode, mode or "—")
        tk.Label(
            panel, text=f"Mode: {mode_str}  |  Difficulty: {difficulty or '—'}",
            font=("Arial", 11, "bold"), bg=BG, fg="black"
        ).pack(pady=(10, 4))

        tk.Label(
            panel, text=f"You are Player {app.player_id}",
            font=("Arial", 11), bg=BG, fg="#333333"
        ).pack(pady=(0, 10))

        # Show LAN IP for the host so they can share it with the other player
        if app.player_id == 1 and local_ip:
            tk.Frame(panel, bg=BORDER_DARK, height=2).pack(fill="x", padx=10, pady=4)
            tk.Label(
                panel, text="Share your IP address with Player 2:",
                font=("Arial", 10), bg=BG, fg="#333333"
            ).pack(pady=(8, 2))
            ip_frame = tk.Frame(panel, bg="#000000", padx=12, pady=6)
            ip_frame.pack(pady=4)
            tk.Label(
                ip_frame, text=local_ip,
                font=("Courier New", 18, "bold"), bg="#000000", fg="#00ff00"
            ).pack()

        tk.Frame(panel, bg=BORDER_DARK, height=2).pack(fill="x", padx=10, pady=8)

        wait_text = (
            "Waiting for Player 2 to join…" if app.player_id == 1
            else "Connected! Game starting soon…"
        )
        tk.Label(
            panel, text=wait_text,
            font=("Arial", 10), bg=BG, fg="#222222"
        ).pack(pady=(0, 14))


# =============================================================================
# GameScreen — the classic Minesweeper window
# =============================================================================
class GameScreen(tk.Frame):
    """
    Looks like the classic Windows Minesweeper:
      • Top bar:    mode label (left)  +  player badge (right)
      • Status bar: [LED mine count]  [😊 face button]  [LED score]
      • Grid:       9×9 raised-relief buttons
      • Footer:     score comparison (both players)
    In Sabotage mode a Sabotage button appears below the status bar.
    """

    def __init__(self, app, mode, initial_state):
        super().__init__(app, bg=BG)
        self.app        = app
        self.mode       = mode
        self.player_id  = app.player_id
        self.buttons     = {}    # {(r, c): tk.Canvas}
        self._cell_states = {}   # {(r, c): state str} — updated each server message
        self.game_over  = False  # disables clicks once the game ends

        # Read board dimensions from the server state so any difficulty works
        self.rows       = initial_state.get("rows",       9)
        self.cols       = initial_state.get("cols",       9)
        self.mine_count = initial_state.get("mines",      10)
        self.difficulty = initial_state.get("difficulty", "Easy")

        self._build_top_bar()
        self._build_status_bar()
        if mode == "sabotage":
            self._build_sabotage_row()
        self._build_grid()
        self._build_footer()

        self.update_state(initial_state)

    # ── Layout builders ───────────────────────────────────────────────────────

    def _build_top_bar(self):
        """Thin bar: mode name on left, difficulty + player badge on right."""
        bar = tk.Frame(self, bg=BG, pady=5)
        bar.pack(fill="x", padx=8)

        mode_text = {
            "classic":  "⚔  Classic Mode",
            "coop":     "🤝  Co-op Mode",
            "sabotage": "💣  Sabotage Mode",
        }.get(self.mode, self.mode)

        tk.Label(bar, text=mode_text, font=("Arial", 10, "bold"),
                 bg=BG, fg="black").pack(side="left")
        tk.Label(bar, text=f"{self.difficulty}  |  Player {self.player_id}",
                 font=("Arial", 10), bg=BG, fg="#333333").pack(side="right")

    def _build_status_bar(self):
        """
        The classic sunken panel with:
          [LED: mines/score left]   [😊 face button]   [LED: my score / timer]
        """
        outer = tk.Frame(self, bg=BG, relief="raised", bd=3)
        outer.pack(fill="x", padx=8, pady=4)

        inner = tk.Frame(outer, bg=BG, relief="sunken", bd=2, padx=6, pady=6)
        inner.pack(fill="x")

        # Left LED — mines remaining (total mines minus flags placed)
        left_frame = tk.Frame(inner, bg=BG)
        left_frame.pack(side="left", padx=8)
        tk.Label(left_frame, text="mines", font=("Arial", 8),
                 bg=BG, fg="#555555").pack()
        self.led_left = LedDisplay(left_frame, digits=3)
        self.led_left.pack()

        # Centre — smiley face button (returns to lobby after game ends)
        self.face_btn = tk.Button(
            inner,
            text=FACE_IDLE,
            font=("Arial", 18),
            bg=BG, relief="raised", bd=3,
            padx=4, pady=2,
            activebackground="#a0a0a0",
            command=self._on_face_click,
        )
        self.face_btn.pack(side="left", expand=True)

        # Right LED — this player's score (safe cells revealed)
        right_frame = tk.Frame(inner, bg=BG)
        right_frame.pack(side="right", padx=8)
        tk.Label(right_frame, text="score", font=("Arial", 8),
                 bg=BG, fg="#555555").pack()
        self.led_right = LedDisplay(right_frame, digits=3)
        self.led_right.pack()

    def _build_sabotage_row(self):
        """Sabotage-only: a row with the sabotage button and charge counter."""
        row = tk.Frame(self, bg=BG, pady=4)
        row.pack(fill="x", padx=8)

        self.sabotage_btn = tk.Button(
            row,
            text="💣  Sabotage!  (3 left)",
            font=("Arial", 11, "bold"),
            bg=BG, fg="black",
            relief="raised", bd=3,
            padx=12, pady=4,
            activebackground="#a0a0a0",
            command=self._on_sabotage,
        )
        self.sabotage_btn.pack(side="left", padx=6)

        tk.Label(
            row,
            text="Plants a fake flag on a random\nhidden cell of the opponent.",
            font=("Arial", 9), bg=BG, fg="#555555", justify="left"
        ).pack(side="left", padx=8)

    def _build_grid(self):
        """Grid of square Canvas cells with hand-drawn Windows-style bevels."""
        outer = tk.Frame(self, bg=BG, relief="raised", bd=3)
        outer.pack(padx=8, pady=4)

        inner = tk.Frame(outer, bg="#808080", relief="sunken", bd=3)
        inner.pack()

        # Choose cell size and font by difficulty
        if self.cols <= 9:        # Easy   9×9
            self._cell_px, fs = 36, 20
        elif self.cols <= 16:     # Medium 16×16
            self._cell_px, fs = 30, 18
        else:                     # Expert 16×30
            self._cell_px, fs = 30, 18
        self._cell_font = ("Arial", fs, "bold")

        for r in range(self.rows):
            for c in range(self.cols):
                cv = tk.Canvas(
                    inner,
                    width=self._cell_px, height=self._cell_px,
                    highlightthickness=0,   # no focus ring between cells
                    cursor="arrow",
                )
                cv.grid(row=r, column=c, padx=0, pady=0)
                draw_raised_cell(cv, self._cell_px, font=self._cell_font)

                cv.bind("<Button-1>",
                        lambda e, row=r, col=c: self._on_left_click(row, col))
                cv.bind("<Button-2>",
                        lambda e, row=r, col=c: self._on_right_click(row, col))
                cv.bind("<Button-3>",
                        lambda e, row=r, col=c: self._on_right_click(row, col))

                self.buttons[(r, c)] = cv

    def _build_footer(self):
        """Small row below the grid showing both players' scores side by side."""
        outer = tk.Frame(self, bg=BG, relief="raised", bd=3)
        outer.pack(fill="x", padx=8, pady=(0, 8))

        inner = tk.Frame(outer, bg=BG, relief="sunken", bd=2, pady=4)
        inner.pack(fill="x")

        self.footer_label = tk.Label(
            inner,
            text="Player 1: 0  |  Player 2: 0",
            font=("Arial", 10),
            bg=BG, fg="black"
        )
        self.footer_label.pack()

        # Co-op / Sabotage extra info line
        self.info_label = tk.Label(
            inner, text="", font=("Arial", 9), bg=BG, fg="#555555"
        )
        self.info_label.pack()

    # ── Click handlers ────────────────────────────────────────────────────────

    def _on_left_click(self, r, c):
        if self.game_over:
            return
        if self.mode == "coop" and self.player_id == 2:
            self._flash_info("You can only place flags (right-click).")
            return
        # Flagged cells are protected — left-click cannot open them
        if self._cell_states.get((r, c)) == "flagged":
            return
        self.app.net.send({"type": "move", "r": r, "c": c})

    def _on_right_click(self, r, c):
        if self.game_over:
            return
        if self.mode == "coop" and self.player_id == 1:
            self._flash_info("You can only reveal cells (left-click).")
            return
        self.app.net.send({"type": "flag", "r": r, "c": c})

    def _on_sabotage(self):
        if self.game_over:
            return
        self.app.net.send({"type": "sabotage"})

    def _on_face_click(self):
        """Clicking the smiley face returns to the main menu after game over."""
        if self.game_over:
            self.app.show_connect_screen()

    def _flash_info(self, text):
        """Temporarily show a hint in the info label."""
        self.info_label.config(text=f"⚠  {text}", fg="#cc0000")
        self.after(2200, lambda: self.info_label.config(text="", fg="#555555"))

    # ── State rendering ───────────────────────────────────────────────────────

    def update_state(self, msg):
        """Re-render the board from a server state message."""
        board      = msg.get("board", [])
        scores     = msg.get("scores", {"1": 0, "2": 0})
        sab_left   = msg.get("sabotage_left", {"1": 3, "2": 3})
        # Keep mine_count in sync in case it wasn't in the initial state
        self.mine_count = msg.get("mines", self.mine_count)

        p1 = scores.get("1", 0)
        p2 = scores.get("2", 0)
        my_score = p1 if self.player_id == 1 else p2

        # Update LED displays
        # Left LED: mines remaining = total mines minus flags placed on board
        flag_count = sum(
            1 for row in board for cell in row if cell.get("state") == "flagged"
        )
        self.led_left.set(max(0, self.mine_count - flag_count))
        self.led_right.set(my_score)

        # Footer score line
        self.footer_label.config(text=f"Player 1: {p1}  |  Player 2: {p2}")

        # Sabotage button
        if self.mode == "sabotage" and hasattr(self, "sabotage_btn"):
            my_sab = sab_left.get(str(self.player_id), 0)
            self.sabotage_btn.config(
                text=f"💣  Sabotage!  ({my_sab} left)",
                state="normal" if my_sab > 0 and not self.game_over else "disabled"
            )
            opp_count = msg.get("opponent_revealed_count", 0)
            self.info_label.config(
                text=f"Opponent has revealed {opp_count} safe cell(s).",
                fg="#555555"
            )

        # Classic race — show each player's progress toward clearing their own board
        if self.mode == "classic":
            opp_count  = msg.get("opponent_revealed_count", 0)
            total_safe = self.rows * self.cols - self.mine_count
            self.info_label.config(
                text=f"You: {my_score} / {total_safe} cells  |  Opponent: {opp_count} / {total_safe} cells",
                fg="#555555"
            )

        # Render every cell and cache their states for click guards
        for r in range(self.rows):
            for c in range(self.cols):
                if r < len(board) and c < len(board[r]):
                    self._cell_states[(r, c)] = board[r][c].get("state", "hidden")
                    self._render_cell(r, c, board[r][c])

    def _render_cell(self, r, c, cell):
        """
        Redraw one Canvas cell to match the server-reported state.

        hidden   → raised bevel (white top-left, gray bottom-right)
        revealed → flat sunken, shows the neighbour-mine count
        flagged  → raised bevel with a flag emoji
        mine     → flat red with a mine emoji (only shown at game over)
        """
        cv    = self.buttons[(r, c)]
        state = cell.get("state")
        value = cell.get("value", 0)

        if state == "hidden":
            draw_raised_cell(cv, self._cell_px, font=self._cell_font)

        elif state == "revealed":
            text  = str(value) if value > 0 else ""
            color = NUMBER_COLORS.get(value, "black")
            draw_sunken_cell(cv, self._cell_px,
                             text=text, text_color=color,
                             font=self._cell_font)

        elif state == "flagged":
            draw_raised_cell(cv, self._cell_px,
                             text="🚩", font=self._cell_font)

        elif state == "mine":
            draw_sunken_cell(cv, self._cell_px,
                             text="💣", bg="#ff4444",
                             font=self._cell_font)

    def show_game_over(self, msg):
        """
        Called when the server declares the game over.
        Shows the full board (mines revealed), changes the smiley face,
        and pops up a result dialog.
        """
        self.game_over = True
        self.update_state(msg)  # renders the revealed board

        winner = msg.get("winner")
        reason = msg.get("reason", "")
        message = msg.get("message", "Game over!")
        scores  = msg.get("final_scores", {"1": 0, "2": 0})

        # Change the face emoji to reflect the outcome
        if winner == self.player_id:
            self.face_btn.config(text=FACE_WIN)
            title = "You Win!"
        elif winner is None and reason == "complete":
            self.face_btn.config(text=FACE_WIN)
            title = "Both Players Win!"
        elif winner == "draw":
            self.face_btn.config(text=FACE_IDLE)
            title = "It's a Draw!"
        elif reason == "disconnect":
            self.face_btn.config(text=FACE_IDLE)
            title = "Opponent Disconnected"
        else:
            self.face_btn.config(text=FACE_LOSE)
            title = "You Lose"

        detail = (
            f"{message}\n\n"
            f"Final scores:\n"
            f"  Player 1: {scores.get('1', 0)}\n"
            f"  Player 2: {scores.get('2', 0)}\n\n"
            f"Click the smiley face or press Yes\nto return to the main menu."
        )

        if messagebox.askyesno(title, detail, parent=self.app):
            self.app.show_connect_screen()


# =============================================================================
# App — the main Tkinter window
# =============================================================================
class App(tk.Tk):
    """
    Root window. Manages screen transitions and routes server messages
    to whichever screen is currently visible.
    """

    def __init__(self):
        super().__init__()
        self.title("Minesweeper")
        self.resizable(False, False)
        self.configure(bg=BG)

        self.player_id         = None
        self.net               = None
        self.current_screen    = None
        self._lobby_mode       = None
        self._lobby_difficulty = None
        self._lobby_local_ip   = None

        self.show_connect_screen()

    def show_connect_screen(self):
        self._switch_screen(ConnectScreen(self))

    def show_lobby_screen(self):
        self._switch_screen(LobbyScreen(
            self,
            mode=self._lobby_mode,
            difficulty=self._lobby_difficulty,
            local_ip=self._lobby_local_ip,
        ))

    def show_game_screen(self, mode, initial_state):
        self._switch_screen(GameScreen(self, mode, initial_state))

    def _switch_screen(self, new_screen):
        if self.current_screen:
            self.current_screen.destroy()
        self.current_screen = new_screen
        new_screen.pack(fill="both", expand=True)

    def connect(self, host):
        """Create the NetworkClient and attempt to connect."""
        self.net = NetworkClient(host, PORT, self._on_message_thread_safe)
        if self.net.connect():
            self.net.start_receive_loop()
            if hasattr(self.current_screen, "status_label"):
                self.current_screen.status_label.config(
                    text="Connected! Waiting for server…"
                )
        else:
            if hasattr(self.current_screen, "status_label"):
                self.current_screen.status_label.config(
                    text="Could not connect. Is server.py running?"
                )

    def _on_message_thread_safe(self, msg):
        """
        NetworkClient runs in a background thread.
        Tkinter widgets must only be updated from the main thread.
        self.after(0, ...) safely hands the call to the main thread.
        """
        self.after(0, lambda: self._on_message(msg))

    def _on_message(self, msg):
        """Dispatch an incoming server message to the right handler."""
        msg_type = msg.get("type")

        if msg_type == "welcome":
            self.player_id         = msg["player_id"]
            self._lobby_mode       = msg.get("mode")
            self._lobby_difficulty = msg.get("difficulty")
            self._lobby_local_ip   = msg.get("local_ip")
            self.show_lobby_screen()

        elif msg_type == "state":
            if isinstance(self.current_screen, LobbyScreen):
                # First state received means the game just started
                self.show_game_screen(msg.get("mode", "classic"), msg)
            elif isinstance(self.current_screen, GameScreen):
                self.current_screen.update_state(msg)

        elif msg_type == "game_over":
            if isinstance(self.current_screen, GameScreen):
                self.current_screen.show_game_over(msg)
            else:
                # Game ended before we reached the game screen (e.g. disconnect in lobby)
                messagebox.showinfo(
                    "Game Over",
                    msg.get("message", "Game over."),
                    parent=self
                )

        elif msg_type == "disconnect":
            messagebox.showerror(
                "Connection Lost",
                "Lost connection to the server.",
                parent=self
            )
            self.show_connect_screen()


# =============================================================================
# Entry point
# =============================================================================
if __name__ == "__main__":
    import sys as _sys

    app = App()

    # If launched from main.py with "--host <ip>", skip the connect screen
    # and auto-connect to that address after the window is ready.
    if "--host" in _sys.argv:
        idx = _sys.argv.index("--host")
        if idx + 1 < len(_sys.argv):
            _host = _sys.argv[idx + 1]
            app.after(300, lambda: app.connect(_host))

    app.mainloop()
# References
#Anthropic. (2026). Claude (May 26 version) [Large language model].
#https://claude.ai/