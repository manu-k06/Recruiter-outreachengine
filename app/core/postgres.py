"""Hosted storage using the same record operations as the local SQLite store."""
from contextlib import contextmanager
from threading import Lock

import psycopg
from psycopg.rows import dict_row

from app.core.storage import SQLiteStore, StorageUnavailableError


class PostgresConnection:
    """Adapt our internal parameter placeholders; values always stay separate."""
    def __init__(self, connection):
        self.connection = connection

    def execute(self, query, parameters=()):
        return self.connection.execute(query.replace("?", "%s"), parameters)


class PostgresStore(SQLiteStore):
    def __init__(self, url: str, daily_limit: int = 25):
        self.url = url
        self.daily_limit = daily_limit
        self._initialized = False
        self._init_lock = Lock()

    @contextmanager
    def _connect(self):
        # Short-lived connections work with a hosted provider's pooled URL.
        # The context commits on success and rolls back on failure, then closes.
        with psycopg.connect(self.url, row_factory=dict_row, connect_timeout=10,
                            prepare_threshold=None) as connection:
            yield PostgresConnection(connection)

    @contextmanager
    def _database(self):
        self.initialize()
        try:
            with self._connect() as connection:
                yield connection
        except psycopg.Error as exc:
            raise StorageUnavailableError("Persistent storage is unavailable.") from exc

    def initialize(self):
        with self._init_lock:
            if self._initialized:
                return
            try:
                with self._connect() as connection:
                    # One deployment creates the schema while others wait.
                    connection.execute("SELECT pg_advisory_xact_lock(721940101)")
                    connection.execute("CREATE TABLE IF NOT EXISTS outreach_schema (version INTEGER NOT NULL)")
                    row = connection.execute("SELECT version FROM outreach_schema").fetchone()
                    if row and row["version"] != 1:
                        raise StorageUnavailableError("Unsupported database schema version.")
                    if not row:
                        connection.execute("""CREATE TABLE records (
                            id TEXT PRIMARY KEY, kind TEXT NOT NULL CHECK(kind IN ('profile','discovery','outbox')),
                            created_at TEXT NOT NULL, payload TEXT NOT NULL, status TEXT, sent_at TEXT
                        )""")
                        connection.execute("CREATE INDEX records_kind_created ON records(kind, created_at DESC, id)")
                        connection.execute("CREATE INDEX records_sent ON records(kind, status, sent_at)")
                        connection.execute("""CREATE TABLE events (
                            id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                            record_id TEXT NOT NULL REFERENCES records(id), kind TEXT NOT NULL,
                            action TEXT NOT NULL, created_at TEXT NOT NULL
                        )""")
                        connection.execute("CREATE INDEX events_record ON events(record_id, id)")
                        connection.execute("CREATE TABLE settings (key TEXT PRIMARY KEY, value INTEGER NOT NULL CHECK(value >= 0))")
                        connection.execute("INSERT INTO outreach_schema(version) VALUES (1)")
                    connection.execute("INSERT INTO settings(key,value) VALUES ('daily_send_limit', ?) ON CONFLICT(key) DO NOTHING", (self.daily_limit,))
                self._initialized = True
            except psycopg.Error as exc:
                raise StorageUnavailableError("Persistent storage is unavailable.") from exc

    def _begin_write(self, connection, record_id):
        # A transaction-scoped lock also protects new IDs, which have no row yet.
        connection.execute("SELECT pg_advisory_xact_lock(hashtextextended(?, 0))", (record_id,))

    def _begin_read(self, connection):
        connection.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
