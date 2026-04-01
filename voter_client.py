"""
voter_client.py – Voter client for the e-voting system.

Flow:
  1. Ask for voter name.
  2. Load voter's private key from data/keys/<name>_private.json.
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
SERVER_PUB_FILE = os.path.join(DATA_DIR, "server_public_key.json")
VOTERS_FILE = os.path.join(DATA_DIR, "voters.json")
CANDIDATES_FILE = os.path.join(DATA_DIR, "candidates.json")
KEYS_DIR = os.path.join(DATA_DIR, "keys")

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

def cast_vote(voter_name: str, candidate_name: str) -> dict:
    """Encrypt, sign, and send a vote to the server.

    Args:
        voter_name: Registered voter name (e.g. ``"Nazim"``).
        candidate_name: Name of the chosen candidate.

    Returns:
        Server response dict (with keys ``status`` and ``message``).

    Raises:
        KeyError: If the voter name is not in the local registry.
        FileNotFoundError: If required data files are missing.
        ConnectionRefusedError: If the server is not reachable.
    """
    # Load server public key
    server_data = _load_json(SERVER_PUB_FILE, "Server public key file")
    server_pub = server_data["public_key"]

    # Load voter registry (to confirm registration)
    voters = _load_json(VOTERS_FILE, "Voter registry")
    if voter_name not in voters:
        raise KeyError(f"Name '{voter_name}' not found in voter registry.")
    if not voters[voter_name].get("public_key"):
        raise KeyError(f"No keys registered for '{voter_name}'. Run generate_keys.py first.")

    # Load voter's private key from their personal key file
    priv_path = os.path.join(KEYS_DIR, f"{voter_name}_private.json")
    if not os.path.exists(priv_path):
        raise KeyError(f"Private key file not found for '{voter_name}'. Run generate_keys.py first.")
    with open(priv_path) as fh:
        voter_priv = json.load(fh)["private_key"]

    # Encrypt & sign
    plaintext_int = text_to_int(candidate_name)
    encrypted_vote = encrypt(plaintext_int, server_pub)
    signature = sign(encrypted_vote, voter_priv)

    envelope = {
        "action": "vote",
        "voter_name": voter_name,
        "encrypted_vote": encrypted_vote,
        "signature": signature,
    }

    # Send over TCP
    with socket.create_connection((HOST, PORT), timeout=10) as sock:
        send_msg(sock, envelope)
        response = recv_msg(sock)

    return response


def close_election() -> dict:
    """Send a close-election command to the server."""
    with socket.create_connection((HOST, PORT), timeout=10) as sock:
        send_msg(sock, {"action": "close_election"})
        return recv_msg(sock)


def get_results() -> dict:
    """Fetch the current tally from the server without closing the election."""
    with socket.create_connection((HOST, PORT), timeout=10) as sock:
        send_msg(sock, {"action": "get_results"})
        return recv_msg(sock)


def reset_votes():
    """Delete the results file to clear vote tallies and voted records."""
    path = os.path.join(DATA_DIR, "results.json")
    if os.path.exists(path):
        os.remove(path)


def reset_all():
    """Delete all data files (keys, voters, candidates, results).

    After calling this, ``admin_setup.py`` must be run again.
    """
    import shutil
    if os.path.isdir(DATA_DIR):
        shutil.rmtree(DATA_DIR)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _cli() -> None:
    print("=== Secure E-Voting System ===\n")

    voter_name = input("Enter your name: ").strip()
    if not voter_name:
        print("[!] No name entered. Exiting.")
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

    print(f"\n[*] Casting vote for '{candidate_name}' as '{voter_name}' …")
    try:
        response = cast_vote(voter_name, candidate_name)
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
