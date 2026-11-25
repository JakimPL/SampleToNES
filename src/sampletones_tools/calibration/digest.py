import hashlib


def sha256_digest(data: bytes) -> str:
    """The SHA-256 digest of ``data`` in hexadecimal, which a run's fingerprint and a sample's checksum both spell."""
    return hashlib.sha256(data).hexdigest()
