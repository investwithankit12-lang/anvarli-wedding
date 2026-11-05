"""
seed_supabase_admin.py
Run this ONCE after setting up Supabase to create the admin user.

Usage:
  1. Copy .env.example to .env and fill in SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY
  2. pip install supabase bcrypt python-dotenv
  3. python seed_supabase_admin.py
"""

import os
import bcrypt

# Load .env if present
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from supabase import create_client

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("ERROR: Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in your .env file.")
    exit(1)

sb = create_client(SUPABASE_URL, SUPABASE_KEY)

USERNAME = "Anvarli12"
PASSWORD = "Anvarli12@"

hashed = bcrypt.hashpw(PASSWORD.encode(), bcrypt.gensalt()).decode()

result = sb.table("admin_users").upsert(
    {"username": USERNAME, "password_hash": hashed},
    on_conflict="username"
).execute()

print(f"[OK] Admin user '{USERNAME}' seeded in Supabase.")
print("     Password stored as bcrypt hash — never in plaintext.")
