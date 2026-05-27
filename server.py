# =============================================================================
# server.py — Minesweeper LAN Multiplayer Server
# =============================================================================
# Run this file on the "host" computer, OR let main.py start it automatically
# when the player picks "Host Game".
#
# Usage (manual):
#   python3 server.py
#   python3 server.py --difficulty Medium
# =============================================================================
# Line 1-687 Generated with Claude, prompt: "Build a simple Python LAN multiplayer Minesweeper project for a school presentation.
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
import socket
import threading
import json
import random
import sys
from collections import deque

# ─── Server network settings ──────────────────────────────────────────────────
HOST = ""        # "" = listen on all network interfaces
PORT = 5555

# ─── Difficulty presets (same as classic Windows Minesweeper) ─────────────────
DIFFICULTIES = {
    "Easy":   {"rows": 9,  "cols": 9,  "mines": 10},
    "Medium": {"rows": 16, "cols": 16, "mines": 40},
    "Expert": {"rows": 16, "cols": 30, "mines": 99},
}


# =============================================================================
# Board — one Minesweeper grid (size and mine count are configurable)
# =============================================================================
class Board:
    """
    Stores everything about a single Minesweeper board.
    rows, cols, and mine_count come from the difficulty setting.

    In Classic and Co-op modes, one Board is shared between both players.
    In Sabotage mode, each player gets their own Board.
    """

    def __init__(self, rows=9, cols=9, mines=10):
        self.rows       = rows
        self.cols       = cols
        self.mine_count = mines

        self.mines      = set()   # (r, c) positions that contain mines
        self.revealed   = set()   # cells the player has opened
        self.flagged    = set()   # cells with a flag on them
        self.wrong_flags = set()  # sabotage-placed fake flags
        self.adjacency  = {}      # (r, c) → number of neighboring mines (0–8)
        self.generated  = False   # mines placed lazily on first click

    # ── Mine generation ───────────────────────────────────────────────────────

    def generate(self, safe_cell):
        """
        Place mines randomly, but guarantee that safe_cell and all its
        neighbors are mine-free. This prevents losing on the very first click.
        """
        sr, sc = safe_cell
        safe_zone = set()
        for dr in range(-1, 2):
            for dc in range(-1, 2):
                nr, nc = sr + dr, sc + dc
                if 0 <= nr < self.rows and 0 <= nc < self.cols:
                    safe_zone.add((nr, nc))

        eligible = [
            (r, c) for r in range(self.rows) for c in range(self.cols)
            if (r, c) not in safe_zone
        ]
        self.mines = set(random.sample(eligible, self.mine_count))
        self._precompute_adjacency()
        self.generated = True

    def _precompute_adjacency(self):
        """Count neighboring mines for every cell (done once after generation)."""
        for r in range(self.rows):
            for c in range(self.cols):
                count = sum(
                    1
                    for dr in range(-1, 2)
                    for dc in range(-1, 2)
                    if not (dr == 0 and dc == 0)
                    and 0 <= r + dr < self.rows
                    and 0 <= c + dc < self.cols
                    and (r + dr, c + dc) in self.mines
                )
                self.adjacency[(r, c)] = count

    # ── Cell actions ──────────────────────────────────────────────────────────

    def reveal(self, r, c):
        """
        Reveal cell (r, c).
        Returns "mine", "already_revealed", or "ok".
        Zero-neighbor cells trigger flood fill automatically.
        """
        if not self.generated:
            self.generate((r, c))

        if (r, c) in self.revealed:
            return "already_revealed"
        if (r, c) in self.mines:
            return "mine"

        self.revealed.add((r, c))
        if self.adjacency[(r, c)] == 0:
            self._flood_fill(r, c)
        return "ok"

    def _flood_fill(self, start_r, start_c):
        """
        BFS: automatically reveal all connected empty cells and their
        numbered borders. This is the standard Minesweeper auto-open behavior.
        """
        queue   = deque([(start_r, start_c)])
        visited = {(start_r, start_c)}

        while queue:
            r, c = queue.popleft()
            for dr in range(-1, 2):
                for dc in range(-1, 2):
                    if dr == 0 and dc == 0:
                        continue
                    nr, nc = r + dr, c + dc
                    if not (0 <= nr < self.rows and 0 <= nc < self.cols):
                        continue
                    if (nr, nc) in visited or (nr, nc) in self.revealed:
                        continue
                    if (nr, nc) in self.mines:
                        continue
                    visited.add((nr, nc))
                    self.revealed.add((nr, nc))
                    if self.adjacency[(nr, nc)] == 0:
                        queue.append((nr, nc))

    def toggle_flag(self, r, c):
        """
        Toggle a flag on an unrevealed cell.
        Returns "flagged", "unflagged", or "invalid".
        Also handles removing sabotage (wrong) flags.
        """
        if (r, c) in self.revealed:
            return "invalid"

        # Removing a sabotage flag works like a normal unflag
        if (r, c) in self.wrong_flags:
            self.wrong_flags.discard((r, c))
            return "unflagged"

        if (r, c) in self.flagged:
            self.flagged.discard((r, c))
            return "unflagged"
        else:
            self.flagged.add((r, c))
            return "flagged"

    def place_wrong_flag(self):
        """
        Sabotage: plant a fake flag on a random hidden, unflagged cell.
        Returns the chosen (r, c), or None if no valid target exists.
        """
        candidates = [
            (r, c)
            for r in range(self.rows) for c in range(self.cols)
            if (r, c) not in self.revealed
            and (r, c) not in self.flagged
            and (r, c) not in self.wrong_flags
        ]
        if not candidates:
            return None
        chosen = random.choice(candidates)
        self.wrong_flags.add(chosen)
        return chosen

    # ── Queries ───────────────────────────────────────────────────────────────

    def count_safe_revealed(self):
        return len(self.revealed)

    def total_safe_cells(self):
        return self.rows * self.cols - self.mine_count

    def is_complete(self):
        return self.count_safe_revealed() >= self.total_safe_cells()

    # ── Serialization ─────────────────────────────────────────────────────────

    def to_client_view(self, reveal_all=False):
        """
        Return a 2-D list of cell dicts for JSON transmission.
        reveal_all=True shows all mine positions (used at game over).
        """
        return [
            [self._describe_cell(r, c, reveal_all) for c in range(self.cols)]
            for r in range(self.rows)
        ]

    def _describe_cell(self, r, c, reveal_all):
        if (r, c) in self.revealed:
            return {"state": "revealed", "value": self.adjacency.get((r, c), 0)}
        if reveal_all and (r, c) in self.mines:
            return {"state": "mine"}
        if (r, c) in self.flagged or (r, c) in self.wrong_flags:
            return {"state": "flagged"}
        return {"state": "hidden"}


# =============================================================================
# GameState — mode-specific game logic (Classic, Co-op, Sabotage)
# =============================================================================
class GameState:
    """
    Manages the rules for whichever game mode is selected.
    The board size comes from the difficulty config chosen by the host.
    """

    def __init__(self, mode, config):
        self.mode   = mode
        self.config = config   # {"rows", "cols", "mines", "difficulty"}
        self.scores = {1: 0, 2: 0}
        self.sabotage_left = {1: 3, 2: 3}
        self.active = True

        rows  = config["rows"]
        cols  = config["cols"]
        mines = config["mines"]

        if mode in ("sabotage", "classic"):
            self.boards = {1: Board(rows, cols, mines), 2: Board(rows, cols, mines)}
            self.board  = None
        else:  # coop
            self.board  = Board(rows, cols, mines)
            self.boards = None

    # ── Action handlers ───────────────────────────────────────────────────────

    def handle_move(self, player_id, r, c):
        if not self.active:
            return {"result": "invalid", "game_over": False}

        if self.mode == "coop":
            if player_id != 1:
                return {"result": "invalid", "game_over": False}
            result = self.board.reveal(r, c)
        else:  # classic or sabotage — each player has their own board
            result = self.boards[player_id].reveal(r, c)

        if result == "already_revealed":
            return {"result": "already_revealed", "game_over": False}
        if result == "mine":
            return self._resolve_loss(player_id)

        # Award points for newly revealed safe cells
        if self.mode in ("sabotage", "classic"):
            self.scores[player_id] = self.boards[player_id].count_safe_revealed()
        else:  # coop
            total_now  = self.board.count_safe_revealed()
            prev_total = self.scores[1] + self.scores[2]
            self.scores[1] += total_now - prev_total

        completion = self._check_completion(player_id)
        if completion:
            self.active = False
            return {"result": "ok", **completion}

        return {"result": "ok", "game_over": False}

    def handle_flag(self, player_id, r, c):
        if not self.active:
            return {"result": "invalid"}

        if self.mode == "coop":
            if player_id != 2:
                return {"result": "invalid"}
            return {"result": self.board.toggle_flag(r, c)}
        else:  # classic or sabotage — flag own board
            return {"result": self.boards[player_id].toggle_flag(r, c)}

    def handle_sabotage(self, player_id):
        if not self.active or self.mode != "sabotage":
            return {"result": "invalid_mode"}
        if self.sabotage_left[player_id] <= 0:
            return {"result": "no_charges"}

        opponent = 3 - player_id
        cell = self.boards[opponent].place_wrong_flag()
        if cell is None:
            return {"result": "no_target"}

        self.sabotage_left[player_id] -= 1
        return {"result": "ok", "cell": cell}

    # ── Win / loss ────────────────────────────────────────────────────────────

    def _resolve_loss(self, loser_id):
        self.active = False
        other = 3 - loser_id

        if self.mode == "coop":
            return {
                "result": "mine", "game_over": True,
                "winner": None, "reason": "mine",
                "message": "You hit a mine! Both players lose.",
            }
        elif self.mode == "sabotage":
            s1 = self.boards[1].count_safe_revealed()
            s2 = self.boards[2].count_safe_revealed()
            winner = 1 if s1 > s2 else (2 if s2 > s1 else "draw")
            return {
                "result": "mine", "game_over": True,
                "winner": winner, "reason": "mine",
                "message": f"Player {loser_id} hit a mine!",
            }
        else:  # classic
            return {
                "result": "mine", "game_over": True,
                "winner": other, "reason": "mine",
                "message": f"Player {loser_id} hit a mine! Player {other} wins!",
            }

    def _check_completion(self, player_id=None):
        if self.mode == "sabotage":
            return None  # Sabotage ends only on mine hit

        if self.mode == "classic":
            # Race: whoever finishes their own board first wins
            if self.boards[player_id].is_complete():
                self.active = False
                return {
                    "game_over": True, "winner": player_id, "reason": "complete",
                    "message": f"Player {player_id} cleared the board first and wins the race!",
                }
            return None

        # coop — shared board
        if self.board.is_complete():
            self.active = False
            return {
                "game_over": True, "winner": None, "reason": "complete",
                "message": "All safe cells revealed! Both players win!",
            }
        return None

    # ── State serialization ───────────────────────────────────────────────────

    def build_state_for_player(self, player_id, reveal_all=False):
        """Build the state payload for one player. Sabotage sends each player
        only their own board; Classic/Co-op send the shared board."""
        payload = {
            "type": "state",
            "mode": self.mode,
            "difficulty": self.config.get("difficulty", "Easy"),
            "rows": self.config["rows"],
            "cols": self.config["cols"],
            "mines": self.config["mines"],
            "scores": {str(k): v for k, v in self.scores.items()},
            "sabotage_left": {str(k): v for k, v in self.sabotage_left.items()},
        }

        if self.mode in ("sabotage", "classic"):
            payload["board"] = self.boards[player_id].to_client_view(reveal_all)
            payload["opponent_revealed_count"] = \
                self.boards[3 - player_id].count_safe_revealed()
        else:  # coop
            payload["board"] = self.board.to_client_view(reveal_all)

        return payload


# =============================================================================
# Server — socket handling, message routing, state broadcasting
# =============================================================================
class Server:
    """
    Listens for exactly 2 TCP connections.
    Manages the lobby (mode voting) and the game loop.
    After every player action the server sends the full updated state to both.
    """

    def __init__(self, config=None):
        # config carries the difficulty and mode chosen in main.py
        self.config        = config or DIFFICULTIES["Easy"]
        self.clients       = {}        # {player_id: socket}
        self.lock          = threading.Lock()
        self.game_state    = None
        self.rematch_votes = set()     # players who want to play again

    def start(self):
        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_sock.bind((HOST, PORT))
        server_sock.listen(2)

        diff     = self.config.get("difficulty", "Custom")
        mode     = self.config.get("mode", "classic")
        local_ip = self._get_local_ip()
        print(f"Server started — mode: {mode}  difficulty: {diff}  port: {PORT}")
        print(f"Your IP address: {local_ip}")
        print("Share your IP address with the other player.")

        pid = 1
        while len(self.clients) < 2:
            conn, addr = server_sock.accept()
            self.clients[pid] = conn
            print(f"Player {pid} connected from {addr}")
            self._send_to(pid, {
                "type":       "welcome",
                "player_id":  pid,
                "mode":       mode,
                "difficulty": self.config.get("difficulty", "Easy"),
                "local_ip":   local_ip,
            })
            t = threading.Thread(
                target=self._handle_client, args=(pid, conn), daemon=True
            )
            t.start()
            pid += 1

        print("Both players connected! Starting game…")
        self._start_game()
        threading.Event().wait()   # keep main thread alive

    def _get_local_ip(self):
        """Get the machine's LAN IP to display in the waiting screen."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return socket.gethostbyname(socket.gethostname())

    # ── Per-client receive loop ───────────────────────────────────────────────

    def _handle_client(self, player_id, conn):
        buffer = ""
        try:
            while True:
                data = conn.recv(4096).decode("utf-8")
                if not data:
                    break
                buffer += data
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()
                    if line:
                        try:
                            self._route_message(player_id, json.loads(line))
                        except json.JSONDecodeError:
                            pass
        except Exception as e:
            print(f"Player {player_id} error: {e}")
        finally:
            self._handle_disconnect(player_id)

    def _route_message(self, player_id, msg):
        t = msg.get("type")
        if   t == "move":     self._handle_move(player_id, msg)
        elif t == "flag":     self._handle_flag(player_id, msg)
        elif t == "sabotage": self._handle_sabotage(player_id)
        elif t == "rematch":  self._handle_rematch(player_id)

    # ── Game start ────────────────────────────────────────────────────────────

    def _start_game(self):
        mode = self.config.get("mode", "classic")
        print(f"Starting {mode} mode at {self.config.get('difficulty', '?')} difficulty")
        self.game_state = GameState(mode, self.config)
        for pid in self.clients:
            self._send_to(pid, self.game_state.build_state_for_player(pid))

    # ── Gameplay ──────────────────────────────────────────────────────────────

    def _handle_move(self, player_id, msg):
        r, c = msg.get("r"), msg.get("c")
        if r is None or c is None:
            return
        with self.lock:
            if not self.game_state:
                return
            self._send_state_or_game_over(
                self.game_state.handle_move(player_id, r, c)
            )

    def _handle_flag(self, player_id, msg):
        r, c = msg.get("r"), msg.get("c")
        if r is None or c is None:
            return
        with self.lock:
            if not self.game_state:
                return
            self.game_state.handle_flag(player_id, r, c)
            self._broadcast_state()

    def _handle_sabotage(self, player_id):
        with self.lock:
            if not self.game_state:
                return
            result = self.game_state.handle_sabotage(player_id)
            if result["result"] == "ok":
                self._broadcast_state()

    def _handle_rematch(self, player_id):
        with self.lock:
            self.rematch_votes.add(player_id)
            print(f"Player {player_id} wants a rematch ({len(self.rematch_votes)}/2)")
            if self.rematch_votes == {1, 2}:
                self.rematch_votes.clear()
                print("Both players agreed — starting rematch!")
                self._start_game()
            else:
                # Tell this player to keep waiting
                self._send_to(player_id, {"type": "rematch_wait"})

    # ── Broadcasting ──────────────────────────────────────────────────────────

    def _send_state_or_game_over(self, action_result):
        if action_result.get("game_over"):
            for pid in self.clients:
                payload = self.game_state.build_state_for_player(pid, reveal_all=True)
                payload.update({
                    "type":         "game_over",
                    "winner":       action_result.get("winner"),
                    "reason":       action_result.get("reason"),
                    "message":      action_result.get("message", "Game over!"),
                    "final_scores": {str(k): v
                                     for k, v in self.game_state.scores.items()},
                })
                self._send_to(pid, payload)
        else:
            self._broadcast_state()

    def _broadcast_state(self):
        for pid in self.clients:
            self._send_to(pid, self.game_state.build_state_for_player(pid))

    def _broadcast(self, payload):
        for pid in self.clients:
            self._send_to(pid, payload)

    def _send_to(self, player_id, payload):
        try:
            self.clients[player_id].sendall(
                (json.dumps(payload) + "\n").encode("utf-8")
            )
        except Exception as e:
            print(f"Send error to player {player_id}: {e}")

    def _handle_disconnect(self, player_id):
        print(f"Player {player_id} disconnected.")
        self.rematch_votes.discard(player_id)
        other = 3 - player_id
        if other in self.clients:
            self._send_to(other, {
                "type":         "game_over",
                "winner":       None,
                "reason":       "disconnect",
                "message":      "The other player disconnected.",
                "final_scores": ({str(k): v for k, v in self.game_state.scores.items()}
                                 if self.game_state else {"1": 0, "2": 0}),
            })


# =============================================================================
# Entry point (when run directly, not via main.py)
# =============================================================================
if __name__ == "__main__":
    # Optional CLI args: python3 server.py --difficulty Medium --mode coop
    config = dict(DIFFICULTIES["Easy"])
    config["difficulty"] = "Easy"
    config["mode"] = "classic"

    args = sys.argv[1:]
    if "--difficulty" in args:
        idx = args.index("--difficulty")
        if idx + 1 < len(args):
            d = args[idx + 1]
            if d in DIFFICULTIES:
                config = dict(DIFFICULTIES[d])
                config["difficulty"] = d
                config["mode"] = "classic"

    if "--mode" in args:
        idx = args.index("--mode")
        if idx + 1 < len(args):
            m = args[idx + 1]
            if m in ("classic", "coop", "sabotage"):
                config["mode"] = m

    Server(config).start()
# References
#Anthropic. (2026). Claude (May 26 version) [Large language model].
#https://claude.ai/