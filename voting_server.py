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
SERVER_PRIV_FILE = os.path.join(DATA_DIR, "server_private_key.json")
VOTERS_FILE = os.path.join(DATA_DIR, "voters.json")
CANDIDATES_FILE = os.path.join(DATA_DIR, "candidates.json")
RESULTS_FILE = os.path.join(DATA_DIR, "results.json")

HOST = "localhost"
PORT = 5555




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


def _load_json(path: str, label: str):
    """Load JSON file or raise a helpful error if missing."""
    try:
        with open(path) as fh:
            return json.load(fh)
    except FileNotFoundError as exc:
        raise FileNotFoundError(
            f"{label} not found at {path}. Run admin_setup.py first."
        ) from exc



class VotingServer:
    """Multi-threaded e-voting TCP server."""

    def __init__(self, host: str = HOST, port: int = PORT):
        self.host = host
        self.port = port

        if not os.path.isdir(DATA_DIR):
            raise FileNotFoundError(
                f"Data directory not found at {DATA_DIR}. Run admin_setup.py first."
            )

        # Load persisted data
        keys = _load_json(SERVER_PRIV_FILE, "Server private key file")
        self.server_priv = keys["private_key"]

        self.voters = _load_json(VOTERS_FILE, "Voter registry")
        self.candidates = _load_json(CANDIDATES_FILE, "Candidates file")

        # State
        self._round = 1
        self._active_candidates = list(self.candidates)
        self.voted_ids: set = set()  
        self._election_closed = False
        if os.path.exists(RESULTS_FILE):
            try:
                prior = _load_json(RESULTS_FILE, "Results file")
                self._round = prior.get("round", 1)
                saved_active = prior.get("active_candidates")
                if saved_active:
                    self._active_candidates = saved_active
                self.voted_ids = set(prior.get("voted_ids", []))
                self._election_closed = prior.get("election_closed", False)
            except (FileNotFoundError, json.JSONDecodeError):
                pass
        # Build tally from active candidates, then restore any saved counts
        self.tally = {c: 0 for c in self._active_candidates}
        if os.path.exists(RESULTS_FILE):
            try:
                prior = _load_json(RESULTS_FILE, "Results file")
                stored_tally = prior.get("tally", {})
                for c in self.tally:
                    self.tally[c] = stored_tally.get(c, 0)
            except (FileNotFoundError, json.JSONDecodeError):
                pass
        self._lock = threading.Lock()
        self._running = True
        self._server_sock = None

    

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
        self._persist_state()
        self._print_results()

    def stop(self) -> None:
        """Signal the server to stop after the current accept cycle."""
        self._running = False

    def get_tally(self) -> dict:
        """Return a copy of the current vote tally."""
        with self._lock:
            return dict(self.tally)



    def _handle_client(self, conn: socket.socket, addr) -> None:
        with conn:
            try:
                msg = recv_msg(conn)
            except Exception as exc:
                send_msg(conn, {"status": "rejected", "message": f"Protocol error: {exc}"})
                return

            action = msg.get("action", "")

            if action == "close_election":
                # Check for tie at the top
                if self.tally:
                    max_votes = max(self.tally.values())
                    if max_votes == 0:
                        send_msg(conn, {
                            "status": "rejected",
                            "message": "No votes cast yet. Cannot close.",
                        })
                        return
                    tied = [c for c, v in self.tally.items() if v == max_votes]
                    if len(tied) > 1:
                        # Tie detected — start runoff round
                        self._initiate_runoff(tied)
                        send_msg(conn, {
                            "status": "runoff",
                            "message": f"Tie detected! Starting round {self._round}.",
                            "round": self._round,
                            "candidates": tied,
                        })
                        return
                # No tie — close the election
                self._election_closed = True
                self.stop()
                send_msg(conn, {"status": "closed", "message": self._results_str()})
                return

            if action == "get_results":
                with self._lock:
                    tally = dict(self.tally)
                    total = sum(tally.values())
                send_msg(conn, {
                    "status": "ok", "tally": tally,
                    "total_votes": total,
                    "total_registered": sum(
                        1 for v in self.voters.values() if v.get("public_key")
                    ),
                    "round": self._round,
                    "active_candidates": list(self._active_candidates),
                })
                return

            if action == "vote":
                response = self._process_vote(msg)
                send_msg(conn, response)
                return

            send_msg(conn, {"status": "rejected", "message": "Unknown action."})

    def _process_vote(self, msg: dict) -> dict:
        """Process a vote in two separated phases for relative anonymity.

        Phase 1 (Identity):  verifies WHO is voting — never inspects the ballot.
        Phase 2 (Counting):  reveals WHAT was voted — never sees voter identity.
        """
        voter_name = msg.get("voter_name", "")
        encrypted_vote = msg.get("encrypted_vote")
        signature = msg.get("signature")

        if not voter_name or encrypted_vote is None or signature is None:
            return {"status": "rejected", "message": "Malformed vote packet."}


        
        voter_record = self.voters.get(voter_name)
        if voter_record is None:
            return {"status": "rejected", "message": "Unknown voter name."}

        voter_pub = voter_record.get("public_key")
        if not voter_pub:
            return {"status": "rejected", "message": "Voter has not generated keys yet."}

        
        if not verify(encrypted_vote, signature, voter_pub):
            return {"status": "rejected", "message": "Invalid signature."}

        
        with self._lock:
            if voter_name in self.voted_ids:
                return {"status": "rejected", "message": "Voter has already voted."}
            self.voted_ids.add(voter_name)  

        

        result = self._count_ballot(encrypted_vote)

        
        if result["status"] != "accepted":
            with self._lock:
                self.voted_ids.discard(voter_name)

        return result

    def _count_ballot(self, encrypted_vote: int) -> dict:
        """Decrypt and tally a single ballot WITHOUT any voter identity.

        This method is intentionally isolated from voter identification
        to uphold relative anonymity: the counting step cannot determine
        who cast this particular ballot.

        Args:
            encrypted_vote: RSA-encrypted candidate name (ciphertext int).

        Returns:
            Response dict with ``status`` and ``message`` keys.
        """
        with self._lock:
            
            try:
                plaintext_int = decrypt(encrypted_vote, self.server_priv)
                candidate_name = int_to_text(plaintext_int)
            except Exception:
                return {"status": "rejected", "message": "Decryption failed."}

            
            if candidate_name not in self._active_candidates:
                return {"status": "rejected", "message": "Invalid candidate."}

            
            self.tally[candidate_name] += 1
            self._persist_state()

            
            registered_with_keys = sum(
                1 for v in self.voters.values() if v.get("public_key")
            )
            if registered_with_keys > 0 and len(self.voted_ids) >= registered_with_keys:
                self._try_auto_close()

        return {"status": "accepted", "message": "Vote recorded successfully."}

    def _try_auto_close(self):
        """Auto-close the election when 100% turnout is reached.

        Must be called while self._lock is held.
        """
        if not self.tally:
            return
        max_votes = max(self.tally.values())
        tied = [c for c, v in self.tally.items() if v == max_votes]

        if len(tied) > 1:
            
            self._round += 1
            self._active_candidates = tied
            self.tally = {c: 0 for c in tied}
            self.voted_ids = set()
            self._persist_state()
            print(f"\n*** AUTO-CLOSE: 100% turnout — tie! Runoff round {self._round} with {tied} ***")
        else:
            self._election_closed = True
            self._persist_state()
            self._print_results()
            print("\n*** AUTO-CLOSE: 100% turnout — election closed ***")



    def _results_str(self) -> str:
        header = f"=== Final Results (Round {self._round}) ==="
        lines = [header]
        for candidate, count in self.tally.items():
            lines.append(f"  {candidate}: {count} vote(s)")
        if self.tally:
            winner = max(self.tally, key=self.tally.get)
            lines.append(f"Winner: {winner}")
        return "\n".join(lines)

    def _print_results(self) -> None:
        print("\n" + self._results_str())

    def _persist_state(self) -> None:
        """Persist tally, voted IDs, round, and active candidates."""
        snapshot = {
            "tally": self.tally,
            "voted_ids": list(self.voted_ids),
            "election_closed": self._election_closed,
            "round": self._round,
            "active_candidates": list(self._active_candidates),
        }
        with open(RESULTS_FILE, "w") as fh:
            json.dump(snapshot, fh, indent=2)

    def _initiate_runoff(self, tied_candidates):
        """Start a new runoff round with only the tied candidates."""
        with self._lock:
            self._round += 1
            self._active_candidates = tied_candidates
            self.tally = {c: 0 for c in tied_candidates}
            self.voted_ids = set()  # everyone can vote again
            self._persist_state()
        print(f"\n*** RUNOFF: Round {self._round} with {tied_candidates} ***")



if __name__ == "__main__":
    server = None
    try:
        server = VotingServer()
        server.start()
    except FileNotFoundError as exc:
        print(f"[!] {exc}")
    except KeyboardInterrupt:
        print("\n[!] Server interrupted by user.")
        if server is not None:
            server.stop()
