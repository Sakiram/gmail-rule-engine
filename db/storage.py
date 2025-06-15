from db.connection import get_connection
from db.models import Email
from datetime import datetime, timezone
from typing import List, Optional


def save_email(email: Email):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute('''
        INSERT INTO emails (
            msg_id, thread_id, subject, sender, recipient, snippet,
            body, date_received, marked_as, msg_moved_to,
            created_at, updated_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, now(), now())
        ON CONFLICT (msg_id) DO NOTHING;
    ''', (
        email.msg_id, email.thread_id, email.subject, email.sender,
        email.recipient, email.snippet, email.body,
        email.date_received, email.marked_as, email.msg_moved_to
    ))

    conn.commit()
    cur.close()
    conn.close()


def get_all_emails() -> List[Email]:
    conn = get_connection()
    cur = conn.cursor()

    cur.execute('SELECT * FROM emails ORDER BY date_received DESC;')
    rows = cur.fetchall()

    cur.close()
    conn.close()

    return [row_to_email(row) for row in rows]


def get_email_by_id(email_id: str) -> Optional[Email]:
    conn = get_connection()
    cur = conn.cursor()

    cur.execute('SELECT * FROM emails WHERE id = %s;', (email_id,))
    row = cur.fetchone()

    cur.close()
    conn.close()

    return row_to_email(row) if row else None

def update_email_status(email_id, marked_as=None, msg_moved_to=None):
    conn = get_connection()
    cur = conn.cursor()
    fields = []
    values = []

    if marked_as:
        fields.append("marked_as = %s")
        values.append(marked_as)
    if msg_moved_to:
        fields.append("msg_moved_to = %s")
        values.append(msg_moved_to)

    # Always update updated_at
    fields.append("updated_at = %s")
    values.append(datetime.now(timezone.utc))

    if not fields:
        return

    values.append(email_id)

    update_query = f"""
        UPDATE emails
        SET {', '.join(fields)}
        WHERE id = %s
    """
    cur.execute(update_query, tuple(values))
    conn.commit()
    cur.close()
    conn.close()
# def update_email_actions(email_id: str, marked_as: Optional[str] = None, msg_moved_to: Optional[str] = None):
#     conn = get_connection()
#     cur = conn.cursor()

#     cur.execute('''
#         UPDATE emails
#         SET marked_as = %s,
#             msg_moved_to = %s,
#             updated_at = now()
#         WHERE id = %s;
#     ''', (marked_as, msg_moved_to, email_id))

#     conn.commit()
#     cur.close()
#     conn.close()


def row_to_email(row) -> Email:
    return Email(
        id=row[0],
        msg_id=row[1],
        thread_id=row[2],
        subject=row[3],
        sender=row[4],
        recipient=row[5],
        snippet=row[6],
        body=row[7],
        date_received=row[8],
        marked_as=row[9],
        msg_moved_to=row[10],
        created_at=row[11],
        updated_at=row[12]
    )
