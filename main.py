# =============================================================================
# main.py — Minesweeper Launcher
# =============================================================================
# This is the starting point. Run:
#   python3 main.py
#
# It shows a classic Windows-style menu where the player chooses:
#   • Mode:       Single Player  /  Host Game  /  Join Game
#   • Difficulty: Easy  /  Medium  /  Expert
#
# Difficulty settings match the original Windows Minesweeper:
#   Easy   —  9 × 9,  10 mines
#   Medium — 16 ×16,  40 mines
#   Expert — 16 ×30,  99 mines
#
# How multiplayer works:
#   Host Game → starts server.py as a background process, then opens
#               client.py in its own window connected to localhost.
#   Join Game → opens client.py connected to the host's IP address.
#   (Each multiplayer window is a separate process, which is the correct
#    way to do LAN networking — every player runs their own client.)
# =============================================================================

# Line 1-611 Generated with Claude, prompt: "Build a simple Python LAN multiplayer Minesweeper project for a school presentation.
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
from tkinter import messagebox, simpledialog
import threading
import subprocess
import sys
import os
import time

# ─── Import game logic (Board class) from server.py ───────────────────────────
from server import Board, DIFFICULTIES

# ─── Re-use widgets and the canvas cell-draw helpers from client.py ────────────
from client import LedDisplay, draw_raised_cell, draw_sunken_cell

# ─── Directory where server.py and client.py live ─────────────────────────────
_DIR = os.path.dirname(os.path.abspath(__file__))

# ─── Visual constants (classic Windows Minesweeper palette) ───────────────────
BG          = "#c0c0c0"
BORDER_DARK = "#808080"


# =============================================================================
# LauncherWindow — the main menu (the one tk.Tk root for the whole process)
# =============================================================================
class LauncherWindow(tk.Tk):
    """
    The very first window the user sees.
    Pick a difficulty and a mode, then launch the game.

    Important: this is the ONLY tk.Tk() in the whole program.
    The single-player game opens as a tk.Toplevel child of this window.
    Multiplayer games run as separate Python processes.
    """

    def __init__(self):
        super().__init__()
        self.title("Minesweeper")
        self.resizable(False, False)
        self.configure(bg=BG)

        # Tracks the chosen difficulty ("Easy" / "Medium" / "Expert")
        self.difficulty_var = tk.StringVar(value="Easy")

        self._build_title()
        self._build_difficulty_panel()
        self._build_mode_panel()
        self._build_footer()

    # ── Layout ────────────────────────────────────────────────────────────────

    def _build_title(self):
        outer = tk.Frame(self, bg=BG, relief="raised", bd=3)
        outer.pack(fill="x", padx=8, pady=(10, 4))

        inner = tk.Frame(outer, bg=BG, relief="sunken", bd=2, pady=10)
        inner.pack(fill="x")

        tk.Label(inner, text="💣  Minesweeper",
                 font=("Arial", 20, "bold"), bg=BG, fg="black").pack()
        tk.Label(inner, text="LAN Multiplayer Edition",
                 font=("Arial", 10), bg=BG, fg="#444444").pack()

    def _build_difficulty_panel(self):
        """
        Radio buttons for Easy / Medium / Expert, with the same grid-size
        details shown in the original Windows Minesweeper dialog.
        """
        outer = tk.Frame(self, bg=BG, relief="raised", bd=3)
        outer.pack(fill="x", padx=8, pady=4)

        inner = tk.Frame(outer, bg=BG, relief="sunken", bd=2, padx=12, pady=8)
        inner.pack(fill="x")

        tk.Label(inner, text="Difficulty", font=("Arial", 11, "bold"),
                 bg=BG, fg="black").pack(anchor="w", pady=(0, 6))

        options = [
            ("Easy",   " 9 × 9,   10 mines"),
            ("Medium", "16 × 16,  40 mines"),
            ("Expert", "16 × 30,  99 mines"),
        ]
        for name, detail in options:
            row = tk.Frame(inner, bg=BG)
            row.pack(fill="x", pady=2)

            tk.Radiobutton(
                row,
                text=name,
                variable=self.difficulty_var,
                value=name,
                font=("Arial", 11),
                bg=BG, fg="black",
                activebackground=BG,
                selectcolor=BG,
                width=8, anchor="w",
            ).pack(side="left")

            tk.Label(row, text=detail, font=("Arial", 9),
                     bg=BG, fg="#555555").pack(side="left", padx=6)

    def _build_mode_panel(self):
        """
        Three buttons: Single Player, Host Game, Join Game.
        """
        outer = tk.Frame(self, bg=BG, relief="raised", bd=3)
        outer.pack(fill="x", padx=8, pady=4)

        inner = tk.Frame(outer, bg=BG, relief="sunken", bd=2, padx=12, pady=10)
        inner.pack(fill="x")

        tk.Label(inner, text="Game Mode", font=("Arial", 11, "bold"),
                 bg=BG, fg="black").pack(anchor="w", pady=(0, 8))

        modes = [
            ("Single Player",
             "Play alone against the board.",
             self._launch_single),
            ("Host Game",
             "Start a server and wait for a friend to join.\n"
             "Share your IP address with them.",
             self._launch_host),
            ("Join Game",
             "Connect to a friend's hosted game.\n"
             "You will need their IP address.",
             self._launch_join),
        ]
        for label, desc, cmd in modes:
            row = tk.Frame(inner, bg=BG, pady=3)
            row.pack(fill="x")

            tk.Button(
                row, text=label,
                font=("Arial", 11, "bold"),
                bg=BG, fg="black",
                relief="raised", bd=3,
                width=14, pady=4,
                activebackground="#a0a0a0",
                command=cmd,
            ).pack(side="left")

            tk.Label(row, text=desc, font=("Arial", 9), bg=BG,
                     fg="#555555", wraplength=220, justify="left",
                     ).pack(side="left", padx=10)

    def _build_footer(self):
        tk.Label(
            self,
            text="Tip: The host runs 'Host Game'. The guest runs 'Join Game'.",
            font=("Arial", 8), bg=BG, fg="#777777", wraplength=320,
        ).pack(pady=(4, 10))

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _get_config(self):
        """Return (difficulty_name, config_dict) for the selected difficulty."""
        name = self.difficulty_var.get()
        cfg  = dict(DIFFICULTIES[name])
        cfg["difficulty"] = name
        return name, cfg

    def _watch_process(self, proc, on_done):
        """
        Wait for a subprocess to finish in a background thread,
        then call on_done() safely on the Tk main thread.
        """
        def _run():
            proc.wait()
            self.after(0, on_done)
        threading.Thread(target=_run, daemon=True).start()

    # ── Launch actions ────────────────────────────────────────────────────────

    def _launch_single(self):
        """
        Open a self-contained single-player game window.
        It's a tk.Toplevel child of this window — same event loop,
        no extra processes needed.
        """
        _, cfg = self._get_config()
        self.withdraw()                          # hide the launcher
        SinglePlayerWindow(self, cfg,
                           on_close=self.deiconify)   # show it again on close

    def _launch_host(self):
        """
        Start server.py as a background process (with chosen difficulty),
        then launch client.py in its own window auto-connected to localhost.
        When the client closes, the server is also stopped.
        """
        name, _ = self._get_config()
        self.iconify()   # minimize launcher (it stays alive)

        # Start the game server ──────────────────────────────────────────────
        server_proc = subprocess.Popen(
            [sys.executable,
             os.path.join(_DIR, "server.py"),
             "--difficulty", name],
        )

        # Give the server half a second to bind the socket before connecting
        time.sleep(0.4)

        # Start the client and auto-connect to localhost ──────────────────────
        client_proc = subprocess.Popen(
            [sys.executable,
             os.path.join(_DIR, "client.py"),
             "--host", "localhost"],
        )

        # When the client window closes → stop server, restore launcher
        def on_client_exit():
            server_proc.terminate()
            self.deiconify()

        self._watch_process(client_proc, on_client_exit)

    def _launch_join(self):
        """
        Ask for the host's IP, then launch client.py auto-connected to it.
        """
        host = simpledialog.askstring(
            "Join Game",
            "Enter the host's IP address:",
            initialvalue="",
            parent=self,
        )
        if not host or not host.strip():
            return

        self.iconify()

        client_proc = subprocess.Popen(
            [sys.executable,
             os.path.join(_DIR, "client.py"),
             "--host", host.strip()],
        )

        self._watch_process(client_proc, self.deiconify)


# =============================================================================
# SinglePlayerWindow — standalone Minesweeper, no networking
# =============================================================================
class SinglePlayerWindow(tk.Toplevel):
    """
    A fully self-contained single-player Minesweeper game.

    This is a tk.Toplevel child of LauncherWindow — it shares the same
    Tkinter event loop, so no extra mainloop() call is needed.

    Uses Board from server.py for all game logic (mine generation, flood fill,
    flag toggling) but handles everything locally without any network code.
    """

    # Classic Minesweeper number colors
    _NUMBER_COLORS = {
        1: "#0000ff", 2: "#007b00", 3: "#ff0000", 4: "#00007b",
        5: "#7b0000", 6: "#007b7b", 7: "#000000", 8: "#7b7b7b",
    }

    def __init__(self, master, config, on_close=None):
        # master = LauncherWindow (the tk.Tk root)
        super().__init__(master)

        self.title("Minesweeper")
        self.resizable(False, False)
        self.configure(bg=BG)
        self.on_close = on_close

        # Game config
        self.rows     = config["rows"]
        self.cols     = config["cols"]
        self.mines    = config["mines"]
        self.diff     = config.get("difficulty", "Easy")

        # Game state
        self.board     = Board(self.rows, self.cols, self.mines)
        self.buttons   = {}    # {(r, c): tk.Canvas}
        self.game_over = False
        # Show the "click emoji to replay" hint only once per window open
        self._hint_shown = False

        # Timer state
        self._elapsed       = 0
        self._timer_running = False

        self._build_ui()
        self._reset_timer()

        # Intercept the window close button
        self.protocol("WM_DELETE_WINDOW", self._close)

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self):
        # ── Info strip ────────────────────────────────────────────────────
        info = tk.Frame(self, bg=BG, pady=4)
        info.pack(fill="x", padx=8)
        tk.Label(info, text=f"Single Player  —  {self.diff}",
                 font=("Arial", 10, "bold"), bg=BG, fg="black").pack(side="left")

        # ── Classic status bar: [mine LED] [face btn] [timer LED] ─────────
        outer = tk.Frame(self, bg=BG, relief="raised", bd=3)
        outer.pack(fill="x", padx=8, pady=4)
        inner = tk.Frame(outer, bg=BG, relief="sunken", bd=2, padx=6, pady=6)
        inner.pack(fill="x")

        # Left LED — mines remaining
        lf = tk.Frame(inner, bg=BG)
        lf.pack(side="left", padx=8)
        tk.Label(lf, text="mines", font=("Arial", 8), bg=BG, fg="#555555").pack()
        self.led_mines = LedDisplay(lf, digits=3)
        self.led_mines.set(self.mines)
        self.led_mines.pack()

        # Centre — smiley face / reset button
        self.face_btn = tk.Button(
            inner, text="🙂", font=("Arial", 18),
            bg=BG, relief="raised", bd=3, padx=4, pady=2,
            activebackground="#a0a0a0",
            command=self._reset,
        )
        self.face_btn.pack(side="left", expand=True)

        # Right LED — elapsed seconds
        rf = tk.Frame(inner, bg=BG)
        rf.pack(side="right", padx=8)
        tk.Label(rf, text="time", font=("Arial", 8), bg=BG, fg="#555555").pack()
        self.led_timer = LedDisplay(rf, digits=3)
        self.led_timer.pack()

        # ── Grid ──────────────────────────────────────────────────────────
        g_outer = tk.Frame(self, bg=BG, relief="raised", bd=3)
        g_outer.pack(padx=8, pady=4)
        g_inner = tk.Frame(g_outer, bg="#808080", relief="sunken", bd=3)
        g_inner.pack()

        # Cell pixel size and font by difficulty
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
                    g_inner,
                    width=self._cell_px, height=self._cell_px,
                    highlightthickness=0,
                    cursor="arrow",
                )
                cv.grid(row=r, column=c, padx=0, pady=0)
                draw_raised_cell(cv, self._cell_px, font=self._cell_font)

                # Left-click → reveal;  right-click → flag
                cv.bind("<Button-1>",
                        lambda e, rr=r, cc=c: self._left_click(rr, cc))
                cv.bind("<Button-2>",
                        lambda e, rr=r, cc=c: self._right_click(rr, cc))
                cv.bind("<Button-3>",
                        lambda e, rr=r, cc=c: self._right_click(rr, cc))

                self.buttons[(r, c)] = cv

    # ── Timer ─────────────────────────────────────────────────────────────────

    def _reset_timer(self):
        self._elapsed       = 0
        self._timer_running = True
        self._tick()

    def _tick(self):
        """Tkinter after()-based timer — increments every second."""
        if self._timer_running:
            self.led_timer.set(self._elapsed)
            self._elapsed = min(self._elapsed + 1, 999)
            self.after(1000, self._tick)

    def _stop_timer(self):
        self._timer_running = False

    # ── Click handlers ────────────────────────────────────────────────────────

    def _left_click(self, r, c):
        if self.game_over:
            return
        # Flagged cells are protected — left-click does nothing on them
        if (r, c) in self.board.flagged:
            return
        # Start the timer only after the first real click
        result = self.board.reveal(r, c)
        self._refresh_board()
        if result == "mine":
            self._lose()
        elif result == "ok" and self.board.is_complete():
            self._win()

    def _right_click(self, r, c):
        if self.game_over:
            return
        self.board.toggle_flag(r, c)
        self._refresh_board()

    # ── Board rendering ───────────────────────────────────────────────────────

    def _refresh_board(self, reveal_all=False):
        """Redraw every cell and sync the mine LED."""
        flag_count = len(self.board.flagged) + len(self.board.wrong_flags)
        self.led_mines.set(max(0, self.mines - flag_count))

        for r in range(self.rows):
            for c in range(self.cols):
                self._render_cell(r, c, reveal_all)

    def _render_cell(self, r, c, reveal_all=False):
        cv = self.buttons[(r, c)]

        if (r, c) in self.board.revealed:
            val   = self.board.adjacency.get((r, c), 0)
            text  = str(val) if val > 0 else ""
            color = self._NUMBER_COLORS.get(val, "black")
            draw_sunken_cell(cv, self._cell_px,
                             text=text, text_color=color,
                             font=self._cell_font)

        elif reveal_all and (r, c) in self.board.mines:
            draw_sunken_cell(cv, self._cell_px,
                             text="💣", bg="#ff4444",
                             font=self._cell_font)

        elif (r, c) in self.board.flagged:
            draw_raised_cell(cv, self._cell_px,
                             text="🚩", font=self._cell_font)

        else:
            draw_raised_cell(cv, self._cell_px, font=self._cell_font)

    # ── Win / loss / reset ────────────────────────────────────────────────────

    def _win(self):
        self.game_over = True
        self._stop_timer()
        self.face_btn.config(text="😎")
        if not self._hint_shown:
            self._hint_shown = True
            messagebox.showinfo(
                "You Win! 🎉",
                f"Congratulations! Board cleared in {self._elapsed} seconds.\n\n"
                "Click the smiley face to play again.",
                parent=self,
            )

    def _lose(self):
        self.game_over = True
        self._stop_timer()
        self.face_btn.config(text="😵")
        self._refresh_board(reveal_all=True)   # show all mine positions
        if not self._hint_shown:
            self._hint_shown = True
            messagebox.showinfo(
                "Game Over 💥",
                "You hit a mine!\n\nClick the smiley face to play again.",
                parent=self,
            )

    def _reset(self):
        """Start a brand-new game with the same difficulty."""
        self._stop_timer()
        self.game_over = False
        self.board     = Board(self.rows, self.cols, self.mines)
        self.face_btn.config(text="🙂")
        self._refresh_board()
        self.led_mines.set(self.mines)
        self._reset_timer()

    def _close(self):
        """User clicked the window's × button."""
        self._stop_timer()
        self.destroy()
        if self.on_close:
            self.on_close()   # show the launcher again


# =============================================================================
# Entry point
# =============================================================================
if __name__ == "__main__":
    launcher = LauncherWindow()
    launcher.mainloop()

# References
#Anthropic. (2026). Claude (May 26 version) [Large language model].
#https://claude.ai/