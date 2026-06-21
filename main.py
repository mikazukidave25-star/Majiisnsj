import os
import time
import threading
import json
import websocket
from colorama import Fore, init
import sys
from flask import Flask

# ----------------- Dummy Web Server untuk Render -----------------
# Render mewajibkan Web Service memiliki server yang listen ke PORT
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot Voice Joiner Sedang Berjalan!"

def run_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# ----------------- Inisialisasi -----------------
init(autoreset=True)

print("=================================================")
print("MULTI TOKEN VOICE JOINER (RENDER.COM EDITION)")
print("=================================================")

# Jalankan Flask Server di background thread
threading.Thread(target=run_server, daemon=True).start()

# ----------------- Ambil Token -----------------
try:
    with open("token.txt", "r") as f:
        tokens = [line.strip() for line in f if line.strip()]
except FileNotFoundError:
    print(Fore.RED + "File token.txt tidak ditemukan!")
    exit()

if not tokens:
    print(Fore.RED + "Token tidak ditemukan di dalam token.txt!")
    exit()

# ----------------- Input via Environment Variables -----------------
# Menggantikan input() manual karena Render tidak mendukung terminal interaktif
guild_id = os.environ.get("GUILD_ID")
channel_id = os.environ.get("CHANNEL_ID")

if not guild_id or not channel_id:
    print(Fore.RED + "GAGAL: GUILD_ID atau CHANNEL_ID belum disetting di Environment Variables Render!")
    exit()

# ----------------- Fungsi Join Voice -----------------
def start_bot(token, index):
    while True:
        seq_num = [None]
        
        def on_message(ws, message):
            data = json.loads(message)
            op = data.get("op")
            
            if data.get("s") is not None:
                seq_num[0] = data.get("s")

            if op == 10:  
                heartbeat_interval = data['d']['heartbeat_interval'] / 1000
                threading.Thread(target=heartbeat_loop, args=(ws, heartbeat_interval), daemon=True).start()

        def heartbeat_loop(ws, interval):
            while True:
                time.sleep(interval)
                try:
                    payload = {"op": 1, "d": seq_num[0]}
                    ws.send(json.dumps(payload))
                except:
                    break 

        def on_open(ws):
            auth_payload = {
                "op": 2,
                "d": {
                    "token": token,
                    "properties": {
                        "$os": "windows",
                        "$browser": "chrome",
                        "$device": "pc"
                    }
                }
            }
            ws.send(json.dumps(auth_payload))
            
            time.sleep(1)
            
            voice_payload = {
                "op": 4,
                "d": {
                    "guild_id": 725672802254061601,
                    "channel_id": 1518195225489834095,
                    "self_mute": False,
                    "self_deaf": False
                 
                }
            }
            ws.send(json.dumps(voice_payload))
            print(Fore.GREEN + f"[Token {index+1}] Berhasil masuk ke Voice Channel.")

        def on_close(ws, close_status_code, close_msg):
            print(Fore.RED + f"[Token {index+1}] Terputus. Mencoba reconnect dalam 5 detik...")
            
        def on_error(ws, error):
            pass 

        ws = websocket.WebSocketApp("wss://gateway.discord.gg/?v=9&encoding=json",
                                    on_open=on_open,
                                    on_message=on_message,
                                    on_close=on_close,
                                    on_error=on_error)
        
        ws.run_forever()
        time.sleep(5)

# ----------------- Eksekusi Multi Token -----------------
for i, token in enumerate(tokens):
    threading.Thread(target=start_bot, args=(token, i), daemon=True).start()
    time.sleep(2) 

print(Fore.YELLOW + "\nSemua token sedang diproses. Bot standby di Voice Channel.")

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print(Fore.CYAN + "\nProgram dihentikan.")
    exit()
