"""
voter_client.py – CLI-based voter client for the e-voting system.

Flow:
  1. Ask for voter ID.
  2. Load voter private key from data/voters.json.
  3. Load server public key from data/server_keys.json.
  4. Display candidates loaded from data/candidates.json.
  5. Ask voter to choose a candidate.
  6. Encrypt the candidate name with the server's public key.
  7. Sign the encrypted vote with the voter's private key.
  8. Send the JSON envelope over TCP to localhost:5555.
  9. Display the server's response.
"""

import json
import os
import socket
import struct

from crypto_utils import encrypt, sign, text_to_int

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
SERVER_KEYS_FILE = os.path.join(DATA_DIR, "server_keys.json")
VOTERS_FILE = os.path.join(DATA_DIR, "voters.json")
CANDIDATES_FILE = os.path.join(DATA_DIR, "candidates.json")
VOTER_PRIVATES_FILE = os.path.join(DATA_DIR, "voter_private_keys.json")

HOST = "localhost"
PORT = 5555


# ---------------------------------------------------------------------------
# Wire protocol helpers (must match voting_server.py)
# ---------------------------------------------------------------------------

def send_msg(sock: socket.socket, data: dict) -> None:
    payload = json.dumps(data).encode("utf-8")
    sock.sendall(struct.pack(">I", len(payload)) + payload)


def recv_msg(sock: socket.socket) -> dict:
    raw_len = _recv_exact(sock, 4)
    if not raw_len:
        return {}
    (length,) = struct.unpack(">I", raw_len)
    payload = _recv_exact(sock, length)
    return json.loads(payload.decode("utf-8"))


def _recv_exact(sock: socket.socket, n: int) -> bytes:
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


# ---------------------------------------------------------------------------
# Core vote-casting logic (also used by the GUI)
# ---------------------------------------------------------------------------

def cast_vote(voter_id: str, candidate_name: str) -> dict:
    """Encrypt, sign, and send a vote to the server.

    Args:
        voter_id: Registered voter ID (e.g. ``"STU_001"``).
        candidate_name: Name of the chosen candidate.

    Returns:
        Server response dict (with keys ``status`` and ``message``).

    Raises:
        KeyError: If the voter ID is not in the local registry.
        FileNotFoundError: If required data files are missing.
        ConnectionRefusedError: If the server is not reachable.
    """
    # Load keys
    server_data = _load_json(SERVER_KEYS_FILE, "Server keys file")
    server_pub = server_data["public_key"]

    voters = _load_json(VOTERS_FILE, "Voter registry (public keys)")
    voter_privs = _load_json(VOTER_PRIVATES_FILE, "Voter private key store")

    if voter_id not in voters:
        raise KeyError(f"Voter ID '{voter_id}' not found in registry.")
    if voter_id not in voter_privs:
        raise KeyError(f"Private key for voter ID '{voter_id}' not found.")

    voter_priv = voter_privs[voter_id]["private_key"]

    # Encrypt & sign
    plaintext_int = text_to_int(candidate_name)
    encrypted_vote = encrypt(plaintext_int, server_pub)
    signature = sign(encrypted_vote, voter_priv)

    envelope = {
        "action": "vote",
        "voter_id": voter_id,
        "encrypted_vote": encrypted_vote,
        "signature": signature,
    }

    # Send over TCP
    with socket.create_connection((HOST, PORT), timeout=10) as sock:
        send_msg(sock, envelope)
        response = recv_msg(sock)

    return response


def close_election() -> dict:
    """Send a close-election command to the server.

    Returns:
        Server response dict.
    """
    with socket.create_connection((HOST, PORT), timeout=10) as sock:
        send_msg(sock, {"action": "close_election"})
        return recv_msg(sock)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _cli() -> None:
    print("=== Secure E-Voting System ===\n")

    voter_id = input("Enter your voter ID (e.g. STU_001): ").strip()
    if not voter_id:
        print("[!] No voter ID entered. Exiting.")
        return

    try:
        candidates = _load_json(CANDIDATES_FILE, "Candidates file")
    except FileNotFoundError as exc:
        print(f"[!] {exc}")
        return

    print("\nAvailable candidates:")
    for idx, name in enumerate(candidates, start=1):
        print(f"  {idx}. {name}")

    choice = input("\nEnter candidate number: ").strip()
    try:
        idx = int(choice) - 1
        if idx < 0 or idx >= len(candidates):
            raise ValueError
        candidate_name = candidates[idx]
    except ValueError:
        print("[!] Invalid selection. Exiting.")
        return

    print(f"\n[*] Casting vote for '{candidate_name}' as '{voter_id}' …")
    try:
        response = cast_vote(voter_id, candidate_name)
    except KeyError as exc:
        print(f"[!] {exc}")
        return
    except FileNotFoundError as exc:
        print(f"[!] {exc}")
        return
    except ConnectionRefusedError:
        print(f"[!] Could not connect to voting server at {HOST}:{PORT}. Is it running?")
        return

    status = response.get("status", "unknown")
    message = response.get("message", "")
    if status == "accepted":
        print(f"[✓] Vote {status}: {message}")
    else:
        print(f"[✗] Vote {status}: {message}")


if __name__ == "__main__":
    _cli()
