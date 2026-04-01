"""
generate_keys.py – Voter key generation script.

Each voter runs this script on their own machine to:
  1. Generate their personal RSA key pair.
  2. Save their private key locally (data/keys/<name>_private.json).
  3. Register their public key with the election server (data/voters.json).

This simulates the real-world scenario where each student generates
their own keys and only sends their public key to the professor.
"""

import json
import os

from crypto_utils import generate_keypair

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
KEYS_DIR = os.path.join(DATA_DIR, "keys")
VOTERS_FILE = os.path.join(DATA_DIR, "voters.json")


def generate_voter_keys(voter_name: str, bits: int = 1024):
    """Generate an RSA key pair for a registered voter.

    Args:
        voter_name: The voter's registered name.
        bits: RSA key bit-length per prime.
    """
    # 1. Check voter is registered
    if not os.path.exists(VOTERS_FILE):
        print("[!] Voter registry not found. Ask the admin to run admin_setup.py first.")
        return

    with open(VOTERS_FILE) as fh:
        voters = json.load(fh)

    if voter_name not in voters:
        print(f"[!] Name '{voter_name}' is not registered. Contact the admin.")
        return

    if voters[voter_name].get("public_key"):
        print(f"[!] Keys for '{voter_name}' have already been generated.")
        print(f"    If you need to regenerate, ask the admin to reset.")
        return

    # 2. Generate RSA key pair
    print(f"[*] Generating RSA key pair for '{voter_name}' …", end=" ", flush=True)
    pub, priv = generate_keypair(bits)
    print("done.")

    # 3. Save private key locally (voter keeps this)
    os.makedirs(KEYS_DIR, exist_ok=True)
    priv_path = os.path.join(KEYS_DIR, f"{voter_name}_private.json")
    with open(priv_path, "w") as fh:
        json.dump({"private_key": priv}, fh, indent=2)
    print(f"[+] Private key saved to: {priv_path}")
    print(f"    KEEP THIS FILE SAFE — it is your identity for voting.")

    # 4. Register public key (like sending public key to the professor)
    voters[voter_name] = {"public_key": pub}
    with open(VOTERS_FILE, "w") as fh:
        json.dump(voters, fh, indent=2)
    print(f"[+] Public key registered for '{voter_name}' in voters.json.")

    print(f"\n[✓] Key generation complete. You can now vote using your name.")


def _cli():
    print("=== Voter Key Generation ===\n")

    name = input("Enter your registered name: ").strip()
    if not name:
        print("[!] No name entered. Exiting.")
        return

    generate_voter_keys(name)


if __name__ == "__main__":
    _cli()
