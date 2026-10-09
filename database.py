import sqlite3
from datetime import datetime
from pathlib import Path
from contextlib import contextmanager

DB_PATH = Path(__file__).parent / "tickets.db"


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    """Создаёт таблицу при первом запуске. Безопасно вызывать повторно."""
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tickets (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id      INTEGER NOT NULL,
                user_name    TEXT,
                question     TEXT NOT NULL,
                status       TEXT NOT NULL DEFAULT 'new',
                answer       TEXT,
                created_at   TEXT NOT NULL,
                answered_at  TEXT
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tickets_user ON tickets(user_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets(status)")


def create_ticket(user_id: int, user_name: str, question: str) -> int:
    """Сохраняет вопрос, возвращает ID тикета."""
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO tickets (user_id, user_name, question, status, created_at) "
            "VALUES (?, ?, ?, 'new', ?)",
            (user_id, user_name, question, datetime.now().isoformat(timespec="seconds")),
        )
        return cur.lastrowid


def get_ticket(ticket_id: int) -> dict | None:
    """Возвращает тикет по ID или None."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM tickets WHERE id = ?", (ticket_id,)
        ).fetchone()
        return dict(row) if row else None


def save_answer_by_ticket(ticket_id: int, answer: str) -> bool:
    """Сохраняет ответ конкретному тикету. Возвращает True при успехе."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id FROM tickets WHERE id = ?", (ticket_id,)
        ).fetchone()
        if row is None:
            return False
        conn.execute(
            "UPDATE tickets SET status = 'answered', answer = ?, answered_at = ? "
            "WHERE id = ?",
            (answer, datetime.now().isoformat(timespec="seconds"), ticket_id),
        )
        return True

def get_user_history(user_id: int, limit: int = 5) -> list[dict]:
    """Последние N тикетов пользователя (на будущее — для команды /history)."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM tickets WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]