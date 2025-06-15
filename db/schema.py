from db.connection import get_connection


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute('''
        CREATE TABLE IF NOT EXISTS emails (
            id SERIAL PRIMARY KEY,
            msg_id TEXT UNIQUE,
            thread_id TEXT,
            subject TEXT,
            sender TEXT,
            recipient TEXT,
            snippet TEXT,
            body TEXT,
            date_received TIMESTAMP,
            marked_as TEXT,
            msg_moved_to TEXT,
            created_at TIMESTAMP DEFAULT now(),
            updated_at TIMESTAMP DEFAULT now()
        );
    ''')

    conn.commit()
    cur.close()
    conn.close()
