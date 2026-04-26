# database.py
# ═══════════════════════════════════════════════════════════════════════════════
# COUCHE BASE DE DONNÉES SQLITE - Migration depuis JSON
# ═══════════════════════════════════════════════════════════════════════════════

import sqlite3
import json
import os
import logging
from datetime import datetime

from config import DATA_DIR

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(DATA_DIR, "lanortrad.db")


class Database:
    """Gestionnaire de base de données SQLite pour LanorTrad."""

    def __init__(self):
        os.makedirs(DATA_DIR, exist_ok=True)
        self.db_path = DB_PATH
        self._init_db()

    def _get_conn(self):
        """Retourne une connexion à la base de données."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _init_db(self):
        """Crée les tables si elles n'existent pas."""
        conn = self._get_conn()
        try:
            conn.executescript("""
                -- Table des tâches de traduction
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    manga TEXT NOT NULL,
                    chapter INTEGER NOT NULL,
                    task_type TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'not_started',
                    claimed_by INTEGER,
                    claimed_at TEXT,
                    completed_at TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(manga, chapter, task_type)
                );

                -- Table des statistiques utilisateur
                CREATE TABLE IF NOT EXISTS user_stats (
                    user_id INTEGER PRIMARY KEY,
                    xp INTEGER DEFAULT 0,
                    total_xp INTEGER DEFAULT 0,
                    messages_count INTEGER DEFAULT 0,
                    voice_minutes INTEGER DEFAULT 0,
                    chapter_reactions INTEGER DEFAULT 0,
                    trivia_correct INTEGER DEFAULT 0,
                    daily_streak INTEGER DEFAULT 0,
                    last_daily TEXT,
                    last_seniority_bonus TEXT,
                    weekly_xp INTEGER DEFAULT 0,
                    week_start INTEGER,
                    monthly_xp INTEGER DEFAULT 0,
                    month_start INTEGER,
                    joined_at TEXT,
                    last_activity TEXT,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                );

                -- Table des sondages
                CREATE TABLE IF NOT EXISTS polls (
                    id TEXT PRIMARY KEY,
                    question TEXT NOT NULL,
                    options TEXT NOT NULL,
                    votes TEXT NOT NULL DEFAULT '{}',
                    author_id INTEGER NOT NULL,
                    channel_id INTEGER NOT NULL,
                    message_id INTEGER,
                    created_at TEXT NOT NULL,
                    ends_at TEXT,
                    multi_vote INTEGER DEFAULT 0,
                    anonymous INTEGER DEFAULT 0,
                    closed INTEGER DEFAULT 0
                );

                -- Table des rappels
                CREATE TABLE IF NOT EXISTS reminders (
                    id TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    manga TEXT NOT NULL,
                    chapters TEXT NOT NULL,
                    task TEXT NOT NULL,
                    deadline TEXT NOT NULL,
                    channel_id INTEGER NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );

                -- Table des giveaways
                CREATE TABLE IF NOT EXISTS giveaways (
                    id TEXT PRIMARY KEY,
                    data TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );

                -- Table des badges utilisateur
                CREATE TABLE IF NOT EXISTS user_badges (
                    user_id INTEGER NOT NULL,
                    badge_id TEXT NOT NULL,
                    earned_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    displayed INTEGER DEFAULT 0,
                    PRIMARY KEY(user_id, badge_id)
                );

                -- Table de l'inventaire shop
                CREATE TABLE IF NOT EXISTS user_inventory (
                    user_id INTEGER NOT NULL,
                    item_id TEXT NOT NULL,
                    quantity INTEGER DEFAULT 1,
                    purchased_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY(user_id, item_id)
                );

                -- Table des achats
                CREATE TABLE IF NOT EXISTS purchases (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    item_id TEXT NOT NULL,
                    price INTEGER NOT NULL,
                    purchased_at TEXT DEFAULT CURRENT_TIMESTAMP
                );

                -- Table du compteur quotidien d'utilisation par mini-jeu
                CREATE TABLE IF NOT EXISTS minigame_daily_usage (
                    user_id INTEGER NOT NULL,
                    game TEXT NOT NULL,
                    day TEXT NOT NULL,          -- format YYYY-MM-DD
                    count INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY(user_id, game, day)
                );

                -- Table des stats de mini-jeux
                CREATE TABLE IF NOT EXISTS minigame_stats (
                    user_id INTEGER NOT NULL,
                    game TEXT NOT NULL,
                    played INTEGER DEFAULT 0,
                    wins INTEGER DEFAULT 0,
                    losses INTEGER DEFAULT 0,
                    xp_earned INTEGER DEFAULT 0,
                    xp_lost INTEGER DEFAULT 0,
                    best_streak INTEGER DEFAULT 0,
                    current_streak INTEGER DEFAULT 0,
                    fastest_win_seconds REAL,
                    last_played TEXT,
                    PRIMARY KEY(user_id, game)
                );

                -- Table de l'état des boss communautaires
                CREATE TABLE IF NOT EXISTS boss_state (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    active INTEGER DEFAULT 0,
                    name TEXT,
                    max_hp INTEGER DEFAULT 0,
                    hp INTEGER DEFAULT 0,
                    participants TEXT DEFAULT '{}',
                    spawned_at TEXT,
                    channel_id INTEGER
                );

                -- Table des logs d'audit (historique)
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    action TEXT NOT NULL,
                    user_id INTEGER,
                    target_id INTEGER,
                    details TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );

                -- Index pour les recherches fréquentes
                CREATE INDEX IF NOT EXISTS idx_tasks_manga ON tasks(manga);
                CREATE INDEX IF NOT EXISTS idx_tasks_claimed ON tasks(claimed_by);
                CREATE INDEX IF NOT EXISTS idx_user_stats_xp ON user_stats(total_xp DESC);
                CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_log(action);
                CREATE INDEX IF NOT EXISTS idx_audit_date ON audit_log(created_at);
                CREATE INDEX IF NOT EXISTS idx_minigame_game ON minigame_stats(game);
                CREATE INDEX IF NOT EXISTS idx_minigame_user ON minigame_stats(user_id);
                CREATE INDEX IF NOT EXISTS idx_minigame_daily_day ON minigame_daily_usage(day);
                CREATE INDEX IF NOT EXISTS idx_minigame_daily_user ON minigame_daily_usage(user_id, day);
            """)
            conn.commit()

            # Migration : ajouter les colonnes monthly_xp et month_start si absentes
            try:
                cursor = conn.execute("PRAGMA table_info(user_stats)")
                columns = [row["name"] for row in cursor.fetchall()]
                if "monthly_xp" not in columns:
                    conn.execute("ALTER TABLE user_stats ADD COLUMN monthly_xp INTEGER DEFAULT 0")
                if "month_start" not in columns:
                    conn.execute("ALTER TABLE user_stats ADD COLUMN month_start INTEGER")
                conn.commit()
            except Exception as e:
                logger.warning(f"⚠️ Migration monthly_xp: {e}")

            logger.info("✅ Base de données initialisée")
        except Exception as e:
            logger.error(f"❌ Erreur initialisation BDD: {e}")
        finally:
            conn.close()

    # ─────────────────────────────────────────────────────────────────────────
    # MIGRATION JSON → SQLITE
    # ─────────────────────────────────────────────────────────────────────────

    def migrate_from_json(self):
        """Migre les données JSON existantes vers SQLite."""
        conn = self._get_conn()
        migrated = 0

        try:
            # Migrer les tâches
            tasks_file = os.path.join(DATA_DIR, "etat_taches.json")
            if os.path.exists(tasks_file):
                with open(tasks_file, "r", encoding="utf-8") as f:
                    tasks = json.load(f)

                for key, task_data in tasks.items():
                    parts = key.rsplit("_", 1)
                    if len(parts) != 2:
                        continue
                    manga, chap = parts[0], parts[1]
                    if not chap.isdigit():
                        continue

                    for task_type in ["clean", "trad", "check", "edit"]:
                        val = task_data.get(task_type, "❌ Non commencé")
                        if isinstance(val, dict):
                            status = "in_progress"
                            claimed_by = val.get("claimed_by")
                            claimed_at = val.get("claimed_at")
                        elif val == "✅ Terminé":
                            status = "completed"
                            claimed_by = None
                            claimed_at = None
                        else:
                            status = "not_started"
                            claimed_by = None
                            claimed_at = None

                        try:
                            conn.execute("""
                                INSERT OR REPLACE INTO tasks (manga, chapter, task_type, status, claimed_by, claimed_at)
                                VALUES (?, ?, ?, ?, ?, ?)
                            """, (manga, int(chap), task_type, status, claimed_by, claimed_at))
                            migrated += 1
                        except:
                            pass

            # Migrer les stats utilisateur
            stats_file = os.path.join(DATA_DIR, "user_stats.json")
            if os.path.exists(stats_file):
                with open(stats_file, "r", encoding="utf-8") as f:
                    stats = json.load(f)

                for user_id_str, data in stats.items():
                    try:
                        conn.execute("""
                            INSERT OR REPLACE INTO user_stats
                            (user_id, xp, total_xp, messages_count, voice_minutes,
                             chapter_reactions, trivia_correct, daily_streak, last_daily,
                             last_seniority_bonus, weekly_xp, week_start,
                             monthly_xp, month_start, joined_at, last_activity)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            int(user_id_str),
                            data.get("xp", data.get("points", 0)),
                            data.get("total_xp", data.get("total_points_earned", 0)),
                            data.get("messages_count", 0),
                            data.get("voice_minutes", 0),
                            data.get("chapter_reactions", 0),
                            data.get("trivia_correct", 0),
                            data.get("daily_streak", 0),
                            data.get("last_daily"),
                            data.get("last_seniority_bonus"),
                            data.get("weekly_xp", data.get("weekly_points", 0)),
                            data.get("week_start"),
                            data.get("monthly_xp", 0),
                            data.get("month_start"),
                            data.get("joined_at"),
                            data.get("last_activity"),
                        ))
                        migrated += 1
                    except:
                        pass

            # Migrer les sondages
            polls_file = os.path.join(DATA_DIR, "polls.json")
            if os.path.exists(polls_file):
                with open(polls_file, "r", encoding="utf-8") as f:
                    polls = json.load(f)

                for poll_id, pdata in polls.items():
                    try:
                        conn.execute("""
                            INSERT OR REPLACE INTO polls
                            (id, question, options, votes, author_id, channel_id, message_id,
                             created_at, ends_at, multi_vote, anonymous, closed)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            poll_id,
                            pdata["question"],
                            json.dumps(pdata["options"]),
                            json.dumps(pdata["votes"]),
                            pdata["author_id"],
                            pdata["channel_id"],
                            pdata.get("message_id"),
                            pdata["created_at"],
                            pdata.get("ends_at"),
                            1 if pdata.get("multi_vote") else 0,
                            1 if pdata.get("anonymous") else 0,
                            1 if pdata.get("closed") else 0,
                        ))
                        migrated += 1
                    except:
                        pass

            conn.commit()
            logger.info(f"✅ Migration terminée: {migrated} enregistrement(s) migrés")
            return migrated

        except Exception as e:
            logger.error(f"❌ Erreur migration: {e}")
            conn.rollback()
            return 0
        finally:
            conn.close()

    # ─────────────────────────────────────────────────────────────────────────
    # OPÉRATIONS GÉNÉRIQUES
    # ─────────────────────────────────────────────────────────────────────────

    def execute(self, query, params=None):
        """Exécute une requête et retourne le curseur."""
        conn = self._get_conn()
        try:
            cursor = conn.execute(query, params or ())
            conn.commit()
            return cursor
        finally:
            conn.close()

    def fetch_one(self, query, params=None):
        """Retourne une seule ligne."""
        conn = self._get_conn()
        try:
            cursor = conn.execute(query, params or ())
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def fetch_all(self, query, params=None):
        """Retourne toutes les lignes."""
        conn = self._get_conn()
        try:
            cursor = conn.execute(query, params or ())
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    # ─────────────────────────────────────────────────────────────────────────
    # AUDIT LOG
    # ─────────────────────────────────────────────────────────────────────────

    def log_action(self, action, user_id=None, target_id=None, details=None):
        """Enregistre une action dans le journal d'audit."""
        self.execute(
            "INSERT INTO audit_log (action, user_id, target_id, details) VALUES (?, ?, ?, ?)",
            (action, user_id, target_id, details)
        )

    def get_audit_log(self, limit=50, action_filter=None):
        """Récupère les dernières entrées du journal d'audit."""
        if action_filter:
            return self.fetch_all(
                "SELECT * FROM audit_log WHERE action = ? ORDER BY created_at DESC LIMIT ?",
                (action_filter, limit)
            )
        return self.fetch_all(
            "SELECT * FROM audit_log ORDER BY created_at DESC LIMIT ?",
            (limit,)
        )

    # ─────────────────────────────────────────────────────────────────────────
    # MINI-JEUX — Limites quotidiennes
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _today_str():
        return datetime.now().strftime("%Y-%m-%d")

    def get_daily_usage(self, user_id, game, day=None):
        """Retourne le nombre de parties jouées aujourd'hui pour ce jeu."""
        day = day or self._today_str()
        row = self.fetch_one(
            "SELECT count FROM minigame_daily_usage WHERE user_id = ? AND game = ? AND day = ?",
            (user_id, game, day),
        )
        return row["count"] if row else 0

    def get_all_daily_usage(self, user_id, day=None):
        """Retourne un dict {game: count} pour la journée."""
        day = day or self._today_str()
        rows = self.fetch_all(
            "SELECT game, count FROM minigame_daily_usage WHERE user_id = ? AND day = ?",
            (user_id, day),
        )
        return {r["game"]: r["count"] for r in rows}

    def increment_daily_usage(self, user_id, game, day=None):
        """Incrémente et retourne le nouveau compteur."""
        day = day or self._today_str()
        conn = self._get_conn()
        try:
            conn.execute(
                """
                INSERT INTO minigame_daily_usage (user_id, game, day, count)
                VALUES (?, ?, ?, 1)
                ON CONFLICT(user_id, game, day) DO UPDATE SET count = count + 1
                """,
                (user_id, game, day),
            )
            conn.commit()
            row = conn.execute(
                "SELECT count FROM minigame_daily_usage WHERE user_id = ? AND game = ? AND day = ?",
                (user_id, game, day),
            ).fetchone()
            return row["count"] if row else 1
        except Exception as e:
            logger.error(f"❌ increment_daily_usage: {e}")
            conn.rollback()
            return 0
        finally:
            conn.close()

    def decrement_daily_usage(self, user_id, game, day=None):
        """Décrémente le compteur (utile quand un jeu est annulé avant de démarrer)."""
        day = day or self._today_str()
        conn = self._get_conn()
        try:
            conn.execute(
                """
                UPDATE minigame_daily_usage
                SET count = MAX(0, count - 1)
                WHERE user_id = ? AND game = ? AND day = ?
                """,
                (user_id, game, day),
            )
            conn.commit()
        except Exception as e:
            logger.error(f"❌ decrement_daily_usage: {e}")
            conn.rollback()
        finally:
            conn.close()

    def purge_old_daily_usage(self, keep_days=7):
        """Nettoyage périodique : supprime les lignes plus anciennes que `keep_days`."""
        try:
            cutoff = (datetime.now() - __import__("datetime").timedelta(days=keep_days)).strftime("%Y-%m-%d")
            self.execute(
                "DELETE FROM minigame_daily_usage WHERE day < ?",
                (cutoff,),
            )
        except Exception as e:
            logger.warning(f"purge_old_daily_usage: {e}")

    # ─────────────────────────────────────────────────────────────────────────
    # MINI-JEUX — Stats cumulées
    # ─────────────────────────────────────────────────────────────────────────

    def record_minigame(self, user_id, game, won, xp_delta=0, duration_seconds=None):
        """Enregistre une partie de mini-jeu.

        - won: True (victoire), False (défaite), None (neutre / participation)
        - xp_delta: signed (positif = gain, négatif = perte)
        - duration_seconds: optionnel, pour suivre le meilleur temps
        """
        conn = self._get_conn()
        try:
            conn.execute(
                "INSERT OR IGNORE INTO minigame_stats (user_id, game) VALUES (?, ?)",
                (user_id, game),
            )
            now_iso = datetime.now().isoformat()

            if won is True:
                gain = max(0, xp_delta)
                conn.execute(
                    """
                    UPDATE minigame_stats
                    SET played = played + 1,
                        wins = wins + 1,
                        xp_earned = xp_earned + ?,
                        current_streak = current_streak + 1,
                        best_streak = MAX(best_streak, current_streak + 1),
                        fastest_win_seconds = CASE
                            WHEN ? IS NULL THEN fastest_win_seconds
                            WHEN fastest_win_seconds IS NULL THEN ?
                            ELSE MIN(fastest_win_seconds, ?)
                        END,
                        last_played = ?
                    WHERE user_id = ? AND game = ?
                    """,
                    (gain, duration_seconds, duration_seconds, duration_seconds, now_iso, user_id, game),
                )
            elif won is False:
                loss = max(0, -xp_delta) if xp_delta and xp_delta < 0 else 0
                conn.execute(
                    """
                    UPDATE minigame_stats
                    SET played = played + 1,
                        losses = losses + 1,
                        xp_lost = xp_lost + ?,
                        current_streak = 0,
                        last_played = ?
                    WHERE user_id = ? AND game = ?
                    """,
                    (loss, now_iso, user_id, game),
                )
            else:
                conn.execute(
                    """
                    UPDATE minigame_stats
                    SET played = played + 1,
                        last_played = ?
                    WHERE user_id = ? AND game = ?
                    """,
                    (now_iso, user_id, game),
                )
            conn.commit()
        except Exception as e:
            logger.error(f"❌ record_minigame: {e}")
            conn.rollback()
        finally:
            conn.close()

        # Hook : notifier les défis hebdo (import différé pour éviter circulaire).
        # On récupère le streak courant si dispo (utile pour le défi "streak").
        try:
            from weekly_challenges import record_event
            current_streak = None
            try:
                from effects import get_streak
                current_streak = get_streak(user_id).get("count")
            except Exception:
                pass
            record_event(user_id, game, won, duration_seconds, current_streak)
        except Exception as e:
            logger.warning(f"weekly_challenges hook error: {e}")

    def get_minigame_stats(self, user_id, game=None):
        """Récupère les stats de mini-jeux d'un utilisateur."""
        if game:
            return self.fetch_one(
                "SELECT * FROM minigame_stats WHERE user_id = ? AND game = ?",
                (user_id, game),
            )
        return self.fetch_all(
            "SELECT * FROM minigame_stats WHERE user_id = ? ORDER BY played DESC",
            (user_id,),
        )

    def get_minigame_totals(self, user_id):
        """Totaux agrégés tous jeux confondus pour un utilisateur."""
        return self.fetch_one(
            """
            SELECT
                COALESCE(SUM(played), 0) AS played,
                COALESCE(SUM(wins), 0) AS wins,
                COALESCE(SUM(losses), 0) AS losses,
                COALESCE(SUM(xp_earned), 0) AS xp_earned,
                COALESCE(SUM(xp_lost), 0) AS xp_lost,
                COALESCE(MAX(best_streak), 0) AS best_streak
            FROM minigame_stats
            WHERE user_id = ?
            """,
            (user_id,),
        )

    def get_minigame_leaderboard(self, game=None, limit=10, sort_by="wins"):
        """Top des joueurs (par jeu ou global). sort_by: wins | xp_earned | played"""
        if sort_by not in ("wins", "xp_earned", "played"):
            sort_by = "wins"
        if game:
            return self.fetch_all(
                f"""
                SELECT user_id, wins, played, xp_earned, best_streak
                FROM minigame_stats
                WHERE game = ?
                ORDER BY {sort_by} DESC, xp_earned DESC
                LIMIT ?
                """,
                (game, limit),
            )
        return self.fetch_all(
            f"""
            SELECT user_id,
                   SUM(wins) AS wins,
                   SUM(played) AS played,
                   SUM(xp_earned) AS xp_earned,
                   MAX(best_streak) AS best_streak
            FROM minigame_stats
            GROUP BY user_id
            ORDER BY {sort_by} DESC, xp_earned DESC
            LIMIT ?
            """,
            (limit,),
        )

    # ─────────────────────────────────────────────────────────────────────────
    # STATS DB
    # ─────────────────────────────────────────────────────────────────────────

    def get_db_stats(self):
        """Retourne les statistiques de la base de données."""
        tables = self.fetch_all(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )

        stats = {}
        conn = self._get_conn()
        try:
            for table in tables:
                name = table["name"]
                cursor = conn.execute(f"SELECT COUNT(*) as count FROM {name}")
                row = cursor.fetchone()
                stats[name] = row["count"] if row else 0
        finally:
            conn.close()

        # Taille du fichier
        if os.path.exists(self.db_path):
            size_bytes = os.path.getsize(self.db_path)
            if size_bytes < 1024:
                size_str = f"{size_bytes} B"
            elif size_bytes < 1024 * 1024:
                size_str = f"{size_bytes / 1024:.1f} KB"
            else:
                size_str = f"{size_bytes / (1024*1024):.1f} MB"
        else:
            size_str = "N/A"

        return {"tables": stats, "size": size_str}

    # ─────────────────────────────────────────────────────────────────────────
    # EXPORT SQLITE → JSON (backup)
    # ─────────────────────────────────────────────────────────────────────────

    def export_to_json(self):
        """Exporte les données critiques en JSON pour le backup GitHub."""
        exports = {}
        conn = self._get_conn()

        try:
            # Exporter user_stats
            cursor = conn.execute("SELECT * FROM user_stats")
            rows = cursor.fetchall()
            user_stats = {}
            for row in rows:
                row_dict = dict(row)
                uid = str(row_dict.pop("user_id"))
                row_dict.pop("updated_at", None)
                user_stats[uid] = row_dict
            exports["user_stats"] = user_stats

            # Exporter tasks
            cursor = conn.execute("SELECT * FROM tasks")
            rows = cursor.fetchall()
            tasks = {}
            for row in rows:
                rd = dict(row)
                key = f"{rd['manga']}_{rd['chapter']}"
                if key not in tasks:
                    tasks[key] = {}
                if rd["status"] == "completed":
                    tasks[key][rd["task_type"]] = "✅ Terminé"
                elif rd["status"] == "in_progress":
                    tasks[key][rd["task_type"]] = {
                        "status": "🔄 En cours",
                        "claimed_by": rd["claimed_by"],
                        "claimed_at": rd["claimed_at"]
                    }
                else:
                    tasks[key][rd["task_type"]] = "❌ Non commencé"
            exports["tasks"] = tasks

            # Exporter polls
            cursor = conn.execute("SELECT * FROM polls")
            rows = cursor.fetchall()
            polls = {}
            for row in rows:
                rd = dict(row)
                pid = rd.pop("id")
                rd["options"] = json.loads(rd["options"])
                rd["votes"] = json.loads(rd["votes"])
                rd["multi_vote"] = bool(rd["multi_vote"])
                rd["anonymous"] = bool(rd["anonymous"])
                rd["closed"] = bool(rd["closed"])
                polls[pid] = rd
            exports["polls"] = polls

        finally:
            conn.close()

        # Écrire les fichiers JSON
        for name, data in exports.items():
            filepath = os.path.join(DATA_DIR, f"{name}.json")
            try:
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=4)
            except Exception as e:
                logger.error(f"Erreur export {name}: {e}")

        return exports


# Instance globale
db = Database()
