"""aiogram uchun SQLite'ga asoslangan FSM (holat) saqlash.

Nega kerak: Vercel'da har bir so'rov alohida funksiya chaqiruvi bo'lib,
xotira (MemoryStorage) saqlanmaydi. Shuning uchun holatni `bot.db` ichida
saqlaymiz — u esa o'z navbatida Redis'ga sinxronlanadi.

Faqat aiogram + stdlib ishlatiladi.
"""
import json
from typing import Any, Dict, Optional

from aiogram.fsm.state import State
from aiogram.fsm.storage.base import BaseStorage, StorageKey, StateType


class SqliteFSM(BaseStorage):
    def __init__(self, db):
        self.db = db
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS fsm_state(chat INT, user INT, state TEXT,
                                             PRIMARY KEY(chat, user));
        CREATE TABLE IF NOT EXISTS fsm_data(chat INT, user INT, data TEXT,
                                            PRIMARY KEY(chat, user));
        """)
        self.db.commit()

    async def set_state(self, key: StorageKey, state: StateType = None) -> None:
        val = state.state if isinstance(state, State) else state
        self.db.execute("INSERT OR REPLACE INTO fsm_state VALUES(?,?,?)",
                        (key.chat_id, key.user_id, val))
        self.db.commit()

    async def get_state(self, key: StorageKey) -> Optional[str]:
        row = self.db.execute("SELECT state FROM fsm_state WHERE chat=? AND user=?",
                              (key.chat_id, key.user_id)).fetchone()
        return row[0] if row else None

    async def set_data(self, key: StorageKey, data: Dict[str, Any]) -> None:
        self.db.execute("INSERT OR REPLACE INTO fsm_data VALUES(?,?,?)",
                        (key.chat_id, key.user_id, json.dumps(data, ensure_ascii=False)))
        self.db.commit()

    async def get_data(self, key: StorageKey) -> Dict[str, Any]:
        row = self.db.execute("SELECT data FROM fsm_data WHERE chat=? AND user=?",
                              (key.chat_id, key.user_id)).fetchone()
        return json.loads(row[0]) if row else {}

    async def close(self) -> None:
        pass
