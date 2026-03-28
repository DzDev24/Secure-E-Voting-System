"""
admin_setup.py – One-time election setup script.

Run this script before starting the election to:
  1. Generate an RSA key pair for the server (default 2048-bit modulus).
  2. Generate RSA key pairs for each registered voter (public registry + client-only privates).
  3. Save the candidate list.

All data is written to the ``data/`` directory as JSON files.
"""

import json
import os
import sys

from crypto_utils import generate_keypair

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
SERVER_KEYS_FILE = os.path.join(DATA_DIR, "server_keys.json")
VOTERS_FILE = os.path.join(DATA_DIR, "voters.json")
CANDIDATES_FILE = os.path.join(DATA_DIR, "candidates.json")
VOTER_PRIVATES_FILE = os.path.join(DATA_DIR, "voter_private_keys.json")


def setup(
    candidate_names=None,
    voter_names=None,
    bits=1024,
    interactive=True,
):
    """Run the election setup.

    Args:
        candidate_names: List of candidate name strings (used when not interactive).
        voter_names: List of voter name strings (used when not interactive).
        bits: RSA key bit-length per prime.
        interactive: If True, prompt the user for input via stdin.

    Returns:
        Dict with keys ``server_keys``, ``voters_public``, ``voters_private``, ``candidates``.
    """
    os.makedirs(DATA_DIR, exist_ok=True)

    # ------------------------------------------------------------------
    # Candidates
    # ------------------------------------------------------------------
    if interactive:
        num_candidates = int(input("Enter number of candidates [3]: ").strip() or 3)
        candidate_names = []
        for i in range(num_candidates):
            name = input(f"  Candidate {i + 1} name [Candidate {chr(65 + i)}]: ").strip()
            candidate_names.append(name or f"Candidate {chr(65 + i)}")
    else:
        if candidate_names is None:
            candidate_names = ["Candidate A", "Candidate B", "Candidate C"]

    with open(CANDIDATES_FILE, "w") as fh:
        json.dump(candidate_names, fh, indent=2)
    print(f"[+] Candidates saved: {candidate_names}")

    # ------------------------------------------------------------------
    # Server key pair
    # ------------------------------------------------------------------
    print("[*] Generating server RSA key pair …", end=" ", flush=True)
    server_pub, server_priv = generate_keypair(bits)
    server_keys = {"public_key": server_pub, "private_key": server_priv}
    with open(SERVER_KEYS_FILE, "w") as fh:
        json.dump(server_keys, fh, indent=2)
    print("done.")

    # ------------------------------------------------------------------
    # Voters
    # ------------------------------------------------------------------
    if interactive:
        num_voters = int(input("Enter number of voters [30]: ").strip() or 30)
        voter_names = []
        for i in range(num_voters):
            name = input(f"  Voter {i + 1} name [Student {i + 1}]: ").strip()
            voter_names.append(name or f"Student {i + 1}")
    else:
        if voter_names is None:
            voter_names = [f"Student {i + 1}" for i in range(30)]

    voters_public = {}
    voters_private = {}
    for idx, name in enumerate(voter_names, start=1):
        voter_id = f"STU_{idx:03d}"
        print(f"[*] Generating keys for {voter_id} ({name}) …", end=" ", flush=True)
        pub, priv = generate_keypair(bits)
        voters_public[voter_id] = {
            "name": name,
            "public_key": pub,
        }
        voters_private[voter_id] = {
            "name": name,
            "private_key": priv,
        }
        print("done.")

    with open(VOTERS_FILE, "w") as fh:
        json.dump(voters_public, fh, indent=2)
    with open(VOTER_PRIVATES_FILE, "w") as fh:
        json.dump(voters_private, fh, indent=2)
    print(f"[+] Voter registry saved ({len(voters_public)} voters).")

    print("\n[✓] Setup complete. Files written to:", DATA_DIR)
    return {
        "server_keys": server_keys,
        "voters_public": voters_public,
        "voters_private": voters_private,
        "candidates": candidate_names,
    }


if __name__ == "__main__":
    setup(interactive=True)
