from flask import Flask, request, jsonify, send_from_directory, session
from flask_session import Session
import sqlite3, os, json, re, requests
from datetime import datetime

BOT_TOKEN = os.getenv("BOT_TOKEN", "8240983295:AAGRPD5rT9_SHf30kdYva8VbD0xcj7AP74s")
ADMIN_ID = int(os.getenv("ADMIN_ID", "5568760903"))
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "1233")
BASE_URL = os.getenv("BASE_URL", "https://yovam-1.onrender.com")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", f"{BASE_URL}/webhook")
PORT = int(os.getenv("PORT", "10000"))

DB_PATH = "db.sqlite"

app = Flask(__name__, static_folder="static", static_url_path="/static")

# --- FIXED SESSION CONFIG ---
app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_FILE_DIR"] = os.path.join(os.getcwd(), "instance", "flask_session")
os.makedirs(app.config["SESSION_FILE_DIR"], exist_ok=True)
app.config["SESSION_COOKIE_NAME"] = "admin_session"
app.config["SESSION_COOKIE_PATH"] = "/"          # доступна на всём сайте
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"   # поддержка Safari/Chrome
app.config["SESSION_COOKIE_SECURE"] = True      # работает только по HTTPS
app.config["SECRET_KEY"] = os.getenv("SESSION_SECRET", "very_secret_session_key")
Session(app)

def db_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = db_conn()
    cur = conn.cursor()
    cur.executescript("""
    CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        price REAL NOT NULL,
        category_id INTEGER,
        image_url TEXT,
        description TEXT,
        available INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        username TEXT,
        first_name TEXT,
        last_name TEXT,
        items_json TEXT,
        total REAL,
        phone TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS pending_orders (
        chat_id INTEGER PRIMARY KEY,
        user_id INTEGER,
        username TEXT,
        first_name TEXT,
        last_name TEXT,
        items_json TEXT,
        total REAL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    """)
    conn.commit()
    conn.close()

init_db()

TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

def tg_send_api(method, data):
    try:
        r = requests.post(f"{TG_API}/{method}", json=data, timeout=10)
        return r.json()
    except Exception as e:
        return {"ok": False, "error": str(e)}

# ================= ROUTES =================

@app.get("/")
def health():
    return "OK"

@app.get("/app")
def webapp_index():
    return send_from_directory("static/webapp", "index.html")

@app.get("/admin")
def admin_index():
    return send_from_directory("static/admin", "index.html")

@app.post("/webhook")
def telegram_webhook():
    upd = request.get_json(silent=True) or {}
    try:
        handle_update(upd)
    except Exception as e:
        print("handle_update error:", e)
    return jsonify({"ok": True})

# ====== ADMIN API (login/logout + CRUD categories/products) ======

@app.post("/api/admin/login")
def api_admin_login():
    data = request.get_json(silent=True) or {}
    if str(data.get("password")) == str(ADMIN_PASSWORD):
        session["is_admin"] = True
        return jsonify({"ok": True})
    return jsonify({"ok": False, "error": "bad_password"}), 403

@app.post("/api/admin/logout")
def api_admin_logout():
    session.clear()
    return jsonify({"ok": True})

def require_admin():
    return bool(session.get("is_admin"))

@app.get("/api/admin/categories")
def api_admin_categories():
    if not require_admin():
        return jsonify({"ok": False, "error": "unauthorized"}), 401
    conn = db_conn()
    rows = conn.execute("SELECT id, name, created_at FROM categories ORDER BY id DESC").fetchall()
    conn.close()
    return jsonify({"ok": True, "data": [dict(r) for r in rows]})

@app.post("/api/admin/categories")
def api_admin_categories_add():
    if not require_admin():
        return jsonify({"ok": False, "error": "unauthorized"}), 401
    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"ok": False, "error": "name_required"}), 400
    conn = db_conn()
    cur = conn.cursor()
    cur.execute("INSERT INTO categories(name) VALUES (?)", (name,))
    conn.commit()
    conn.close()
    return jsonify({"ok": True, "id": cur.lastrowid})

# (остальные CRUD API для категорий и продуктов, обработка заказов и handle_update
# оставлены как в предыдущей версии — их нужно скопировать из твоего рабочего файла)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT, debug=False)
