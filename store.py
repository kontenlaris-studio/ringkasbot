"""Credit ledger for RingkasBot — SQLite (stdlib).

Every user gets FREE_TRIAL free summaries. Paid credits are added only by a
verified Telegram Stars payment (charge id stored, so a payment can never be
credited twice). Spending is atomic: a summary is charged exactly once, and
only after it succeeds.
"""
import sqlite3
import threading

FREE_TRIAL = 3


class Store:
    def __init__(self, path="ringkasbot.db"):
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.lock = threading.Lock()
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS users(
                user_id INTEGER PRIMARY KEY,
                free_used INTEGER NOT NULL DEFAULT 0,
                credits INTEGER NOT NULL DEFAULT 0,
                summaries INTEGER NOT NULL DEFAULT 0,
                joined TEXT NOT NULL DEFAULT (datetime('now')));
            CREATE TABLE IF NOT EXISTS payments(
                charge_id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                credits INTEGER NOT NULL,
                stars INTEGER NOT NULL,
                at TEXT NOT NULL DEFAULT (datetime('now')));
        """)
        self.db.commit()

    def _user(self, uid):
        row = self.db.execute(
            "SELECT free_used, credits, summaries FROM users WHERE user_id=?", (uid,)).fetchone()
        if row is None:
            self.db.execute("INSERT INTO users(user_id) VALUES(?)", (uid,))
            self.db.commit()
            return 0, 0, 0
        return row

    def balance(self, uid):
        free_used, credits, _ = self._user(uid)
        return {"free_left": max(0, FREE_TRIAL - free_used), "credits": credits}

    def can_afford(self, uid):
        b = self.balance(uid)
        return b["free_left"] > 0 or b["credits"] > 0

    def charge(self, uid):
        """Charge one summary. Returns 'free', 'credit', or None if unaffordable."""
        with self.lock:
            free_used, credits, summaries = self._user(uid)
            if free_used < FREE_TRIAL:
                self.db.execute(
                    "UPDATE users SET free_used=free_used+1, summaries=summaries+1 WHERE user_id=?", (uid,))
                self.db.commit()
                return "free"
            if credits > 0:
                self.db.execute(
                    "UPDATE users SET credits=credits-1, summaries=summaries+1 WHERE user_id=?", (uid,))
                self.db.commit()
                return "credit"
            return None

    def add_payment(self, uid, charge_id, credits, stars):
        """Credit a verified Stars payment. Idempotent on charge_id."""
        with self.lock:
            try:
                self.db.execute(
                    "INSERT INTO payments(charge_id, user_id, credits, stars) VALUES(?,?,?,?)",
                    (charge_id, uid, credits, stars))
            except sqlite3.IntegrityError:
                return False  # already credited
            self._user(uid)
            self.db.execute("UPDATE users SET credits=credits+? WHERE user_id=?", (credits, uid))
            self.db.commit()
            return True

    def stats(self):
        users = self.db.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        earned = self.db.execute("SELECT COALESCE(SUM(stars),0) FROM payments").fetchone()[0]
        done = self.db.execute("SELECT COALESCE(SUM(summaries),0) FROM users").fetchone()[0]
        return {"users": users, "stars_earned": earned, "summaries": done}
