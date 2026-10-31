"""SQLite storage for domain check history and state."""

from datetime import datetime, timezone
from pathlib import Path

import aiosqlite


class Storage:
    """Storage for domain check results and state."""

    def __init__(self, db_path: str):
        """Initialize storage.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    async def initialize(self):
        """Create database tables if they don't exist."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS domain_checks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    domain TEXT NOT NULL,
                    checked_at TEXT NOT NULL,
                    status TEXT NOT NULL,
                    http_code INTEGER,
                    response_time_ms INTEGER,
                    dns_resolved BOOLEAN,
                    ssl_valid BOOLEAN,
                    ssl_days_remaining INTEGER,
                    error_message TEXT,
                    consecutive_failures INTEGER DEFAULT 0
                )
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS domain_state (
                    domain TEXT PRIMARY KEY,
                    last_status TEXT NOT NULL,
                    consecutive_failures INTEGER DEFAULT 0,
                    last_alert_sent TEXT,
                    last_recovery_sent TEXT,
                    updated_at TEXT NOT NULL,
                    is_active BOOLEAN DEFAULT 1,
                    last_seen TEXT NOT NULL
                )
            """)

            # Migrate databases created by v1.0.x (no is_active / last_seen).
            async with db.execute("PRAGMA table_info(domain_state)") as cur:
                columns = {row[1] for row in await cur.fetchall()}
            if "is_active" not in columns:
                await db.execute(
                    "ALTER TABLE domain_state ADD COLUMN is_active BOOLEAN DEFAULT 1"
                )
            if "last_seen" not in columns:
                await db.execute(
                    "ALTER TABLE domain_state ADD COLUMN last_seen TEXT NOT NULL DEFAULT ''"
                )
                await db.execute(
                    "UPDATE domain_state SET last_seen = updated_at WHERE last_seen = ''"
                )

            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_domain_checks_domain
                ON domain_checks(domain)
            """)

            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_domain_checks_checked_at
                ON domain_checks(checked_at)
            """)

            await db.commit()

    async def save_check_result(self, domain: str, result: dict):
        """Save domain check result.

        Args:
            domain: Domain name
            result: Check result dictionary
        """
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO domain_checks (
                    domain, checked_at, status, http_code, response_time_ms,
                    dns_resolved, ssl_valid, ssl_days_remaining, error_message,
                    consecutive_failures
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    domain,
                    datetime.now(timezone.utc).isoformat(),
                    result.get("status", "unknown"),
                    result.get("http_code"),
                    result.get("response_time_ms"),
                    result.get("dns_resolved"),
                    result.get("ssl_valid"),
                    result.get("ssl_days_remaining"),
                    result.get("error_message"),
                    result.get("consecutive_failures", 0),
                ),
            )
            await db.commit()

    async def get_domain_state(self, domain: str) -> dict | None:
        """Get current state of a domain.

        Args:
            domain: Domain name

        Returns:
            Domain state dictionary or None if not found
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM domain_state WHERE domain = ?", (domain,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return dict(row)
                return None

    async def update_domain_state(self, domain: str, state: dict):
        """Update domain state.

        Args:
            domain: Domain name
            state: State dictionary with last_status, consecutive_failures, etc.
        """
        now = datetime.now(timezone.utc).isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT OR REPLACE INTO domain_state (
                    domain, last_status, consecutive_failures,
                    last_alert_sent, last_recovery_sent, updated_at,
                    is_active, last_seen
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    domain,
                    state.get("last_status", "unknown"),
                    state.get("consecutive_failures", 0),
                    state.get("last_alert_sent"),
                    state.get("last_recovery_sent"),
                    now,
                    state.get("is_active", True),
                    state.get("last_seen", now),
                ),
            )
            await db.commit()

    async def get_recent_checks(self, domain: str, limit: int = 10) -> list[dict]:
        """Get recent check results for a domain.

        Args:
            domain: Domain name
            limit: Maximum number of results to return

        Returns:
            List of check result dictionaries
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """
                SELECT * FROM domain_checks
                WHERE domain = ?
                ORDER BY checked_at DESC
                LIMIT ?
                """,
                (domain, limit),
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def get_all_domain_states(self, active_only: bool = True) -> list[dict]:
        """Get states of all domains.

        Args:
            active_only: If True, only return active domains

        Returns:
            List of domain state dictionaries
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            query = "SELECT * FROM domain_state"
            if active_only:
                query += " WHERE is_active = 1"
            async with db.execute(query) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def mark_domains_inactive(self, active_domains: list[str]):
        """Mark domains not in the active list as inactive.

        Args:
            active_domains: List of currently active domain names
        """
        async with aiosqlite.connect(self.db_path) as db:
            placeholders = ",".join("?" * len(active_domains))
            query = f"""
                UPDATE domain_state
                SET is_active = 0
                WHERE domain NOT IN ({placeholders}) AND is_active = 1
            """
            await db.execute(query, active_domains)
            await db.commit()

    async def mark_domains_active(self, domains: list[str]):
        """Mark domains as active and update their last_seen timestamp.

        Args:
            domains: List of domain names to mark as active
        """
        now = datetime.now(timezone.utc).isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            for domain in domains:
                await db.execute(
                    "UPDATE domain_state SET is_active = 1, last_seen = ? WHERE domain = ?",
                    (now, domain),
                )
            await db.commit()
