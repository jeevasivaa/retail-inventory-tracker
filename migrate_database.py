#!/usr/bin/env python3
"""
Database migration script to add reorder_level column to products table.
Run this script if you're getting operational errors related to missing reorder_level column.
"""

import sqlite3
import os

DATABASE_PATH = 'database/inventory.db'

def migrate_database():
    """Add reorder_level column to products table if it doesn't exist."""
    
    if not os.path.exists(DATABASE_PATH):
        print("Database not found. Please run the main application first to create it.")
        return
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    try:
        # Check if reorder_level column exists
        cursor.execute("PRAGMA table_info(products)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'reorder_level' not in columns:
            print("Adding reorder_level column to products table...")
            cursor.execute("ALTER TABLE products ADD COLUMN reorder_level INTEGER DEFAULT 10")
            conn.commit()
            print("✅ Successfully added reorder_level column!")
        else:
            print("✅ reorder_level column already exists in products table.")
        
        # Verify the column was added
        cursor.execute("PRAGMA table_info(products)")
        columns = [column[1] for column in cursor.fetchall()]
        print(f"Products table columns: {columns}")
        
    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    migrate_database()