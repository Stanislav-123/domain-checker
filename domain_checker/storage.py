"""SQLite storage for domain check history and state."""

import aiosqlite
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional


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
                    updated_at TEXT NOT NULL
                )
            """)
            
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_domain_checks_domain 
                ON domain_checks(domain)
            """)
            
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_domain_checks_checked_at 
                ON domain_checks(checked_at)
            """)
            
            await db.commit()
    
    async def save_check_result(self, domain: str, result: Dict):
        """Save domain check result.
        
        Args:
            domain: Domain name
            result: Check result dictionary
        """
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO domain_checks (
                    domain, checked_at, status, http_code, response_time_ms,
                    dns_resolved, ssl_valid, ssl_days_remaining, error_message,
                    consecutive_failures
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                domain,
                datetime.now(timezone.utc).isoformat(),
                result.get('status', 'unknown'),
                result.get('http_code'),
                result.get('response_time_ms'),
                result.get('dns_resolved'),
                result.get('ssl_valid'),
                result.get('ssl_days_remaining'),
                result.get('error_message'),
                result.get('consecutive_failures', 0)
            ))
            await db.commit()
    
    async def get_domain_state(self, domain: str) -> Optional[Dict]:
        """Get current state of a domain.
        
        Args:
            domain: Domain name
            
        Returns:
            Domain state dictionary or None if not found
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM domain_state WHERE domain = ?",
                (domain,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return dict(row)
                return None
    
    async def update_domain_state(self, domain: str, state: Dict):
        """Update domain state.
        
        Args:
            domain: Domain name
            state: State dictionary with last_status, consecutive_failures, etc.
        """
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO domain_state (
                    domain, last_status, consecutive_failures,
                    last_alert_sent, last_recovery_sent, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                domain,
                state.get('last_status', 'unknown'),
                state.get('consecutive_failures', 0),
                state.get('last_alert_sent'),
                state.get('last_recovery_sent'),
                datetime.now(timezone.utc).isoformat()
            ))
            await db.commit()
    
    async def get_recent_checks(self, domain: str, limit: int = 10) -> List[Dict]:
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
                (domain, limit)
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
    
    async def get_all_domain_states(self) -> List[Dict]:
        """Get states of all domains.
        
        Returns:
            List of domain state dictionaries
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM domain_state") as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
