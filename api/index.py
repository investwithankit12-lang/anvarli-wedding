"""
api/index.py — Vercel Serverless Handler for ANVARLI EVENT MANAGERS
Uses Supabase (PostgreSQL + Storage) instead of local SQLite.
Handles all /api/* routes including admin CRUD, file uploads, and enquiries.

Environment variables required (set in Vercel Dashboard → Settings → Environment Variables):
  SUPABASE_URL               — e.g. https://xxxx.supabase.co
  SUPABASE_SERVICE_ROLE_KEY  — service role secret key (server-side only, never expose)
  SUPABASE_STORAGE_BUCKET    — storage bucket name, default: "uploads"
"""

from http.server import BaseHTTPRequestHandler
import json
import os
import urllib.parse
import time
import uuid
import base64
import io
import csv
import bcrypt

# ---------------------------------------------------------------------------
# Supabase client (lazy-initialised so cold-start only pays once)
# ---------------------------------------------------------------------------
_sb = None

def get_supabase():
    global _sb
    if _sb is None:
        url = os.environ.get("SUPABASE_URL", "")
        key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
        if not url or not key:
            raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set.")
        from supabase import create_client
        _sb = create_client(url, key)
    return _sb

BUCKET = os.environ.get("SUPABASE_STORAGE_BUCKET", "uploads")
MAX_ATTEMPTS = 5
WINDOW_SECS  = 900   # 15 minutes lockout

# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------
def check_rate_limit(ip):
    sb = get_supabase()
    cutoff = time.time() - WINDOW_SECS
    res = sb.table("login_attempts") \
            .select("id, attempt_time") \
            .eq("ip", ip).eq("success", 0) \
            .gt("attempt_time", cutoff) \
            .execute()
    fails = len(res.data)
    if fails >= MAX_ATTEMPTS:
        last = max(r["attempt_time"] for r in res.data)
        remaining = int(WINDOW_SECS - (time.time() - last))
        return False, max(1, remaining)
    return True, 0

def record_attempt(ip, success):
    sb = get_supabase()
    sb.table("login_attempts").insert(
        {"ip": ip, "attempt_time": time.time(), "success": 1 if success else 0}
    ).execute()
    if success:
        sb.table("login_attempts").delete().eq("ip", ip).eq("success", 0).execute()

def verify_login(username, password, ip):
    allowed, wait = check_rate_limit(ip)
    if not allowed:
        mins = wait // 60 + 1
        return None, f"Too many failed login attempts. Locked out for {mins} more minutes."
    sb = get_supabase()
    res = sb.table("admin_users").select("password_hash").eq("username", username).execute()
    if not res.data:
        record_attempt(ip, False)
        return None, "Invalid username or password."
    ph = res.data[0]["password_hash"].encode()
    if bcrypt.checkpw(password.encode(), ph):
        record_attempt(ip, True)
        token = uuid.uuid4().hex + uuid.uuid4().hex
        now = time.time()
        sb.table("sessions").insert({
            "token": token, "username": username,
            "created_at": now, "expires_at": now + 86400 * 7
        }).execute()
        return token, None
    record_attempt(ip, False)
    return None, "Invalid username or password."

def validate_session(token):
    if not token:
        return None
    sb = get_supabase()
    res = sb.table("sessions").select("username, expires_at").eq("token", token).execute()
    if res.data and res.data[0]["expires_at"] > time.time():
        return res.data[0]["username"]
    return None

def destroy_session(token):
    if not token:
        return
    get_supabase().table("sessions").delete().eq("token", token).execute()

# ---------------------------------------------------------------------------
# File upload helper (Supabase Storage)
# ---------------------------------------------------------------------------
def upload_to_storage(file_bytes: bytes, filename: str, content_type: str) -> str:
    sb = get_supabase()
    unique_name = f"{int(time.time())}_{uuid.uuid4().hex[:8]}_{filename}"
    sb.storage.from_(BUCKET).upload(
        path=unique_name,
        file=file_bytes,
        file_options={"content-type": content_type, "upsert": "true"}
    )
    url = sb.storage.from_(BUCKET).get_public_url(unique_name)
    return url

# ---------------------------------------------------------------------------
# Vercel handler class
# ---------------------------------------------------------------------------
class handler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        pass  # silence access log in serverless

    # ---- Utilities ---------------------------------------------------------
    def get_ip(self):
        fwd = self.headers.get("X-Forwarded-For")
        return fwd.split(",")[0].strip() if fwd else "127.0.0.1"

    def get_token(self):
        auth = self.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            return auth[7:].strip()
        cookie = self.headers.get("Cookie", "")
        for part in cookie.split(";"):
            part = part.strip()
            if part.startswith("session_token="):
                return part.split("=", 1)[1].strip()
        return None

    def require_auth(self):
        return validate_session(self.get_token())

    def read_json(self):
        try:
            n = int(self.headers.get("Content-Length", 0))
            if n <= 0:
                return {}
            return json.loads(self.rfile.read(n).decode("utf-8"))
        except Exception:
            return None

    def send_json(self, data, status=200, cookie=None):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        if cookie:
            self.send_header("Set-Cookie", cookie)
        self.end_headers()
        self.wfile.write(body)

    def err(self, msg, status=400):
        self.send_json({"error": msg, "success": False}, status)

    # ---- OPTIONS (CORS pre-flight) -----------------------------------------
    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    # ---- GET ---------------------------------------------------------------
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        qs = urllib.parse.parse_qs(parsed.query)
        sb = get_supabase()

        # Public: services list
        if path == "/api/services":
            rows = sb.table("services").select("*").order("id").execute().data
            self.send_json({"success": True, "services": rows})
            return

        # Public: gallery list
        if path == "/api/gallery":
            rows = sb.table("gallery_items").select("*").order("id").execute().data
            self.send_json({"success": True, "gallery": rows})
            return

        # Admin: check session
        if path == "/api/admin/me":
            username = self.require_auth()
            if not username:
                return self.err("Unauthorized", 401)
            self.send_json({"success": True, "username": username})
            return

        # Admin: list services
        if path == "/api/admin/services":
            if not self.require_auth():
                return self.err("Unauthorized", 401)
            rows = sb.table("services").select("*").order("id").execute().data
            self.send_json({"success": True, "services": rows})
            return

        # Admin: list gallery
        if path == "/api/admin/gallery":
            if not self.require_auth():
                return self.err("Unauthorized", 401)
            rows = sb.table("gallery_items").select("*").order("id").execute().data
            self.send_json({"success": True, "gallery": rows})
            return

        # Admin: enquiries (with optional search/status filter)
        if path == "/api/admin/enquiries":
            if not self.require_auth():
                return self.err("Unauthorized", 401)
            q = sb.table("enquiries").select("*")
            status_f = qs.get("status", [None])[0]
            search_f = qs.get("search", [None])[0]
            if status_f and status_f != "All":
                q = q.eq("status", status_f)
            rows = q.order("id", desc=True).execute().data
            if search_f:
                s = search_f.lower()
                rows = [r for r in rows if s in (r.get("name","") + r.get("phone","") +
                        r.get("address","") + r.get("message","") + r.get("event_type","")).lower()]
            self.send_json({"success": True, "enquiries": rows})
            return

        # Admin: export enquiries as CSV
        if path == "/api/admin/enquiries/export":
            if not self.require_auth():
                return self.err("Unauthorized", 401)
            rows = sb.table("enquiries").select("*").order("id", desc=True).execute().data
            out = io.StringIO()
            w = csv.writer(out)
            w.writerow(["ID","Name","Phone","Address","Event Type","Preferred Date","Message","Status","Submitted At"])
            for r in rows:
                w.writerow([r.get("id"), r.get("name"), r.get("phone"), r.get("address"),
                             r.get("event_type",""), r.get("preferred_date",""),
                             r.get("message",""), r.get("status"), r.get("created_at")])
            csv_bytes = out.getvalue().encode("utf-8-sig")
            self.send_response(200)
            self.send_header("Content-Type", "text/csv; charset=utf-8")
            self.send_header("Content-Disposition", "attachment; filename=anvarli_enquiries.csv")
            self.send_header("Content-Length", str(len(csv_bytes)))
            self.end_headers()
            self.wfile.write(csv_bytes)
            return

        self.err("Not found", 404)

    # ---- POST --------------------------------------------------------------
    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        sb = get_supabase()

        # Admin login
        if path == "/api/admin/login":
            body = self.read_json()
            if not body:
                return self.err("Invalid request body.")
            username = str(body.get("username", "")).strip()
            password = str(body.get("password", "")).strip()
            if not username or not password:
                return self.err("Username and password are required.", 400)
            token, error = verify_login(username, password, self.get_ip())
            if error:
                status = 429 if "Locked" in error else 401
                return self.send_json({"success": False, "error": error}, status)
            cookie = f"session_token={token}; Path=/; HttpOnly; SameSite=Lax; Max-Age=604800"
            return self.send_json({"success": True, "token": token}, cookie=cookie)

        # Admin logout
        if path == "/api/admin/logout":
            destroy_session(self.get_token())
            cookie = "session_token=; Path=/; HttpOnly; Max-Age=0"
            return self.send_json({"success": True}, cookie=cookie)

        # Public enquiry submission
        if path == "/api/enquiries":
            body = self.read_json()
            if not body:
                return self.err("Invalid request body.")
            name  = str(body.get("name", "")).strip()
            phone = str(body.get("phone", "")).strip()
            addr  = str(body.get("address", "")).strip()
            if not name or not phone or not addr:
                return self.err("Name, phone, and address are required.", 400)
            row = sb.table("enquiries").insert({
                "name": name, "phone": phone, "address": addr,
                "event_type": str(body.get("eventType", "")),
                "preferred_date": str(body.get("preferredDate", "") or ""),
                "message": str(body.get("message", "")),
                "status": "New"
            }).execute()
            new_id = row.data[0]["id"] if row.data else None
            return self.send_json({"success": True, "id": new_id}, 201)

        # Admin: add service
        if path == "/api/admin/services":
            if not self.require_auth():
                return self.err("Unauthorized", 401)
            body = self.read_json()
            if not body:
                return self.err("Invalid body.")
            row = sb.table("services").insert({
                "category":    str(body.get("category", "")).strip(),
                "title":       str(body.get("title", "")).strip(),
                "description": str(body.get("description", "")).strip(),
                "image":       str(body.get("image", "")).strip(),
                "needs_image": 1 if body.get("needs_image") else 0
            }).execute()
            new_id = row.data[0]["id"] if row.data else None
            return self.send_json({"success": True, "id": new_id, "message": "Service added."})

        # Admin: upload service image
        if path.startswith("/api/admin/services/") and path.endswith("/image"):
            if not self.require_auth():
                return self.err("Unauthorized", 401)
            parts = path.strip("/").split("/")
            svc_id = int(parts[3])
            body = self.read_json()
            if not body or "image_data" not in body:
                return self.err("Missing image_data.", 400)
            raw = body["image_data"]
            if "," in raw:
                raw = raw.split(",", 1)[1]
            file_bytes = base64.b64decode(raw)
            fn = str(body.get("filename", "service.jpg"))
            ext = os.path.splitext(fn)[1].lower()
            if ext not in [".jpg", ".jpeg", ".png", ".webp"]:
                return self.err("Invalid format. Use JPG, PNG, or WEBP.", 400)
            if len(file_bytes) > 25 * 1024 * 1024:
                return self.err("File exceeds 25 MB limit.", 400)
            mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg",
                    "png": "image/png", "webp": "image/webp"}.get(ext.lstrip("."), "image/jpeg")
            pub_url = upload_to_storage(file_bytes, f"service_{svc_id}{ext}", mime)
            sb.table("services").update({"image": pub_url, "needs_image": 0}).eq("id", svc_id).execute()
            return self.send_json({"success": True, "url": pub_url})

        # Admin: add gallery item
        if path == "/api/admin/gallery":
            if not self.require_auth():
                return self.err("Unauthorized", 401)
            body = self.read_json()
            if not body:
                return self.err("Invalid body.")
            g_type = str(body.get("type", "photo"))
            if g_type not in ("photo", "video"):
                return self.err("type must be 'photo' or 'video'.")
            row = sb.table("gallery_items").insert({
                "type":     g_type,
                "url":      str(body.get("url", "")).strip(),
                "title":    str(body.get("title", "")).strip(),
                "category": str(body.get("category", "")).strip()
            }).execute()
            new_id = row.data[0]["id"] if row.data else None
            return self.send_json({"success": True, "id": new_id, "message": "Gallery item added."})

        # Admin: upload gallery file
        if path == "/api/admin/gallery/upload":
            if not self.require_auth():
                return self.err("Unauthorized", 401)
            body = self.read_json()
            if not body or "file_data" not in body:
                return self.err("Missing file_data.", 400)
            raw = body["file_data"]
            if "," in raw:
                raw = raw.split(",", 1)[1]
            fn = str(body.get("filename", "gallery.jpg"))
            ext = os.path.splitext(fn)[1].lower()
            if ext not in [".jpg", ".jpeg", ".png", ".webp", ".mp4"]:
                return self.err("Invalid format. Allowed: JPG, PNG, WEBP, MP4.", 400)
            file_bytes = base64.b64decode(raw)
            if len(file_bytes) > 25 * 1024 * 1024:
                return self.err("File exceeds 25 MB limit.", 400)
            mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg",
                    "png": "image/png", "webp": "image/webp",
                    "mp4": "video/mp4"}.get(ext.lstrip("."), "image/jpeg")
            pub_url = upload_to_storage(file_bytes, f"gallery{ext}", mime)
            return self.send_json({"success": True, "url": pub_url})

        self.err("Not found", 404)

    # ---- PUT ---------------------------------------------------------------
    def do_PUT(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        if not self.require_auth():
            return self.err("Unauthorized", 401)
        sb = get_supabase()

        # Update service
        if path.startswith("/api/admin/services/"):
            svc_id = int(path.strip("/").split("/")[3])
            body = self.read_json()
            if not body:
                return self.err("Invalid body.")
            update = {
                "category":    str(body.get("category", "")).strip(),
                "title":       str(body.get("title", "")).strip(),
                "description": str(body.get("description", "")).strip(),
            }
            if "image" in body:
                update["image"] = str(body["image"]).strip()
            if "needs_image" in body:
                update["needs_image"] = 1 if body["needs_image"] else 0
            sb.table("services").update(update).eq("id", svc_id).execute()
            return self.send_json({"success": True, "message": "Service updated."})

        # Update gallery item
        if path.startswith("/api/admin/gallery/"):
            item_id = int(path.strip("/").split("/")[3])
            body = self.read_json()
            if not body:
                return self.err("Invalid body.")
            g_type = str(body.get("type", "photo"))
            if g_type not in ("photo", "video"):
                return self.err("type must be 'photo' or 'video'.")
            sb.table("gallery_items").update({
                "type":     g_type,
                "url":      str(body.get("url", "")).strip(),
                "title":    str(body.get("title", "")).strip(),
                "category": str(body.get("category", "")).strip()
            }).eq("id", item_id).execute()
            return self.send_json({"success": True, "message": "Gallery item updated."})

        # Update enquiry status
        if path.startswith("/api/admin/enquiries/"):
            enq_id = int(path.strip("/").split("/")[3])
            body = self.read_json()
            if not body:
                return self.err("Invalid body.")
            sb.table("enquiries").update({"status": str(body.get("status", "New"))}).eq("id", enq_id).execute()
            return self.send_json({"success": True, "message": "Enquiry updated."})

        self.err("Not found", 404)

    # ---- DELETE ------------------------------------------------------------
    def do_DELETE(self):
        path = urllib.parse.urlparse(self.path).path
        if not self.require_auth():
            return self.err("Unauthorized", 401)
        sb = get_supabase()

        if path.startswith("/api/admin/services/"):
            svc_id = int(path.strip("/").split("/")[3])
            sb.table("services").delete().eq("id", svc_id).execute()
            return self.send_json({"success": True, "message": "Service deleted."})

        if path.startswith("/api/admin/gallery/"):
            item_id = int(path.strip("/").split("/")[3])
            sb.table("gallery_items").delete().eq("id", item_id).execute()
            return self.send_json({"success": True, "message": "Gallery item deleted."})

        if path.startswith("/api/admin/enquiries/"):
            enq_id = int(path.strip("/").split("/")[3])
            sb.table("enquiries").delete().eq("id", enq_id).execute()
            return self.send_json({"success": True, "message": "Enquiry deleted."})

        self.err("Not found", 404)
