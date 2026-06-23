import os
import time
import threading
import json
import websocket
import requests
from colorama import Fore, init
from flask import Flask

# --- Dummy Web Server ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot Voice Joiner & Auto-Reply AFK Sedang Berjalan!"

def run_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# --- Inisialisasi ---
init(autoreset=True)
print("=================================================")
print("MULTI TOKEN VOICE JOINER & AFK AUTO-REPLY")
print("=================================================")

threading.Thread(target=run_server, daemon=True).start()

# --- Ambil Token ---
try:
    with open("token.txt", "r") as f:
        tokens = [line.strip() for line in f if line.strip()]
except FileNotFoundError:
    print(Fore.RED + "File token.txt tidak ditemukan!")
    exit()

if not tokens:
    print(Fore.RED + "Token kosong!")
    exit()

# --- Ambil ID dari Environment Variables ---
guild_id = os.environ.get("GUILD_ID")
channel_id = os.environ.get("CHANNEL_ID")

if not guild_id or not channel_id:
    print(Fore.RED + "GAGAL: GUILD_ID atau CHANNEL_ID belum disetting di Render!")
    exit()

# --- Fungsi Bot ---
def start_bot(token, index):
    while True:
        seq_num = [None]
        
        # Fungsi HTTP POST untuk mengirim pesan teks
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
                    print(Fore.GREEN + f"[Token {index+1}] Berhasil membalas '{message_text}' ke bot musik.")
                else:
                    print(Fore.RED + f"[Token {index+1}] Gagal membalas pesan, status: {res.status_code}")
            except Exception as e:
                print(Fore.RED + f"[Token {index+1}] Error pengiriman: {e}")

        def on_message(ws, message):
            data = json.loads(message)
            op = data.get("op")
            t = data.get("t") # Event type
            d = data.get("d") # Data payload
            
            if data.get("s") is not None:
                seq_num[0] = data.get("s")

            # --- FITUR AUTO REPLY ---
            # Jika ada pesan baru masuk di server
            if t == "MESSAGE_CREATE" and d is not None:
                content = d.get("content", "").lower()
                embeds = d.get("embeds", [])
                msg_channel_id = d.get("channel_id")
                
                # Gabungkan teks biasa dengan teks di dalam embed (kotak pesan bot)
                full_text = content
                for embed in embeds:
                    full_text += " " + embed.get("description", "").lower()
                    full_text += " " + embed.get("title", "").lower()
                
                # Deteksi jika pesan berisi kata kunci AFK Check
                keywords = ["hey wake up", "confirm by saying `yes`", "are you still here"]
                if any(keyword in full_text for keyword in keywords):
                    print(Fore.YELLOW + f"[Token {index+1}] Peringatan AFK dari bot terdeteksi!")
                    # Gunakan thread agar koneksi utama websocket tidak terhambat
                    time.sleep(2) # Beri jeda 2 detik agar terlihat lebih natural (seperti manusia mengetik)
                    threading.Thread(target=send_chat_reply, args=(msg_channel_id, "yes"), daemon=True).start()

            # --- KONEKSI WEBSOCKET ---
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
                print(Fore.CYAN + f"[Token {index+1}] Sesi divalidasi, mencoba masuk Voice...")
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
                print(Fore.GREEN + f"[Token {index+1}] Berhasil mengirim sinyal masuk ke Voice Channel.")

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

# --- Eksekusi ---
for i, token in enumerate(tokens):
    threading.Thread(target=start_bot, args=(token, i), daemon=True).start()
    time.sleep(3) 

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    exit()
