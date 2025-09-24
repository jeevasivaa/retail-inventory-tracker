#!/usr/bin/env python3
import sqlite3
import sys
from pathlib import Path
from werkzeug.security import generate_password_hash

# Minimal, clean script: update seeded users' password_hash fields to
# Werkzeug's generate_password_hash output so Flask's check_password_hash
# will validate the intended plaintext passwords.

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
#!/usr/bin/env python3
import sqlite3
import sys
from pathlib import Path
from werkzeug.security import generate_password_hash

# Minimal, clean script: update seeded users' password_hash fields to
# Werkzeug's generate_password_hash output so Flask's check_password_hash
# will validate the intended plaintext passwords.

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
#!/usr/bin/env python3
import sqlite3
import sys
from pathlib import Path
from werkzeug.security import generate_password_hash

# Update seeded user password hashes to Werkzeug format so Flask's
# check_password_hash will validate the intended plaintext credentials.

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
        cur.execute('SELECT id FROM users WHERE username = ?', (username,))
        if cur.fetchone():
            cur.execute(
                'UPDATE users SET password_hash = ? WHERE username = ?',
                (generate_password_hash(plain), username)
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
#!/usr/bin/env python3
import sqlite3
import sys
from pathlib import Path
from werkzeug.security import generate_password_hash

# Clean, minimal script to update seeded user password hashes to Werkzeug format.
# This ensures the Flask app's check_password_hash will validate the intended
# plaintext credentials created by setup_database.py.

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
        cur.execute('SELECT id FROM users WHERE username = ?', (username,))
        if cur.fetchone():
            cur.execute('UPDATE users SET password_hash = ? WHERE username = ?',
                        (generate_password_hash(plain), username))
            updated.append(username)

    conn.commit()
    conn.close()

    if updated:
        print('Updated password hashes for: ' + ', '.join(updated))
    else:
        print('No matching users found to update.')


if __name__ == '__main__':
    main()
"""
Script to re-hash seeded user passwords in the SQLite database using Werkzeug
so the app's `check_password_hash` will validate them correctly.
"""
This will update the users created by `setup_database.py` (admin, manager, employee, john_doe, jane_smith)
with Werkzeug's `generate_password_hash` output for the known plaintext passwords.

Run this with the project's virtualenv python:
& "C:\Users\HP\Desktop\ajdbs hqwkyg\.venv-1\Scripts\python.exe" fix_user_passwords.py
"""

import sqlite3
from werkzeug.security import generate_password_hash

DB_PATH = 'database/inventory.db'
# Mapping of username -> plaintext password that was originally intended
PASSWORDS = {
    'admin': 'admin123',
    'jane_smith': 'password123'
}

"""fix_user_passwords.py

Update seeded users' password_hash fields to Werkzeug-compatible hashes so
the Flask login (check_password_hash) will validate the known plaintext
credentials.

Run from the project directory using the project's venv:
& "C:\Users\HP\Desktop\ajdbs hqwkyg\.venv-1\Scripts\python.exe" fix_user_passwords.py
"""

import sqlite3
from werkzeug.security import generate_password_hash
from pathlib import Path


DB_PATH = Path(__file__).resolve().parent / 'database' / 'inventory.db'

PASSWORDS = {
    'admin': 'admin123',
    'manager': 'manager123',
    'employee': 'employee123',
    'john_doe': 'password123',
    'jane_smith': 'password123'
}


def main():
    if not DB_PATH.exists():
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()

    updated = []
    for username, plain in PASSWORDS.items():
        cur.execute('SELECT id FROM users WHERE username = ?', (username,))
        if cur.fetchone():
            cur.execute('UPDATE users SET password_hash = ? WHERE username = ?',
                        (generate_password_hash(plain), username))
            updated.append(username)

    conn.commit()
    conn.close()

    if updated:
        print('Updated password hashes for: ' + ', '.join(updated))
    else:
        print('No matching users found to update.')


if __name__ == '__main__':
    main()
        if updated:

            print(f"Updated password hashes for: {', '.join(updated)}")
