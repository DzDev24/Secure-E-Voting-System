"""
admin_setup.py – Election setup script (Admin only).

Run this script to:
  1. Generate an RSA key pair for the server.
  2. Register candidate names.
  3. Register voter names (no key generation — voters generate their own keys).

All data is written to the ``data/`` directory as JSON files.
"""

import json
import os

from crypto_utils import generate_keypair

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
SERVER_PUB_FILE  = os.path.join(DATA_DIR, "server_public_key.json")
SERVER_PRIV_FILE = os.path.join(DATA_DIR, "server_private_key.json")
VOTERS_FILE = os.path.join(DATA_DIR, "voters.json")
CANDIDATES_FILE = os.path.join(DATA_DIR, "candidates.json")


def setup(
    candidate_names=None,
    voter_names=None,
    bits=1024,
    interactive=True,
):
    """Run the election setup.

    Args:
        candidate_names: List of candidate name strings.
        voter_names: List of voter name strings.
        bits: RSA key bit-length per prime (for server keys only).
        interactive: If True, prompt the user for input via stdin.
    """
    os.makedirs(DATA_DIR, exist_ok=True)

    # ------------------------------------------------------------------
    # Candidates
    # ------------------------------------------------------------------
    if interactive:
        num_candidates = int(input("Enter number of candidates [3]: ").strip() or 3)
        candidate_names = []
        for i in range(num_candidates):
            name = input(f"  Candidate {i + 1} name [Candidate {i + 1}]: ").strip()
            candidate_names.append(name or f"Candidate {i + 1}")
    else:
        if candidate_names is None:
            candidate_names = [f"Candidate {i + 1}" for i in range(3)]

    with open(CANDIDATES_FILE, "w") as fh:
        json.dump(candidate_names, fh, indent=2)
    print(f"[+] Candidates saved: {candidate_names}")

    # ------------------------------------------------------------------
    # Server key pair
    # ------------------------------------------------------------------
    print("[*] Generating server RSA key pair …", end=" ", flush=True)
    server_pub, server_priv = generate_keypair(bits)
    with open(SERVER_PUB_FILE, "w") as fh:
        json.dump({"public_key": server_pub}, fh, indent=2)
    with open(SERVER_PRIV_FILE, "w") as fh:
        json.dump({"private_key": server_priv}, fh, indent=2)
    print("done.")
    print(f"    Public key  → {SERVER_PUB_FILE}  (shared with voters)")
    print(f"    Private key → {SERVER_PRIV_FILE} (server only)")

    # ------------------------------------------------------------------
    # Voters — register names only (voters generate their own keys)
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

    # Save voter registry — names only, no keys yet
    voters = {}
    for name in voter_names:
        if name in voters:
            print(f"[!] Warning: Duplicate voter name '{name}' — skipped.")
            continue
        voters[name] = {}  # empty — public key will be added by generate_keys.py

    with open(VOTERS_FILE, "w") as fh:
        json.dump(voters, fh, indent=2)
    print(f"[+] Voter registry saved ({len(voters)} voters).")
    print(f"    Each voter must now run generate_keys.py to generate their own keys.")

    print("\n[✓] Setup complete. Files written to:", DATA_DIR)


if __name__ == "__main__":
    setup(interactive=True)
