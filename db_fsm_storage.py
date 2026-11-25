"""FSM storage backed by the bot's own database (fsm_storage table in db.py)
instead of aiogram's in-memory MemoryStorage.

MemoryStorage loses every mid-flow state (a pending /newquiz upload name,
the new AI-answer-review step) the instant the process restarts -- which
happens on every redeploy. For a bot that gets redeployed often and whose
upload flow can now take several minutes (AI review of a big file), that's
a real way to strand someone mid-upload. This persists to the same
Turso/SQLite database everything else uses, so it survives restarts.
"""

from aiogram.fsm.storage.base import BaseStorage, StorageKey

import db


def _serialize_key(key: StorageKey) -> str:
    return ":".join(
        str(part)
        for part in (
            key.bot_id,
            key.chat_id,
            key.user_id,
            key.thread_id,
            key.business_connection_id,
            key.destiny,
        )
    )


class DBStorage(BaseStorage):
    async def set_state(self, key: StorageKey, state=None) -> None:
        state_str = state.state if hasattr(state, "state") else state
        await db.set_fsm_state(_serialize_key(key), state_str)

    async def get_state(self, key: StorageKey) -> str | None:
        return await db.get_fsm_state(_serialize_key(key))

    async def set_data(self, key: StorageKey, data) -> None:
        await db.set_fsm_data(_serialize_key(key), dict(data))

    async def get_data(self, key: StorageKey) -> dict:
        return await db.get_fsm_data(_serialize_key(key))

    async def close(self) -> None:
        pass
