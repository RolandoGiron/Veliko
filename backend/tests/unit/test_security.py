import pytest

from app.auth import security


def test_password_hash_roundtrip():
    h = security.hash_password("s3cret-pw")
    assert h != "s3cret-pw"
    assert security.verify_password("s3cret-pw", h) is True
    assert security.verify_password("wrong", h) is False


def test_jwt_roundtrip():
    token = security.create_access_token(subject="user-123")
    assert security.decode_access_token(token) == "user-123"


def test_jwt_rejects_tampered_token():
    token = security.create_access_token(subject="user-123")
    with pytest.raises(security.InvalidToken):
        security.decode_access_token(token + "x")
