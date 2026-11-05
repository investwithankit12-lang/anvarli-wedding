-- ============================================================
-- ANVARLI EVENT MANAGERS — Supabase PostgreSQL Schema
-- Run this in: Supabase Dashboard → SQL Editor → New Query
-- ============================================================

-- 1. Admin Users
CREATE TABLE IF NOT EXISTS admin_users (
  id            SERIAL PRIMARY KEY,
  username      TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  created_at    TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Services
CREATE TABLE IF NOT EXISTS services (
  id          SERIAL PRIMARY KEY,
  category    TEXT NOT NULL,
  title       TEXT NOT NULL,
  description TEXT NOT NULL,
  image       TEXT NOT NULL DEFAULT '',
  needs_image INTEGER NOT NULL DEFAULT 0,
  created_at  TIMESTAMPTZ DEFAULT NOW(),
  updated_at  TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Gallery Items
CREATE TABLE IF NOT EXISTS gallery_items (
  id         SERIAL PRIMARY KEY,
  type       TEXT NOT NULL CHECK (type IN ('photo', 'video')),
  url        TEXT NOT NULL,
  title      TEXT NOT NULL,
  category   TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. Enquiries
CREATE TABLE IF NOT EXISTS enquiries (
  id             SERIAL PRIMARY KEY,
  name           TEXT NOT NULL,
  phone          TEXT NOT NULL,
  address        TEXT NOT NULL,
  event_type     TEXT,
  preferred_date TEXT,
  message        TEXT,
  status         TEXT NOT NULL DEFAULT 'New',
  created_at     TIMESTAMPTZ DEFAULT NOW(),
  updated_at     TIMESTAMPTZ DEFAULT NOW()
);

-- 5. Sessions (custom auth)
CREATE TABLE IF NOT EXISTS sessions (
  token      TEXT PRIMARY KEY,
  username   TEXT NOT NULL,
  created_at FLOAT NOT NULL,
  expires_at FLOAT NOT NULL
);

-- 6. Login Attempts (rate limiting)
CREATE TABLE IF NOT EXISTS login_attempts (
  id           SERIAL PRIMARY KEY,
  ip           TEXT NOT NULL,
  attempt_time FLOAT NOT NULL,
  success      INTEGER NOT NULL DEFAULT 0
);

-- ============================================================
-- Disable Row-Level Security for all tables
-- (The service role key used server-side bypasses RLS anyway,
--  but disabling is cleaner for a custom-auth setup)
-- ============================================================
ALTER TABLE admin_users   DISABLE ROW LEVEL SECURITY;
ALTER TABLE services      DISABLE ROW LEVEL SECURITY;
ALTER TABLE gallery_items DISABLE ROW LEVEL SECURITY;
ALTER TABLE enquiries     DISABLE ROW LEVEL SECURITY;
ALTER TABLE sessions      DISABLE ROW LEVEL SECURITY;
ALTER TABLE login_attempts DISABLE ROW LEVEL SECURITY;

-- ============================================================
-- Seed: 17 service categories
-- (Run after bcrypt-hashing the admin password via seed_admin.py)
-- ============================================================
INSERT INTO services (category, title, description, image, needs_image) VALUES
('Wedding Planning & Management',          'Full Bengali Wedding Styling & Coordination',          'From the holy Chhadnatala mandap to Borjatri reception and the tearful Bidaai, complete end-to-end ritual curation and aesthetic styling.',                 'assets/images/services/wedding-planning.jpg',   0),
('Engagement & Ring Ceremony',             'Aashirbaad & Ring Exchange Styling',                   'Auspicious Aashirbaad settings with fragrant rajnigandha florals, custom ring presentation platters, and intimate family coordination.',                  'assets/images/services/engagement.jpg',          0),
('Birthday Parties',                       'Milestone & Themed Birthday Celebrations',             'From magical first birthdays to royal 50th and 60th milestone galas, complete themed props, backdrops, and entertainment.',                               'assets/images/services/birthday.jpg',            0),
('Bachelor Parties',                       'Pre-Wedding Groomsmen Soirees',                        'Unforgettable nights for the groom and his circle — high-energy sound, lounge styling, signature mocktails, and ambient lighting.',                       'assets/images/services/bachelor.jpg',            0),
('Bachelorette Parties',                   'Bridal Shower & Hen Night Gatherings',                 'Elegant pastel canopies, photo booths, personalized floral favors, and custom games for the bride-to-be and her bridesmaids.',                            'assets/images/services/bachelorette.jpg',         0),
('Anniversary & Couple Events',            'Silver, Golden & Intimate Milestone Galas',            'Romantic candlelit banquets, violinists, nostalgic photo galleries, and warm Bengali hospitality to toast years of shared love.',                          'assets/images/services/anniversary.jpg',         0),
('Small House Parties',                    'Boutique Terrace & Living Room Gatherings',             'Compact, high-taste floral styling, low seating bolsters, lighting accents, and seamless housekeeping for up to 50 guests.',                              'assets/images/services/house-parties.jpg',       0),
('Private & Family Events',                'Gaye Holud, Annaprashan & Upanayan',                   'Traditional rituals with brass urlis, turmeric platters, painted kulo winnowing fans, and Vedic ceremonial precision.',                                  'assets/images/services/family-events.jpg',       0),
('Catering & Food Management',             'Authentic Bengali Feasts & Global Menus',              'From traditional Bhetki Paturi, Chingri Malai Curry, and Kosha Mangsho to multi-cuisine live counters with five-star service standards.',                 'assets/images/services/catering.jpg',            0),
('Decoration & Theme Setup',               'Regal Mandaps, Alpona Art & Floral Canopies',          'Bespoke structures crafted with fresh marigolds, imported orchids, hand-painted Alpona motifs, and heritage Bengali fabrics.',                            'assets/images/services/decoration.jpg',          0),
('DJ, Music & Entertainment',              'High-Energy Dancefloors & Sangeet Sets',               'Top Kolkata DJs, live percussionists, seamless sound mixing, and customized tracks tailored to traditional and modern celebrations.',                       'assets/images/services/dj-music.jpg',            0),
('Photography & Videography',              'Cinematic 4K Wedding Films & Heritage Portraits',       'Capturing subtle glances, sacred mantras, and tearful smiles with master documentary and candid wedding cinematographers.',                               'assets/images/services/photography.jpg',         0),
('Sound, Lighting & LED Screens',          'Concert-Grade Acoustic Rigs & Architectural Illumination', 'Warm fairy-light canopies, architectural uplighting on heritage facades, intelligent moving heads, and ultra-HD LED video walls.',                    'assets/images/services/sound-lighting.jpg',      0),
('DJ/Anchor/Emcee & Live Performers',      'Bilingual Emcees & Bengali Folk Performers',           'Charismatic hosts fluent in Bengali, Hindi, and English, coupled with traditional Baul musicians, Shehnai maestros, and Dhakis.',                        'assets/images/services/emcee.jpg',               0),
('Artist & Celebrity Booking',             'Tollywood Stars, Playback Singers & Bands',            'Direct liaison and backstage management for celebrated singers, musicians, and performers across Bengal and Mumbai.',                                      'assets/images/services/artist-celebrity.jpg',    0),
('Guest Transportation & Event Logistics', 'Luxury Fleet, Airport Pickups & Valet Management',    'Coordinated transfers across Kolkata and West Bengal districts with air-conditioned luxury coaches, private sedans, and dedicated pilots.',               'assets/images/services/logistics.jpg',           0),
('Complete Event Planning & Vendor Management', 'Turnkey Production, Budgeting & Day-Of Orchestration', 'Single-point accountability from the first moodboard consultation to final invoice reconciliation, letting your family simply celebrate.',          'assets/images/services/complete-planning.jpg',   0)
ON CONFLICT DO NOTHING;

-- ============================================================
-- Supabase Storage
-- Run separately in Dashboard → Storage → Create Bucket:
--   Bucket name: uploads
--   Public: YES (toggle on)
-- ============================================================
