"""Small SQLite repository. Every record and its history event commit together."""
from contextlib import contextmanager
from datetime import datetime, time, timedelta, timezone
from pathlib import Path
import sqlite3
from threading import Lock
from uuid import uuid4

from app.schemas.outbox import OutboxItem, OutboxStats, OutboxStatus
from app.schemas.pitch import CandidateProfile
from app.schemas.recruiter import DiscoverRecruitersRequest, DiscoverRecruitersResponse
from app.schemas.storage import SavedProfile, SavedDiscovery, HistoryEvent


class StorageUnavailableError(RuntimeError):
    pass


class RecordConflictError(RuntimeError):
    pass


class RecordNotFoundError(RuntimeError):
    pass


class SQLiteStore:
    """Connections are short lived; workers share a file, never a Python dictionary."""

    def __init__(self, path: str | Path, daily_limit: int = 25):
        self.path = Path(path).expanduser().resolve()
        self.daily_limit = daily_limit
        self._initialized = False
        self._init_lock = Lock()

    def initialize(self):
        with self._init_lock:
            if self._initialized:
                return
            try:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                with self._connect() as connection:
                    # Serializes first-time setup across processes as well as threads.
                    connection.execute("BEGIN IMMEDIATE")
                    version = connection.execute("PRAGMA user_version").fetchone()[0]
                    if version > 1:
                        raise StorageUnavailableError("Database schema is newer than this application.")
                    if version == 0:
                        connection.execute("""CREATE TABLE records (
                            id TEXT PRIMARY KEY,
                            kind TEXT NOT NULL CHECK(kind IN ('profile', 'discovery', 'outbox')),
                            created_at TEXT NOT NULL,
                            payload TEXT NOT NULL,
                            status TEXT,
                            sent_at TEXT
                        )""")
                        connection.execute("CREATE INDEX records_kind_created ON records(kind, created_at DESC, id)")
                        connection.execute("CREATE INDEX records_sent ON records(kind, status, sent_at)")
                        connection.execute("""CREATE TABLE events (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            record_id TEXT NOT NULL REFERENCES records(id),
                            kind TEXT NOT NULL,
                            action TEXT NOT NULL,
                            created_at TEXT NOT NULL
                        )""")
                        connection.execute("CREATE INDEX events_record ON events(record_id, id)")
                        connection.execute("CREATE TABLE settings (key TEXT PRIMARY KEY, value INTEGER NOT NULL CHECK(value >= 0))")
                        connection.execute("PRAGMA user_version = 1")
                    # The first startup establishes the shared cap. Later workers cannot reset it.
                    connection.execute("INSERT OR IGNORE INTO settings(key, value) VALUES ('daily_send_limit', ?)", (self.daily_limit,))
                self._initialized = True
            except (sqlite3.Error, OSError) as exc:
                raise StorageUnavailableError("Persistent storage is unavailable.") from exc

    @contextmanager
    def _connect(self):
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        try:
            connection.execute("PRAGMA foreign_keys = ON")
            # The connection context commits on success and rolls back on any failure.
            with connection:
                yield connection
        finally:
            connection.close()

    @contextmanager
    def _database(self):
        self.initialize()
        try:
            with self._connect() as connection:
                yield connection
        except sqlite3.Error as exc:
            raise StorageUnavailableError("Persistent storage is unavailable.") from exc

    def _save(self, kind, record, action, status=None, sent_at=None):
        with self._database() as connection:
            connection.execute(
                "INSERT INTO records(id, kind, created_at, payload, status, sent_at) VALUES (?, ?, ?, ?, ?, ?)",
                (record.id, kind, record.created_at.astimezone(timezone.utc).isoformat(), record.model_dump_json(), status,
                 sent_at.astimezone(timezone.utc).isoformat() if sent_at else None),
            )
            self._append_event(connection, record.id, kind, action, record.created_at)
        return record

    def _append_event(self, connection, record_id, kind, action, created_at):
        connection.execute(
            "INSERT INTO events(record_id, kind, action, created_at) VALUES (?, ?, ?, ?)",
            (record_id, kind, action, created_at.astimezone(timezone.utc).isoformat()),
        )

    def _get(self, kind, record_id, model):
        with self._database() as connection:
            row = connection.execute("SELECT payload FROM records WHERE kind = ? AND id = ?", (kind, record_id)).fetchone()
        return model.model_validate_json(row["payload"]) if row else None

    def _list(self, kind, model, limit=50, offset=0, status=None):
        query = "SELECT payload FROM records WHERE kind = ?"
        parameters = [kind]
        if status is not None:
            query += " AND status = ?"
            parameters.append(status)
        query += " ORDER BY created_at DESC, id DESC LIMIT ? OFFSET ?"
        parameters.extend([limit, offset])
        with self._database() as connection:
            rows = connection.execute(query, parameters).fetchall()
        return [model.model_validate_json(row["payload"]) for row in rows]

    def save_profile(self, candidate: CandidateProfile) -> SavedProfile:
        record = SavedProfile(id=str(uuid4()), created_at=datetime.now(timezone.utc), candidate=candidate)
        return self._save("profile", record, "profile_saved")

    def get_profile(self, record_id):
        return self._get("profile", record_id, SavedProfile)

    def list_profiles(self, limit=50, offset=0):
        return self._list("profile", SavedProfile, limit, offset)

    def save_discovery(self, request: DiscoverRecruitersRequest, result: DiscoverRecruitersResponse) -> SavedDiscovery:
        record_id = str(uuid4())
        result = result.model_copy(update={"discovery_id": record_id})
        record = SavedDiscovery(id=record_id, created_at=datetime.now(timezone.utc), request=request, result=result)
        return self._save("discovery", record, "discovery_saved")

    def get_discovery(self, record_id):
        return self._get("discovery", record_id, SavedDiscovery)

    def list_discoveries(self, limit=50, offset=0):
        return self._list("discovery", SavedDiscovery, limit, offset)

    def save_outbox(self, item: OutboxItem):
        return self._save("outbox", item, f"outbox_{item.status.value}", item.status.value, item.sent_at)

    def get_outbox(self, record_id):
        return self._get("outbox", record_id, OutboxItem)

    def save_workflow_draft(self, item: OutboxItem):
        """A request ID prevents a repeated Save click from creating another draft."""
        with self._database() as connection:
            self._begin_write(connection, item.id)
            row = connection.execute("SELECT kind, payload FROM records WHERE id = ?", (item.id,)).fetchone()
            if row:
                if row["kind"] != "outbox":
                    raise RecordConflictError("This request ID is already in use.")
                existing = OutboxItem.model_validate_json(row["payload"])
                fields = ("recipient_email", "subject_line", "body", "profile_id", "discovery_id", "lead_index")
                if any(getattr(existing, field) != getattr(item, field) for field in fields):
                    raise RecordConflictError("This request ID was already used for a different draft. Reload the saved draft before retrying.")
                return existing
            connection.execute(
                "INSERT INTO records(id, kind, created_at, payload, status) VALUES (?, 'outbox', ?, ?, 'draft')",
                (item.id, item.created_at.isoformat(), item.model_dump_json()),
            )
            self._append_event(connection, item.id, "outbox", "outbox_draft", item.created_at)
        return item

    def edit_draft(self, record_id, change):
        """Serialize edits and reject stale versions rather than losing another edit."""
        with self._database() as connection:
            self._begin_write(connection, record_id)
            row = connection.execute("SELECT payload FROM records WHERE kind = 'outbox' AND id = ?", (record_id,)).fetchone()
            if row is None:
                raise RecordNotFoundError("Draft not found")
            item = OutboxItem.model_validate_json(row["payload"])
            if item.status != OutboxStatus.DRAFT:
                raise RecordConflictError("Only drafts can be edited.")
            if item.version != change.expected_version:
                raise RecordConflictError("This draft changed in another session. Reopen it before saving again.")
            now = datetime.now(timezone.utc)
            item = item.model_copy(update={
                "recipient_email": str(change.recipient_email), "subject_line": change.subject_line,
                "body": change.body, "version": item.version + 1, "updated_at": now,
            })
            connection.execute("UPDATE records SET payload = ? WHERE id = ?", (item.model_dump_json(), item.id))
            self._append_event(connection, item.id, "outbox", "draft_updated", now)
        return item

    def list_outbox(self, status: OutboxStatus | None = None, limit=50, offset=0):
        return self._list("outbox", OutboxItem, limit, offset, status.value if status else None)

    def outbox_stats(self) -> OutboxStats:
        start = datetime.combine(datetime.now(timezone.utc).date(), time.min, tzinfo=timezone.utc)
        with self._database() as connection:
            # One read transaction gives the cap and counts from the same snapshot.
            self._begin_read(connection)
            daily_limit = connection.execute("SELECT value FROM settings WHERE key = 'daily_send_limit'").fetchone()["value"]
            counts = {row["status"]: row["count"] for row in connection.execute(
                "SELECT status, count(*) AS count FROM records WHERE kind = 'outbox' GROUP BY status"
            )}
            sent_today = connection.execute(
                "SELECT count(*) AS count FROM records WHERE kind = 'outbox' AND status = 'sent' AND sent_at >= ? AND sent_at < ?",
                (start.isoformat(), (start + timedelta(days=1)).isoformat()),
            ).fetchone()["count"]
        return OutboxStats(
            daily_limit=daily_limit, sent_today=sent_today, remaining_today=max(0, daily_limit - sent_today),
            total_drafts=counts.get("draft", 0), total_queued=counts.get("queued", 0) + counts.get("queued_for_tomorrow", 0),
            total_sent=counts.get("sent", 0), total_simulated=counts.get("simulated", 0),
        )

    def history(self, record_id=None, limit=50, offset=0):
        query = "SELECT * FROM events"
        parameters = []
        if record_id is not None:
            query += " WHERE record_id = ?"
            parameters.append(record_id)
        query += " ORDER BY id DESC LIMIT ? OFFSET ?"
        parameters.extend([limit, offset])
        with self._database() as connection:
            rows = connection.execute(query, parameters).fetchall()
        return [HistoryEvent(**dict(row)) for row in rows]

    def _begin_write(self, connection, record_id):
        connection.execute("BEGIN IMMEDIATE")

    def _begin_read(self, connection):
        connection.execute("BEGIN")

    def workspace_summary(self):
        today = datetime.now(timezone.utc).date()
        start = today - timedelta(days=6)
        with self._database() as connection:
            self._begin_read(connection)
            counts = {row["kind"]: row["count"] for row in connection.execute(
                "SELECT kind, count(*) AS count FROM records GROUP BY kind"
            )}
            activity = {row["day"]: row["count"] for row in connection.execute(
                "SELECT substr(created_at, 1, 10) AS day, count(*) AS count FROM events "
                "WHERE created_at >= ? GROUP BY substr(created_at, 1, 10)", (start.isoformat(),)
            )}
        return {
            "profiles": counts.get("profile", 0), "research": counts.get("discovery", 0),
            "database": "PostgreSQL" if self.__class__.__name__ == "PostgresStore" else "SQLite",
            "activity": [{"date": (start + timedelta(days=i)).isoformat(),
                          "count": activity.get((start + timedelta(days=i)).isoformat(), 0)} for i in range(7)],
        }
