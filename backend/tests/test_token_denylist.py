from datetime import datetime, timedelta, timezone

from app.services import token_denylist


def test_token_not_revoked_by_default(db_session):
    assert token_denylist.is_revoked(db_session, jti="some-jti") is False


def test_revoke_then_is_revoked(db_session):
    token_denylist.revoke(db_session, jti="abc123", expires_at=datetime.now(timezone.utc) + timedelta(minutes=15))
    assert token_denylist.is_revoked(db_session, jti="abc123") is True


def test_revoke_is_idempotent(db_session):
    expires = datetime.now(timezone.utc) + timedelta(minutes=15)
    token_denylist.revoke(db_session, jti="dup", expires_at=expires)
    token_denylist.revoke(db_session, jti="dup", expires_at=expires)  # must not raise (e.g. PK conflict)
    assert token_denylist.is_revoked(db_session, jti="dup") is True


def test_prune_expired_removes_only_past_entries(db_session):
    token_denylist.revoke(db_session, jti="expired", expires_at=datetime.now(timezone.utc) - timedelta(minutes=1))
    token_denylist.revoke(db_session, jti="still-valid", expires_at=datetime.now(timezone.utc) + timedelta(minutes=15))

    deleted = token_denylist.prune_expired(db_session)

    assert deleted == 1
    assert token_denylist.is_revoked(db_session, jti="expired") is False
    assert token_denylist.is_revoked(db_session, jti="still-valid") is True


class TestLogoutRevocationApi:
    def test_logged_out_access_token_is_immediately_rejected(self, client):
        client.post("/auth/register", json={"email": "revoke@example.com", "password": "password123", "full_name": "R"})
        login = client.post("/auth/login", json={"email": "revoke@example.com", "password": "password123"})
        access_token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}

        # token works before logout
        assert client.get("/auth/me", headers=headers).status_code == 200

        resp = client.post("/auth/logout", headers=headers)
        assert resp.status_code == 204

        # the SAME access token must now be rejected immediately, not just after its natural expiry
        resp = client.get("/auth/me", headers=headers)
        assert resp.status_code == 401
        assert resp.json()["detail"] == "Token has been revoked"

    def test_logout_without_credentials_still_clears_cookie_and_succeeds(self, client):
        # Logout should be safe to call even without a bearer token (e.g. an already-expired
        # session): it should still clear the refresh cookie and return 204, not error.
        resp = client.post("/auth/logout")
        assert resp.status_code == 204

    def test_revocation_is_specific_to_the_logged_out_token_not_the_user(self, client):
        client.post("/auth/register", json={"email": "twosessions@example.com", "password": "password123", "full_name": "T"})

        login1 = client.post("/auth/login", json={"email": "twosessions@example.com", "password": "password123"})
        token1 = login1.json()["access_token"]

        login2 = client.post("/auth/login", json={"email": "twosessions@example.com", "password": "password123"})
        token2 = login2.json()["access_token"]

        # log out session 1 only
        client.post("/auth/logout", headers={"Authorization": f"Bearer {token1}"})

        assert client.get("/auth/me", headers={"Authorization": f"Bearer {token1}"}).status_code == 401
        # session 2's token must remain valid -- revocation is per-token (per jti), not per-user
        assert client.get("/auth/me", headers={"Authorization": f"Bearer {token2}"}).status_code == 200
