import os
import time
import threading
import json
import websocket
import requests
from colorama import Fore, init
from flask import Flask, request, render_template_string

# --- Inisialisasi ---
init(autoreset=True)
app = Flask(__name__)

# Menyimpan status thread/bot agar tidak dijalankan berkali-kali secara tidak sengaja
active_threads = []
is_running = False

# HTML Template Sederhana
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Discord Voice Joiner & AFK Bot</title>
    <style>
        body { font-family: Arial, sans-serif; background-color: #1e1e2e; color: #cdd6f4; padding: 20px; }
        .container { max-width: 600px; margin: auto; background: #313244; padding: 25px; border-radius: 10px; box-shadow: 0 4px 10px rgba(0,0,0,0.3); }
        h2 { color: #89b4fa; text-align: center; }
        label { font-weight: bold; display: block; margin-top: 15px; }
        input, textarea { width: 100%; padding: 10px; margin-top: 5px; border-radius: 5px; border: 1px solid #45475a; background-color: #181825; color: #cdd6f4; box-sizing: border-box; }
        button { width: 100%; background: #a6e3a1; color: #11111b; border: none; padding: 12px; margin-top: 20px; font-weight: bold; border-radius: 5px; cursor: pointer; }
        button:hover { background: #94e2d5; }
        .status { margin-top: 15px; padding: 10px; border-radius: 5px; text-align: center; }
        .active { background: #254636; color: #a6e3a1; }
    </style>
</head>
<body>
    <div class="container">
        <h2>Control Panel Bot Voice</h2>
        {% if is_running %}
            <div class="status active">Status: Bot Sedang Berjalan!</div>
        {% endif %}
        <form method="POST" action="/start">
            <label for="tokens">Token Discord (Satu token per baris):</label>
            <textarea id="tokens" name="tokens" rows="5" placeholder="Masukkan token di sini..." required></textarea>
            
            <label for="guild_id">Server / Guild ID:</label>
            <input type="text" id="guild_id" name="guild_id" placeholder="Contoh: 123456789012345678" required>
            
            <label for="channel_id">Voice Channel ID:</label>
            <input type="text" id="channel_id" name="channel_id" placeholder="Contoh: 987654321098765432" required>
            
            <button type="submit">Jalankan Bot</button>
        </form>
    </div>
</body>
</html>
"""

# --- Route Web Server ---
@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE, is_running=is_running)

@app.route('/start', methods=['POST'])
def start_bots():
    global is_running
    
    # Ambil data dari form web
    raw_tokens = request.form.get('tokens', '')
    guild_id = request.form.get('guild_id', '').strip()
    channel_id = request.form.get('channel_id', '').strip()
    
    # Parsing token menjadi list
    tokens = [t.strip() for t in raw_tokens.splitlines() if t.strip()]
    
    if not tokens or not guild_id or not channel_id:
        return "Gagal: Harap isi semua kolom!", 400

    # Jalankan bot untuk setiap token
    is_running = True
    for i, token in enumerate(tokens):
        t = threading.Thread(target=start_bot, args=(token, guild_id, channel_id, i), daemon=True)
        t.start()
        active_threads.append(t)
        time.sleep(2)

    return render_template_string(HTML_TEMPLATE, is_running=is_running)

# --- Logika Bot Discord ---
def start_bot(token, guild_id, channel_id, index):
    while True:
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
                    print(Fore.GREEN + f"[Token {index+1}] Berhasil membalas '{message_text}'.")
                else:
                    print(Fore.RED + f"[Token {index+1}] Gagal membalas pesan: {res.status_code}")
            except Exception as e:
                print(Fore.RED + f"[Token {index+1}] Error pengiriman: {e}")

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
                        print(Fore.YELLOW + f"[Token {index+1}] Peringatan AFK terdeteksi!")
                        time.sleep(2) 
                        threading.Thread(target=send_chat_reply, args=(msg_channel_id, "yes"), daemon=True).start()

            # Gateway Handshake & Voice Join
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
                print(Fore.CYAN + f"[Token {index+1}] Sesi valid, mencoba masuk Voice...")
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
                print(Fore.GREEN + f"[Token {index+1}] Sinyal masuk Voice Channel dikirim.")

        def heartbeat_loop(ws, interval):
            while True:
                time.sleep(interval)
                try:
                    ws.send(json.dumps({"op": 1, "d": seq_num[0]}))
                except:
                    break 

        def on_close(ws, close_status_code, close_msg):
            print(Fore.RED + f"[Token {index+1}] Terputus. Reconnect 5 detik...")
            
        def on_error(ws, error):
            pass 

        ws = websocket.WebSocketApp("wss://gateway.discord.gg/?v=10&encoding=json",
                                    on_message=on_message,
                                    on_close=on_close, 
                                    on_error=on_error)
        ws.run_forever()
        time.sleep(5)

# --- Eksekusi Server ---
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    print(f"Server berjalan di http://0.0.0.0:{port}")
    app.run(host='0.0.0.0', port=port)
