"""
Telegram Kids Database
SQLite база данных.
"""

import sqlite3
import json
import os
import random
import string
from datetime import datetime, timedelta


class Database:
    def __init__(self, db_path: str = "familyguard.db"):
        self.db_path = db_path
        self._init_db()
        self._migrate()

    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _migrate(self):
        """Применяет миграции для существующих БД (добавляет новые колонки)."""
        migrations = [
            "ALTER TABLE privacy_policy_consents ADD COLUMN confirmed_at TEXT",
            "ALTER TABLE email_verification_tokens ADD COLUMN expired_at TEXT",
        ]
        with self._connect() as conn:
            for sql in migrations:
                try:
                    conn.execute(sql)
                except sqlite3.OperationalError:
                    pass  # колонка уже существует

    def _init_db(self):
        with self._connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS rate_limits (
                    key TEXT PRIMARY KEY,
                    attempts INTEGER DEFAULT 0,
                    window_start TEXT NOT NULL,
                    blocked_until TEXT,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS parents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id TEXT UNIQUE NOT NULL,
                    name TEXT,
                    email TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS children (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    parent_id INTEGER NOT NULL REFERENCES parents(id),
                    name TEXT NOT NULL,
                    birth_date TEXT,
                    phone TEXT,
                    telegram_id TEXT,
                    relationship TEXT,
                    is_linked INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS email_verification_tokens (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    parent_id INTEGER NOT NULL REFERENCES parents(id),
                    child_id INTEGER NOT NULL REFERENCES children(id),
                    token TEXT UNIQUE NOT NULL,
                    expires_at TEXT NOT NULL,
                    expired_at TEXT,
                    verified_at TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS linking_codes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    child_id INTEGER NOT NULL REFERENCES children(id),
                    code TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    used_at TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS privacy_policy_versions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    version TEXT UNIQUE NOT NULL,
                    text TEXT NOT NULL,
                    url TEXT,
                    is_current INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS privacy_policy_consents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    parent_id INTEGER NOT NULL REFERENCES parents(id),
                    policy_version_id INTEGER NOT NULL REFERENCES privacy_policy_versions(id),
                    consent_text TEXT NOT NULL,
                    consented_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    confirmed_at TEXT
                );

                CREATE TABLE IF NOT EXISTS registration_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    parent_id INTEGER REFERENCES parents(id),
                    child_id INTEGER REFERENCES children(id),
                    event_type TEXT NOT NULL,
                    details TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS blocked (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    child_id INTEGER REFERENCES children(id),
                    type TEXT NOT NULL,
                    item_id TEXT NOT NULL,
                    name TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(child_id, type, item_id)
                );

                CREATE TABLE IF NOT EXISTS pending_requests (
                    request_id TEXT PRIMARY KEY,
                    child_id INTEGER REFERENCES children(id),
                    data TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS device_tokens (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    child_id INTEGER NOT NULL REFERENCES children(id),
                    fcm_token TEXT NOT NULL,
                    platform TEXT NOT NULL DEFAULT 'android',
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(child_id)
                );

                CREATE TABLE IF NOT EXISTS activity_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    child_id INTEGER REFERENCES children(id),
                    action TEXT NOT NULL,
                    details TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
            """)

    # ============================================================
    # RATE LIMITING
    # ============================================================

    def rate_check(self, key: str, max_attempts: int,
                   window_seconds: int, block_seconds: int = 0) -> tuple[bool, int]:
        """
        Проверяет лимит И засчитывает попытку атомарно.
        Используется для ограничения частоты запросов (OTP, email).
        Возвращает (allowed, retry_after_seconds).
        """
        now = datetime.now()
        with self._connect() as conn:
            row = conn.execute(
                "SELECT attempts, window_start, blocked_until FROM rate_limits WHERE key = ?",
                (key,)
            ).fetchone()

            if row:
                attempts, window_start_str, blocked_until_str = row
                window_start = datetime.fromisoformat(window_start_str)

                if blocked_until_str:
                    blocked_until = datetime.fromisoformat(blocked_until_str)
                    if now < blocked_until:
                        return False, int((blocked_until - now).total_seconds())
                    # блок истёк — сбрасываем
                    conn.execute(
                        "UPDATE rate_limits SET attempts=0, window_start=?, blocked_until=NULL WHERE key=?",
                        (now.isoformat(), key)
                    )
                    attempts, window_start = 0, now

                elapsed = (now - window_start).total_seconds()
                if elapsed > window_seconds:
                    # новое окно
                    conn.execute(
                        "UPDATE rate_limits SET attempts=1, window_start=?, blocked_until=NULL, updated_at=? WHERE key=?",
                        (now.isoformat(), now.isoformat(), key)
                    )
                    return True, 0

                if attempts >= max_attempts:
                    if block_seconds:
                        blocked_until = (now + timedelta(seconds=block_seconds)).isoformat()
                        conn.execute(
                            "UPDATE rate_limits SET blocked_until=?, updated_at=? WHERE key=?",
                            (blocked_until, now.isoformat(), key)
                        )
                        return False, block_seconds
                    retry_after = int(window_seconds - elapsed)
                    return False, max(retry_after, 1)

                conn.execute(
                    "UPDATE rate_limits SET attempts=attempts+1, updated_at=? WHERE key=?",
                    (now.isoformat(), key)
                )
                return True, 0
            else:
                conn.execute(
                    "INSERT INTO rate_limits (key, attempts, window_start, updated_at) VALUES (?,1,?,?)",
                    (key, now.isoformat(), now.isoformat())
                )
                return True, 0

    def rate_fail(self, key: str, max_attempts: int, block_seconds: int) -> tuple[bool, int]:
        """
        Засчитывает неудачную попытку (неверный код и т.п.).
        Если превышен лимит — блокирует ключ.
        Используется ПОСЛЕ неудачной проверки кода, чтобы не наказывать за корректный запрос.
        Возвращает (is_now_blocked, retry_after_seconds).
        """
        now = datetime.now()
        with self._connect() as conn:
            row = conn.execute(
                "SELECT attempts FROM rate_limits WHERE key = ?", (key,)
            ).fetchone()
            attempts = (row[0] if row else 0) + 1

            if attempts >= max_attempts:
                blocked_until = (now + timedelta(seconds=block_seconds)).isoformat()
                conn.execute(
                    """INSERT INTO rate_limits (key, attempts, window_start, blocked_until, updated_at)
                       VALUES (?,?,?,?,?)
                       ON CONFLICT(key) DO UPDATE SET
                           attempts=excluded.attempts,
                           blocked_until=excluded.blocked_until,
                           updated_at=excluded.updated_at""",
                    (key, attempts, now.isoformat(), blocked_until, now.isoformat())
                )
                return True, block_seconds
            else:
                conn.execute(
                    """INSERT INTO rate_limits (key, attempts, window_start, updated_at)
                       VALUES (?,?,?,?)
                       ON CONFLICT(key) DO UPDATE SET
                           attempts=excluded.attempts,
                           updated_at=excluded.updated_at""",
                    (key, attempts, now.isoformat(), now.isoformat())
                )
                return False, 0

    def rate_is_blocked(self, key: str) -> tuple[bool, int]:
        """Только проверяет блокировку, без изменений. Возвращает (blocked, retry_after)."""
        now = datetime.now()
        with self._connect() as conn:
            row = conn.execute(
                "SELECT blocked_until FROM rate_limits WHERE key = ?", (key,)
            ).fetchone()
            if row and row[0]:
                blocked_until = datetime.fromisoformat(row[0])
                if now < blocked_until:
                    return True, int((blocked_until - now).total_seconds())
        return False, 0

    def rate_reset(self, key: str):
        """Сбрасывает счётчик после успешного действия."""
        with self._connect() as conn:
            conn.execute("DELETE FROM rate_limits WHERE key = ?", (key,))

    # ============================================================
    # РОДИТЕЛИ
    # ============================================================

    def get_or_create_parent(self, telegram_id: str) -> dict:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id, telegram_id, name, email FROM parents WHERE telegram_id = ?",
                (telegram_id,)
            ).fetchone()
            if row:
                return {"id": row[0], "telegram_id": row[1], "name": row[2], "email": row[3]}
            cursor = conn.execute(
                "INSERT INTO parents (telegram_id) VALUES (?)", (telegram_id,)
            )
            return {"id": cursor.lastrowid, "telegram_id": telegram_id, "name": None, "email": None}

    def get_parent_by_id(self, parent_id: int) -> dict | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id, telegram_id, name, email FROM parents WHERE id = ?",
                (parent_id,)
            ).fetchone()
            if row:
                return {"id": row[0], "telegram_id": row[1], "name": row[2], "email": row[3]}
            return None

    def get_parent_by_telegram_id(self, telegram_id: str) -> dict | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id, telegram_id, name, email FROM parents WHERE telegram_id = ?",
                (telegram_id,)
            ).fetchone()
            if row:
                return {"id": row[0], "telegram_id": row[1], "name": row[2], "email": row[3]}
            return None

    def update_parent(self, telegram_id: str, name: str = None, email: str = None):
        with self._connect() as conn:
            if name is not None:
                conn.execute(
                    "UPDATE parents SET name = ? WHERE telegram_id = ?", (name, telegram_id)
                )
            if email is not None:
                conn.execute(
                    "UPDATE parents SET email = ? WHERE telegram_id = ?", (email, telegram_id)
                )

    # ============================================================
    # ДЕТИ
    # ============================================================

    def add_child(self, parent_id: int, name: str, birth_date: str,
                  phone: str, relationship: str) -> int:
        with self._connect() as conn:
            cursor = conn.execute(
                """INSERT INTO children (parent_id, name, birth_date, phone, relationship)
                   VALUES (?, ?, ?, ?, ?)""",
                (parent_id, name, birth_date, phone, relationship)
            )
            return cursor.lastrowid

    def get_children(self, parent_id: int) -> list:
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT id, name, birth_date, phone, telegram_id, relationship, is_linked
                   FROM children WHERE parent_id = ? ORDER BY created_at""",
                (parent_id,)
            ).fetchall()
            return [
                {
                    "id": r[0], "name": r[1], "birth_date": r[2],
                    "phone": r[3], "telegram_id": r[4],
                    "relationship": r[5], "is_linked": bool(r[6]),
                }
                for r in rows
            ]

    def get_child_by_id(self, child_id: int) -> dict | None:
        with self._connect() as conn:
            row = conn.execute(
                """SELECT id, parent_id, name, birth_date, phone, telegram_id, relationship, is_linked
                   FROM children WHERE id = ?""",
                (child_id,)
            ).fetchone()
            if row:
                return {
                    "id": row[0], "parent_id": row[1], "name": row[2],
                    "birth_date": row[3], "phone": row[4], "telegram_id": row[5],
                    "relationship": row[6], "is_linked": bool(row[7]),
                }
            return None

    def get_child_by_phone(self, phone: str) -> dict | None:
        with self._connect() as conn:
            row = conn.execute(
                """SELECT id, parent_id, name, birth_date, phone, telegram_id, relationship, is_linked
                   FROM children WHERE phone = ?""",
                (phone,)
            ).fetchone()
            if row:
                return {
                    "id": row[0], "parent_id": row[1], "name": row[2],
                    "birth_date": row[3], "phone": row[4], "telegram_id": row[5],
                    "relationship": row[6], "is_linked": bool(row[7]),
                }
            return None

    def get_child_by_telegram_id(self, telegram_id: str) -> dict | None:
        with self._connect() as conn:
            row = conn.execute(
                """SELECT id, parent_id, name, birth_date, phone, telegram_id, relationship, is_linked
                   FROM children WHERE telegram_id = ?""",
                (telegram_id,)
            ).fetchone()
            if row:
                return {
                    "id": row[0], "parent_id": row[1], "name": row[2],
                    "birth_date": row[3], "phone": row[4], "telegram_id": row[5],
                    "relationship": row[6], "is_linked": bool(row[7]),
                }
            return None

    def set_child_telegram_id(self, child_id: int, telegram_id: str):
        with self._connect() as conn:
            conn.execute(
                "UPDATE children SET telegram_id = ? WHERE id = ?", (telegram_id, child_id)
            )

    def link_child(self, child_id: int):
        """Отмечает ребёнка как привязанного (после ввода кода родителем)."""
        with self._connect() as conn:
            conn.execute(
                "UPDATE children SET is_linked = 1 WHERE id = ?", (child_id,)
            )

    # ============================================================
    # КОДЫ ПРИВЯЗКИ
    # ============================================================

    def create_linking_code(self, child_id: int) -> str:
        """Генерирует 6-значный код, действует 15 минут. Старые коды ребёнка инвалидируются."""
        code = "".join(random.choices(string.digits, k=6))
        expires_at = (datetime.now() + timedelta(minutes=15)).isoformat()
        with self._connect() as conn:
            # Удаляем неиспользованные старые коды этого ребёнка
            conn.execute(
                "DELETE FROM linking_codes WHERE child_id = ? AND used_at IS NULL",
                (child_id,)
            )
            conn.execute(
                "INSERT INTO linking_codes (child_id, code, expires_at) VALUES (?, ?, ?)",
                (child_id, code, expires_at)
            )
        return code

    def verify_linking_code(self, code: str) -> dict | None:
        """Проверяет код. Если валиден — помечает использованным и возвращает данные ребёнка."""
        with self._connect() as conn:
            row = conn.execute(
                """SELECT id, child_id, expires_at FROM linking_codes
                   WHERE code = ? AND used_at IS NULL""",
                (code,)
            ).fetchone()
            if not row:
                return None
            link_id, child_id, expires_at = row
            if datetime.fromisoformat(expires_at) < datetime.now():
                return None
            conn.execute(
                "UPDATE linking_codes SET used_at = ? WHERE id = ?",
                (datetime.now().isoformat(), link_id)
            )
        return self.get_child_by_id(child_id)

    # ============================================================
    # ПОДТВЕРЖДЕНИЕ EMAIL
    # ============================================================

    def create_email_token(self, parent_id: int, child_id: int) -> str:
        import secrets
        token = secrets.token_urlsafe(32)
        now = datetime.now()
        expires_at = (now + timedelta(hours=24)).isoformat()
        with self._connect() as conn:
            # Инвалидируем предыдущие неиспользованные токены, не удаляя их (аудит-история)
            conn.execute(
                """UPDATE email_verification_tokens
                   SET expired_at = ?
                   WHERE parent_id = ? AND verified_at IS NULL AND expired_at IS NULL""",
                (now.isoformat(), parent_id)
            )
            conn.execute(
                """INSERT INTO email_verification_tokens (parent_id, child_id, token, expires_at)
                   VALUES (?, ?, ?, ?)""",
                (parent_id, child_id, token, expires_at)
            )
        return token

    def is_email_token_verified(self, parent_id: int, child_id: int) -> bool:
        """Проверяет, подтверждён ли последний email-токен для этого родителя/ребёнка."""
        with self._connect() as conn:
            row = conn.execute(
                """SELECT verified_at FROM email_verification_tokens
                   WHERE parent_id = ? AND child_id = ?
                   ORDER BY created_at DESC LIMIT 1""",
                (parent_id, child_id)
            ).fetchone()
            return bool(row and row[0] is not None)

    def verify_email_token(self, token: str) -> dict | None:
        """Помечает токен использованным. Возвращает {parent, child} или None."""
        with self._connect() as conn:
            row = conn.execute(
                """SELECT id, parent_id, child_id, expires_at
                   FROM email_verification_tokens
                   WHERE token = ? AND verified_at IS NULL AND expired_at IS NULL""",
                (token,)
            ).fetchone()
            if not row:
                return None
            token_id, parent_id, child_id, expires_at = row
            if datetime.fromisoformat(expires_at) < datetime.now():
                return None
            conn.execute(
                "UPDATE email_verification_tokens SET verified_at = ? WHERE id = ?",
                (datetime.now().isoformat(), token_id)
            )
        parent = self.get_parent_by_id(parent_id)
        child = self.get_child_by_id(child_id)
        return {"parent": parent, "child": child}

    # ============================================================
    # ПОЛИТИКА КОНФИДЕНЦИАЛЬНОСТИ
    # ============================================================

    def get_current_policy(self) -> dict | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id, version, text, url FROM privacy_policy_versions WHERE is_current = 1"
            ).fetchone()
            if row:
                return {"id": row[0], "version": row[1], "text": row[2], "url": row[3]}
            return None

    def save_policy_version(self, version: str, text: str, url: str = None):
        """Добавляет новую версию политики и делает её текущей."""
        with self._connect() as conn:
            conn.execute("UPDATE privacy_policy_versions SET is_current = 0")
            conn.execute(
                "INSERT OR REPLACE INTO privacy_policy_versions (version, text, url, is_current) VALUES (?, ?, ?, 1)",
                (version, text, url)
            )

    def save_policy_consent(self, parent_id: int, policy_version_id: int, consent_text: str):
        """Первый opt-in: сохраняет клик «Согласен» в боте. confirmed_at = NULL до email-подтверждения."""
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO privacy_policy_consents (parent_id, policy_version_id, consent_text)
                   VALUES (?, ?, ?)""",
                (parent_id, policy_version_id, consent_text)
            )

    def confirm_policy_consent(self, parent_id: int):
        """Второй opt-in (Double Opt-In): проставляет confirmed_at после перехода по email-ссылке."""
        with self._connect() as conn:
            conn.execute(
                """UPDATE privacy_policy_consents
                   SET confirmed_at = ?
                   WHERE id = (
                       SELECT id FROM privacy_policy_consents
                       WHERE parent_id = ? AND confirmed_at IS NULL
                       ORDER BY consented_at DESC
                       LIMIT 1
                   )""",
                (datetime.now().isoformat(), parent_id)
            )

    # ============================================================
    # ЛОГ РЕГИСТРАЦИИ
    # ============================================================

    def log_registration_event(self, event_type: str, parent_id: int = None,
                                child_id: int = None, details: str = None):
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO registration_logs (parent_id, child_id, event_type, details)
                   VALUES (?, ?, ?, ?)""",
                (parent_id, child_id, event_type, details)
            )

    # ============================================================
    # FCM ТОКЕНЫ УСТРОЙСТВ
    # ============================================================

    def save_device_token(self, child_id: int, fcm_token: str, platform: str = "android"):
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO device_tokens (child_id, fcm_token, platform, updated_at)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(child_id) DO UPDATE SET
                       fcm_token=excluded.fcm_token,
                       platform=excluded.platform,
                       updated_at=excluded.updated_at""",
                (child_id, fcm_token, platform, datetime.now().isoformat())
            )

    def get_device_token(self, child_id: int) -> str | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT fcm_token FROM device_tokens WHERE child_id = ?", (child_id,)
            ).fetchone()
            return row[0] if row else None

    # ============================================================
    # БЛОКИРОВКИ
    # ============================================================

    def add_blocked(self, item_type: str, item_id: str, name: str = "", child_id: int = None):
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO blocked (child_id, type, item_id, name) VALUES (?, ?, ?, ?)",
                (child_id, item_type, item_id, name)
            )

    def remove_blocked(self, block_id: int):
        with self._connect() as conn:
            conn.execute("DELETE FROM blocked WHERE id = ?", (block_id,))

    def is_blocked(self, item_type: str, item_id: str, child_id: int = None) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id FROM blocked WHERE type = ? AND item_id = ? AND (child_id = ? OR child_id IS NULL)",
                (item_type, item_id, child_id)
            ).fetchone()
            return row is not None

    def get_all_blocked(self, child_id: int = None) -> list:
        with self._connect() as conn:
            if child_id is not None:
                rows = conn.execute(
                    """SELECT id, type, item_id, name FROM blocked
                       WHERE child_id = ? OR child_id IS NULL
                       ORDER BY created_at DESC""",
                    (child_id,)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT id, type, item_id, name FROM blocked ORDER BY created_at DESC"
                ).fetchall()
            return [
                {"id": r[0], "type": r[1], "item_id": r[2], "name": r[3]}
                for r in rows
            ]

    # ============================================================
    # ЗАПРОСЫ НА РАЗРЕШЕНИЕ
    # ============================================================

    def save_pending_request(self, request_id: str, data: dict, child_id: int = None):
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO pending_requests (request_id, child_id, data, status) VALUES (?, ?, ?, ?)",
                (request_id, child_id, json.dumps(data), "pending")
            )

    def get_pending_request(self, request_id: str) -> dict | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT data, status FROM pending_requests WHERE request_id = ?",
                (request_id,)
            ).fetchone()
            if row:
                data = json.loads(row[0])
                data["status"] = row[1]
                return data
            return None

    def update_request_status(self, request_id: str, status: str):
        with self._connect() as conn:
            conn.execute(
                "UPDATE pending_requests SET status = ?, updated_at = ? WHERE request_id = ?",
                (status, datetime.now().isoformat(), request_id)
            )

    def get_pending_requests(self, child_id: int = None) -> dict:
        with self._connect() as conn:
            if child_id is not None:
                rows = conn.execute(
                    """SELECT request_id, data, status FROM pending_requests
                       WHERE status = 'pending' AND child_id = ?""",
                    (child_id,)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT request_id, data, status FROM pending_requests WHERE status = 'pending'"
                ).fetchall()
            result = {}
            for row in rows:
                data = json.loads(row[1])
                data["status"] = row[2]
                result[row[0]] = data
            return result

    # ============================================================
    # НАСТРОЙКИ
    # ============================================================

    def get_setting(self, key: str, default=None):
        with self._connect() as conn:
            row = conn.execute(
                "SELECT value FROM settings WHERE key = ?", (key,)
            ).fetchone()
            return row[0] if row else default

    def set_setting(self, key: str, value: str):
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                (key, value)
            )

    # ============================================================
    # ЛОГ АКТИВНОСТИ
    # ============================================================

    def log_activity(self, action: str, details: str = "", child_id: int = None):
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO activity_log (child_id, action, details) VALUES (?, ?, ?)",
                (child_id, action, details)
            )

    def get_activity_log(self, limit: int = 50, child_id: int = None) -> list:
        with self._connect() as conn:
            if child_id is not None:
                rows = conn.execute(
                    """SELECT action, details, created_at FROM activity_log
                       WHERE child_id = ? ORDER BY created_at DESC LIMIT ?""",
                    (child_id, limit)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT action, details, created_at FROM activity_log ORDER BY created_at DESC LIMIT ?",
                    (limit,)
                ).fetchall()
            return [
                {"action": r[0], "details": r[1], "created_at": r[2]}
                for r in rows
            ]
