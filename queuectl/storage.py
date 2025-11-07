# storage.py -  This is the persistence layer for queuectl which uses SQLite to store jobs and configuration.

import sqlite3
import time
from datetime import datetime, timezone
import json
from typing import Optional, Dict, Any, List, Tuple

DB_PATH = "queue.db"

def iso_now() -> str:
    #Returns current UTC time in ISO format
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat() + "Z"

def now_ts() -> float:
    #Return current time as POSIX timestamp 
    return time.time()

class JobStore:
    """
    SQLite-backed job store.

    Methods included in the class are:
      . init_db(): create tables if missing
      . enqueue(job_dict): insert a job
      . claim_one(): atomically claim a runnable job and mark it as processing
      . mark_completed(job_id)
      . schedule_retry_or_dead(job_id, attempts, max_retries, last_error)
      . list_by_state(state=None)
      . get(job_id)
      . config_get/set

    """

    def __init__(self, path: str = DB_PATH):
        # store DB path
        self.path = path

    def _conn(self):
        # open a sqlite connection with row factory for name based access
        conn = sqlite3.connect(self.path, timeout=30, isolation_level=None)
        conn.row_factory = sqlite3.Row
        return conn
 
    def init_db(self):
        
        #Initialize database schema. Uses WAL journaling.
        
        conn = self._conn()
        cur = conn.cursor()

        # enable WAL and create tables
        cur.executescript("""
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            command TEXT NOT NULL,
            state TEXT NOT NULL,
            attempts INTEGER NOT NULL DEFAULT 0,
            max_retries INTEGER NOT NULL DEFAULT 3,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            next_run_at REAL NOT NULL DEFAULT 0,
            last_error TEXT
        );
        CREATE TABLE IF NOT EXISTS config (
            k TEXT PRIMARY KEY,
            v TEXT NOT NULL
        );
        """)
        # default configs
        cur.execute("INSERT OR IGNORE INTO config(k,v) VALUES(?,?)", ("backoff_base", "2"))
        cur.execute("INSERT OR IGNORE INTO config(k,v) VALUES(?,?)", ("max_retries", "3"))
        conn.commit()
        conn.close()

    def config_get(self, key: str) -> Optional[str]:
        conn = self._conn()
        cur = conn.cursor()
        cur.execute("SELECT v FROM config WHERE k=?", (key,))
        row = cur.fetchone()
        conn.close()
        return row["v"] if row else None

    def config_set(self, key: str, value: str):
        conn = self._conn()
        cur = conn.cursor()
        cur.execute("INSERT OR REPLACE INTO config(k,v) VALUES(?,?)", (key, str(value)))
        conn.commit()
        conn.close()

    def enqueue(self, job: Dict[str, Any]) -> str:
        """
        Insert a job dictionary into jobs table.
        Required field  is 'command'
        Returns job id.

        """
        # generate id if not present
        job_id = job.get("id") or f"job-{int(time.time()*1000)}"
        command = job.get("command")
        if not command:
            raise ValueError("job must have 'command'")
        max_retries = int(job.get("max_retries") or int(self.config_get("max_retries") or 3))
        now_iso = iso_now()
        now_epoch = now_ts()

        conn = self._conn()
        cur = conn.cursor()
        cur.execute("""
            INSERT OR REPLACE INTO jobs (id, command, state, attempts, max_retries, created_at, updated_at, next_run_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (job_id, command, "pending", 0, max_retries, now_iso, now_iso, now_epoch))
        conn.commit()
        conn.close()
        return job_id

    def claim_one(self) -> Optional[Dict[str, Any]]:
        """
        Atomically claim one runnable job (pending or failed) whose next_run_at <= now.
        Returns the row as dict or None if no job available.
        This uses BEGIN IMMEDIATE to ensure only one process successfully updates the chosen job.
        """
        conn = self._conn()
        cur = conn.cursor()
        now = now_ts()
        try:
            cur.execute("BEGIN IMMEDIATE")
            # pick an eligible job; ordering by created_at gives FIFO behavior
            cur.execute("""
                SELECT * FROM jobs
                WHERE (state = 'pending' OR state = 'failed') AND next_run_at <= ?
                ORDER BY created_at ASC
                LIMIT 1
            """, (now,))
            row = cur.fetchone()
            if not row:
                conn.commit()
                return None
            job_id = row["id"]
            new_attempts = row["attempts"] + 1
            cur.execute("""
                UPDATE jobs
                SET state = ?, attempts = ?, updated_at = ?
                WHERE id = ?
            """, ("processing", new_attempts, iso_now(), job_id))
            conn.commit()
            # re-fetch the updated row to return consistent data
            cur.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
            claimed = cur.fetchone()
            return dict(claimed) if claimed else None
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def mark_completed(self, job_id: str):
        conn = self._conn()
        cur = conn.cursor()
        cur.execute("UPDATE jobs SET state=?, updated_at=? WHERE id=?", ("completed", iso_now(), job_id))
        conn.commit()
        conn.close()

    def schedule_retry_or_dead(self, job_id: str, attempts: int, max_retries: int, last_error: str):
        """
        If attempts > max_retries -> mark dead.
        Else compute backoff delay = base ** attempts (seconds)
        and set next_run_at = now + delay and state = 'failed'
        """
        base = float(self.config_get("backoff_base") or 2)
        conn = self._conn()
        cur = conn.cursor()
        if attempts > max_retries:
            cur.execute("UPDATE jobs SET state=?, updated_at=?, last_error=? WHERE id=?",
                        ("dead", iso_now(), last_error, job_id))
        else:
            delay = base ** attempts
            next_run = now_ts() + delay
            cur.execute("UPDATE jobs SET state=?, next_run_at=?, updated_at=?, last_error=? WHERE id=?",
                        ("failed", next_run, iso_now(), last_error, job_id))
        conn.commit()
        conn.close()

    def list_by_state(self, state: Optional[str] = None) -> List[Dict[str, Any]]:
        conn = self._conn()
        cur = conn.cursor()
        if state:
            cur.execute("SELECT * FROM jobs WHERE state=? ORDER BY created_at ASC", (state,))
        else:
            cur.execute("SELECT * FROM jobs ORDER BY created_at ASC")
        rows = cur.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get(self, job_id: str) -> Optional[Dict[str, Any]]:
        conn = self._conn()
        cur = conn.cursor()
        cur.execute("SELECT * FROM jobs WHERE id=?", (job_id,))
        row = cur.fetchone()
        conn.close()
        return dict(row) if row else None
