import hashlib
import secrets

import bcrypt


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def hash_token_sha256(plain: str) -> str:
    return hashlib.sha256(plain.encode()).hexdigest()
