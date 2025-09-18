
from flask import Flask, request, jsonify, send_from_directory, session
from flask_session import Session
import sqlite3, os, json, re, requests
from datetime import datetime

BOT_TOKEN = os.getenv("BOT_TOKEN", "8240983295:AAGRPD5rT9_SHf30kdYva8VbD0xcj7AP74s")
ADMIN_ID = int(os.getenv("ADMIN_ID", "5568760903"))
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "1233")
BASE_URL = os.getenv("BASE_URL", "https://yovam.onrender.com")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", f"{BASE_URL}/webhook")
PORT = int(os.getenv("PORT", "10000"))

DB_PATH = "/var/data/db.sqlite"

app = Flask(__name__, static_folder="static", static_url_path="/static")

# Sessions only for /admin
app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_FILE_DIR"] = os.path.join(os.getcwd(), "instance", "flask_session")
os.makedirs(app.config["SESSION_FILE_DIR"], exist_ok=True)
app.config["SESSION_COOKIE_NAME"] = "admin_session"
app.config["SESSION_COOKIE_PATH"] = "/"   # доступна на всем сайте
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"   # поддержка Safari/Chrome  
app.config["SESSION_COOKIE_SECURE"] = True   # работает только по HTTPS
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
    ccount = cur.execute("SELECT COUNT(*) FROM categories").fetchone()[0]
    if ccount == 0:
        cur.execute("INSERT INTO categories(name) VALUES (?)", ("Популярное",))
        cat_id = cur.lastrowid
        cur.execute("INSERT INTO products (name, price, category_id, image_url, description, available) VALUES (?,?,?,?,?,?)",
                    ("Пример товара", 30, cat_id, "https://images.unsplash.com/photo-1585238342028-4bbc267a9731?q=80&w=800", "Описание примера товара", 1))
    conn.commit()
    conn.close()

init_db()

TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

def tg_send_message(chat_id, text, reply_markup=None, parse_mode="HTML"):
    payload = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode, "disable_web_page_preview": True}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    try:
        r = requests.post(f"{TG_API}/sendMessage", json=payload, timeout=10)
        return r.json()
    except Exception as e:
        return {"ok": False, "error": str(e)}

def keyboard_menu():
    return {
        "keyboard": [[{"text": "🛍️ Меню", "web_app": {"url": f"{BASE_URL}/app"}}]],
        "resize_keyboard": True,
        "one_time_keyboard": False
    }

def keyboard_ask_phone():
    return {
        "keyboard": [
            [{"text": "📞 Отправить номер", "request_contact": True}],
            [{"text": "🛍️ Вернуться в меню", "web_app": {"url": f"{BASE_URL}/app"}}]
        ],
        "resize_keyboard": True
    }

phone_re = re.compile(r"(\+?\d[\d\-\(\)\s]{5,})")

@app.get("/app")
def webapp_index():
    return send_from_directory("static/webapp", "index.html")

@app.get("/admin")
def admin_index():
    return send_from_directory("static/admin", "index.html")

@app.get("/api/categories/public")
def api_public_categories():
    conn = db_conn()
    rows = conn.execute("SELECT id, name FROM categories ORDER BY id ASC").fetchall()
    conn.close()
    return jsonify({"ok": True, "data": [dict(r) for r in rows]})

@app.get("/api/products/public")
def api_public_products():
    conn = db_conn()
    rows = conn.execute(
        """
        SELECT p.id, p.name, p.price, p.category_id, p.image_url, p.description, p.available,
               c.name AS category_name
        FROM products p
        LEFT JOIN categories c ON c.id = p.category_id
        WHERE p.available = 1
        ORDER BY p.id DESC
        """
    ).fetchall()
    conn.close()
    return jsonify({"ok": True, "data": [dict(r) for r in rows]})

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

@app.put("/api/admin/categories/<int:cid>")
def api_admin_categories_edit(cid):
    if not require_admin():
        return jsonify({"ok": False, "error": "unauthorized"}), 401
    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"ok": False, "error": "name_required"}), 400
    conn = db_conn()
    conn.execute("UPDATE categories SET name=? WHERE id=?", (name, cid))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})

@app.delete("/api/admin/categories/<int:cid>")
def api_admin_categories_del(cid):
    if not require_admin():
        return jsonify({"ok": False, "error": "unauthorized"}), 401
    conn = db_conn()
    conn.execute("DELETE FROM categories WHERE id=?", (cid,))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})

@app.get("/api/admin/products")
def api_admin_products():
    if not require_admin():
        return jsonify({"ok": False, "error": "unauthorized"}), 401
    conn = db_conn()
    rows = conn.execute("""
        SELECT p.*, c.name AS category_name
        FROM products p LEFT JOIN categories c ON c.id = p.category_id
        ORDER BY p.id DESC
    """).fetchall()
    conn.close()
    return jsonify({"ok": True, "data": [dict(r) for r in rows]})

@app.post("/api/admin/products")
def api_admin_products_add():
    if not require_admin():
        return jsonify({"ok": False, "error": "unauthorized"}), 401
    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    price = data.get("price")
    if not name or price is None:
        return jsonify({"ok": False, "error": "name_and_price_required"}), 400
    category_id = data.get("category_id")
    image_url = data.get("image_url")
    description = data.get("description")
    available = 1 if data.get("available", True) else 0
    conn = db_conn()
    cur = conn.cursor()
    cur.execute("""INSERT INTO products(name, price, category_id, image_url, description, available)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (name, float(price), category_id, image_url, description, available))
    conn.commit()
    conn.close()
    return jsonify({"ok": True, "id": cur.lastrowid})

@app.put("/api/admin/products/<int:pid>")
def api_admin_products_edit(pid):
    if not require_admin():
        return jsonify({"ok": False, "error": "unauthorized"}), 401
    data = request.get_json() or {}
    conn = db_conn()
    conn.execute("""UPDATE products SET name=?, price=?, category_id=?, image_url=?, description=?, available=?
                    WHERE id=?""",
                 (data.get("name"), float(data.get("price")), data.get("category_id"),
                  data.get("image_url"), data.get("description"), 1 if data.get("available") else 0, pid))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})

@app.delete("/api/admin/products/<int:pid>")
def api_admin_products_del(pid):
    if not require_admin():
        return jsonify({"ok": False, "error": "unauthorized"}), 401
    conn = db_conn()
    conn.execute("DELETE FROM products WHERE id=?", (pid,))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})

@app.route("/webhook", methods=["POST"])
def telegram_webhook():
    upd = request.get_json(silent=True) or {}
    print("RAW update:", upd)    # оставляем для отладки  
    try:
        handle_update(upd)
    except Exception as e:
        print("handle_update error:", e)
    return jsonify({"ok": True})

def tg_send_api(method, data):
    try:
        r = requests.post(f"{TG_API}/{method}", json=data, timeout=10)
        return r.json()
    except Exception as e:
        return {"ok": False, "error": str(e)}

def handle_update(update):
    message = update.get("message") or update.get("edited_message")
    if not message:
        return
    chat_id = message["chat"]["id"]
    from_user = message.get("from", {})
    text = message.get("text", "") or ""
    contact = message.get("contact")
    web_app_data = message.get("web_app_data")

    if text.startswith("/start") or text.startswith("/menu"):
        tg_send_api("sendMessage", {
            "chat_id": chat_id,
            "text": "Привет! Нажми кнопку «🛍️ Меню» ниже, чтобы открыть магазин.",
            "parse_mode": "HTML",
            "reply_markup": {
                "keyboard": [[{"text":"🛍️ Меню","web_app":{"url": f"{BASE_URL}/app"}}]],
                "resize_keyboard": True
            }
        })
        return

    if web_app_data and web_app_data.get("data"):
        try:
            data = json.loads(web_app_data["data"])
        except Exception:
            tg_send_api("sendMessage", {"chat_id": chat_id, "text": "Ошибка обработки заказа."})
            return
        if data.get("type") == "order":
            items = data.get("payload", {}).get("items", [])
            total = float(data.get("payload", {}).get("total", 0))
            if not items:
                tg_send_api("sendMessage", {"chat_id": chat_id, "text": "Корзина пустая."})
                return
            conn = db_conn()
            conn.execute("""INSERT OR REPLACE INTO pending_orders
                            (chat_id, user_id, username, first_name, last_name, items_json, total)
                            VALUES (?, ?, ?, ?, ?, ?, ?)""",
                         (chat_id, from_user.get("id"), from_user.get("username"),
                          from_user.get("first_name"), from_user.get("last_name"),
                          json.dumps(items, ensure_ascii=False), total))
            conn.commit()
            conn.close()
            tg_send_api("sendMessage", {
                "chat_id": chat_id,
                "text": "Укажите номер телефона для связи:",
                "reply_markup": {
                    "keyboard":[
                        [{"text":"📞 Отправить номер","request_contact":True}],
                        [{"text":"🛍️ Вернуться в меню","web_app":{"url": f"{BASE_URL}/app"}}]
                    ],
                    "resize_keyboard": True
                }
            })
            return

    if contact and contact.get("phone_number"):
        finalize_order(chat_id, from_user, contact["phone_number"])
        return

    import re
    m = re.search(r"(\+?\d[\d\-\(\)\s]{5,})", text)
    if m and len(re.sub(r"\D","",m.group(1))) >= 7:
        finalize_order(chat_id, from_user, m.group(1))
        return

def finalize_order(chat_id, from_user, phone):
    conn = db_conn()
    row = conn.execute("SELECT * FROM pending_orders WHERE chat_id=?", (chat_id,)).fetchone()
    if not row:
        tg_send_api("sendMessage", {
            "chat_id": chat_id,
            "text": "У вас нет активного заказа. Нажмите «Меню».",
            "reply_markup": {"keyboard":[[{"text":"🛍️ Меню","web_app":{"url": f"{BASE_URL}/app"}}]],"resize_keyboard":True}
        })
        conn.close()
        return

    items = json.loads(row["items_json"] or "[]")
    total = float(row["total"] or 0)

    conn.execute("""INSERT INTO orders (user_id, username, first_name, last_name, items_json, total, phone)
                    VALUES (?, ?, ?, ?, ?, ?, ?)""",
                 (from_user.get("id"), from_user.get("username"), from_user.get("first_name"),
                  from_user.get("last_name"), json.dumps(items, ensure_ascii=False), total, phone))
    conn.execute("DELETE FROM pending_orders WHERE chat_id=?", (chat_id,))
    conn.commit()
    conn.close()

    lines = []
    for i, it in enumerate(items, 1):
        name = it.get("name")
        qty = it.get("qty", 1)
        price = float(it.get("price", 0))
        lines.append(f"{i}) {name} × {qty} = {qty*price} TJS")
    order_text = (
        f"🆕 <b>Новый заказ</b>\n"
        f"👤 Пользователь: <a href='tg://user?id={from_user.get('id')}'>{from_user.get('first_name','Пользователь')}</a> (@{from_user.get('username','нет')})\n"
        f"📞 Телефон: {phone}\n"
        f"🧾 Состав:\n" + "\n".join(lines) + "\n"
        f"💰 Итого: <b>{total} TJS</b>\n"
        f"🕒 Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )
    tg_send_api("sendMessage", {"chat_id": ADMIN_ID, "text": order_text, "parse_mode":"HTML"})
    tg_send_api("sendMessage", {
        "chat_id": chat_id,
        "text": f"Спасибо! Мы получили ваш заказ. Мы свяжемся по номеру: <b>{phone}</b>.",
        "parse_mode":"HTML",
        "reply_markup": {"keyboard":[[{"text":"🛍️ Меню","web_app":{"url": f"{BASE_URL}/app"}}]],"resize_keyboard":True}
    })

@app.get("/set-webhook")
def set_webhook():
    key = request.args.get("key")
    if key != "letmein":
        return "forbidden", 403
    url = WEBHOOK_URL
    r = requests.post(f"{TG_API}/setWebhook", json={"url": url}, timeout=10)
    return jsonify(r.json())

@app.get("/delete-webhook")
def delete_webhook():
    key = request.args.get("key")
    if key != "letmein":
        return "forbidden", 403
    r = requests.post(f"{TG_API}/deleteWebhook", timeout=10)
    return jsonify(r.json())

@app.get("/")
def health():
    return "OK"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT, debug=False)
