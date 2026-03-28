# Secure E-Voting System – Summary Report

## Overview

This project implements a client-server electronic voting system using
custom RSA encryption, SHA-256 hashing, and digital signatures over Python
TCP sockets. The system provides the following security guarantees:

| Property | Mechanism |
|---|---|
| **Confidentiality** | RSA encryption of the vote with the server's public key |
| **Authenticity** | RSA digital signature with the voter's private key |
| **Integrity** | SHA-256 hash signed alongside the ciphertext |
| **Vote Uniqueness** | Server maintains a set of voters who have already voted |

---

## Cryptographic Concepts

### Confusion

> *Confusion* means the relationship between the plaintext and ciphertext is
> as complex as possible, making it hard to deduce the key from the
> ciphertext.

RSA achieves confusion through modular exponentiation: `C = M^e mod n`.
Even for a short candidate name (e.g., "Alice"), the resulting ciphertext is
a number of hundreds of digits that bears no readable relationship to the
original text. An attacker who observes the ciphertext cannot determine which
candidate was chosen without the server's private key `d`.

### Diffusion

> *Diffusion* means that a small change in the plaintext (or key) propagates
> widely in the ciphertext.

SHA-256 provides the diffusion property. If a single bit of the input is
flipped, on average 128 of the 256 output bits change (the avalanche effect).
This is critical for the signature scheme: even a 1-bit change to the
encrypted vote produces a completely different hash, and therefore a
completely different signature. The server can detect any tampering with the
ciphertext by verifying the signature.

---

## System Limitations

| Limitation | Description |
|---|---|
| **Small key size** | 512-bit RSA keys are used for speed in this educational project. Real-world RSA uses ≥ 2048 bits. |
| **Voter private keys stored locally** | In a production system, private keys would never be stored on the same machine as the server registry. Each voter would hold their own key exclusively. |
| **No receipt-freeness** | The voter can prove to a third party how they voted (by revealing their key), enabling coercion. Receipt-free voting requires more advanced cryptography (e.g., commitment schemes). |
| **No coercion resistance** | A coercer who controls the voter's terminal can observe the vote before encryption. |
| **Single server** | The server is a single point of failure and trust. A real deployment would use threshold cryptography or multiple independent tallying authorities. |
| **No authentication beyond signatures** | There is no challenge-response protocol to prove the voter is online at vote time. Replay attacks are mitigated by the duplicate-vote check but not by a nonce. |
| **Plaintext candidate names** | Encrypting short, predictable strings (candidate names) is vulnerable to a chosen-plaintext dictionary attack. A real system would use probabilistic encryption (e.g., OAEP padding). |

---

## File Structure

```
ProjectDB/
├── crypto_utils.py        # RSA keygen, encrypt, decrypt, sign, verify, SHA-256
├── voting_server.py       # TCP server – verification, decryption, tallying
├── voter_client.py        # CLI client – encrypt, sign, send vote
├── voter_client_gui.py    # [BONUS] Tkinter GUI client
├── admin_setup.py         # Generate all keys, register voters & candidates
├── data/
│   ├── server_keys.json        # Server RSA key pair
│   ├── voters.json             # Voter registry {id → name, public_key}
│   ├── voter_private_keys.json # Client-side private keys (not loaded by server)
│   ├── candidates.json         # Candidate list
│   └── results.json            # Persisted tally & voted_ids
├── tests/
│   ├── test_crypto.py     # Unit tests for crypto_utils
│   └── test_integration.py# End-to-end voting flow tests
└── report.md              # This report
```

---

## How to Run

### 1. Setup (once before the election)

```bash
python admin_setup.py
```

Enter the number of candidates and voters when prompted. The script saves:
- `server_keys.json` (server public/private key pair)
- `voters.json` (public registry only)
- `voter_private_keys.json` (per-voter private keys; distribute securely to clients)
- `candidates.json` (candidate names)

### 2. Start the server

```bash
python voting_server.py
```
The server will also persist `results.json` (tally + voted_ids) so restarts do not allow double voting.

### 3. Cast a vote (CLI)

In a second terminal:

```bash
python voter_client.py
```

### 4. Cast a vote (GUI – bonus)

```bash
python voter_client_gui.py
```

### 5. Run tests

```bash
python -m pytest tests/ -v
```
