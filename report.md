# Secure E-Voting System

**Course:** Introduction to Computer Security — 3rd Year Engineering  
**Project:** Secure E-Voting System (Client-Server)

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [System Description and Architecture](#2-system-description-and-architecture)
3. [Security Mechanisms](#3-security-mechanisms)
4. [Implementation](#4-implementation)
5. [Tests and Validation](#5-tests-and-validation)
6. [Interfaces](#6-interfaces)
7. [Group Contributions](#7-group-contributions)
8. [Conclusion](#8-conclusion)

---

## 1. Introduction

In today's digital age, computer security has become a fundamental pillar of modern society. It shapes the way we communicate, exchange data, and protect our most sensitive information. In the domain of democracy, one of the most critical challenges remains that of voting: how can we allow every citizen to express their choice securely, while guaranteeing that this choice remains absolutely secret and that no entity — not even the system itself — can modify it? This fundamental paradox of modern cryptography becomes increasingly important as electoral processes around the world are progressively digitized.

Thus, it becomes necessary to design and implement a **Secure E-Voting System**. This project aims to solve this paradox by building a "digital ballot box" based on a **Client-Server** architecture, integrating **RSA** asymmetric encryption for confidentiality and **digital signatures** for authenticity. The system securely stores, verifies, and tallies votes, guaranteeing that:

- Only authorized voters can participate.
- The content of each ballot remains secret through encryption.
- Any attempt at modification is detected by SHA-256 hashing.
- No voter can vote more than once.
- The integrity of every vote is **mathematically proven**.

---

## 2. System Description and Architecture

### 2.1 Global Overview

The system follows a classic **Client-Server** architecture:

- **The Server (Digital ballot box)**: receives encrypted and signed votes,
  verifies the voter's identity, decrypts the ballot, and tallies the vote.
- **The Client (Voter)**: encrypts their choice with the server's public key,
  signs the encrypted ballot with their own private key, then sends it to the
  server.

Communication is done via **TCP sockets** on `localhost:5555`, with messages
exchanged in **JSON** format framed by a 4-byte big-endian header indicating
the message size.

### 2.2 Architecture Diagram

```
┌─────────────────────────────┐       TCP/JSON        ┌──────────────────────────────┐
│     CLIENT (Voter)          │ ◄──────────────────► │     SERVER (Ballot Box)      │
│                             │                       │                              │
│  voter_client_gui.py        │      localhost:5555    │  voting_server.py            │
│  voter_client.py            │                       │  (embedded in admin_gui.py)  │
│                             │                       │                              │
│  • Encrypts vote (RSA)      │   ──► {voter_name,   │  • Verifies signature        │
│  • Hashes (SHA-256)         │        ciphertext,    │  • Decrypts vote (RSA)       │
│  • Signs (RSA private key)  │        signature}     │  • Tallies the vote          │
└─────────────────────────────┘                       └──────────────────────────────┘
         │                                                        │
         ▼                                                        ▼
   data/keys/                                              data/server_private_key.json
   <name>_private.json                                     data/voters.json
   (voter's private key)                                   data/results.json
```

### 2.3 Complete Vote Flow

The voting process follows these precise steps:

```
Voter (Client)                              Server (Ballot Box)
──────────────                              ───────────────────
1. Convert candidate name to integer M
2. Encrypt:  C = M^e_server mod n_server
3. Hash:     H = SHA-256(C)
4. Sign:     S = H^d_voter mod n_voter
5. Send {voter_name, C, S}            ───►
                                             PHASE 1 — Identity (WHO)
                                             6. Look up public key by name
                                             7. Verify: S^e_voter mod n ≟ SHA-256(C)
                                             8. Check: voter not in voted_ids
                                             ─────────────────────────────────────
                                             PHASE 2 — Counting (WHAT)
                                             9.  Decrypt: M = C^d_server mod n_server
                                             10. Convert M back to candidate name
                                             11. Increment candidate counter
                                       ◄──── 12. Respond with result (accepted/rejected)
```

**Phase 1 / Phase 2 Separation:** The server's `_count_ballot()` method
receives only the encrypted vote — the voter's name is **never** passed to
this method. The code that counts votes therefore cannot correlate a ballot
with a specific voter, ensuring **relative anonymity**.

---

## 3. Security Mechanisms

### 3.1 RSA Encryption (Confidentiality)

RSA encryption protects the ballot content during transit:

- **Key generation:** The system generates RSA key pairs using 1024-bit prime
  numbers. Each key consists of `(e, n)` for the public part and `(d, n)` for
  the private part.
- **Encryption:** `C = M^e mod n` — the plaintext vote (e.g., "Candidate B")
  is converted to an integer then transformed into an unrecognizable number
  through modular exponentiation.
- **Decryption:** `M = C^d mod n` — only the server, which holds the private
  key `d`, can recover the original vote.
- **Result:** An observer on the network sees only the encrypted number `C`,
  which reveals absolutely nothing about the voter's choice.

**Confusion (Shannon):** RSA modular exponentiation creates a complex,
non-linear relationship between plaintext and ciphertext. Without the private
key `d`, one would need to factor `n = p × q`, which is computationally
infeasible for large prime numbers.

### 3.2 Digital Signature (Authenticity and Non-Repudiation)

The digital signature proves the voter's identity:

- **Signing:** The voter computes `H = SHA-256(C)` then
  `S = H^d_voter mod n_voter` using their private key.
- **Verification:** The server recomputes `SHA-256(C)` and verifies that
  `S^e_voter mod n_voter == SHA-256(C)`.
- **Authenticity:** Only the holder of the private key can produce a valid
  signature — an impostor cannot vote on behalf of another person.
- **Non-repudiation:** The voter cannot deny having voted, as their signature
  is mathematically bound to their unique private key.

### 3.3 SHA-256 Hashing (Integrity)

SHA-256 hashing guarantees that the vote has not been tampered with:

- **Avalanche property:** Changing a single bit in the encrypted vote `C`
  flips approximately 50% of the hash bits — any modification is detectable.
- **Process:** If an attacker intercepts and modifies `C` in transit, the hash
  recomputed by the server will not match the one signed by the voter, and
  signature verification will fail.

**Diffusion (Shannon):** SHA-256 spreads the influence of each input bit across
all output bits. This is the diffusion property: a minimal change in input
produces a radically different output.

### 3.4 Security Properties Summary

| Property          | Mechanism                                  | Guarantee                                                |
|-------------------|--------------------------------------------|----------------------------------------------------------|
| Confidentiality   | Vote encrypted with server's public key    | Only the server can decrypt                              |
| Authenticity      | Vote signed with voter's private key       | Only a registered voter can produce a valid signature    |
| Integrity         | SHA-256 hash before signing                | Any in-transit modification invalidates the signature    |
| Non-repudiation   | Verifiable signature                       | The voter cannot deny having voted                       |
| Uniqueness        | `voted_ids` set on the server              | A voter can only vote once                               |
| Relative Anonymity| Two-phase server processing                | Counting does not know the voter's identity              |

### 3.5 How Confusion and Diffusion Work Together

| Step                        | Property   | Effect                                   |
|-----------------------------|------------|------------------------------------------|
| `C = M^e mod n`             | Confusion  | Hides the vote content                   |
| `H = SHA-256(C)`            | Diffusion  | Detects any modification to the vote     |
| `S = H^d_voter mod n`       | Confusion  | Binds the hash to the voter's identity   |
| Verify `S^e ≟ SHA-256(C)`   | Both       | Confirms authenticity AND integrity      |

---

## 4. Implementation

### 4.1 Project Structure

```
Secure-E-Voting-System/
├── launcher.py              # Main entry point (launcher)
├── Start.bat                # Double-click to launch (Windows)
│
├── admin_setup_gui.py       # Election setup interface
├── admin_setup.py           # CLI version of setup
├── generate_keys_gui.py     # Key generation interface (voter)
├── generate_keys.py         # CLI version of key generation
│
├── admin_gui.py             # Admin panel (embedded server)
├── voting_server.py         # Multi-threaded TCP voting server
│
├── voter_client_gui.py      # Graphical voting interface
├── voter_client.py          # Shared client logic (encrypt, sign, send)
│
├── crypto_utils.py          # RSA + SHA-256 cryptographic primitives
│
├── REPORT.md                # This report
│
└── data/                    # Generated at runtime
    ├── server_public_key.json    # Server public key (shared)
    ├── server_private_key.json   # Server private key (server only)
    ├── candidates.json           # List of candidates
    ├── voters.json               # Voter registry + public keys
    ├── results.json              # Election state (tally, votes)
    └── keys/
        └── <name>_private.json   # Each voter's private key
```

### 4.2 Technologies Used

| Technology          | Usage                                                |
|---------------------|------------------------------------------------------|
| **Python 3.8+**     | Primary language                                     |
| **CustomTkinter**   | Modern graphical interfaces (pip install)             |
| **socket**          | TCP Client-Server communication                      |
| **threading**       | Multi-threaded server + non-blocking network calls    |
| **hashlib**         | SHA-256 hashing                                      |
| **json**            | Data exchange format and persistence                 |
| **struct**          | Binary headers (message size)                        |
| **random**          | Prime number generation for RSA                      |

All libraries are from the **Python standard library**, except `customtkinter`
which is the only external package required.

**Manual RSA implementation:** The RSA primitives (key generation, encryption,
decryption, signing, verification) are implemented **entirely from scratch** in
`crypto_utils.py`, without using any external cryptographic library. This
includes:
- Miller-Rabin primality testing
- Extended Euclidean algorithm for modular inverse
- Fast modular exponentiation (`pow(base, exp, mod)`)

### 4.3 Installation and Execution Procedure

#### Prerequisites

```bash
pip install customtkinter
```

#### Launching

Double-click **`Start.bat`** (Windows) or run:

```bash
python launcher.py
```

This opens the **Launcher** — a single window with buttons for each component.
No terminal commands are needed for any step.

#### Step 1 — Election Setup

From the launcher, click **Election Setup**:

1. Type each candidate name and click **Add**.
2. Type each voter name and click **Add**.
3. Click **Create Election** to generate server keys and save everything.

Files created in `data/`:

| File                        | Contents                                  |
|-----------------------------|-------------------------------------------|
| `server_public_key.json`    | Server RSA public key                     |
| `server_private_key.json`   | Server RSA private key                    |
| `voters.json`               | Voter registry (names, no keys yet)       |
| `candidates.json`           | List of candidate names                   |

#### Step 2 — Key Generation (Each Voter)

From the launcher, click **Generate My Keys**:

1. Enter your registered name.
2. Click **Generate Keys**.
3. Your private key is saved locally; your public key is registered.

Repeat for each voter.

#### Step 3 — Launch the Admin Panel

From the launcher, click **Admin Panel**. The panel displays a **server control
bar** at the top. Click **Start Server** to launch the voting server on
`localhost:5555`. A green indicator confirms the server is running.

#### Step 4 — Cast Votes

From the launcher, click **Voter Interface**:

1. Enter your name on the login page and click **Log In**.
2. Select a candidate using the radio buttons and click **Cast Vote**.
3. Confirm your choice on the confirmation page.

#### Step 5 — Monitoring and Closing

From the admin panel:

- **Start / Stop the server** via the control bar.
- **View live results** with animated progress bars and voter turnout.
- **Manually end the election** (triggers a runoff round if tied).
- **Reset the election** (automatically stops the server first).

The election **closes automatically** when 100% of voters have cast their ballot.

---

## 5. Tests and Validation

### 5.1 Test Cases

| Test Case                                | Expected Result                                 | Actual Result   |
|------------------------------------------|-------------------------------------------------|-----------------|
| Valid vote (registered voter)            | Vote accepted, counter incremented              | ✓ Passed        |
| Double vote (same voter)                 | Vote rejected: "Already voted"                  | ✓ Passed        |
| Unregistered voter                       | Rejected: "Voter not found in registry"         | ✓ Passed        |
| Voter without generated keys             | Rejected at login: "Generate keys first"        | ✓ Passed        |
| Invalid candidate (modified vote)        | Rejected: "Candidate not found"                 | ✓ Passed        |
| Invalid signature (tampered vote)        | Rejected: "Signature verification failed"       | ✓ Passed        |
| Auto-close (100% turnout)               | Election closed, results displayed              | ✓ Passed        |
| Tie between candidates                   | Runoff round with only tied candidates           | ✓ Passed        |
| Server not started                       | Clear error message in the interface             | ✓ Passed        |
| Vote reset                              | Counters reset to zero, server stopped           | ✓ Passed        |

### 5.2 Cryptographic Integrity Verification

For every received vote, the server performs in order:

1. **Public key lookup** for the voter by name.
2. **Signature verification**: `S^e mod n` must equal `SHA-256(C)`.
3. **Anti-double-vote check**: the name must not be in `voted_ids`.
4. **Decryption**: `M = C^d mod n` only if all 3 previous steps passed.
5. **Candidate validation**: the decrypted name must exist in the candidate list.

If **any single** step fails, the vote is rejected with a precise error message
sent back to the client.

### 5.3 Server Logs

The server prints a log for every operation to the console:

```
[*] Voting server listening on localhost:5555
[+] Connection from ('127.0.0.1', 52341)
[✓] VOTE ACCEPTED from Nazim → Candidate A (Round 1)
[✗] DOUBLE VOTE attempt by Nazim
[!] Signature verification failed for Midou
```

---

## 6. Interfaces

The system includes **5 graphical interfaces** built with CustomTkinter, all
sharing a unified light theme:

### 6.1 Launcher (`launcher.py`)

Single entry point. Displays 4 card-style buttons to launch each component:
Election Setup, Generate My Keys, Admin Panel, Voter Interface.

### 6.2 Election Setup (`admin_setup_gui.py`)

Interface allowing the admin to:
- Add/remove candidates (scrollable list).
- Add/remove voters (scrollable list).
- Generate server RSA keys and save the configuration.
- Both lists occupy 50% of the space each with independent scrolling.

### 6.3 Key Generation (`generate_keys_gui.py`)

Individual interface for each voter:
- Enter registered name.
- RSA key pair generated in the background (threaded).
- Success page with summary and file paths.

### 6.4 Admin Panel (`admin_gui.py`)

Real-time dashboard:
- **Server control bar**: start/stop the server with status indicator
  (green dot = running, gray dot = stopped).
- **Live results**: animated progress bars (ease-out) for each candidate with
  percentage and vote count.
- **Voter turnout**: automatically updated every 30 seconds.
- **Close and reset**: inline confirmation pages (no popups).
- **Threading**: all network calls run in the background to prevent UI freezing.

### 6.5 Voter Interface (`voter_client_gui.py`)

Multi-page voting flow:
1. **Login page**: name entry, validation.
2. **Voting page**: radio buttons for each candidate, scrollable list if more
   than 7 candidates.
3. **Confirmation page**: choice summary with Confirm / Go Back buttons.
4. **Result page**: acceptance confirmation or error message.
5. **Automatic detection** of round changes (runoff) and election closure.

*Note: All confirmations and error messages are displayed directly within the
interface — no popup dialog boxes are used.*

---

## 7. Group Contributions

### 7.1 Work Completed

- Complete implementation of RSA primitives (key generation, encryption,
  decryption, signing, verification) without external libraries.
- TCP Client-Server architecture with JSON protocol.
- Decentralized key generation system (each voter generates their own keys).
- Server key separation (public and private keys in separate files).
- Multi-threaded server with concurrency management (locks).
- Five graphical interfaces with unified theme.
- Complete election state persistence.
- Automatic closure at 100% turnout with tie handling (runoff rounds).

### 7.2 External Tools Used

| Tool                | Usage                                                    |
|---------------------|----------------------------------------------------------|
| **CustomTkinter**   | Graphical interface library (modern theme)                |
| **Python stdlib**   | socket, threading, hashlib, json, struct, random, os     |

### 7.3 Adaptations Made

- **Decentralized key generation**: adapted from an initial centralized model
  to one where each voter generates their own keys, in accordance with the
  project specification.
- **Server key separation**: the server's public and private keys are stored in
  separate files (`server_public_key.json` and `server_private_key.json`) to
  simulate publishing the public key "on the board."
- **Embedded server**: the voting server is embedded within the admin panel and
  runs as a background thread, eliminating the need for a separate terminal.
- **Name-based authentication**: voters identify by name (equivalent to
  presenting an ID card at the polling station).

### 7.4 Task Distribution

- **Student A:**
- **Student B:**
- **Student C:**
- **Student D:**

---

## 8. Conclusion

This project implements a functional and secure electronic voting system that
solves the fundamental paradox of voting: guaranteeing the voter's identity
while preserving ballot secrecy.

The cryptographic mechanisms employed — RSA encryption for confidentiality,
digital signatures for authenticity, and SHA-256 hashing for integrity —
together ensure that:

- No one can read a vote in transit (confidentiality).
- No one can vote on behalf of another person (authenticity).
- No one can modify a vote without being detected (integrity).
- A voter cannot vote more than once (uniqueness).
- Vote counting does not reveal the voter's identity (relative anonymity).

The system is fully functional with graphical interfaces for every step,
state persistence, and comprehensive edge case handling (double voting, ties,
automatic runoff rounds, closure at 100% turnout).

### Known Limitations

1. **Server trust**: the server performs both verification and decryption. A
   compromised server could theoretically correlate votes with voters.
2. **Single-machine environment**: in this academic demo, all files reside on
   one machine. In production, each voter would keep their private key
   exclusively on their own device.
3. **No verifiability**: voters cannot independently verify that their vote was
   correctly counted.
4. **Key size**: 1024-bit primes are sufficient for this academic exercise, but
   NIST recommends at least 2048 bits for production systems.
