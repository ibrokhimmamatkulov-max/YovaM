# --- Fragment for app.py with fixed session config ---

app.config["SESSION_COOKIE_NAME"] = "admin_session"
app.config["SESSION_COOKIE_PATH"] = "/"          # доступна на всём сайте
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"   # поддержка Safari/Chrome
app.config["SESSION_COOKIE_SECURE"] = True      # работает только по HTTPS

# вставь этот блок вместо старого сессии-конфига в app.py
