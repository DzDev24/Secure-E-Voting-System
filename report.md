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

| Component          | File                   | Role                                                  |
|--------------------| -----------------------|-------------------------------------------------------|
| Launcher           | `launcher.py`          | Main entry point — launches all other components      |
| Setup GUI          | `admin_setup_gui.py`   | Register candidates and voters, generate server keys  |
| Key Gen GUI        | `generate_keys_gui.py` | Each voter generates their own RSA key pair           |
| Crypto Primitives  | `crypto_utils.py`      | RSA keygen, encrypt/decrypt, hash, sign/verify        |
| Voting Server      | `voting_server.py`     | TCP server — verify, decrypt, and tally votes         |
| Voter Client Logic | `voter_client.py`      | Shared client logic (encrypt, sign, send)             |
| Voter GUI          | `voter_client_gui.py`  | Graphical voter interface (CustomTkinter)             |
| Admin GUI          | `admin_gui.py`         | Admin dashboard — embeds the server, live results     |

### Cryptographic Flow

```
Voter (Client)                              Server (Ballot Box)
──────────────                              ───────────────────
1. Convert candidate name to integer M
2. Encrypt:  C = M^e_server mod n_server    ──► Receives packet
3. Hash:     H = SHA-256(C)                      │
4. Sign:     S = H^d_voter mod n_voter           │
5. Send {voter_name, C, S}                  ──►  │
                                                  ▼
                                    PHASE 1 — Identity (WHO)
                                    6. Look up voter's public key by name
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

- **Phase 1 — Identity Verification:** The server checks WHO is voting (voter
  name lookup, signature verification, duplicate check). It never decrypts the
  vote during this phase.
- **Phase 2 — Anonymous Counting:** The `_count_ballot()` method receives only
  the encrypted vote — the voter's name is deliberately **not** passed. It
  decrypts and tallies the vote without knowing who cast it.

This architectural separation means the counting logic **cannot correlate** a
ballot with a specific voter, providing relative anonymity within the system.

---

## 5. Key Distribution Model

The system implements a decentralized key generation model as follows:

### Server Keys (Generated by Admin)

The admin generates the server's RSA key pair during setup.  The keys are stored
in **separate files** to enforce proper access control:

| File                        | Contents         | Who accesses it              |
|-----------------------------|------------------|------------------------------|
| `server_public_key.json`    | Public key only  | All voters (to encrypt votes)|
| `server_private_key.json`   | Private key only | Server only (to decrypt)     |

This simulates the real-world scenario described in the project specification:
*"The Server publishes its Public Key on the board for all students."*  The voter
client reads only `server_public_key.json` and has no access to the private key.

### Voter Keys (Generated by Each Voter)

Each registered voter generates their own RSA key pair by running
`generate_keys.py` on their machine.  This produces:

- **Private key** → saved locally in `data/keys/<name>_private.json` (voter
  keeps this file — it is their identity for voting).
- **Public key** → registered in `data/voters.json` (the equivalent of sending
  the public key to the professor for recording).

This matches the project specification: *"Each student generates their own RSA
key pair on their computer.  The administration records each student's Public Key
to verify their identity later."*

---

## 6. Authentication

Voters authenticate using their **name** (not a numeric ID).  When a voter
enters their name in the voter interface, the system:

1. Checks the name exists in the voter registry (`voters.json`).
2. Confirms the voter has generated their keys (public key is registered).
3. Checks the voter hasn't already voted in this round (`voted_ids`).
4. Loads the voter's private key from their personal key file.

This is equivalent to a student presenting their identity at the ballot box.

---

## 7. Additional Features

### Automatic Election Closure

When voter turnout reaches **100%** (all registered voters who have generated
keys have voted), the server automatically closes the election:

- If there is a **clear winner**, the election ends and results are finalized.
- If there is a **tie**, a runoff round is automatically initiated with only
  the tied candidates — all voters can vote again.

### Runoff Tie-Breaking

The system supports multi-round runoff elections:

- When a tie is detected (either by manual close or auto-close at 100% turnout),
  the server eliminates candidates with fewer votes and starts a new round.
- The round counter, active candidates, tally, and voted IDs are all reset and
  persisted, allowing multiple runoff rounds if needed.
- Both the voter and admin interfaces detect the round change and update
  automatically.

### Inline Messaging

All confirmations, warnings, and error messages are displayed **within the
interface** — no popup dialog boxes are used.  This includes:

- Vote confirmation (a dedicated page showing the selected candidate with
  Confirm/Go Back buttons).
- Vote result feedback (accepted/rejected with details).
- Admin actions (end election, reset) with inline confirmation pages.
- Status banners showing operation results at the top of the admin dashboard.

---

## 8. System Limitations

Despite its security features, this system has several acknowledged limitations:

1. **Server Trust:** The server holds its own RSA private key and performs both
   identity verification and vote decryption. A compromised or malicious server
   could theoretically record the mapping between voters and their decrypted
   votes (even with the two-phase separation, both phases run on the same
   machine in the same process).

2. **Single-Machine Demo:** While key generation is logically separated (each
   voter runs `generate_keys.py` independently), all files reside on one machine
   for this academic demo. In a real deployment, each voter's private key would
   exist exclusively on their own device.

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

### Quick Start

Double-click **`Start.bat`** (Windows) or run:

```bash
python launcher.py
```

This opens the **Launcher** — a single window with buttons to open each
component.  No terminal commands are needed for any step.

### Step 1 — Election Setup

From the launcher, click **Election Setup**.  In the setup interface:

1. Type each candidate name and click **Add**.
2. Type each voter name and click **Add**.
3. Click **Create Election** to generate server keys and save everything.

This creates the following files in the `data/` directory:

| File                      | Contents                                  |
|---------------------------|-------------------------------------------|
| `server_public_key.json`  | Server RSA public key (shared with voters)|
| `server_private_key.json` | Server RSA private key (server only)      |
| `voters.json`             | Voter registry (names, no keys yet)       |
| `candidates.json`         | List of candidate names                   |

### Step 2 — Key Generation (Each Voter)

From the launcher, click **Generate My Keys**:

1. Enter your registered name.
2. Click **Generate Keys**.
3. Your private key is saved locally; your public key is registered.

Repeat for each voter.

### Step 3 — Launch the Admin Panel

From the launcher, click **Admin Panel**.  The admin panel displays a **server
control bar** at the top.  Click **Start Server** to launch the voting server on
`localhost:5555`.  A green indicator confirms the server is running.

### Step 4 — Cast Votes

From the launcher, click **Voter Interface**:

1. Enter your name on the login page and click **Log In**.
2. Select a candidate using the radio buttons and click **Cast Vote**.
3. Confirm your choice on the confirmation page.

### Step 5 — Monitor and Close (Admin Panel)

From the admin panel, the admin can:
- **Start / Stop the server** using the server control bar.
- **View live results** with animated progress bars and voter turnout.
- **Manually end the election** (triggers a runoff round if there is a tie).
- **Reset the election** (automatically stops the server first).

The election also **closes automatically** when all registered voters have voted.
Closing the admin panel window automatically stops the server.

---

## 10. Bonus Features

- **Graphical User Interface:** All interactions are handled through
  CustomTkinter-based GUIs with a clean light theme, card-based layouts, and
  smooth animations:
  - `launcher.py` — Central entry point with buttons for each component.
  - `admin_setup_gui.py` — Visual election setup (add/remove candidates and
    voters, generate server keys).
  - `generate_keys_gui.py` — Per-voter key generation with success feedback.
  - `voter_client_gui.py` — Multi-page voting flow (login → vote → confirm →
    result) with automatic state polling and runoff round detection.
  - `admin_gui.py` — Full admin dashboard with integrated server control
    (start/stop), animated progress bars, inline status messages, and threaded
    network calls to prevent UI freezing.

- **Integrated Server:** The voting server is embedded directly in the admin
  panel and runs in a background thread.  No separate terminal is needed — the
  admin starts and stops the server with a single button click.

- **Persistence:** The server saves the complete election state (tally, voted
  names, current round, active candidates) to `data/results.json` after every
  vote, allowing it to survive restarts without losing any data.
