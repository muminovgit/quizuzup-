"""Thin async-compatible shim around the sync `libsql` driver, so db.py's
existing aiosqlite-style code (`async with aiosqlite.connect(...) as db:`,
`db.row_factory = aiosqlite.Row`, `except aiosqlite.OperationalError`) works
completely unchanged against either:

- a local SQLite file (dev default, no TURSO_* env vars set), or
- a remote Turso database (prod -- the only way to get storage that
  survives a redeploy on Render's free tier, which has no persistent disk).

db.py imports this as `import db_driver as aiosqlite`, so every symbol
below exists only to match what aiosqlite-calling code expects.
"""

import asyncio

import libsql

from config import TURSO_AUTH_TOKEN, TURSO_DATABASE_URL


class OperationalError(Exception):
    """Normalized stand-in for aiosqlite.OperationalError -- libsql raises
    plain ValueError/RuntimeError for SQL errors, not a dedicated type."""


class Row:
    """Sentinel matching aiosqlite's `db.row_factory = aiosqlite.Row`."""


class _NullCursor:
    """Returned for a PRAGMA sent to a remote Turso DB, which manages its
    own storage -- local-file pragmas like `journal_mode=WAL` don't apply
    and the real driver has no use for them."""

    description: list = []
    lastrowid = None

    def fetchone(self):
        return None

    def fetchall(self):
        return []


class _Cursor:
    def __init__(self, raw_cursor, row_factory):
        self._cursor = raw_cursor
        self._row_factory = row_factory
        self.lastrowid = raw_cursor.lastrowid

    def _wrap(self, row):
        if row is None:
            return None
        if self._row_factory is not None:
            columns = [d[0] for d in self._cursor.description]
            return dict(zip(columns, row))
        return row

    async def fetchone(self):
        row = await asyncio.to_thread(self._cursor.fetchone)
        return self._wrap(row)

    async def fetchall(self):
        rows = await asyncio.to_thread(self._cursor.fetchall)
        return [self._wrap(r) for r in rows]


class _Connection:
    def __init__(self, database: str, **kwargs):
        self._database = database
        self._kwargs = kwargs
        self._is_remote = bool(kwargs.get("auth_token"))
        self._conn = None
        self.row_factory = None

    async def __aenter__(self):
        self._conn = await asyncio.to_thread(libsql.connect, self._database, **self._kwargs)
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await asyncio.to_thread(self._conn.close)

    async def execute(self, sql, params=()):
        if self._is_remote and sql.strip().upper().startswith("PRAGMA"):
            return _Cursor(_NullCursor(), self.row_factory)
        try:
            cursor = await asyncio.to_thread(self._conn.execute, sql, params)
        except Exception as exc:
            raise OperationalError(str(exc)) from exc
        return _Cursor(cursor, self.row_factory)

    async def executemany(self, sql, seq):
        try:
            await asyncio.to_thread(self._conn.executemany, sql, list(seq))
        except Exception as exc:
            raise OperationalError(str(exc)) from exc

    async def executescript(self, script: str):
        try:
            await asyncio.to_thread(self._conn.executescript, script)
        except Exception as exc:
            raise OperationalError(str(exc)) from exc

    async def commit(self):
        await asyncio.to_thread(self._conn.commit)


def connect(path_or_unused: str) -> _Connection:
    if TURSO_DATABASE_URL:
        return _Connection(TURSO_DATABASE_URL, auth_token=TURSO_AUTH_TOKEN)
    return _Connection(path_or_unused)
