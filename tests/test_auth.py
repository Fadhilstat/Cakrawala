from cakrawala.terminal.auth import OwnerPolicy, authorize_verified_claims


def test_owner_identity_uses_stable_subject() -> None:
    policy = OwnerPolicy("https://accounts.google.com", "client-id", "owner-sub")
    claims = {
        "iss": "https://accounts.google.com",
        "aud": "client-id",
        "sub": "owner-sub",
        "email": "display-only@example.com",
    }
    assert authorize_verified_claims(claims, policy)


def test_email_match_cannot_replace_subject() -> None:
    policy = OwnerPolicy("https://accounts.google.com", "client-id", "owner-sub")
    claims = {
        "iss": "https://accounts.google.com",
        "aud": "client-id",
        "sub": "attacker-sub",
        "email": "owner@example.com",
    }
    assert not authorize_verified_claims(claims, policy)
