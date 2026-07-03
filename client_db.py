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
            score INTEGER DEFAULT 0,
            tier TEXT DEFAULT 'Green',
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

        CREATE TABLE IF NOT EXISTS email_sequence_state (
            client_id TEXT PRIMARY KEY,
            started_at DATETIME NOT NULL,
            last_step_sent INTEGER DEFAULT 0,
            paused INTEGER DEFAULT 0,
            FOREIGN KEY (client_id) REFERENCES clients(id)
        );

        CREATE INDEX IF NOT EXISTS idx_actions_client_id ON actions(client_id);
        CREATE INDEX IF NOT EXISTS idx_actions_created_at ON actions(created_at);
        CREATE INDEX IF NOT EXISTS idx_reports_client_id ON reports(client_id);
        CREATE INDEX IF NOT EXISTS idx_checkup_client_id ON checkup_submissions(client_id);
        CREATE INDEX IF NOT EXISTS idx_checkup_created_at ON checkup_submissions(created_at);
    """)
    # Backfill columns for databases created before score/tier existed.
    # SQLite has no "ADD COLUMN IF NOT EXISTS" — guard with a catch on the
    # duplicate-column error instead.
    for stmt in (
        "ALTER TABLE checkup_submissions ADD COLUMN score INTEGER DEFAULT 0",
        "ALTER TABLE checkup_submissions ADD COLUMN tier TEXT DEFAULT 'Green'",
    ):
        try:
            conn.execute(stmt)
        except sqlite3.OperationalError:
            pass  # column already exists
    conn.commit()
    conn.close()


TIER_GREEN, TIER_YELLOW, TIER_RED = 'Green', 'Yellow', 'Red'


def compute_lead_score(ss_taxed, irmaa_tier, hot_lead):
    """Derive a 0-11 risk score and a Green/Yellow/Red tier from the same
    figures already shown on the Check-Up tool (no new inputs required).

    ss_taxed: string like "42%" (or "" / None)
    irmaa_tier: tier name string, e.g. "Standard", "Tier 1", ... (or "" / None)
    hot_lead: truthy/falsy (couple, or IRA balance >= $750k, per checkup.html)
    """
    score = 0
    try:
        pct = float(str(ss_taxed).strip().rstrip('%')) if ss_taxed else 0
    except ValueError:
        pct = 0
    if pct >= 85:
        score += 4
    elif pct >= 50:
        score += 2
    elif pct > 0:
        score += 1

    if irmaa_tier and str(irmaa_tier).strip().lower() != 'standard':
        score += 3

    if hot_lead:
        score += 2

    if score >= 6:
        tier = TIER_RED
    elif score >= 3:
        tier = TIER_YELLOW
    else:
        tier = TIER_GREEN
    return score, tier


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
    """Insert a Check-Up tool submission for a client and ensure it appears on the leads dashboard.
    Also computes the Score/Tier and (re)starts the email nurture sequence for this client."""
    conn = _get_conn()
    now = datetime.now(timezone.utc).isoformat()
    score, tier = compute_lead_score(ss_taxed, irmaa_tier, hot_lead)
    conn.execute(
        """INSERT INTO checkup_submissions
           (client_id, request_type, wants_call, hot_lead, filing, age, ss_taxed,
            provisional, projected_rmd, irmaa_tier, score, tier, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (client_id, request_type, 1 if wants_call else 0, 1 if hot_lead else 0,
         filing, age, ss_taxed, provisional, projected_rmd, irmaa_tier, score, tier, now),
    )
    _ensure_lead_status(conn, client_id)
    # Start the drip sequence the first time we see this client; a repeat
    # Check-Up submission should not reset an already-running sequence.
    conn.execute(
        "INSERT OR IGNORE INTO email_sequence_state (client_id, started_at, last_step_sent, paused) "
        "VALUES (?, ?, 0, 0)",
        (client_id, now),
    )
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
            latest.score, latest.tier,
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
            CASE latest.tier WHEN 'Red' THEN 0 WHEN 'Yellow' THEN 1 ELSE 2 END,
            latest.hot_lead DESC,
            latest.created_at DESC
    """).fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]


# ─── Email nurture sequence ───────────────────────────────────────────

def get_leads_due_for_sequence_email(sequence_days):
    """Return [{client_id, first_name, email, next_step, days_elapsed}, ...]
    for every client whose next unsent drip step's day-offset has arrived.

    sequence_days: sorted list of day-offsets for steps 1, 2, 3, ... (step 0
    is the instant "your result" email already sent by the Check-Up tool
    itself, so this list starts at the first drip step).
    """
    conn = _get_conn()
    rows = conn.execute("""
        SELECT c.id AS client_id, c.first_name, c.email,
               es.started_at, es.last_step_sent
        FROM email_sequence_state es
        JOIN clients c ON c.id = es.client_id
        WHERE es.paused = 0 AND es.last_step_sent < ?
    """, (len(sequence_days),)).fetchall()
    conn.close()

    now = datetime.now(timezone.utc)
    due = []
    for r in rows:
        started = datetime.fromisoformat(r['started_at'])
        if started.tzinfo is None:
            started = started.replace(tzinfo=timezone.utc)
        days_elapsed = (now - started).days
        next_step = r['last_step_sent'] + 1  # 1-indexed into sequence_days
        threshold = sequence_days[next_step - 1]
        if days_elapsed >= threshold:
            due.append({
                'client_id': r['client_id'],
                'first_name': r['first_name'],
                'email': r['email'],
                'next_step': next_step,
                'days_elapsed': days_elapsed,
            })
    return due


def mark_sequence_step_sent(client_id, step):
    """Record that drip step N was sent for this client."""
    conn = _get_conn()
    conn.execute(
        "UPDATE email_sequence_state SET last_step_sent = ? WHERE client_id = ?",
        (step, client_id),
    )
    conn.commit()
    conn.close()


def pause_sequence(client_id, paused=True):
    """Pause (or resume) the drip sequence — e.g. once a lead books or becomes a client."""
    conn = _get_conn()
    conn.execute(
        "UPDATE email_sequence_state SET paused = ? WHERE client_id = ?",
        (1 if paused else 0, client_id),
    )
    conn.commit()
    conn.close()


# Auto-initialize on import
_init_db()