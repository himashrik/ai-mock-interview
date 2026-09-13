import uuid

from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.types import CHAR, TypeDecorator


class GUID(TypeDecorator):
    """Platform-independent UUID column type.

    Uses PostgreSQL's native `uuid` type in production (via psycopg2, which
    accepts both `uuid.UUID` and plain hex-string values transparently), and
    falls back to a `CHAR(32)` hex-string representation on dialects without
    native UUID support (notably SQLite, used by the fast unit/integration
    test suite). Application code always sees plain `uuid.UUID` objects on
    read, and can pass either a `uuid.UUID` or a valid UUID string on write,
    regardless of which dialect is active underneath.

    This exists specifically because `sqlalchemy.dialects.postgresql.UUID(as_uuid=True)`
    silently requires bind values to already be `uuid.UUID` instances once SQLAlchemy
    falls back to CHAR-based storage for non-Postgres dialects -- passing a plain string
    (e.g. a JWT subject claim, or a UUID echoed back from a JSON API response) raises
    `AttributeError: 'str' object has no attribute 'hex'` deep inside the bind processor.
    That's a test-infrastructure gap, not an application bug: the same code path is fine
    against real Postgres. This type makes both paths behave identically.
    """

    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        return dialect.type_descriptor(CHAR(32))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if not isinstance(value, uuid.UUID):
            value = uuid.UUID(str(value))
        if dialect.name == "postgresql":
            return str(value)
        return value.hex

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        if isinstance(value, uuid.UUID):
            return value
        return uuid.UUID(value)
