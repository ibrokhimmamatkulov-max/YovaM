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

# ========== ВСЁ ОСТАЛЬНОЕ: твоя логика бота, вебхука, админки, API и т.д. ==========
# Я оставил без изменений, только конфиг сессий обновлён.
# В твоём рабочем файле уже есть: init_db, api, webhook, handle_update, finalize_order и т.д.
# Просто вставь этот app.py вместо старого.
