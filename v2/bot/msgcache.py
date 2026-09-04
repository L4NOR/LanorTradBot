"""
Cache SQLite des messages — pour des logs réellement exploitables
==================================================================
Discord n'envoie le contenu d'un message supprimé/édité que s'il est encore
dans le cache RAM du bot (donc posté depuis le dernier démarrage). On archive
donc chaque message dans un petit SQLite local : les logs retrouvent alors le
contenu même après un redémarrage.

Rétention : MSG_CACHE_DAYS jours, purge automatique quotidienne.
Le fichier vit dans `data/messages.db` (ignoré par git).
"""
import logging
import os
import sqlite3
import threading
import time

log = logging.getLogger("lanortrad.msgcache")

_DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
DB_PATH = os.path.join(_DATA_DIR, "messages.db")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS messages (
    id          INTEGER PRIMARY KEY,
    channel_id  INTEGER NOT NULL,
    guild_id    INTEGER,
    author_id   INTEGER NOT NULL,
    author_name TEXT,
    content     TEXT,
    attachments TEXT,
    created_at  INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_messages_created ON messages (created_at);
"""


class MessageCache:
    """Stockage minimal des messages récents."""

    def __init__(self, max_len: int = 3000):
        self.max_len = max_len
        self._lock = threading.Lock()
        os.makedirs(_DATA_DIR, exist_ok=True)
        self._db = sqlite3.connect(DB_PATH, check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        with self._lock:
            self._db.executescript(_SCHEMA)
            self._db.commit()

    def store(self, message):
        content = (message.content or "")[:self.max_len]
        attachments = "\n".join(a.url for a in message.attachments[:10])
        try:
            with self._lock:
                self._db.execute(
                    "INSERT OR REPLACE INTO messages "
                    "(id, channel_id, guild_id, author_id, author_name, content, "
                    " attachments, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (message.id, message.channel.id,
                     message.guild.id if message.guild else None,
                     message.author.id, str(message.author), content, attachments,
                     int(message.created_at.timestamp())),
                )
                self._db.commit()
        except sqlite3.Error as e:
            log.warning("Message non archivé : %s", e)

    def update_content(self, message_id: int, content: str):
        """Met à jour le contenu archivé après une édition."""
        try:
            with self._lock:
                self._db.execute(
                    "UPDATE messages SET content = ? WHERE id = ?",
                    ((content or "")[:self.max_len], message_id))
                self._db.commit()
        except sqlite3.Error as e:
            log.warning("Mise à jour cache KO : %s", e)

    def get(self, message_id: int):
        try:
            with self._lock:
                row = self._db.execute(
                    "SELECT * FROM messages WHERE id = ?", (message_id,)).fetchone()
            return dict(row) if row else None
        except sqlite3.Error as e:
            log.warning("Lecture cache KO : %s", e)
            return None

    def purge(self, days: int) -> int:
        cutoff = int(time.time()) - days * 86400
        try:
            with self._lock:
                cur = self._db.execute(
                    "DELETE FROM messages WHERE created_at < ?", (cutoff,))
                self._db.commit()
            return cur.rowcount
        except sqlite3.Error as e:
            log.warning("Purge cache KO : %s", e)
            return 0

    def stats(self) -> dict:
        try:
            with self._lock:
                total = self._db.execute("SELECT COUNT(*) AS n FROM messages").fetchone()["n"]
                oldest = self._db.execute(
                    "SELECT MIN(created_at) AS t FROM messages").fetchone()["t"]
            size = os.path.getsize(DB_PATH) if os.path.exists(DB_PATH) else 0
            return {"count": total, "oldest": oldest, "size": size}
        except (sqlite3.Error, OSError):
            return {"count": 0, "oldest": None, "size": 0}

    def close(self):
        try:
            self._db.close()
        except sqlite3.Error:
            pass
