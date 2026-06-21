import os
import time
import threading
import json
import websocket
from colorama import Fore, init
from flask import Flask

# --- Dummy Web Server ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot Voice Joiner Sedang Berjalan!"

def run_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# --- Inisialisasi ---
init(autoreset=True)
print("=================================================")
print("MULTI TOKEN VOICE JOINER (RENDER.COM EDITION)")
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
        
        def on_message(ws, message):
            data = json.loads(message)
            op = data.get("op")
            t = data.get("t") # Event type
            
            if data.get("s") is not None:
                seq_num[0] = data.get("s")

            # Opcode 10: Sinyal HELLO pertama dari Discord
            if op == 10:  
                heartbeat_interval = data['d']['heartbeat_interval'] / 1000
                threading.Thread(target=heartbeat_loop, args=(ws, heartbeat_interval), daemon=True).start()
                
                # Kirim perintah Login (Identify) SETELAH menerima Hello
                auth_payload = {
                    "op": 2,
                    "d": {
                        "token": token,
                        "properties": {"os": "windows", "browser": "chrome", "device": "pc"}
                    }
                }
                ws.send(json.dumps(auth_payload))

            # Event READY: Sinyal bahwa Login telah berhasil diproses oleh Discord
            if t == "READY":
                print(Fore.CYAN + f"[Token {index+1}] Sesi divalidasi, mencoba masuk Voice...")
                voice_payload = {
                    "op": 4,
                    "d": {
                        "guild_id": str(guild_id),     # Dipaksa menjadi string agar Discord bisa membaca format ID yang panjang
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

        # Menggunakan Discord Gateway API v10 (Terbaru)
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
