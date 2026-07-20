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

# --- TOKEN UNIVERSAL ---
# Masukkan Token Universal Anda di sini (Akun ini yang akan Join -> Verif Yes -> Leave)
UNIVERSAL_TOKEN = "ISI_TOKEN_UNIVERSAL_DI_SINI"

# Database sederhana di memori untuk menyimpan akun web
USERS_DB = {
    "admin": "admin123"  
}

# Kamus untuk menyimpan data bot aktif per User
user_active_bots = {}

# --- SISTEM ANTI-SPAM (BERDASARKAN ID PESAN) ---
processed_afk_messages = []
message_lock = threading.Lock()

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
            document.getElementById("single_channel_sec").style.display = "none";
            document.getElementById("multi_channel_sec").style.display = "none";
            document.getElementById("verify_only_sec").style.display = "none";

            if (mode === "single") {
                document.getElementById("single_channel_sec").style.display = "block";
            } else if (mode === "multi") {
                document.getElementById("multi_channel_sec").style.display = "block";
            } else if (mode === "verify_only") {
                document.getElementById("verify_only_sec").style.display = "block";
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
            <h3>Daftar Bot / Tugas Aktif ({{ my_bots|length }})</h3>
            {% if my_bots %}
                <table class="bot-table">
                    <thead>
                        <tr>
                            <th>Identitas</th>
                            <th>Guild ID</th>
                            <th>Channel ID</th>
                            <th>Mode</th>
                            <th>Aksi</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for bot_id, info in my_bots.items() %}
                        <tr>
                            <td>
                                {% if info.is_verify_only %}
                                    <span style="color: #f9e2af; font-weight:bold;">[Universal]</span><br>Pemantau Chat
                                {% else %}
                                    <span style="color: #89b4fa;">[Tumbal]</span><br>{{ bot_id[:15] }}...
                                {% endif %}
                            </td>
                            <td>{{ info.guild_id }}</td>
                            <td>{{ info.channel_id }}</td>
                            <td>{{ 'Hanya Verif' if info.is_verify_only else 'Stay di Voice' }}</td>
                            <td>
                                <form method="POST" action="/stop" style="margin:0;">
                                    <input type="hidden" name="bot_id" value="{{ bot_id }}">
                                    <button type="submit" class="btn-delete">Stop</button>
                                </form>
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            {% else %}
                <p style="text-align: center; color: #a6adc8;">Belum ada tugas yang dijalankan.</p>
            {% endif %}
        </div>

        <div class="card">
            <h3>Tambah Tugas Baru</h3>
            <form method="POST" action="/start">
                
                <label for="guild_id">Server / Guild ID:</label>
                <input type="text" id="guild_id" name="guild_id" placeholder="Contoh: 123456789012345678" required>

                <label for="mode">Pilih Mode Eksekusi:</label>
                <select id="mode" name="mode" onchange="toggleMode()">
                    <option value="single">Bot Tumbal Stay (1 Voice Channel untuk Semua Token)</option>
                    <option value="multi">Bot Tumbal Stay (Voice Channel Berbeda per Token)</option>
                    <option value="verify_only">Hanya Verifikasi (Tanpa Tumbal, Hanya Input Channel ID)</option>
                </select>

                <!-- MODE SINGLE -->
                <div id="single_channel_sec">
                    <label for="tokens_single">Token Akun Bot Tumbal (Satu token per baris):</label>
                    <textarea id="tokens_single" name="tokens_single" rows="4" placeholder="TokenBot1&#10;TokenBot2"></textarea>
                    
                    <label for="channel_id_single">Voice Channel ID:</label>
                    <input type="text" id="channel_id_single" name="channel_id_single" placeholder="Contoh: 987654321098765432">
                </div>

                <!-- MODE MULTI -->
                <div id="multi_channel_sec" style="display: none;">
                    <label for="token_channel_pairs">Pasangan Token & Voice Channel ID:</label>
                    <p class="hint">Format: <code>TOKEN|CHANNEL_ID</code> (Satu per baris)</p>
                    <textarea id="token_channel_pairs" name="token_channel_pairs" rows="5" placeholder="Token1|ChannelID1&#10;Token2|ChannelID2"></textarea>
                </div>

                <!-- MODE HANYA VERIFIKASI -->
                <div id="verify_only_sec" style="display: none; background: #313244; padding: 15px; border-radius: 8px; margin-top: 15px; border: 1px solid #f9e2af;">
                    <label for="channel_id_verify" style="color:#f9e2af; margin-top:0;">Target Voice Channel ID (Tempat Pantau & Verif):</label>
                    <p class="hint" style="color: #cdd6f4;">Pada mode ini, <b>Token Universal</b> akan memantau channel ini di balik layar. Jika peringatan muncul, ia akan otomatis masuk VC -> jawab "yes" -> keluar VC.</p>
                    <input type="text" id="channel_id_verify" name="channel_id_verify" placeholder="Contoh: 987654321098765432">
                </div>

                <button type="submit">Jalankan Eksekusi</button>
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
    if 'username' not in session: return redirect(url_for('login'))
        
    username = session['username']
    guild_id = request.form.get('guild_id', '').strip()
    mode = request.form.get('mode')

    if not guild_id: return "Guild ID wajib diisi!", 400

    entries = [] 

    if mode == 'single':
        raw_tokens = request.form.get('tokens_single', '')
        channel_id = request.form.get('channel_id_single', '').strip()
        tokens = [t.strip() for t in raw_tokens.splitlines() if t.strip()]
        if not tokens or not channel_id: return "Token dan Channel ID wajib diisi!", 400
        for t in tokens:
            entries.append((t, t, channel_id, False))

    elif mode == 'multi':
        pairs_raw = request.form.get('token_channel_pairs', '')
        lines = [line.strip() for line in pairs_raw.splitlines() if line.strip()]
        for line in lines:
            if '|' in line:
                t, c = line.split('|', 1)
                entries.append((t.strip(), t.strip(), c.strip(), False))
            else: return "Format multi-channel salah!", 400

    elif mode == 'verify_only':
        channel_id = request.form.get('channel_id_verify', '').strip()
        if not channel_id: return "Target Channel ID wajib diisi untuk verifikasi!", 400
        bot_id = f"VERIFY_{channel_id}" 
        entries.append((bot_id, UNIVERSAL_TOKEN, channel_id, True))

    if username not in user_active_bots:
        user_active_bots[username] = {}

    for bot_id, real_token, ch_id, is_verify_only in entries:
        if bot_id in user_active_bots[username]:
            stop_bot_instance(username, bot_id)

        bot_info = {
            "guild_id": guild_id,
            "channel_id": ch_id,
            "is_verify_only": is_verify_only,
            "ws": None,
            "running": True
        }
        
        t = threading.Thread(target=start_bot, args=(bot_id, real_token, guild_id, ch_id, bot_info), daemon=True)
        bot_info["thread"] = t
        user_active_bots[username][bot_id] = bot_info
        t.start()
        time.sleep(1.5)

    return redirect(url_for('home'))

@app.route('/stop', methods=['POST'])
def stop_bot():
    if 'username' not in session: return redirect(url_for('login'))
        
    username = session['username']
    bot_id = request.form.get('bot_id')
    stop_bot_instance(username, bot_id)
    return redirect(url_for('home'))

def stop_bot_instance(username, bot_id):
    if username in user_active_bots and bot_id in user_active_bots[username]:
        user_active_bots[username][bot_id]["running"] = False
        ws = user_active_bots[username][bot_id].get("ws")
        if ws:
            try: ws.close()
            except: pass
        del user_active_bots[username][bot_id]
        print(Fore.RED + f"[System] Menghentikan tugas: {bot_id[:15]}...")

# --- Fungsi Bantuan untuk Bot Tumbal (DENGAN JEDA WAKTU YANG DIPERBAIKI) ---
def universal_join_verify_leave(guild_id, channel_id):
    print(Fore.CYAN + "[Universal Temp WS] Masuk untuk mengeksekusi Verifikasi...")
    ws = websocket.WebSocket()
    try:
        ws.connect("wss://gateway.discord.gg/?v=10&encoding=json")
        
        # Menerima paket Hello (OP 10) sebelum mengirim login agar koneksi stabil
        ws.recv()
        
        # Login dengan Token Universal
        ws.send(json.dumps({
            "op": 2, "d": { "token": UNIVERSAL_TOKEN, "properties": {"os": "windows", "browser": "chrome", "device": "pc"} }
        }))
        time.sleep(3) # Tunggu login berhasil
        
        # 1. Join Voice
        ws.send(json.dumps({"op": 4, "d": {"guild_id": str(guild_id), "channel_id": str(channel_id), "self_mute": False, "self_deaf": False}}))
        
        # WAJIB TUNGGU LAMA (5 DETIK) agar status join terdaftar di server Discord sebelum kirim pesan
        time.sleep(5) 
        
        # 2. Reply Pesan (API)
        url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
        res = requests.post(url, headers={"Authorization": UNIVERSAL_TOKEN, "Content-Type": "application/json"}, json={"content": "yes"})
        print(Fore.GREEN + "[Universal Temp WS] Chat terkirim." if res.status_code == 200 else Fore.RED + "[Universal Temp WS] Gagal kirim chat.")
        
        # WAJIB TUNGGU LAMA (4 DETIK) agar bot verifikasi membaca pesan kita saat masih di Voice Channel
        time.sleep(4)
        
        # 3. Leave Voice
        ws.send(json.dumps({"op": 4, "d": {"guild_id": str(guild_id), "channel_id": None, "self_mute": False, "self_deaf": False}}))
        time.sleep(2) 
        
    except Exception as e:
        print(Fore.RED + f"[Universal] Error Join-Verif: {e}")
    finally:
        ws.close()

# --- Logika Inti Bot (Mendukung Tumbal & Hanya Verifikasi) ---
def start_bot(bot_id, real_token, guild_id, channel_id, bot_info):
    is_verify_only = bot_info.get("is_verify_only", False)
    index_name = ("Pemantau" if is_verify_only else bot_id[:10])
    
    while bot_info.get("running", True):
        seq_num = [None]
        
        def on_message(ws, message):
            data = json.loads(message)
            op = data.get("op")
            t = data.get("t")
            d = data.get("d")
            if data.get("s") is not None: seq_num[0] = data.get("s")

            # MENDETEKSI CHAT MASUK
            if t == "MESSAGE_CREATE" and d is not None:
                msg_channel_id = str(d.get("channel_id"))
                msg_id = str(d.get("id")) # Mendapatkan ID Pesan Unik
                
                if msg_channel_id == str(channel_id):
                    content = d.get("content", "").lower()
                    full_text = content + " ".join([emb.get("description", "").lower() + " " + emb.get("title", "").lower() for emb in d.get("embeds", [])])
                    
                    keywords = ["hey wake up", "confirm by saying `yes`", "are you still here"]
                    if any(keyword in full_text for keyword in keywords):
                        
                        # SISTEM PELACAKAN ID PESAN
                        with message_lock:
                            if msg_id not in processed_afk_messages:
                                processed_afk_messages.append(msg_id)
                                if len(processed_afk_messages) > 100:
                                    processed_afk_messages.pop(0)
                                
                                if is_verify_only:
                                    print(Fore.YELLOW + f"[{index_name}] Peringatan AFK! Mengeksekusi verifikasi dari balik layar...")
                                    def execute_direct():
                                        # 1. Join Voice
                                        ws.send(json.dumps({"op": 4, "d": {"guild_id": str(guild_id), "channel_id": str(channel_id), "self_mute": False, "self_deaf": False}}))
                                        
                                        # WAJIB TUNGGU LAMA (5 DETIK)
                                        time.sleep(5)
                                        
                                        # 2. Reply via API
                                        requests.post(f"https://discord.com/api/v10/channels/{channel_id}/messages", 
                                                      headers={"Authorization": real_token, "Content-Type": "application/json"}, 
                                                      json={"content": "yes"})
                                                      
                                        # WAJIB TUNGGU LAMA (4 DETIK)
                                        time.sleep(4)
                                        
                                        # 3. Leave Voice
                                        ws.send(json.dumps({"op": 4, "d": {"guild_id": str(guild_id), "channel_id": None, "self_mute": False, "self_deaf": False}}))
                                        print(Fore.GREEN + f"[{index_name}] Verifikasi selesai. Kembali memantau di balik layar.")
                                    
                                    threading.Thread(target=execute_direct, daemon=True).start()
                                else:
                                    print(Fore.YELLOW + f"[{index_name}] Peringatan AFK! Memanggil Universal Token untuk membalas...")
                                    threading.Thread(target=universal_join_verify_leave, args=(guild_id, msg_channel_id), daemon=True).start()
                            else:
                                print(Fore.MAGENTA + f"[{index_name}] AFK Terdeteksi, tapi sudah dieksekusi tumbal lain. (Skip)")

            # WebSocket Handshake
            if op == 10:  
                threading.Thread(target=heartbeat_loop, args=(ws, data['d']['heartbeat_interval'] / 1000), daemon=True).start()
                ws.send(json.dumps({"op": 2, "d": {"token": real_token, "properties": {"os": "windows", "browser": "chrome", "device": "pc"}}}))

            if t == "READY":
                if is_verify_only:
                    print(Fore.MAGENTA + f"[{index_name}] Sukses! Memantau channel {channel_id} (Tanpa masuk Voice)...")
                else:
                    print(Fore.CYAN + f"[{index_name}] Sukses! Masuk dan nangkring di Voice ({channel_id})...")
                    ws.send(json.dumps({"op": 4, "d": {"guild_id": str(guild_id), "channel_id": str(channel_id), "self_mute": False, "self_deaf": False}}))

        def heartbeat_loop(ws, interval):
            while bot_info.get("running", True):
                time.sleep(interval)
                try: ws.send(json.dumps({"op": 1, "d": seq_num[0]}))
                except: break 

        def on_close(ws, close_status_code, close_msg):
            if bot_info.get("running", True): print(Fore.RED + f"[{index_name}] Terputus. Reconnect dalam 5 detik...")
            
        def on_error(ws, error): pass 

        ws = websocket.WebSocketApp("wss://gateway.discord.gg/?v=10&encoding=json", on_message=on_message, on_close=on_close, on_error=on_error)
        bot_info["ws"] = ws
        ws.run_forever()
        
        if not bot_info.get("running", True): break
        time.sleep(5)

# --- Eksekusi Server ---
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    print(f"Server berjalan di http://0.0.0.0:{port}")
    app.run(host='0.0.0.0', port=port)
