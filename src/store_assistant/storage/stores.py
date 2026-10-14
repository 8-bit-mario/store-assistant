# ABOUTME: Saves, finds and updates stores, keyed by their normalized name.
# ABOUTME: Callers pass cleaned names and E.164 phones; this layer only persists them.
import sqlite3
from dataclasses import dataclass

from store_assistant.clock import Clock, utc_now
from store_assistant.validation.store_name import normalize_store_name, strip_generic_label


class DuplicateStoreError(Exception):
    """Raised when adding a store whose normalized name already exists."""


class StoreNotFoundError(Exception):
    """Raised when updating a store that does not exist."""


@dataclass(frozen=True)
class Store:
    """A saved store."""

    store_id: int
    name: str
    phone: str
    created_at: str
    updated_at: str


class StoreRepository:
    """Store records in the app database."""

    def __init__(self, conn: sqlite3.Connection, clock: Clock = utc_now) -> None:
        self._conn = conn
        self._clock = clock

    def find_by_name(self, name: str) -> Store | None:
        """Find a store by name, ignoring case and spacing."""
        row = self._conn.execute(
            "SELECT store_id, name, phone, created_at, updated_at FROM stores "
            "WHERE name_normalized = ?",
            (normalize_store_name(name),),
        ).fetchone()
        return Store(**dict(row)) if row else None

    def find_matching(self, name: str) -> Store | None:
        """Find a store by exact name, else by the name without a label like "store abc"."""
        exact = self.find_by_name(name)
        if exact is not None:
            return exact
        stripped = strip_generic_label(name)
        return self.find_by_name(stripped) if stripped else None

    def add(self, name: str, phone: str) -> Store:
        """
        Save a new store.

        Raises:
            DuplicateStoreError: If a store with the same normalized name exists.
        """
        now = self._clock().isoformat()
        try:
            self._conn.execute(
                "INSERT INTO stores (name, name_normalized, phone, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (name, normalize_store_name(name), phone, now, now),
            )
        except sqlite3.IntegrityError as error:
            raise DuplicateStoreError(f"A store named {name!r} already exists") from error
        return self._get(name)

    def update_phone(self, name: str, phone: str) -> Store:
        """
        Replace the phone of an existing store.

        Raises:
            StoreNotFoundError: If no store has that name.
        """
        cursor = self._conn.execute(
            "UPDATE stores SET phone = ?, updated_at = ? WHERE name_normalized = ?",
            (phone, self._clock().isoformat(), normalize_store_name(name)),
        )
        if cursor.rowcount == 0:
            raise StoreNotFoundError(f"No store named {name!r}")
        return self._get(name)

    def _get(self, name: str) -> Store:
        store = self.find_by_name(name)
        if store is None:
            raise StoreNotFoundError(f"No store named {name!r}")
        return store
