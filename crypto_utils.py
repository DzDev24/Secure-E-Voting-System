"""
crypto_utils.py – Cryptographic primitives for the e-voting system.

Implements:
  - Miller-Rabin primality test
  - RSA key-pair generation
  - RSA encryption / decryption
  - SHA-256 hashing (via hashlib)
  - Digital signature generation & verification
  - UTF-8 text ↔ integer conversion helpers
"""

import hashlib
import random


# ---------------------------------------------------------------------------
# Primality
# ---------------------------------------------------------------------------

def is_prime(n: int, k: int = 10) -> bool:
    """Miller-Rabin primality test.

    Args:
        n: Integer to test.
        k: Number of witness rounds (higher = more accurate).

    Returns:
        True if n is (probably) prime, False if composite.
    """
    if n < 2:
        return False
    if n == 2 or n == 3:
        return True
    if n % 2 == 0:
        return False

    # Write n-1 as 2^r * d
    r, d = 0, n - 1
    while d % 2 == 0:
        r += 1
        d //= 2

    for _ in range(k):
        a = random.randrange(2, n - 1)
        x = pow(a, d, n)
        if x == 1 or x == n - 1:
            continue
        for _ in range(r - 1):
            x = pow(x, 2, n)
            if x == n - 1:
                break
        else:
            return False
    return True


def generate_prime(bits: int) -> int:
    """Generate a random prime of the given bit-length.

    Args:
        bits: Desired bit-length of the prime.

    Returns:
        A probable prime integer of `bits` bits.
    """
    while True:
        candidate = random.getrandbits(bits)
        # Ensure the number has exactly `bits` bits and is odd
        candidate |= (1 << (bits - 1)) | 1
        if is_prime(candidate):
            return candidate


# ---------------------------------------------------------------------------
# Mathematical helpers
# ---------------------------------------------------------------------------

def gcd(a: int, b: int) -> int:
    """Return the GCD of a and b using the Euclidean algorithm."""
    while b:
        a, b = b, a % b
    return a


def mod_inverse(e: int, phi: int) -> int:
    """Return d such that e*d ≡ 1 (mod phi) using the extended Euclidean algorithm.

    Args:
        e: Public exponent.
        phi: Euler's totient.

    Returns:
        Modular inverse d.

    Raises:
        ValueError: If the inverse does not exist.
    """
    old_r, r = e, phi
    old_s, s = 1, 0

    while r != 0:
        quotient = old_r // r
        old_r, r = r, old_r - quotient * r
        old_s, s = s, old_s - quotient * s

    if old_r != 1:
        raise ValueError("Modular inverse does not exist.")
    return old_s % phi


# ---------------------------------------------------------------------------
# RSA key generation
# ---------------------------------------------------------------------------

def generate_keypair(bits: int = 512):
    """Generate an RSA key pair.

    Args:
        bits: Bit-length for each prime p and q (total modulus is 2*bits).

    Returns:
        Tuple (public_key, private_key) where each key is a dict with keys
        ``e`` (or ``d``) and ``n``.
    """
    e = 65537  # Standard public exponent

    while True:
        p = generate_prime(bits)
        q = generate_prime(bits)
        if p == q:
            continue
        n = p * q
        phi = (p - 1) * (q - 1)
        if gcd(e, phi) == 1:
            break

    d = mod_inverse(e, phi)
    public_key = {"e": e, "n": n}
    private_key = {"d": d, "n": n}
    return public_key, private_key


# ---------------------------------------------------------------------------
# RSA encryption / decryption
# ---------------------------------------------------------------------------

def encrypt(message_int: int, pub_key: dict) -> int:
    """RSA-encrypt an integer: C = M^e mod n.

    Args:
        message_int: Plaintext as a non-negative integer (must be < n).
        pub_key: Dict with keys ``e`` and ``n``.

    Returns:
        Ciphertext integer.
    """
    return pow(message_int, pub_key["e"], pub_key["n"])


def decrypt(cipher_int: int, priv_key: dict) -> int:
    """RSA-decrypt an integer: M = C^d mod n.

    Args:
        cipher_int: Ciphertext integer.
        priv_key: Dict with keys ``d`` and ``n``.

    Returns:
        Plaintext integer.
    """
    return pow(cipher_int, priv_key["d"], priv_key["n"])


# ---------------------------------------------------------------------------
# Text ↔ integer conversion
# ---------------------------------------------------------------------------

def text_to_int(text: str) -> int:
    """Convert a UTF-8 string to a non-negative integer (big-endian bytes).

    Args:
        text: Input string.

    Returns:
        Integer representation.
    """
    return int.from_bytes(text.encode("utf-8"), byteorder="big")


def int_to_text(number: int) -> str:
    """Convert a non-negative integer back to a UTF-8 string.

    Args:
        number: Integer produced by :func:`text_to_int`.

    Returns:
        Decoded string.
    """
    byte_length = (number.bit_length() + 7) // 8
    return number.to_bytes(byte_length, byteorder="big").decode("utf-8")


# ---------------------------------------------------------------------------
# Hashing
# ---------------------------------------------------------------------------

def sha256_hash(data) -> int:
    """Compute SHA-256 of *data* and return the digest as an integer.

    Args:
        data: Integer or string to hash.

    Returns:
        256-bit integer digest.
    """
    if isinstance(data, int):
        data_bytes = data.to_bytes((data.bit_length() + 7) // 8 or 1, byteorder="big")
    else:
        data_bytes = str(data).encode("utf-8")
    digest = hashlib.sha256(data_bytes).digest()
    return int.from_bytes(digest, byteorder="big")


# ---------------------------------------------------------------------------
# Digital signatures
# ---------------------------------------------------------------------------

def sign(message_int: int, priv_key: dict) -> int:
    """Sign a message: S = hash(message)^d mod n.

    Args:
        message_int: The message (or ciphertext) to sign, as an integer.
        priv_key: Dict with keys ``d`` and ``n``.

    Returns:
        Signature integer.
    """
    h = sha256_hash(message_int)
    # Reduce hash modulo n so it fits within the RSA modulus
    h_mod = h % priv_key["n"]
    return pow(h_mod, priv_key["d"], priv_key["n"])


def verify(message_int: int, signature: int, pub_key: dict) -> bool:
    """Verify a signature: check that S^e mod n == hash(message) mod n.

    Args:
        message_int: Original message (or ciphertext) integer.
        signature: Signature to verify.
        pub_key: Dict with keys ``e`` and ``n``.

    Returns:
        True if the signature is valid, False otherwise.
    """
    h = sha256_hash(message_int)
    h_mod = h % pub_key["n"]
    recovered = pow(signature, pub_key["e"], pub_key["n"])
    return recovered == h_mod
