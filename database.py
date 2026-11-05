"""
database.py — Database management and seed data for ANVARLI EVENT MANAGERS
Handles SQLite database connection, table initialization, bcrypt user seeding,
and full CRUD queries for Services, Gallery, Enquiries, and Admin Sessions.
"""

import sqlite3
import os
import time
import uuid
import bcrypt

DB_PATH = os.path.join(os.path.dirname(__file__), "wedding.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cur = conn.cursor()

    # 1. Admin Users
    cur.execute("""
    CREATE TABLE IF NOT EXISTS admin_users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """)

    # 2. Services
    cur.execute("""
    CREATE TABLE IF NOT EXISTS services (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT NOT NULL,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        image TEXT NOT NULL,
        needs_image INTEGER DEFAULT 0,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """)

    # 3. Gallery Items
    cur.execute("""
    CREATE TABLE IF NOT EXISTS gallery_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        type TEXT NOT NULL CHECK(type IN ('photo', 'video')),
        url TEXT NOT NULL,
        title TEXT NOT NULL,
        category TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """)

    # 4. Enquiries
    cur.execute("""
    CREATE TABLE IF NOT EXISTS enquiries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        phone TEXT NOT NULL,
        address TEXT NOT NULL,
        event_type TEXT,
        preferred_date TEXT,
        message TEXT,
        status TEXT DEFAULT 'New',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """)

    # 5. Sessions
    cur.execute("""
    CREATE TABLE IF NOT EXISTS sessions (
        token TEXT PRIMARY KEY,
        username TEXT NOT NULL,
        created_at REAL NOT NULL,
        expires_at REAL NOT NULL
    )
    """)

    # 6. Login Attempts (for rate limiting / lockout)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS login_attempts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ip TEXT NOT NULL,
        attempt_time REAL NOT NULL,
        success INTEGER NOT NULL
    )
    """)

    conn.commit()

    # Seed Admin User if not exists
    cur.execute("SELECT id FROM admin_users WHERE username = ?", ("Anvarli12",))
    if not cur.fetchone():
        # Store password hashed using bcrypt — never in plaintext!
        raw_pw = b"Anvarli12@"
        hashed = bcrypt.hashpw(raw_pw, bcrypt.gensalt()).decode("utf-8")
        cur.execute(
            "INSERT INTO admin_users (username, password_hash, created_at) VALUES (?, ?, datetime('now'))",
            ("Anvarli12", hashed)
        )
        conn.commit()
        print("[DB] Admin user 'Anvarli12' seeded with bcrypt hash.")

    # Seed 17 Service Categories if table is empty
    cur.execute("SELECT COUNT(*) AS cnt FROM services")
    if cur.fetchone()["cnt"] == 0:
        seed_services = [
            (
                "Wedding Planning & Management",
                "Full Bengali Wedding Styling & Coordination",
                "From the holy Chhadnatala mandap to Borjatri reception and the tearful Bidaai, complete end-to-end ritual curation and aesthetic styling.",
                "assets/gallery/mandap-decor.svg",
                0
            ),
            (
                "Engagement & Ring Ceremony",
                "Aashirbaad & Ring Exchange Styling",
                "Auspicious Aashirbaad settings with fragrant rajnigandha florals, custom ring presentation platters, and intimate family coordination.",
                "assets/gallery/sindoor-daan.svg",
                0
            ),
            (
                "Birthday Parties",
                "Milestone & Themed Birthday Celebrations",
                "From magical first birthdays to royal 50th and 60th milestone galas, complete themed props, backdrops, and entertainment.",
                "assets/gallery/placeholder-birthday.svg",
                1
            ),
            (
                "Bachelor Parties",
                "Pre-Wedding Groomsmen Soirees",
                "Unforgettable nights for the groom and his circle — high-energy sound, lounge styling, signature mocktails, and ambient lighting.",
                "assets/gallery/placeholder-bachelor.svg",
                1
            ),
            (
                "Bachelorette Parties",
                "Bridal Shower & Hen Night Gatherings",
                "Elegant pastel canopies, photo booths, personalized floral favors, and custom games for the bride-to-be and her bridesmaids.",
                "assets/gallery/placeholder-bachelorette.svg",
                1
            ),
            (
                "Anniversary & Couple Events",
                "Silver, Golden & Intimate Milestone Galas",
                "Romantic candlelit banquets, violinists, nostalgic photo galleries, and warm Bengali hospitality to toast years of shared love.",
                "assets/gallery/anniversary-milestone.svg",
                0
            ),
            (
                "Small House Parties",
                "Boutique Terrace & Living Room Gatherings",
                "Compact, high-taste floral styling, low seating bolsters, lighting accents, and seamless housekeeping for up to 50 guests.",
                "assets/gallery/placeholder-houseparty.svg",
                1
            ),
            (
                "Private & Family Events",
                "Gaye Holud, Annaprashan & Upanayan",
                "Traditional rituals with brass urlis, turmeric platters, painted kulo winnowing fans, and Vedic ceremonial precision.",
                "assets/gallery/gaye-holud.svg",
                0
            ),
            (
                "Catering & Food Management",
                "Authentic Bengali Feasts & Global Menus",
                "From traditional Bhetki Paturi, Chingri Malai Curry, and Kosha Mangsho to multi-cuisine live counters with five-star service standards.",
                "assets/gallery/placeholder-catering.svg",
                1
            ),
            (
                "Decoration & Theme Setup",
                "Regal Mandaps, Alpona Art & Floral Canopies",
                "Bespoke structures crafted with fresh marigolds, imported orchids, hand-painted Alpona motifs, and heritage Bengali fabrics.",
                "assets/gallery/mandap-decor.svg",
                0
            ),
            (
                "DJ, Music & Entertainment",
                "High-Energy Dancefloors & Sangeet Sets",
                "Top Kolkata DJs, live percussionists, seamless sound mixing, and customized tracks tailored to traditional and modern celebrations.",
                "assets/gallery/mehendi-night.svg",
                0
            ),
            (
                "Photography & Videography",
                "Cinematic 4K Wedding Films & Heritage Portraits",
                "Capturing subtle glances, sacred mantras, and tearful smiles with master documentary and candid wedding cinematographers.",
                "assets/frames/garland-exchange/ezgif-frame-040.jpg",
                0
            ),
            (
                "Sound, Lighting & LED Screens",
                "Concert-Grade Acoustic Rigs & Architectural Illumination",
                "Warm fairy-light canopies, architectural uplighting on heritage facades, intelligent moving heads, and ultra-HD LED video walls.",
                "assets/gallery/royal-reception.svg",
                0
            ),
            (
                "DJ/Anchor/Emcee & Live Performers",
                "Bilingual Emcees & Bengali Folk Performers",
                "Charismatic hosts fluent in Bengali, Hindi, and English, coupled with traditional Baul musicians, Shehnai maestros, and Dhakis.",
                "assets/gallery/placeholder-emcee.svg",
                1
            ),
            (
                "Artist & Celebrity Booking",
                "Tollywood Stars, Playback Singers & Bands",
                "Direct liaison and backstage management for celebrated singers, musicians, and performers across Bengal and Mumbai.",
                "assets/gallery/placeholder-artist.svg",
                1
            ),
            (
                "Guest Transportation & Event Logistics",
                "Luxury Fleet, Airport Pickups & Valet Management",
                "Coordinated transfers across Kolkata and West Bengal districts with air-conditioned luxury coaches, private sedans, and dedicated pilots.",
                "assets/gallery/placeholder-logistics.svg",
                1
            ),
            (
                "Complete Event Planning & Vendor Management",
                "Turnkey Production, Budgeting & Day-Of Orchestration",
                "Single-point accountability from the first moodboard consultation to final invoice reconciliation, letting your family simply celebrate.",
                "assets/frames/garland-exchange/ezgif-frame-001.jpg",
                0
            )
        ]

        now = time.strftime("%Y-%m-%d %H:%M:%S")
        for cat, title, desc, img, needs_img in seed_services:
            cur.execute("""
            INSERT INTO services (category, title, description, image, needs_image, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (cat, title, desc, img, needs_img, now, now))
        conn.commit()
        print(f"[DB] Seeded {len(seed_services)} service categories.")

    # Seed Gallery Items if empty
    cur.execute("SELECT COUNT(*) AS cnt FROM gallery_items")
    if cur.fetchone()["cnt"] == 0:
        seed_gallery = [
            ("photo", "assets/gallery/mandap-decor.svg", "Traditional Mandap Styling", "Wedding"),
            ("photo", "assets/gallery/gaye-holud.svg", "Gaye Holud Floral Pavilion", "Haldi"),
            ("photo", "assets/gallery/sindoor-daan.svg", "Saat Paake Bandha & Sindoor Daan", "Wedding"),
            ("photo", "assets/gallery/mehendi-night.svg", "Colour-Led Mehendi Lounge", "Mehendi"),
            ("photo", "assets/gallery/royal-reception.svg", "Royal Reception Decor & Stage", "Reception"),
            ("photo", "assets/gallery/anniversary-milestone.svg", "Intimate Milestone Celebration", "Anniversary"),
            ("video", "assets/frames/garland-exchange/ezgif-frame-001.jpg", "Cinematic Garland Exchange Ceremony", "Wedding Film")
        ]
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        for g_type, url, title, cat in seed_gallery:
            cur.execute("""
            INSERT INTO gallery_items (type, url, title, category, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (g_type, url, title, cat, now, now))
        conn.commit()
        print(f"[DB] Seeded {len(seed_gallery)} gallery items.")

    conn.close()

# -----------------------------------------------------------------------------
# Authentication & Rate Limiting
# -----------------------------------------------------------------------------
def check_rate_limit(ip, max_attempts=5, window_seconds=900):
    """
    Check if IP has exceeded failed login attempts within window_seconds.
    Returns (allowed: bool, remaining_lockout_seconds: int).
    """
    conn = get_connection()
    cur = conn.cursor()
    cutoff = time.time() - window_seconds
    cur.execute("""
        SELECT COUNT(*) AS fails, MAX(attempt_time) as last_attempt
        FROM login_attempts
        WHERE ip = ? AND attempt_time > ? AND success = 0
    """, (ip, cutoff))
    row = cur.fetchone()
    conn.close()

    fails = row["fails"] or 0
    if fails >= max_attempts:
        last_attempt = row["last_attempt"] or time.time()
        remaining = int(window_seconds - (time.time() - last_attempt))
        return False, max(1, remaining)
    return True, 0

def record_login_attempt(ip, success):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO login_attempts (ip, attempt_time, success) VALUES (?, ?, ?)",
        (ip, time.time(), 1 if success else 0)
    )
    if success:
        # Clear previous failed attempts on success
        cur.execute("DELETE FROM login_attempts WHERE ip = ? AND success = 0", (ip,))
    conn.commit()
    conn.close()

def verify_admin_login(username, password, ip):
    allowed, wait_seconds = check_rate_limit(ip)
    if not allowed:
        return None, f"Too many failed login attempts. Locked out for {wait_seconds // 60 + 1} more minutes."

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT password_hash FROM admin_users WHERE username = ?", (username,))
    row = cur.fetchone()
    conn.close()

    if not row:
        record_login_attempt(ip, False)
        return None, "Invalid username or password."

    pwd_hash = row["password_hash"].encode("utf-8")
    if bcrypt.checkpw(password.encode("utf-8"), pwd_hash):
        record_login_attempt(ip, True)
        # Create session token
        token = str(uuid.uuid4()) + str(uuid.uuid4())
        created_at = time.time()
        expires_at = created_at + (86400 * 7)  # 7 days valid
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO sessions (token, username, created_at, expires_at) VALUES (?, ?, ?, ?)",
            (token, username, created_at, expires_at)
        )
        conn.commit()
        conn.close()
        return token, None
    else:
        record_login_attempt(ip, False)
        return None, "Invalid username or password."

def validate_session(token):
    if not token:
        return None
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT username, expires_at FROM sessions WHERE token = ?",
        (token,)
    )
    row = cur.fetchone()
    conn.close()

    if row and row["expires_at"] > time.time():
        return row["username"]
    return None

def destroy_session(token):
    if not token:
        return
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM sessions WHERE token = ?", (token,))
    conn.commit()
    conn.close()

# -----------------------------------------------------------------------------
# Services CRUD
# -----------------------------------------------------------------------------
def get_all_services():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM services ORDER BY id ASC")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows

def add_service(category, title, description, image, needs_image=0):
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
    INSERT INTO services (category, title, description, image, needs_image, created_at, updated_at)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (category, title, description, image, 1 if needs_image else 0, now, now))
    new_id = cur.lastrowid
    conn.commit()
    conn.close()
    return new_id

def update_service(service_id, category, title, description, image=None, needs_image=None):
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    conn = get_connection()
    cur = conn.cursor()

    if image is not None and needs_image is not None:
        cur.execute("""
        UPDATE services
        SET category = ?, title = ?, description = ?, image = ?, needs_image = ?, updated_at = ?
        WHERE id = ?
        """, (category, title, description, image, 1 if needs_image else 0, now, service_id))
    elif image is not None:
        cur.execute("""
        UPDATE services
        SET category = ?, title = ?, description = ?, image = ?, updated_at = ?
        WHERE id = ?
        """, (category, title, description, image, now, service_id))
    else:
        cur.execute("""
        UPDATE services
        SET category = ?, title = ?, description = ?, updated_at = ?
        WHERE id = ?
        """, (category, title, description, now, service_id))

    conn.commit()
    conn.close()

def update_service_image(service_id, image_path, needs_image=0):
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
    UPDATE services
    SET image = ?, needs_image = ?, updated_at = ?
    WHERE id = ?
    """, (image_path, 1 if needs_image else 0, now, service_id))
    conn.commit()
    conn.close()

def delete_service(service_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM services WHERE id = ?", (service_id,))
    conn.commit()
    conn.close()

# -----------------------------------------------------------------------------
# Gallery Items CRUD
# -----------------------------------------------------------------------------
def get_all_gallery():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM gallery_items ORDER BY id ASC")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows

def add_gallery_item(item_type, url, title, category):
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
    INSERT INTO gallery_items (type, url, title, category, created_at, updated_at)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (item_type, url, title, category, now, now))
    new_id = cur.lastrowid
    conn.commit()
    conn.close()
    return new_id

def update_gallery_item(item_id, item_type, url, title, category):
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
    UPDATE gallery_items
    SET type = ?, url = ?, title = ?, category = ?, updated_at = ?
    WHERE id = ?
    """, (item_type, url, title, category, now, item_id))
    conn.commit()
    conn.close()

def delete_gallery_item(item_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM gallery_items WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()

# -----------------------------------------------------------------------------
# Enquiries CRUD
# -----------------------------------------------------------------------------
def save_enquiry(name, phone, address, event_type, preferred_date, message):
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
    INSERT INTO enquiries (name, phone, address, event_type, preferred_date, message, status, created_at, updated_at)
    VALUES (?, ?, ?, ?, ?, ?, 'New', ?, ?)
    """, (name, phone, address, event_type, preferred_date, message, now, now))
    enquiry_id = cur.lastrowid
    conn.commit()
    conn.close()
    return enquiry_id

def get_enquiries(search=None, status=None):
    conn = get_connection()
    cur = conn.cursor()
    query = "SELECT * FROM enquiries WHERE 1=1"
    params = []

    if status and status != "All":
        query += " AND status = ?"
        params.append(status)

    if search:
        query += " AND (name LIKE ? OR phone LIKE ? OR address LIKE ? OR message LIKE ? OR event_type LIKE ?)"
        term = f"%{search}%"
        params.extend([term, term, term, term, term])

    query += " ORDER BY id DESC"
    cur.execute(query, params)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows

def update_enquiry_status(enquiry_id, status):
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
    UPDATE enquiries
    SET status = ?, updated_at = ?
    WHERE id = ?
    """, (status, now, enquiry_id))
    conn.commit()
    conn.close()

def delete_enquiry(enquiry_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM enquiries WHERE id = ?", (enquiry_id,))
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("[DB] Initialized database and verified seeds.")
