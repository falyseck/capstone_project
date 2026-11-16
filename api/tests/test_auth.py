import auth


def test_password_hash_roundtrip():
    h = auth.hash_password("secret123")
    assert h != "secret123" and auth.verify_password("secret123", h) and not auth.verify_password("nope", h)


def test_token_contains_subject_and_role():
    token = auth.create_access_token({"sub": "u1", "role": "mother"})
    from jose import jwt
    claims = jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
    assert claims["sub"] == "u1" and claims["role"] == "mother" and "exp" in claims
