#!/usr/bin/env python3
"""
Show what's actually in the database
"""
import sqlite3

conn = sqlite3.connect('moonlighter.db')
cursor = conn.cursor()

# Get first faculty member
cursor.execute("SELECT id, name, password_hash FROM faculty LIMIT 1")
row = cursor.fetchone()

if row:
    faculty_id, name, password_hash = row
    print(f"Sample faculty: {name} ({faculty_id})")
    print(f"Password hash: {password_hash[:50]}...")
    print(f"Hash length: {len(password_hash)}")
    print(f"Starts with: {password_hash[:10]}")
    
    if password_hash.startswith('$2b$'):
        print("\n✅ This is a bcrypt hash (CORRECT)")
    elif len(password_hash) == 64 and all(c in '0123456789abcdef' for c in password_hash):
        print("\n❌ This is a SHA256 hash (WRONG - needs fixing)")
    else:
        print("\n❓ Unknown hash format")
else:
    print("No faculty found")

conn.close()
