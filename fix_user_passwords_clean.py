#!/usr/bin/env python3
import sqlite3
import sys
from pathlib import Path
from werkzeug.security import generate_password_hash

DB = Path(__file__).resolve().parent / 'database' / 'inventory.db'

PASSWORDS = {
    'admin': 'admin123',
    'manager': 'manager123',
    'employee': 'employee123',
    'john_doe': 'password123',
    'jane_smith': 'password123'
}


def main():
    if not DB.exists():
        print(f"Database not found at {DB}")
        sys.exit(1)

    conn = sqlite3.connect(str(DB))
    cur = conn.cursor()

    updated = []
    for username, plain in PASSWORDS.items():
        cur.execute("SELECT id FROM users WHERE username = ?", (username,))
        if cur.fetchone():
            cur.execute(
                "UPDATE users SET password_hash = ? WHERE username = ?",
                (generate_password_hash(plain), username),
            )
            updated.append(username)

    conn.commit()
    conn.close()

    if updated:
        print('Updated password hashes for: ' + ', '.join(updated))
    else:
        print('No matching users found to update.')


if __name__ == '__main__':
    main()
