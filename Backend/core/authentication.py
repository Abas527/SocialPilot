"""Password hashing and opaque access-token helpers."""
import base64
import binascii
import hashlib
import hmac
import secrets

_SCRYPT_N = 2**14
_SCRYPT_R = 8
_SCRYPT_P = 1
_SCRYPT_KEY_BYTES = 32
_SCRYPT_MAX_MEMORY = 32 * 1024 * 1024


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    derived = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=_SCRYPT_N,
        r=_SCRYPT_R,
        p=_SCRYPT_P,
        dklen=_SCRYPT_KEY_BYTES,
        maxmem=_SCRYPT_MAX_MEMORY,
    )
    return "scrypt${}${}${}${}${}".format(
        _SCRYPT_N,
        _SCRYPT_R,
        _SCRYPT_P,
        base64.urlsafe_b64encode(salt).decode("ascii"),
        base64.urlsafe_b64encode(derived).decode("ascii"),
    )


def verify_password(password: str, encoded_hash: str | None) -> bool:
    valid_hash = bool(encoded_hash)
    salt = bytes(16)
    expected = bytes(_SCRYPT_KEY_BYTES)
    try:
        if encoded_hash:
            algorithm, n, r, p, salt_text, expected_text = encoded_hash.split("$")
            salt = base64.urlsafe_b64decode(salt_text.encode("ascii"))
            expected = base64.urlsafe_b64decode(expected_text.encode("ascii"))
            valid_hash = (
                algorithm == "scrypt"
                and int(n) == _SCRYPT_N
                and int(r) == _SCRYPT_R
                and int(p) == _SCRYPT_P
                and len(salt) == 16
                and len(expected) == _SCRYPT_KEY_BYTES
            )
    except (ValueError, TypeError, UnicodeError, binascii.Error):
        valid_hash = False
    if not valid_hash:
        salt = bytes(16)
        expected = bytes(_SCRYPT_KEY_BYTES)
    actual = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=_SCRYPT_N,
        r=_SCRYPT_R,
        p=_SCRYPT_P,
        dklen=_SCRYPT_KEY_BYTES,
        maxmem=_SCRYPT_MAX_MEMORY,
    )
    return valid_hash and hmac.compare_digest(actual, expected)


def create_access_token() -> str:
    return secrets.token_urlsafe(32)
