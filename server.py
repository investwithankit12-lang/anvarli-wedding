"""
server.py — Production HTTP Server for RISHAN EVENTS
Serves the public Bengali wedding marketing website, public enquiry API,
and the authenticated /admin control panel with SQLite persistence,
bcrypt auth, brute-force protection, and full CRUD for Services, Gallery, & Enquiries.
"""

import http.server
import socketserver
import os
import json
import urllib.parse
import mimetypes
import time
import base64
import csv
import io
import database

PORT = 8000
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Ensure uploads directory exists
os.makedirs(os.path.join(BASE_DIR, "assets", "uploads"), exist_ok=True)

class AnvarliRequestHandler(http.server.BaseHTTPRequestHandler):
    def send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_cors_headers()
        self.end_headers()

    def send_json(self, data, status=200, cookie=None):
        payload = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        if cookie:
            self.send_header("Set-Cookie", cookie)
        self.send_cors_headers()
        self.end_headers()
        self.wfile.write(payload)

    def send_error_json(self, message, status=400):
        self.send_json({"error": message, "success": False}, status=status)

    def get_client_ip(self):
        forwarded = self.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return self.client_address[0] if self.client_address else "127.0.0.1"

    def get_session_token(self):
        # 1. From Authorization header
        auth_hdr = self.headers.get("Authorization")
        if auth_hdr and auth_hdr.startswith("Bearer "):
            return auth_hdr[7:].strip()

        # 2. From Cookie header
        cookie_hdr = self.headers.get("Cookie")
        if cookie_hdr:
            for part in cookie_hdr.split(";"):
                part = part.strip()
                if part.startswith("session_token="):
                    return part.split("=", 1)[1].strip()
        return None

    def require_auth(self):
        token = self.get_session_token()
        username = database.validate_session(token)
        if not username:
            return None
        return username

    def read_json_body(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            if content_length <= 0:
                return {}
            raw_body = self.rfile.read(content_length)
            return json.loads(raw_body.decode("utf-8"))
        except Exception as e:
            return None

    def serve_static_file(self, file_path, content_type=None):
        if not os.path.isfile(file_path):
            self.send_response(404)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"404 Not Found")
            return

        if not content_type:
            content_type, _ = mimetypes.guess_type(file_path)
            if not content_type:
                content_type = "application/octet-stream"

        file_size = os.path.getsize(file_path)
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(file_size))
        self.send_header("Cache-Control", "public, max-age=3600")
        self.end_headers()

        with open(file_path, "rb") as f:
            while chunk := f.read(65536):
                self.wfile.write(chunk)

    # -------------------------------------------------------------------------
    # GET Requests
    # -------------------------------------------------------------------------
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        # 1. Public API: Services
        if path == "/api/services":
            services = database.get_all_services()
            self.send_json({"success": True, "services": services})
            return

        # 2. Public API: Gallery
        if path == "/api/gallery":
            gallery = database.get_all_gallery()
            self.send_json({"success": True, "gallery": gallery})
            return

        # 3. Admin Authentication Check
        if path == "/api/admin/me":
            user = self.require_auth()
            if not user:
                self.send_error_json("Unauthorized", 401)
                return
            self.send_json({"success": True, "username": user})
            return

        # 4. Admin API: Get Services
        if path == "/api/admin/services":
            if not self.require_auth():
                self.send_error_json("Unauthorized", 401)
                return
            services = database.get_all_services()
            self.send_json({"success": True, "services": services})
            return

        # 5. Admin API: Get Gallery
        if path == "/api/admin/gallery":
            if not self.require_auth():
                self.send_error_json("Unauthorized", 401)
                return
            gallery = database.get_all_gallery()
            self.send_json({"success": True, "gallery": gallery})
            return

        # 6. Admin API: Get Enquiries
        if path == "/api/admin/enquiries":
            if not self.require_auth():
                self.send_error_json("Unauthorized", 401)
                return
            search_term = query.get("search", [None])[0]
            status_filter = query.get("status", [None])[0]
            enquiries = database.get_enquiries(search=search_term, status=status_filter)
            self.send_json({"success": True, "enquiries": enquiries})
            return

        # 7. Admin API: Export Enquiries as CSV
        if path == "/api/admin/enquiries/export":
            if not self.require_auth():
                self.send_error_json("Unauthorized", 401)
                return
            enquiries = database.get_enquiries()
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(["ID", "Name", "Phone", "Address", "Event Type", "Preferred Date", "Message", "Status", "Submitted At"])
            for e in enquiries:
                writer.writerow([
                    e["id"], e["name"], e["phone"], e["address"], e["event_type"] or "",
                    e["preferred_date"] or "", e["message"] or "", e["status"], e["created_at"]
                ])
            csv_data = output.getvalue().encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/csv; charset=utf-8")
            self.send_header("Content-Disposition", 'attachment; filename="rishan_enquiries_export.csv"')
            self.send_header("Content-Length", str(len(csv_data)))
            self.end_headers()
            self.wfile.write(csv_data)
            return

        # 8. Admin Route: /admin/login
        if path == "/admin/login" or path == "/admin/login/":
            self.serve_static_file(os.path.join(BASE_DIR, "login.html"), "text/html; charset=utf-8")
            return

        # 9. Admin Route: /admin (Protected by Session)
        if path == "/admin" or path == "/admin/":
            if not self.require_auth():
                self.send_response(302)
                self.send_header("Location", "/admin/login")
                self.end_headers()
                return
            self.serve_static_file(os.path.join(BASE_DIR, "admin.html"), "text/html; charset=utf-8")
            return

        # 10. Public Site & Static Files
        if path == "/" or path == "/index.html":
            self.serve_static_file(os.path.join(BASE_DIR, "index.html"), "text/html; charset=utf-8")
            return

        # Clean sanitized local static path
        relative_path = path.lstrip("/")
        safe_path = os.path.normpath(os.path.join(BASE_DIR, relative_path))
        if safe_path.startswith(BASE_DIR) and os.path.isfile(safe_path):
            self.serve_static_file(safe_path)
            return

        # Not found
        self.send_response(404)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"404 Not Found")

    # -------------------------------------------------------------------------
    # POST Requests
    # -------------------------------------------------------------------------
    def do_POST(self):
        path = urllib.parse.urlparse(self.path).path
        ip = self.get_client_ip()

        # 1. Admin Login API with Brute-Force Rate Limiting
        if path == "/api/admin/login":
            body = self.read_json_body()
            if not body or "username" not in body or "password" not in body:
                self.send_error_json("Username and password are required.", 400)
                return

            username = str(body["username"]).strip()
            password = str(body["password"]).strip()

            token, err = database.verify_admin_login(username, password, ip)
            if err:
                status_code = 429 if "Locked out" in err else 401
                self.send_error_json(err, status_code)
                return

            # Set secure session cookie (HttpOnly; SameSite=Lax; Path=/)
            cookie = f"session_token={token}; Path=/; HttpOnly; SameSite=Lax; Max-Age=604800"
            self.send_json({
                "success": True,
                "message": "Login successful",
                "token": token,
                "username": username
            }, 200, cookie=cookie)
            return

        # 2. Admin Logout API
        if path == "/api/admin/logout":
            token = self.get_session_token()
            if token:
                database.destroy_session(token)
            cookie = "session_token=; Path=/; HttpOnly; Max-Age=0"
            self.send_json({"success": True, "message": "Logged out"}, 200, cookie=cookie)
            return

        # 3. Public Enquiry Submission (Saves to DB)
        if path == "/api/enquiries":
            body = self.read_json_body()
            if not body:
                self.send_error_json("Invalid enquiry payload.", 400)
                return

            name = str(body.get("name", "")).strip()
            phone = str(body.get("phone", "")).strip()
            address = str(body.get("address", "")).strip()
            event_type = str(body.get("eventType", "")).strip()
            preferred_date = str(body.get("preferredDate", "")).strip()
            message = str(body.get("message", "")).strip()

            if not name or not phone or not address:
                self.send_error_json("Name, Phone, and Address are required.", 400)
                return

            enquiry_id = database.save_enquiry(name, phone, address, event_type, preferred_date, message)
            self.send_json({
                "success": True,
                "message": "Enquiry received and saved to database.",
                "id": enquiry_id
            }, 201)
            return

        # --- Protected Admin Endpoints ---
        if not self.require_auth():
            self.send_error_json("Unauthorized. Admin access required.", 401)
            return

        # 4. Admin API: Add Service Category
        if path == "/api/admin/services":
            body = self.read_json_body()
            if not body or not body.get("category") or not body.get("title") or not body.get("description"):
                self.send_error_json("Category, title, and description are required.", 400)
                return

            cat = str(body["category"]).strip()
            title = str(body["title"]).strip()
            desc = str(body["description"]).strip()
            img = str(body.get("image", "assets/gallery/mandap-decor.svg")).strip()
            needs_img = 1 if body.get("needs_image") else 0

            new_id = database.add_service(cat, title, desc, img, needs_img)
            self.send_json({"success": True, "id": new_id, "message": "Service added successfully."})
            return

        # 5. Admin API: Upload / Replace Service Image
        if path.startswith("/api/admin/services/") and path.endswith("/image"):
            # e.g. /api/admin/services/1/image
            parts = path.strip("/").split("/")
            try:
                service_id = int(parts[3])
            except ValueError:
                self.send_error_json("Invalid service ID.", 400)
                return

            body = self.read_json_body()
            if not body or "image_data" not in body:
                self.send_error_json("Missing image_data payload.", 400)
                return

            raw_b64 = body["image_data"]
            filename = body.get("filename", "upload.jpg")
            # Validation
            ext = os.path.splitext(filename)[1].lower()
            if ext not in [".jpg", ".jpeg", ".png", ".webp", ".svg"]:
                self.send_error_json("Invalid image format. Allowed: JPG, PNG, WEBP, SVG.", 400)
                return

            if "," in raw_b64:
                raw_b64 = raw_b64.split(",", 1)[1]

            try:
                file_bytes = base64.b64decode(raw_b64)
                if len(file_bytes) > 10 * 1024 * 1024:  # 10MB limit
                    self.send_error_json("Image exceeds maximum 10MB limit.", 400)
                    return

                new_fn = f"service_{service_id}_{int(time.time())}{ext}"
                dest_path = os.path.join(BASE_DIR, "assets", "uploads", new_fn)
                with open(dest_path, "wb") as f:
                    f.write(file_bytes)

                rel_url = f"assets/uploads/{new_fn}"
                database.update_service_image(service_id, rel_url, needs_image=0)
                self.send_json({"success": True, "image": rel_url, "message": "Image updated successfully."})
            except Exception as e:
                self.send_error_json(f"Upload failed: {str(e)}", 500)
            return

        # 6. Admin API: Add Gallery Item
        if path == "/api/admin/gallery":
            body = self.read_json_body()
            if not body or not body.get("type") or not body.get("url") or not body.get("title") or not body.get("category"):
                self.send_error_json("Type, URL, title, and category are required.", 400)
                return

            g_type = str(body["type"]).strip().lower()
            if g_type not in ["photo", "video"]:
                self.send_error_json("Type must be either 'photo' or 'video'.", 400)
                return

            url = str(body["url"]).strip()
            title = str(body["title"]).strip()
            cat = str(body["category"]).strip()

            new_id = database.add_gallery_item(g_type, url, title, cat)
            self.send_json({"success": True, "id": new_id, "message": "Gallery item added."})
            return

        # 7. Admin API: Upload Gallery File
        if path == "/api/admin/gallery/upload":
            body = self.read_json_body()
            if not body or "file_data" not in body:
                self.send_error_json("Missing file_data payload.", 400)
                return

            raw_b64 = body["file_data"]
            filename = body.get("filename", "gallery_upload.jpg")
            ext = os.path.splitext(filename)[1].lower()
            if ext not in [".jpg", ".jpeg", ".png", ".webp", ".svg", ".mp4"]:
                self.send_error_json("Invalid format. Allowed: JPG, PNG, WEBP, SVG, MP4.", 400)
                return

            if "," in raw_b64:
                raw_b64 = raw_b64.split(",", 1)[1]

            try:
                file_bytes = base64.b64decode(raw_b64)
                if len(file_bytes) > 25 * 1024 * 1024:  # 25MB limit
                    self.send_error_json("File exceeds maximum 25MB limit.", 400)
                    return

                new_fn = f"gallery_{int(time.time())}_{uuid.uuid4().hex[:6]}{ext}"
                dest_path = os.path.join(BASE_DIR, "assets", "uploads", new_fn)
                with open(dest_path, "wb") as f:
                    f.write(file_bytes)

                rel_url = f"assets/uploads/{new_fn}"
                self.send_json({"success": True, "url": rel_url})
            except Exception as e:
                self.send_error_json(f"Upload failed: {str(e)}", 500)
            return

        self.send_error_json("Endpoint not found", 404)

    # -------------------------------------------------------------------------
    # PUT Requests (Update Services, Gallery, Enquiries)
    # -------------------------------------------------------------------------
    def do_PUT(self):
        path = urllib.parse.urlparse(self.path).path
        if not self.require_auth():
            self.send_error_json("Unauthorized", 401)
            return

        # 1. Update Service
        if path.startswith("/api/admin/services/"):
            service_id = int(path.strip("/").split("/")[3])
            body = self.read_json_body()
            if not body:
                self.send_error_json("Invalid body", 400)
                return

            cat = str(body.get("category", "")).strip()
            title = str(body.get("title", "")).strip()
            desc = str(body.get("description", "")).strip()
            img = body.get("image")
            needs_img = body.get("needs_image")

            database.update_service(service_id, cat, title, desc, img, needs_img)
            self.send_json({"success": True, "message": "Service updated."})
            return

        # 2. Update Gallery Item
        if path.startswith("/api/admin/gallery/"):
            item_id = int(path.strip("/").split("/")[3])
            body = self.read_json_body()
            if not body:
                self.send_error_json("Invalid body", 400)
                return

            g_type = str(body.get("type", "photo")).strip()
            url = str(body.get("url", "")).strip()
            title = str(body.get("title", "")).strip()
            cat = str(body.get("category", "")).strip()

            database.update_gallery_item(item_id, g_type, url, title, cat)
            self.send_json({"success": True, "message": "Gallery item updated."})
            return

        # 3. Update Enquiry Status
        if path.startswith("/api/admin/enquiries/"):
            enquiry_id = int(path.strip("/").split("/")[3])
            body = self.read_json_body()
            if not body or "status" not in body:
                self.send_error_json("Status is required.", 400)
                return

            status = str(body["status"]).strip()
            if status not in ["New", "Contacted", "Confirmed", "Archived"]:
                self.send_error_json("Invalid status value.", 400)
                return

            database.update_enquiry_status(enquiry_id, status)
            self.send_json({"success": True, "message": "Enquiry status updated."})
            return

        self.send_error_json("Endpoint not found", 404)

    # -------------------------------------------------------------------------
    # DELETE Requests
    # -------------------------------------------------------------------------
    def do_DELETE(self):
        path = urllib.parse.urlparse(self.path).path
        if not self.require_auth():
            self.send_error_json("Unauthorized", 401)
            return

        # 1. Delete Service
        if path.startswith("/api/admin/services/"):
            service_id = int(path.strip("/").split("/")[3])
            database.delete_service(service_id)
            self.send_json({"success": True, "message": "Service deleted."})
            return

        # 2. Delete Gallery Item
        if path.startswith("/api/admin/gallery/"):
            item_id = int(path.strip("/").split("/")[3])
            database.delete_gallery_item(item_id)
            self.send_json({"success": True, "message": "Gallery item deleted."})
            return

        # 3. Delete Enquiry
        if path.startswith("/api/admin/enquiries/"):
            enquiry_id = int(path.strip("/").split("/")[3])
            database.delete_enquiry(enquiry_id)
            self.send_json({"success": True, "message": "Enquiry deleted."})
            return

        self.send_error_json("Endpoint not found", 404)

def run_server():
    database.init_db()
    with socketserver.TCPServer(("", PORT), AnvarliRequestHandler) as httpd:
        print(f"[SERVER] Rishan Events running at http://localhost:{PORT}")
        print(f"[SERVER] Admin portal available at http://localhost:{PORT}/admin")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n[SERVER] Shutting down...")
            httpd.shutdown()

if __name__ == "__main__":
    run_server()
