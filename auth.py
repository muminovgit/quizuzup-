"""Password hashing and session-token helpers shared by the bot and the web API."""

import binascii
import hashlib
import os
import secrets

PBKDF2_ITERATIONS = 100_000
SESSION_TOKEN_BYTES = 32


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    derived = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PBKDF2_ITERATIONS)
    return f"{binascii.hexlify(salt).decode()}:{binascii.hexlify(derived).decode()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt_hex, hash_hex = stored.split(":", 1)
    except ValueError:
        return False
    salt = binascii.unhexlify(salt_hex)
    derived = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PBKDF2_ITERATIONS)
    return secrets.compare_digest(binascii.hexlify(derived).decode(), hash_hex)


def generate_password(length: int = 10) -> str:
    alphabet = "abcdefghjkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def generate_session_token() -> str:
    return secrets.token_urlsafe(SESSION_TOKEN_BYTES)
