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
import socket  # Used for network communication over TCP
import struct  # Used to pack/unpack binary data (like the message length prefix)

from crypto_utils import encrypt, sign, text_to_int

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
SERVER_PUB_FILE = os.path.join(DATA_DIR, "server_public_key.json")
VOTERS_FILE = os.path.join(DATA_DIR, "voters.json")
CANDIDATES_FILE = os.path.join(DATA_DIR, "candidates.json")
KEYS_DIR = os.path.join(DATA_DIR, "keys")

# The server listens on localhost at port 5555
HOST = "localhost"
PORT = 5555


def send_msg(sock: socket.socket, data: dict) -> None:
    """Send a JSON dictionary over a socket."""
    # Convert dictionary to a JSON string, then encode it to raw bytes
    payload = json.dumps(data).encode("utf-8")
    
    # struct.pack(">I", length) creates a 4-byte big-endian integer header.
    # This tells the server exactly how many bytes to read before processing the JSON.
    sock.sendall(struct.pack(">I", len(payload)) + payload)


def recv_msg(sock: socket.socket) -> dict:
    """Read a JSON dictionary from a socket."""
    # First, read exactly 4 bytes to get the length prefix
    raw_len = _recv_exact(sock, 4)
    if not raw_len:
        return {}
        
    # Unpack the 4 bytes back into a normal integer
    (length,) = struct.unpack(">I", raw_len)
    
    # Read exactly 'length' bytes of JSON payload
    payload = _recv_exact(sock, length)
    
    # Decode bytes to string, then parse the JSON string back into a dictionary
    return json.loads(payload.decode("utf-8"))


def _recv_exact(sock: socket.socket, n: int) -> bytes:
    """Helper function to reliably read exactly n bytes from the socket."""
    buf = b""
    while len(buf) < n:
        # Keep reading chunks until we have exactly 'n' bytes
        chunk = sock.recv(n - len(buf))
        if not chunk:
            return b""  # Connection closed abruptly
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


def cast_vote(voter_name: str, candidate_name: str) -> dict:
    """Encrypt, sign, and send a vote to the server."""
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

    # CRYPTOGRAPHY IN ACTION:
    # 1. Convert candidate name string into a big number
    plaintext_int = text_to_int(candidate_name)
    
    # 2. Encrypt the vote so only the server can read it (Confidentiality)
    encrypted_vote = encrypt(plaintext_int, server_pub)
    
    # 3. Sign the encrypted vote using the voter's private key (Authenticity & Integrity)
    signature = sign(encrypted_vote, voter_priv)

    # Pack everything into a "JSON Envelope"
    envelope = {
        "action": "vote",
        "voter_name": voter_name,
        "encrypted_vote": encrypted_vote,
        "signature": signature,
    }

    # Send over TCP
    # create_connection automatically establishes a TCP socket connection
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
    """Delete all data files (keys, voters, candidates, results)."""
    import shutil  # Used to delete entire folders
    if os.path.isdir(DATA_DIR):
        shutil.rmtree(DATA_DIR)  # Deletes the data directory and everything inside it


def _cli() -> None:
    """Command Line Interface (used if running without the GUI)."""
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
    # enumerate gives us an automatic index counter for the list
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
