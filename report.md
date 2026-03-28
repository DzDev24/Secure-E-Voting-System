# Secure E-Voting System — Summary Report

**Course:** Introduction to Computer Security — 3rd Year Engineering  
**Project:** Secure E-Voting System (Client-Server)

---

## 1. System Overview

This project implements a secure electronic voting system using a Client-Server
architecture built on TCP sockets.  The system guarantees **confidentiality**,
**authenticity**, **integrity**, and **uniqueness** of votes through RSA
asymmetric encryption, SHA-256 hashing, and digital signatures.

### Architecture

| Component          | File                 | Role                                         |
|--------------------|----------------------|----------------------------------------------|
| Admin Setup        | `admin_setup.py`     | Generate RSA keys for server and all voters   |
| Crypto Primitives  | `crypto_utils.py`    | RSA keygen, encrypt/decrypt, hash, sign/verify|
| Voting Server      | `voting_server.py`   | TCP server — verify, decrypt, and tally votes |
| CLI Client         | `voter_client.py`    | Command-line voter interface                  |
| GUI Client (Bonus) | `voter_client_gui.py`| Graphical voter interface with tkinter        |

### Cryptographic Flow

```
Voter (Client)                              Server (Ballot Box)
──────────────                              ───────────────────
1. Convert candidate name to integer M
2. Encrypt:  C = M^e_server mod n_server    ──► Receives packet
3. Hash:     H = SHA-256(C)                      │
4. Sign:     S = H^d_voter mod n_voter           │
5. Send {voter_id, C, S}                    ──►  │
                                                  ▼
                                    PHASE 1 — Identity (WHO)
                                    6. Look up voter public key
                                    7. Verify: S^e_voter mod n ≟ SHA-256(C)
                                    8. Check: voter not in voted_ids
                                    ─────────────────────────────
                                    PHASE 2 — Counting (WHAT)
                                    9.  Decrypt: M = C^d_server mod n_server
                                    10. Convert M back to candidate name
                                    11. Tally += 1
```

---

## 2. The Roles of Confusion and Diffusion

In classical cryptography, **Confusion** and **Diffusion** are the two
fundamental properties that make a cipher secure (as defined by Claude Shannon).

### Confusion — RSA Encryption

**Confusion** obscures the relationship between the plaintext and the
ciphertext.  Each bit of the ciphertext should depend on multiple parts of the
key, making it impossible to deduce the key from the ciphertext.

In this project, RSA provides confusion:

- **Encryption:** `C = M^e mod n` transforms the readable vote ("Candidate B")
  into an unrecognizable integer.  The modular exponentiation creates a complex,
  non-linear mapping between input and output.
- **Key dependency:** Without the private exponent `d`, reversing the encryption
  requires factoring `n = p × q`, which is computationally infeasible for large
  primes.
- **Practical result:** The encrypted vote `C` reveals absolutely nothing about
  the original candidate choice to any observer on the network.

### Diffusion — SHA-256 Hashing

**Diffusion** spreads the influence of each input bit across many output bits.
A small change in the input should produce a dramatically different output
(the "avalanche effect").

In this project, SHA-256 provides diffusion:

- **Hashing before signing:** `H = SHA-256(C)` produces a fixed 256-bit digest.
  Even a 1-bit change in the encrypted vote `C` causes approximately half of the
  hash bits to flip.
- **Integrity guarantee:** If an attacker intercepts the packet and modifies `C`
  (e.g., changing a vote from "Candidate A" to "Candidate C"), the hash will be
  completely different from the one the voter originally signed, and the
  server's signature verification will fail.
- **Practical result:** Any tampering with the vote in transit is immediately
  detected and rejected.

### How They Work Together

| Step                      | Property   | Effect                                  |
|---------------------------|------------|-----------------------------------------|
| `C = M^e mod n`           | Confusion  | Hides the vote content                  |
| `H = SHA-256(C)`          | Diffusion  | Detects any modification to the vote    |
| `S = H^d_voter mod n`     | Confusion  | Binds the hash to the voter's identity  |
| Verify `S^e ≟ SHA-256(C)` | Both       | Confirms authenticity AND integrity     |

---

## 3. Security Guarantees

| Property          | Mechanism                                  | Guarantee                                                |
|-------------------|--------------------------------------------|----------------------------------------------------------|
| Confidentiality   | Vote encrypted with server's public key    | Only the server can decrypt — nobody else can see the vote|
| Authenticity      | Vote signed with voter's private key       | Only a registered voter can produce a valid signature     |
| Integrity         | SHA-256 hash before signing                | Any in-transit modification invalidates the signature     |
| Non-repudiation   | Signature is verifiable                    | The voter cannot deny having cast their vote              |
| Uniqueness        | `voted_ids` set on the server              | A student cannot vote more than once                      |
| Relative Anonymity| Two-phase server processing                | Identity verification is separated from vote counting     |

---

## 4. Relative Anonymity Design

The server processes each vote in two strictly separated phases:

- **Phase 1 — Identity Verification:** The server checks WHO is voting (voter ID
  lookup, signature verification, duplicate check). It never decrypts the vote.
- **Phase 2 — Anonymous Counting:** The `_count_ballot()` method receives only
  the encrypted vote — no voter ID is passed. It decrypts and tallies the vote
  without knowing who cast it.

This architectural separation means the counting logic **cannot correlate** a
ballot with a specific voter, providing relative anonymity within the system.

---

## 5. System Limitations

Despite its security features, this system has several acknowledged limitations:

1. **Server Trust:** The server holds its own RSA private key and performs both
   identity verification and vote decryption. A compromised or malicious server
   could theoretically record the mapping between voters and their decrypted
   votes (even with our two-phase separation, both phases run on the same
   machine in the same process).

2. **Shared Key Storage:** In this academic implementation, all voter private
   keys are stored in a single file (`voter_private_keys.json`) for convenience.
   In a real deployment, each voter would generate and store their private key
   exclusively on their own device.

3. **No Receipt-Freeness:** A voter can prove how they voted by showing their
   private key and the candidate name, which enables potential vote buying or
   coercion.

4. **No Forward Secrecy:** If the server's private key is compromised after the
   election, all past encrypted votes can be decrypted retroactively.

5. **Key Size:** While the default 1024-bit primes (2048-bit modulus) are
   sufficient for this academic exercise, NIST currently recommends at least
   2048-bit primes (4096-bit modulus) for production systems.

6. **No Verifiability:** Voters have no way to independently verify that their
   vote was correctly counted without trusting the server.

---

## 6. How to Run

### Prerequisites

- **Python 3.8+** (no external packages required — only standard library modules
  `socket`, `hashlib`, `json`, `struct`, `threading`, and `tkinter` are used).

### Step 1 — Election Setup

Run the admin setup script to generate RSA keys for the server and all voters,
and to register the candidate list:

```bash
python admin_setup.py
```

You will be prompted to enter:
1. The number of candidates and their names (e.g., Candidate A, Candidate B, Candidate C).
2. The number of voters and their names (e.g., Student 1, Student 2, …).

This creates the `data/` directory with four JSON files:

| File                      | Contents                                  |
|---------------------------|-------------------------------------------|
| `server_keys.json`        | Server RSA public + private key pair      |
| `voters.json`             | Voter registry (voter IDs + public keys)  |
| `voter_private_keys.json` | Voter private keys (one per voter)        |
| `candidates.json`         | List of candidate names                   |

### Step 2 — Start the Voting Server

In a **separate terminal**, start the server:

```bash
python voting_server.py
```

The server listens on `localhost:5555` and waits for incoming votes. Keep this
terminal open for the duration of the election.

### Step 3 — Cast Votes

Voters can use either the **CLI** or the **GUI** client:

**Option A — Command Line:**
```bash
python voter_client.py
```
Enter your voter ID (e.g., `STU_001`), then select a candidate by number.

**Option B — Graphical Interface (Bonus):**
```bash
python voter_client_gui.py
```
1. Enter your voter ID on the login page and click **Log In**.
2. Select a candidate using the radio buttons and click **Cast Vote**.
3. Confirm your choice in the dialog that appears.

### Step 4 — Close the Election and View Results

**From the GUI:** Click the **"Close Election & View Results"** button on the
login page. The final tally and winner are displayed.

**From the CLI:** You can send the close command programmatically:
```python
from voter_client import close_election
print(close_election())
```

**From the server terminal:** Press `Ctrl+C` to stop the server. The final
results will be printed to the console and saved to `data/results.json`.

---

## 7. Bonus Features

- **Graphical User Interface:** A tkinter-based GUI (`voter_client_gui.py`)
  provides a multi-page voting experience with login authentication, ballot
  selection, vote confirmation, and admin controls for closing the election.

- **Persistence:** The server saves the tally and voted IDs to
  `data/results.json` after every vote, allowing it to survive restarts without
  losing election state.
