from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.revoked_token import RevokedToken


def revoke(db: Session, *, jti: str, expires_at: datetime) -> None:
    if db.get(RevokedToken, jti) is not None:
        return  # already revoked, nothing to do
    db.add(RevokedToken(jti=jti, expires_at=expires_at))
    db.commit()


def is_revoked(db: Session, *, jti: str) -> bool:
    return db.get(RevokedToken, jti) is not None


def prune_expired(db: Session) -> int:
    """Deletes denylist entries whose token has naturally expired anyway (they're no longer
    needed since an expired token is already rejected by signature/exp validation regardless).
    Not called automatically -- wire this into a periodic job (cron, Celery beat, etc.) in a real
    deployment so the table doesn't grow unbounded; for the traffic this reference app expects,
    it's small enough not to matter for a demo/portfolio deployment."""
    now = datetime.now(timezone.utc)
    deleted = db.query(RevokedToken).filter(RevokedToken.expires_at < now).delete()
    db.commit()
    return deleted
