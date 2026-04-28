# pipeline/queue.py
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from pipeline.config import QUEUE_FILE, REJECTED


@dataclass
class QueueEntry:
    """One icon waiting to be generated."""
    name:         str
    concept:      str
    retry_reason: str = ""
    added_at:     str = ""

    def __post_init__(self):
        if not self.added_at:
            self.added_at = datetime.now().isoformat()

    def to_dict(self) -> dict:
        return {
            "name":         self.name,
            "concept":      self.concept,
            "retry_reason": self.retry_reason,
            "added_at":     self.added_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "QueueEntry":
        return cls(
            name         = data.get("name", ""),
            concept      = data.get("concept", ""),
            retry_reason = data.get("retry_reason", ""),
            added_at     = data.get("added_at", ""),
        )


class QueueManager:
    """
    Manages the icon work queue and rejected list.
    All queue state lives in queue.json and rejected.json.
    Single responsibility: queue persistence only.
    """

    def __init__(
        self,
        queue_file:    Path = QUEUE_FILE,
        rejected_file: Path = REJECTED,
    ):
        self._queue_file    = queue_file
        self._rejected_file = rejected_file

    # ── Queue operations ──────────────────────────────────────────────────────

    def read(self) -> list[QueueEntry]:
        return [QueueEntry.from_dict(d) for d in self._load(self._queue_file)]

    def write(self, entries: list[QueueEntry]):
        self._save(self._queue_file, [e.to_dict() for e in entries])

    def peek(self) -> QueueEntry | None:
        """Return the first entry without removing it."""
        entries = self.read()
        return entries[0] if entries else None

    def pop(self) -> QueueEntry | None:
        """Remove and return the first entry."""
        entries = self.read()
        if not entries:
            return None
        entry = entries[0]
        self.write(entries[1:])
        return entry

    def add(self, entry: QueueEntry) -> bool:
        """Add entry if not already queued. Returns True if added."""
        entries = self.read()
        if any(e.name == entry.name for e in entries):
            return False
        entries.append(entry)
        self.write(entries)
        return True

    def add_many(self, new_entries: list[QueueEntry]) -> int:
        """Add multiple entries, skipping duplicates. Returns count added."""
        entries  = self.read()
        existing = {e.name for e in entries}
        added    = 0
        for entry in new_entries:
            if entry.name not in existing:
                entries.append(entry)
                existing.add(entry.name)
                added += 1
        self.write(entries)
        return added

    def count(self) -> int:
        return len(self.read())

    def clear(self) -> int:
        """Clear queue. Returns how many were removed."""
        count = self.count()
        self.write([])
        return count

    def contains(self, name: str) -> bool:
        return any(e.name == name for e in self.read())

    # ── Rejected operations ───────────────────────────────────────────────────

    def reject(self, entry: QueueEntry, reason: str):
        """Move an entry to rejected.json with a reason."""
        rejected = self._load(self._rejected_file)
        rejected.append({
            **entry.to_dict(),
            "rejected_reason": reason,
            "rejected_at":     datetime.now().isoformat(),
        })
        self._save(self._rejected_file, rejected)

    def read_rejected(self) -> list[dict]:
        return self._load(self._rejected_file)

    def requeue_rejected(self) -> int:
        """Move all rejected entries back into the queue. Returns count."""
        rejected = self.read_rejected()
        entries  = [QueueEntry.from_dict(r) for r in rejected]
        added    = self.add_many(entries)
        if added:
            self._save(self._rejected_file, [])
        return added

    # ── Private helpers ───────────────────────────────────────────────────────

    def _load(self, path: Path) -> list[dict]:
        if not path.exists():
            return []
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except (json.JSONDecodeError, OSError):
            return []

    def _save(self, path: Path, data: list[dict]):
        path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )