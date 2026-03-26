"""
voting_server.py – TCP socket server for the e-voting system.

Protocol (JSON over TCP, length-prefixed):
  Client → Server:
    {"action": "vote", "voter_id": "STU_001",
     "encrypted_vote": <int>, "signature": <int>}

    {"action": "close_election"}

  Server → Client:
    {"status": "accepted", "message": "Vote recorded successfully."}
    {"status": "rejected", "message": "<reason>"}
    {"status": "closed",   "message": "<final tally>"}

The server performs, in order:
  1. Identity check   – voter_id must exist in the registry.
  2. Signature verify – verify(encrypted_vote, signature, voter_pub_key).
  3. Duplicate check  – voter_id must not have voted before.
  4. Decrypt          – M = C^d mod n using server private key.
  5. Candidate check  – decrypted name must be in the candidate list.
  6. Tally            – increment candidate counter, record voter_id.
"""

import json
import os
import socket
import struct
import threading

from crypto_utils import decrypt, int_to_text, verify

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
SERVER_KEYS_FILE = os.path.join(DATA_DIR, "server_keys.json")
VOTERS_FILE = os.path.join(DATA_DIR, "voters.json")
CANDIDATES_FILE = os.path.join(DATA_DIR, "candidates.json")

HOST = "localhost"
PORT = 5555


# ---------------------------------------------------------------------------
# Wire protocol helpers
# ---------------------------------------------------------------------------

def send_msg(sock: socket.socket, data: dict) -> None:
    """Send a JSON message prefixed with a 4-byte big-endian length."""
    payload = json.dumps(data).encode("utf-8")
    sock.sendall(struct.pack(">I", len(payload)) + payload)


def recv_msg(sock: socket.socket) -> dict:
    """Receive a length-prefixed JSON message."""
    raw_len = _recv_exact(sock, 4)
    if not raw_len:
        return {}
    (length,) = struct.unpack(">I", raw_len)
    payload = _recv_exact(sock, length)
    return json.loads(payload.decode("utf-8"))


def _recv_exact(sock: socket.socket, n: int) -> bytes:
    """Read exactly n bytes from the socket."""
    buf = b""
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            return b""
        buf += chunk
    return buf


# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------

class VotingServer:
    """Multi-threaded e-voting TCP server."""

    def __init__(self, host: str = HOST, port: int = PORT):
        self.host = host
        self.port = port

        # Load persisted data
        with open(SERVER_KEYS_FILE) as fh:
            keys = json.load(fh)
        self.server_priv = keys["private_key"]

        with open(VOTERS_FILE) as fh:
            self.voters = json.load(fh)

        with open(CANDIDATES_FILE) as fh:
            self.candidates = json.load(fh)

        # State
        self.tally = {c: 0 for c in self.candidates}
        self.voted_ids: set = set()
        self._lock = threading.Lock()
        self._running = True
        self._server_sock = None

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Bind and start listening; blocks until the election is closed."""
        self._server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server_sock.bind((self.host, self.port))
        self._server_sock.listen(5)
        self._server_sock.settimeout(1.0)
        print(f"[*] Voting server listening on {self.host}:{self.port}")

        while self._running:
            try:
                conn, addr = self._server_sock.accept()
            except socket.timeout:
                continue
            t = threading.Thread(target=self._handle_client, args=(conn, addr), daemon=True)
            t.start()

        self._server_sock.close()
        self._print_results()

    def stop(self) -> None:
        """Signal the server to stop after the current accept cycle."""
        self._running = False

    def get_tally(self) -> dict:
        """Return a copy of the current vote tally."""
        with self._lock:
            return dict(self.tally)

    # ------------------------------------------------------------------
    # Connection handler
    # ------------------------------------------------------------------

    def _handle_client(self, conn: socket.socket, addr) -> None:
        with conn:
            try:
                msg = recv_msg(conn)
            except Exception as exc:
                send_msg(conn, {"status": "rejected", "message": f"Protocol error: {exc}"})
                return

            action = msg.get("action", "")

            if action == "close_election":
                self.stop()
                send_msg(conn, {"status": "closed", "message": self._results_str()})
                return

            if action == "vote":
                response = self._process_vote(msg)
                send_msg(conn, response)
                return

            send_msg(conn, {"status": "rejected", "message": "Unknown action."})

    def _process_vote(self, msg: dict) -> dict:
        voter_id = msg.get("voter_id", "")
        encrypted_vote = msg.get("encrypted_vote")
        signature = msg.get("signature")

        if not voter_id or encrypted_vote is None or signature is None:
            return {"status": "rejected", "message": "Malformed vote packet."}

        # 1. Identity check
        voter_record = self.voters.get(voter_id)
        if voter_record is None:
            return {"status": "rejected", "message": "Unknown voter ID."}

        voter_pub = voter_record["public_key"]

        # 2. Signature verification
        if not verify(encrypted_vote, signature, voter_pub):
            return {"status": "rejected", "message": "Invalid signature."}

        with self._lock:
            # 3. Duplicate vote check
            if voter_id in self.voted_ids:
                return {"status": "rejected", "message": "Voter has already voted."}

            # 4. Decrypt the vote
            try:
                plaintext_int = decrypt(encrypted_vote, self.server_priv)
                candidate_name = int_to_text(plaintext_int)
            except Exception:
                return {"status": "rejected", "message": "Decryption failed."}

            # 5. Validate candidate
            if candidate_name not in self.candidates:
                return {"status": "rejected", "message": "Invalid candidate."}

            # 6. Tally
            self.tally[candidate_name] += 1
            self.voted_ids.add(voter_id)

        return {"status": "accepted", "message": "Vote recorded successfully."}

    # ------------------------------------------------------------------
    # Results
    # ------------------------------------------------------------------

    def _results_str(self) -> str:
        lines = ["=== Final Results ==="]
        for candidate, count in self.tally.items():
            lines.append(f"  {candidate}: {count} vote(s)")
        if self.tally:
            winner = max(self.tally, key=self.tally.get)
            lines.append(f"Winner: {winner}")
        return "\n".join(lines)

    def _print_results(self) -> None:
        print("\n" + self._results_str())


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    server = VotingServer()
    try:
        server.start()
    except KeyboardInterrupt:
        print("\n[!] Server interrupted by user.")
        server.stop()
