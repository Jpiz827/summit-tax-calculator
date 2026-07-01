"""
Summit Tax Services — Client Database Module
SQLite-backed client tracking with actions, reports, and dashboard data.
"""

import sqlite3
import random
import string
import os
from datetime import datetime, timezone

# Use /tmp for writable storage on Railway (ephemeral), local dir for dev
DATA_DIR = os.environ.get('DATA_DIR', os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(DATA_DIR, 'clients.db')

# Characters for client IDs: uppercase alphanumeric, no ambiguous chars (O/0/I/1/L)
ID_CHARS = 'ABCDEFGHJKMNPQRSTUVWXYZ23456789'


def _get_conn():
    """Get a database connection with row factory."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _init_db():
    """Create tables if they don't exist."""
    conn = _get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS clients (
            id TEXT PRIMARY KEY,
            first_name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            phone TEXT,
            created_at DATETIME NOT NULL,
            guide_sent_at DATETIME
        );

        CREATE TABLE IF NOT EXISTS actions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id TEXT NOT NULL,
            action TEXT NOT NULL,
            details TEXT DEFAULT '',
            created_at DATETIME NOT NULL,
            FOREIGN KEY (client_id) REFERENCES clients(id)
        );

        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id TEXT NOT NULL,
            calculator TEXT NOT NULL,
            inputs_json TEXT,
            sent_at DATETIME NOT NULL,
            FOREIGN KEY (client_id) REFERENCES clients(id)
        );

        CREATE TABLE IF NOT EXISTS checkup_submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id TEXT NOT NULL,
            request_type TEXT,
            wants_call INTEGER DEFAULT 0,
            hot_lead INTEGER DEFAULT 0,
            filing TEXT,
            age TEXT,
            ss_taxed TEXT,
            provisional TEXT,
            projected_rmd TEXT,
            irmaa_tier TEXT,
            created_at DATETIME NOT NULL,
            FOREIGN KEY (client_id) REFERENCES clients(id)
        );

        CREATE TABLE IF NOT EXISTS lead_status (
            client_id TEXT PRIMARY KEY,
            status TEXT NOT NULL DEFAULT 'New',
            notes TEXT DEFAULT '',
            next_follow_up TEXT,
            updated_at DATETIME NOT NULL,
            FOREIGN KEY (client_id) REFERENCES clients(id)
        );

        CREATE INDEX IF NOT EXISTS idx_actions_client_id ON actions(client_id);
        CREATE INDEX IF NOT EXISTS idx_actions_created_at ON actions(created_at);
        CREATE INDEX IF NOT EXISTS idx_reports_client_id ON reports(client_id);
        CREATE INDEX IF NOT EXISTS idx_checkup_client_id ON checkup_submissions(client_id);
        CREATE INDEX IF NOT EXISTS idx_checkup_created_at ON checkup_submissions(created_at);
    """)
    conn.commit()
    conn.close()


# Auto-initialize database on import
_init_db()


def _generate_client_id():
    """Generate a unique 6-character client ID."""
    conn = _get_conn()
    while True:
        client_id = ''.join(random.choices(ID_CHARS, k=6))
        row = conn.execute("SELECT id FROM clients WHERE id = ?", (client_id,)).fetchone()
        if row is None:
            conn.close()
            return client_id


def _row_to_dict(row):
    """Convert a sqlite3.Row to a plain dict."""
    if row is None:
        return None
    return dict(row)


def create_client(first_name, email, phone=None):
    """Create a new client. Returns client dict with unique 6-char ID."""
    conn = _get_conn()
    client_id = _generate_client_id()
    now = datetime.now(timezone.utc).isoformat()
    try:
        conn.execute(
            "INSERT INTO clients (id, first_name, email, phone, created_at) VALUES (?, ?, ?, ?, ?)",
            (client_id, first_name, email, phone, now),
        )
        conn.commit()
        client = _row_to_dict(
            conn.execute("SELECT * FROM clients WHERE id = ?", (client_id,)).fetchone()
        )
        conn.close()
        return client
    except sqlite3.IntegrityError:
        conn.close()
        raise ValueError(f"Client with email '{email}' already exists")


def get_client(client_id):
    """Return client dict by ID, or None if not found."""
    conn = _get_conn()
    row = conn.execute("SELECT * FROM clients WHERE id = ?", (client_id,)).fetchone()
    conn.close()
    return _row_to_dict(row)


def get_client_by_email(email):
    """Return client dict by email, or None if not found."""
    conn = _get_conn()
    row = conn.execute("SELECT * FROM clients WHERE email = ?", (email,)).fetchone()
    conn.close()
    return _row_to_dict(row)


def log_action(client_id, action, details=''):
    """Insert an action record for a client."""
    conn = _get_conn()
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO actions (client_id, action, details, created_at) VALUES (?, ?, ?, ?)",
        (client_id, action, details, now),
    )
    conn.commit()
    conn.close()


def get_all_clients():
    """Return list of all clients with their action counts."""
    conn = _get_conn()
    rows = conn.execute("""
        SELECT c.*, COUNT(a.id) AS action_count
        FROM clients c
        LEFT JOIN actions a ON c.id = a.client_id
        GROUP BY c.id
        ORDER BY c.created_at DESC
    """).fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]


def get_client_actions(client_id):
    """Return list of actions for a client, newest first."""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM actions WHERE client_id = ? ORDER BY created_at DESC",
        (client_id,),
    ).fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]


def log_report(client_id, calculator, inputs_json):
    """Insert a report record for a client."""
    conn = _get_conn()
    now = datetime.now(timezone.utc).isoformat()
    cursor = conn.execute(
        "INSERT INTO reports (client_id, calculator, inputs_json, sent_at) VALUES (?, ?, ?, ?)",
        (client_id, calculator, inputs_json, now),
    )
    report_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return report_id


def get_dashboard_data():
    """Return all clients with latest actions, report counts, and guide status."""
    conn = _get_conn()
    rows = conn.execute("""
        SELECT
            c.*,
            COUNT(DISTINCT a.id) AS action_count,
            COUNT(DISTINCT r.id) AS report_count,
            c.guide_sent_at IS NOT NULL AS guide_sent,
            latest_action.action AS latest_action_type,
            latest_action.created_at AS latest_action_at
        FROM clients c
        LEFT JOIN actions a ON c.id = a.client_id
        LEFT JOIN reports r ON c.id = r.client_id
        LEFT JOIN (
            SELECT client_id, action, created_at
            FROM actions a2
            WHERE created_at = (
                SELECT MAX(a3.created_at)
                FROM actions a3
                WHERE a3.client_id = a2.client_id
            )
        ) latest_action ON c.id = latest_action.client_id
        GROUP BY c.id
        ORDER BY c.created_at DESC
    """).fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]


def find_or_create_client(first_name, email, phone=None):
    """Get client by email or create a new one. Returns client dict."""
    existing = get_client_by_email(email)
    if existing:
        return existing
    return create_client(first_name, email, phone)


LEAD_STATUSES = ('New', 'Contacted', 'Booked', 'Client', 'Lost')


def _ensure_lead_status(conn, client_id):
    """Insert a default 'New' lead_status row for a client if none exists yet."""
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT OR IGNORE INTO lead_status (client_id, status, notes, next_follow_up, updated_at) "
        "VALUES (?, 'New', '', NULL, ?)",
        (client_id, now),
    )


def create_checkup_submission(client_id, request_type, wants_call, hot_lead,
                               filing, age, ss_taxed, provisional, projected_rmd, irmaa_tier):
    """Insert a Check-Up tool submission for a client and ensure it appears on the leads dashboard."""
    conn = _get_conn()
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        """INSERT INTO checkup_submissions
           (client_id, request_type, wants_call, hot_lead, filing, age, ss_taxed,
            provisional, projected_rmd, irmaa_tier, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (client_id, request_type, 1 if wants_call else 0, 1 if hot_lead else 0,
         filing, age, ss_taxed, provisional, projected_rmd, irmaa_tier, now),
    )
    _ensure_lead_status(conn, client_id)
    conn.commit()
    conn.close()


def update_lead_status(client_id, status, notes, next_follow_up):
    """Update (or create) the CRM status/notes/follow-up date for a client."""
    if status not in LEAD_STATUSES:
        raise ValueError(f"Invalid status: {status}")
    conn = _get_conn()
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        """INSERT INTO lead_status (client_id, status, notes, next_follow_up, updated_at)
           VALUES (?, ?, ?, ?, ?)
           ON CONFLICT(client_id) DO UPDATE SET
             status=excluded.status, notes=excluded.notes,
             next_follow_up=excluded.next_follow_up, updated_at=excluded.updated_at""",
        (client_id, status, notes or '', next_follow_up or None, now),
    )
    conn.commit()
    conn.close()


def get_leads_dashboard():
    """Return one row per client who has at least one Check-Up submission,
    with their latest submission numbers and current CRM status."""
    conn = _get_conn()
    rows = conn.execute("""
        SELECT
            c.id AS client_id, c.first_name, c.email, c.phone, c.created_at AS first_seen,
            latest.request_type, latest.wants_call, latest.hot_lead, latest.filing, latest.age,
            latest.ss_taxed, latest.provisional, latest.projected_rmd, latest.irmaa_tier,
            latest.created_at AS last_submitted,
            sub_counts.submission_count,
            COALESCE(ls.status, 'New') AS status,
            COALESCE(ls.notes, '') AS notes,
            ls.next_follow_up
        FROM clients c
        JOIN checkup_submissions latest ON latest.id = (
            SELECT s2.id FROM checkup_submissions s2
            WHERE s2.client_id = c.id ORDER BY s2.created_at DESC LIMIT 1
        )
        JOIN (
            SELECT client_id, COUNT(*) AS submission_count
            FROM checkup_submissions GROUP BY client_id
        ) sub_counts ON sub_counts.client_id = c.id
        LEFT JOIN lead_status ls ON ls.client_id = c.id
        ORDER BY
            CASE WHEN ls.next_follow_up IS NOT NULL AND ls.next_follow_up <= date('now') THEN 0 ELSE 1 END,
            latest.hot_lead DESC,
            latest.created_at DESC
    """).fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]


# Auto-initialize on import
_init_db()