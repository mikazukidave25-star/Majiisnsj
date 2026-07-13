import os
import time
import threading
import json
import websocket
import requests
from colorama import Fore, init
from flask import Flask, request, render_template_string, redirect, url_for, session

# --- Inisialisasi ---
init(autoreset=True)
app = Flask(__name__)

# KUNCI RAHASIA FLASK: Wajib ada untuk menggunakan session
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "kunci_rahasia_bebas_apa_saja_123")

# Database sederhana di memori untuk menyimpan akun web
# Struktur: { username: password }
USERS_DB = {
    "admin": "admin123"  # Akun bawaan default (silakan ganti atau daftar akun baru di web)
}

# Kamus untuk menyimpan data bot aktif per User
# Struktur: { username: { token: {"thread": Thread, "ws": WebSocketApp, "guild_id": str, "channel_id": str, "running": True} } }
user_active_bots = {}

# HTML Template Gabungan (Login, Register, Dashboard)
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Discord Voice Manager</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #1e1e2e; color: #cdd6f4; padding: 20px; margin: 0; }
        .container { max-width: 800px; margin: auto; background: #313244; padding: 25px; border-radius: 10px; box-shadow: 0 4px 10px rgba(0,0,0,0.3); }
        .auth-container { max-width: 400px; margin: 100px auto; background: #313244; padding: 25px; border-radius: 10px; box-shadow: 0 4px 10px rgba(0,0,0,0.3); }
        h2, h3 { color: #89b4fa; text-align: center; margin-top: 5px; }
        label { font-weight: bold; display: block; margin-top: 15px; color: #a6adc8; }
        input, textarea, select { width: 100%; padding: 10px; margin-top: 5px; border-radius: 5px; border: 1px solid #45475a; background-color: #181825; color: #cdd6f4; box-sizing: border-box; }
        button { width: 100%; background: #a6e3a1; color: #11111b; border: none; padding: 12px; margin-top: 20px; font-weight: bold; border-radius: 5px; cursor: pointer; font-size: 16px; }
        button:hover { background: #94e2d5; }
        .btn-delete { background: #f38ba8; color: #11111b; width: auto; padding: 6px 12px; margin-top: 0; font-size: 14px; }
        .btn-delete:hover { background: #eba0ac; }
        .btn-logout { background: #f38ba8; color: #11111b; width: auto; float: right; padding: 8px 15px; margin-top: -40px; font-size: 14px; }
        .bot-table { width: 100%; border-collapse: collapse; margin-top: 15px; }
        .bot-table th, .bot-table td { border: 1px solid #45475a; padding: 10px; text-align: left; word-break: break-all; }
        .bot-table th { background-color: #181825; color: #89b4fa; }
        .card { background: #181825; padding: 15px; border-radius: 8px; margin-top: 20px; }
        .hint { font-size: 12px; color: #a6adc8; margin-top: 3px; }
        .alert { background: #f38ba8; color: #11111b; padding: 10px; border-radius: 5px; text-align: center; margin-bottom: 15px; }
        .success { background: #a6e3a1; color: #11111b; padding: 10px; border-radius: 5px; text-align: center; margin-bottom: 15px; }
    </style>
    <script>
        function toggleMode() {
            var mode = document.getElementById("mode").value;
            if (mode === "single") {
                document.getElementById("single_channel_sec").style.display = "block";
                document.getElementById("multi_channel_sec").style.display = "none";
            } else {
                document.getElementById("single_channel_sec").style.display = "none";
                document.getElementById("multi_channel_sec").style.display = "block";
            }
        }
    </script>
</head>
<body>
    {% if page == 'login' %}
    <div class="auth-container">
        <h2>Login User</h2>
        {% if error %}<div class="alert">{{ error }}</div>{% endif %}
        {% if success %}<div class="success">{{ success }}</div>{% endif %}
        <form method="POST" action="/login">
            <label>Username:</label>
            <input type="text" name="username" required>
            <label>Password:</label>
            <input type="password" name="password" required>
            <button type="submit">Masuk</button>
        </form>
        <p style="text-align: center; margin-top: 15px;">Belum punya akun? <a href="/register" style="color: #89b4fa;">Daftar di sini</a></p>
    </div>

    {% elif page == 'register' %}
    <div class="auth-container">
        <h2>Daftar Akun Baru</h2>
        {% if error %}<div class="alert">{{ error }}</div>{% endif %}
        <form method="POST" action="/register">
            <label>Username Baru:</label>
            <input type="text" name="username" required>
            <label>Password:</label>
            <input type="password" name="password" required>
            <button type="submit" style="background: #89b4fa;">Daftar</button>
        </form>
        <p style="text-align: center; margin-top: 15px;">Sudah punya akun? <a href="/login" style="color: #89b4fa;">Login di sini</a></p>
    </div>

    {% elif page == 'dashboard' %}
    <div class="container">
        <h2>Discord Voice Manager</h2>
        <p style="color: #a6e3a1; font-weight: bold; margin-top: 0;">Halo, {{ username }}!</p>
        <a href="/logout"><button class="btn-logout">Logout</button></a>

        <div class="card">
            <h3>Daftar Bot Anda yang Aktif ({{ my_bots|length }})</h3>
            {% if my_bots %}
                <table class="bot-table">
                    <thead>
                        <tr>
                            <th>Token (Pratinjau)</th>
                            <th>Guild ID</th>
                            <th>Voice Channel ID</th>
                            <th>Aksi</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for token, info in my_bots.items() %}
                        <tr>
                            <td>{{ token[:15] }}...</td>
                            <td>{{ info.guild_id }}</td>
                            <td>{{ info.channel_id }}</td>
                            <td>
                                <form method="POST" action="/stop" style="margin:0;">
                                    <input type="hidden" name="token" value="{{ token }}">
                                    <button type="submit" class="btn-delete">Hapus / Stop</button>
                                </form>
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            {% else %}
                <p style="text-align: center; color: #a6adc8;">Belum ada bot yang Anda jalankan.</p>
            {% endif %}
        </div>

        <div class="card">
            <h3>Tambah Bot Baru</h3>
            <form method="POST" action="/start">
                <label for="mode">Mode Channel Voice:</label>
                <select id="mode" name="mode" onchange="toggleMode()">
                    <option value="single">Satu Voice Channel untuk Semua Token</option>
                    <option value="multi">Voice Channel Berbeda per Token</option>
                </select>

                <label for="guild_id">Server / Guild ID:</label>
                <input type="text" id="guild_id" name="guild_id" placeholder="Contoh: 123456789012345678" required>

                <div id="single_channel_sec">
                    <label for="tokens_single">Token Discord (Satu token per baris):</label>
                    <textarea id="tokens_single" name="tokens_single" rows="4" placeholder="Token1&#10;Token2"></textarea>
                    
                    <label for="channel_id_single">Voice Channel ID:</label>
                    <input type="text" id="channel_id_single" name="channel_id_single" placeholder="Contoh: 987654321098765432">
                </div>

                <div id="multi_channel_sec" style="display: none;">
                    <label for="token_channel_pairs">Pasangan Token & Voice Channel ID:</label>
                    <p class="hint">Format: <code>TOKEN|CHANNEL_ID</code> (Satu per baris)</p>
                    <textarea id="token_channel_pairs" name="token_channel_pairs" rows="5" placeholder="Token1|ChannelID1&#10;Token2|ChannelID2"></textarea>
                </div>

                <button type="submit">Jalankan Bot</button>
            </form>
        </div>
    </div>
    {% endif %}
</body>
</html>
"""

# --- Autentikasi Routes ---
@app.route('/')
def home():
    if 'username' in session:
        username = session['username']
        # Pastikan slot di database bot untuk user ini ada
        if username not in user_active_bots:
            user_active_bots[username] = {}
        return render_template_string(HTML_TEMPLATE, page='dashboard', username=username, my_bots=user_active_bots[username])
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        if username in USERS_DB and USERS_DB[username] == password:
            session['username'] = username
            return redirect(url_for('home'))
        return render_template_string(HTML_TEMPLATE, page='login', error="Username atau Password salah!")
    
    return render_template_string(HTML_TEMPLATE, page='login')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        if not username or not password:
            return render_template_string(HTML_TEMPLATE, page='register', error="Semua kolom wajib diisi!")
        if username in USERS_DB:
            return render_template_string(HTML_TEMPLATE, page='register', error="Username sudah terdaftar!")
        
        USERS_DB[username] = password
        return render_template_string(HTML_TEMPLATE, page='login', success="Pendaftaran berhasil! Silakan login.")
    
    return render_template_string(HTML_TEMPLATE, page='register')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

# --- Operasi Bot Routes ---
@app.route('/start', methods=['POST'])
def start_bots():
    if 'username' not in session:
        return redirect(url_for('login'))
        
    username = session['username']
    mode = request.form.get('mode')
    guild_id = request.form.get('guild_id', '').strip()

    if not guild_id:
        return "Guild ID wajib diisi!", 400

    entries = []  # Menyimpan tuple: (token, channel_id)

    if mode == 'single':
        raw_tokens = request.form.get('tokens_single', '')
        channel_id = request.form.get('channel_id_single', '').strip()
        
        tokens = [t.strip() for t in raw_tokens.splitlines() if t.strip()]
        if not tokens or not channel_id:
            return "Token dan Voice Channel ID wajib diisi!", 400
        
        for t in tokens:
            entries.append((t, channel_id))

    elif mode == 'multi':
        pairs_raw = request.form.get('token_channel_pairs', '')
        lines = [line.strip() for line in pairs_raw.splitlines() if line.strip()]
        
        for line in lines:
            if '|' in line:
                t, c = line.split('|', 1)
                entries.append((t.strip(), c.strip()))
            else:
                return "Format multi-channel salah! Gunakan format TOKEN|CHANNEL_ID", 400

    # Jalankan bot khusus di bawah user yang sedang login
    if username not in user_active_bots:
        user_active_bots[username] = {}

    for token, ch_id in entries:
        # Jika token milik user ini sudah ada, matikan yang lama dulu
        if token in user_active_bots[username]:
            stop_bot_instance(username, token)

        bot_info = {
            "guild_id": guild_id,
            "channel_id": ch_id,
            "ws": None,
            "running": True
        }
        
        t = threading.Thread(target=start_bot, args=(token, guild_id, ch_id, bot_info), daemon=True)
        bot_info["thread"] = t
        user_active_bots[username][token] = bot_info
        t.start()
        time.sleep(1.5)

    return redirect(url_for('home'))

@app.route('/stop', methods=['POST'])
def stop_bot():
    if 'username' not in session:
        return redirect(url_for('login'))
        
    username = session['username']
    token = request.form.get('token')
    
    if username in user_active_bots and token in user_active_bots[username]:
        stop_bot_instance(username, token)
        
    return redirect(url_for('home'))

def stop_bot_instance(username, token):
    """Menghentikan bot milik user tertentu berdasarkan token"""
    if username in user_active_bots and token in user_active_bots[username]:
        user_active_bots[username][token]["running"] = False
        ws = user_active_bots[username][token].get("ws")
        if ws:
            try:
                ws.close()
            except Exception:
                pass
        del user_active_bots[username][token]
        print(Fore.RED + f"[System] User '{username}' menghentikan bot {token[:15]}...")

# --- Logika Bot Discord ---
def start_bot(token, guild_id, channel_id, bot_info):
    index_name = token[:10] + "..."
    
    while bot_info.get("running", True):
        seq_num = [None]
        
        def send_chat_reply(msg_channel_id, message_text):
            url = f"https://discord.com/api/v10/channels/{msg_channel_id}/messages"
            headers = {
                "Authorization": token,
                "Content-Type": "application/json"
            }
            payload = {"content": message_text}
            try:
                res = requests.post(url, headers=headers, json=payload)
                if res.status_code == 200:
                    print(Fore.GREEN + f"[{index_name}] Berhasil membalas '{message_text}'.")
                else:
                    print(Fore.RED + f"[{index_name}] Gagal membalas pesan: {res.status_code}")
            except Exception as e:
                print(Fore.RED + f"[{index_name}] Error pengiriman: {e}")

        def on_message(ws, message):
            data = json.loads(message)
            op = data.get("op")
            t = data.get("t")
            d = data.get("d")
            
            if data.get("s") is not None:
                seq_num[0] = data.get("s")

            # AFK Auto Reply
            if t == "MESSAGE_CREATE" and d is not None:
                msg_channel_id = str(d.get("channel_id"))
                
                if msg_channel_id == str(channel_id):
                    content = d.get("content", "").lower()
                    embeds = d.get("embeds", [])
                    
                    full_text = content
                    for embed in embeds:
                        full_text += " " + embed.get("description", "").lower()
                        full_text += " " + embed.get("title", "").lower()
                    
                    keywords = ["hey wake up", "confirm by saying `yes`", "are you still here"]
                    if any(keyword in full_text for keyword in keywords):
                        print(Fore.YELLOW + f"[{index_name}] Peringatan AFK terdeteksi!")
                        time.sleep(2) 
                        threading.Thread(target=send_chat_reply, args=(msg_channel_id, "yes"), daemon=True).start()

            # WebSocket Handshake & Voice Join
            if op == 10:  
                heartbeat_interval = data['d']['heartbeat_interval'] / 1000
                threading.Thread(target=heartbeat_loop, args=(ws, heartbeat_interval), daemon=True).start()
                
                auth_payload = {
                    "op": 2,
                    "d": {
                        "token": token,
                        "properties": {"os": "windows", "browser": "chrome", "device": "pc"}
                    }
                }
                ws.send(json.dumps(auth_payload))

            if t == "READY":
                print(Fore.CYAN + f"[{index_name}] Sesi valid, masuk ke Voice ({channel_id})...")
                voice_payload = {
                    "op": 4,
                    "d": {
                        "guild_id": str(guild_id), 
                        "channel_id": str(channel_id), 
                        "self_mute": False,
                        "self_deaf": False  
                    }
                }
                ws.send(json.dumps(voice_payload))
                print(Fore.GREEN + f"[{index_name}] Berhasil masuk ke Voice Channel {channel_id}.")

        def heartbeat_loop(ws, interval):
            while bot_info.get("running", True):
                time.sleep(interval)
                try:
                    ws.send(json.dumps({"op": 1, "d": seq_num[0]}))
                except:
                    break 

        def on_close(ws, close_status_code, close_msg):
            if bot_info.get("running", True):
                print(Fore.RED + f"[{index_name}] Terputus. Reconnect dalam 5 detik...")
            
        def on_error(ws, error):
            pass 

        ws = websocket.WebSocketApp("wss://gateway.discord.gg/?v=10&encoding=json",
                                    on_message=on_message,
                                    on_close=on_close, 
                                    on_error=on_error)
        bot_info["ws"] = ws
        ws.run_forever()
        
        if not bot_info.get("running", True):
            break
            
        time.sleep(5)

# --- Eksekusi Server ---
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    print(f"Server berjalan di http://0.0.0.0:{port}")
    app.run(host='0.0.0.0', port=port)
