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


def is_prime(n: int, k: int = 10) -> bool:
    """Miller-Rabin primality test.
    Checks if a number is prime using probability.

    Args:
        n: Integer to test.
        k: Number of witness rounds (higher = more accurate).
    """
    if n < 2:
        return False
    if n == 2 or n == 3:
        return True
    if n % 2 == 0:  # Quick check to rule out even numbers
        return False

# --- PHASE 2: The Setup ---
    # We want to break (n-1) down into an odd number multiplied by powers of 2.
    # Write n-1 as 2^r * d (factoring out powers of 2)
    r, d = 0, n - 1
    while d % 2 == 0:
        r += 1 # Count how many times we can halve it
        d //= 2 # Keep halving using floor division until 'd' is odd

    # --- PHASE 3: The Witness Rounds ---
    # Run the test k times
    for _ in range(k):
        a = random.randrange(2, n - 1) # Pick a random "witness" base 'a' between 2 and n-2
        # pow(a, d, n) efficiently calculates (a^d) mod n
        x = pow(a, d, n)

        # If x is 1 or n-1, it acts like a prime for this base 'a'. Move to next round.
        if x == 1 or x == n - 1:
            continue

        # If x wasn't 1 or n-1, we repeatedly square x up to (r - 1) times.
        # We are checking if any of the intermediate squareings equal n-1.
        for _ in range(r - 1):
            x = pow(x, 2, n)
            if x == n - 1:
                # We found n-1! The number passes the test for this base 'a'.
                # Break out of the inner squaring loop to start the next 'k' round.
                break
        else:
            return False  # Definitely not prime
    return True  # Probably prime


def generate_prime(bits: int) -> int:
    """Generate a random prime number of the given bit-length."""
    while True:
        # Generate a random integer with exactly 'bits' bits
        candidate = random.getrandbits(bits)
        # Force the highest and lowest bit to be 1 to ensure it's odd and big enough
        candidate |= (1 << (bits - 1)) | 1
        if is_prime(candidate):
            return candidate


def gcd(a: int, b: int) -> int:
    """Return the Greatest Common Divisor (GCD) using the Euclidean algorithm."""
    while b:
        # Swap 'a' and 'b', replacing 'b' with the remainder of a / b
        a, b = b, a % b
    return a


def mod_inverse(e: int, phi: int) -> int:
    """Return d such that (e * d) mod phi = 1 using the Extended Euclidean algorithm.
    This calculates the private exponent 'd' for RSA.
    """
    old_r, r = e, phi
    old_s, s = 1, 0

    while r != 0:
        quotient = old_r // r
        # Update r and s simultaneously
        old_r, r = r, old_r - quotient * r
        old_s, s = s, old_s - quotient * s

    if old_r != 1:
        raise ValueError("Modular inverse does not exist.")
    # Ensure the result is positive
    return old_s % phi


def generate_keypair(bits: int = 512):
    """Generate an RSA key pair (public and private keys)."""
    
    # Standard public exponent used universally in RSA
    e = 65537  

    while True:
        p = generate_prime(bits)
        q = generate_prime(bits)
        if p == q:
            continue
        n = p * q  # The modulus
        phi = (p - 1) * (q - 1)  # Euler's totient function
        # e and phi must be coprime (gcd = 1) for the math to work
        if gcd(e, phi) == 1:
            break

    # Calculate the private exponent
    d = mod_inverse(e, phi)
    public_key = {"e": e, "n": n}
    private_key = {"d": d, "n": n}
    return public_key, private_key


def encrypt(message_int: int, pub_key: dict) -> int:
    """RSA-encrypt an integer: C = M^e mod n.
    Provides confidentiality by scrambling the data with the public key.
    Only the matching private key can decrypt it.
    """
    # Using python's built-in modular exponentiation: (message_int ** e) % n
    return pow(message_int, pub_key["e"], pub_key["n"])


def decrypt(cipher_int: int, priv_key: dict) -> int:
    """RSA-decrypt an integer: M = C^d mod n."""
    return pow(cipher_int, priv_key["d"], priv_key["n"])


def text_to_int(text: str) -> int:
    """Convert a UTF-8 string into a large integer for RSA math."""
    # Convert string to bytes, then bytes to an integer (big-endian order)
    return int.from_bytes(text.encode("utf-8"), byteorder="big")


def int_to_text(number: int) -> str:
    """Convert an RSA integer back into a readable UTF-8 string."""
    # Calculate how many bytes are needed to store this number
    byte_length = (number.bit_length() + 7) // 8
    # Convert integer back to bytes, then decode bytes to a string
    return number.to_bytes(byte_length, byteorder="big").decode("utf-8")


def sha256_hash(data) -> int:
    """Compute the SHA-256 hash of data and return it as a large integer.
    Hashing ensures that if a single bit changes, the entire hash changes.
    """
    if isinstance(data, int):
        # Convert integer to bytes before hashing
        data_bytes = data.to_bytes((data.bit_length() + 7) // 8 or 1, byteorder="big")
    else:
        # Convert string to bytes
        data_bytes = str(data).encode("utf-8")
        
    # Get the 256-bit hash digest
    digest = hashlib.sha256(data_bytes).digest()
    # Convert the raw hash bytes back into a massive integer
    return int.from_bytes(digest, byteorder="big")


def sign(message_int: int, priv_key: dict) -> int:
    """Sign a message: S = hash(message)^d mod n.
    Proves authenticity. You hash the message, then "encrypt" the hash 
    with your PRIVATE key. Anyone can verify it with your PUBLIC key.
    """
    h = sha256_hash(message_int)
    # Ensure the hash is smaller than 'n' so RSA math works
    h_mod = h % priv_key["n"]
    return pow(h_mod, priv_key["d"], priv_key["n"])


def verify(message_int: int, signature: int, pub_key: dict) -> bool:
    """Verify a signature: check that S^e mod n == hash(message) mod n."""
    h = sha256_hash(message_int)
    h_mod = h % pub_key["n"]
    
    # "Decrypt" the signature using the public key
    recovered = pow(signature, pub_key["e"], pub_key["n"])
    
    # If the recovered hash matches the actual hash, the signature is authentic!
    return recovered == h_mod
