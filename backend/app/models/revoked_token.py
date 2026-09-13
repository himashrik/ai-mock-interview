from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RevokedToken(Base):
    """A denylist of revoked access-token `jti` claims.

    Populated on logout so an already-issued access token stops working immediately, rather than
    remaining valid until its natural (short) expiry. Rows are safe to prune once `expires_at` is
    in the past -- see the note in `app/services/token_denylist.py`.
    """

    __tablename__ = "revoked_tokens"

    jti: Mapped[str] = mapped_column(String(32), primary_key=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
