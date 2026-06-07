import os
import time
import random
import requests
import threading
from datetime import datetime
from colorama import init, Fore
import re
import base64
from http.server import BaseHTTPRequestHandler, HTTPServer

# ----------------- KONFIGURASI UTAMA -----------------
YESCAPTCHA_CLIENT_KEY = "4833cd9be06f143f76fc531a5312404bbdb09dc0100535"

# ⚠️ UBAH BAGIAN INI: MASUKKAN ID CHANNEL DISCORD KAMU! ⚠️
channel_id = "1502243644281720933" 

init(autoreset=True)
start_dt = datetime.now()

UA_LIST = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
]

# ----------------- Server Pancingan Render -----------------
class RenderKeepAliveHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Bot is online on Render.com!")
    def log_message(self, format, *args):
        pass

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), RenderKeepAliveHandler)
    print(Fore.GREEN + f"✔ Web Server internal berjalan di port {port}")
    server.serve_forever()

threading.Thread(target=run_web_server, daemon=True).start()

# ----------------- Load Data -----------------
def load_file(filename, default_val):
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip()]
    return default_val

words = load_file("pesan.txt", ["Halo ini pesan otomatis"])
tokens = load_file("token.txt", [])

lock = threading.Lock()
pause_spam = False
counters = {f"Token {i+1}": 0 for i in range(len(tokens))}
current_message = random.choice(words) if words else "Bot Active"
token_info = {}
token_strings = {}
last_sent_token = "Token 1"

# ----------------- Verifikasi Token -----------------
print(Fore.YELLOW + "⏳ Memulai sistem dan memverifikasi token...")
for i, token in enumerate(tokens):
    t_name = f"Token {i+1}"
    token_strings[t_name] = token
    try:
        r = requests.get("https://discord.com/api/v9/users/@me", headers={"Authorization": token, "User-Agent": random.choice(UA_LIST)}, timeout=10)
        if r.status_code == 200:
            data = r.json()
            token_info[str(data["id"])] = t_name
            print(Fore.GREEN + f"✔ [{t_name}] Terhubung: {data['username']}")
        else:
            print(Fore.RED + f"✖ [{t_name}] Invalid! Status: {r.status_code}")
    except Exception:
        print(Fore.RED + f"✖ [{t_name}] Error koneksi awal.")

# ----------------- YESCAPTCHA SOLVER -----------------
def solve_image_captcha(image_url):
    if not YESCAPTCHA_CLIENT_KEY or "MASUKKAN" in YESCAPTCHA_CLIENT_KEY:
        return None
    try:
        img_resp = requests.get(image_url, headers={'User-Agent': random.choice(UA_LIST)}, timeout=15)
        img_base64 = base64.b64encode(img_resp.content).decode('utf-8')
        res = requests.post("https://api.yescaptcha.com/createTask", json={"clientKey": YESCAPTCHA_CLIENT_KEY, "task": {"type": "ImageToTextTask", "body": img_base64}}, timeout=15)
        task_id = res.json().get("taskId")
        
        start_poll = time.time()
        while time.time() - start_poll < 15:
            time.sleep(1.5)
            r = requests.post("https://api.yescaptcha.com/getTaskResult", json={"clientKey": YESCAPTCHA_CLIENT_KEY, "taskId": task_id}, timeout=10)
            if r.json().get("status") == "ready":
                return re.sub(r'[^A-Za-z0-9]', '', r.json().get("solution", {}).get("text", "")).upper()
    except: pass
    return None

# ----------------- MATA BOT (Pendeteksi Chat & Captcha) -----------------
def get_target_token(msg, full_text=""):
    global last_sent_token
    for user in msg.get("mentions", []):
        if str(user.get("id")) in token_info: return token_info[str(user.get("id"))]
    for uid in re.findall(r'<@!?(\d+)>', full_text):
        if uid in token_info: return token_info[uid]
    return last_sent_token

def listen_channel():
    global current_message, pause_spam
    if not tokens: return
    headers = {"Authorization": tokens[0], "User-Agent": random.choice(UA_LIST)}
    last_id = None
    MOTHICA_ID = "1357551261494415431"

    while True:
        try:
            r = requests.get(f"https://discord.com/api/v9/channels/{channel_id}/messages?limit=10", headers=headers, timeout=10)
            if r.status_code == 200:
                msgs = r.json()
                if last_id is None:
                    if msgs: last_id = int(msgs[0]["id"])
                    time.sleep(2)
                    continue
                new_msgs = [m for m in msgs if int(m["id"]) > last_id]
                new_msgs.sort(key=lambda x: int(x["id"]))
                
                for msg in new_msgs:
                    last_id = int(msg["id"])
                    content = msg.get("content", "")
                    a_id = str(msg.get("author", {}).get("id", ""))
                    
                    # 1. Fitur Ganti Pesan
                    if content.startswith("!ganti "):
                        current_message = content.replace("!ganti ", "", 1).strip()
                        print(Fore.CYAN + f"⚙ Perintah Diterima: Pesan diubah menjadi -> {current_message}")
                    
                    # 2. Fitur Deteksi Captcha Mothica
                    elif a_id == MOTHICA_ID:
                        target = get_target_token(msg, content)
                        pause_spam = True
                        print(Fore.YELLOW + f"🔒 [Mothica] Captcha muncul untuk {target}! Menjeda aktivitas spam...")
                        
                        img_url = msg["attachments"][0]["url"] if msg.get("attachments") else (msg["embeds"][0].get("image", {}).get("url") if msg.get("embeds") else None)
                        
                        ans = None
                        if img_url:
                            print(Fore.YELLOW + f"⏳ Meminta YesCaptcha memecahkan gambar...")
                            ans = solve_image_captcha(img_url)
                        
                        if ans:
                            time.sleep(random.uniform(1.5, 3.0))
                            try:
                                t_headers = {'Authorization': token_strings[target], 'User-Agent': random.choice(UA_LIST)}
                                requests.post(f"https://discord.com/api/v9/channels/{channel_id}/typing", headers=t_headers, timeout=5)
                                time.sleep(random.uniform(1.0, 2.0))
                                requests.post(f"https://discord.com/api/v9/channels/{channel_id}/messages", json={'content': str(ans)}, headers=t_headers, timeout=10)
                                print(Fore.GREEN + f"✔ [{target}] Captcha Sukses Terjawab: {ans}")
                            except: pass
                        
                        # Tunggu sebentar sebelum melanjutkan spam
                        time.sleep(4)
                        pause_spam = False
        except: pass
        
        # Jeda refresh mata bot setiap 2 detik
        time.sleep(2)

# ----------------- Loop Spammer Per Akun -----------------
def run_spammer_akun(idx, token):
    global last_sent_token
    t_name = f"Token {idx+1}"
    time.sleep(idx * (33.0 / max(1, len(tokens)))) 
    
    while True:
        if pause_spam:
            time.sleep(2)
            continue
            
        headers = {'Authorization': token, 'Content-Type': 'application/json', 'User-Agent': random.choice(UA_LIST)}
        
        try:
            requests.post(f"https://discord.com/api/v9/channels/{channel_id}/typing", headers=headers, timeout=5)
            time.sleep(random.uniform(0.5, 1.5))
            
            if not pause_spam:
                with lock:
                    msg_send = random.choice(words) if words else current_message
                
                r = requests.post(f"https://discord.com/api/v9/channels/{channel_id}/messages", json={'content': msg_send}, headers=headers, timeout=10)
                
                if r.status_code in [200, 201]:
                    counters[t_name] += 1
                    last_sent_token = t_name
                    print(Fore.CYAN + f"🚀 [{t_name}] Pesan Terkirim ({counters[t_name]})")
                elif r.status_code == 429:
                    retry_after = r.json().get("retry_after", 5)
                    print(Fore.YELLOW + f"⚠️ [{t_name}] Rate Limit! Istirahat {retry_after}s")
                    time.sleep(retry_after)
                else:
                    print(Fore.RED + f"✖ [{t_name}] Error {r.status_code}: Gagal kirim.")
        except:
            print(Fore.RED + f"⚠️ [{t_name}] Gangguan jaringan.")
        
        time.sleep(31.0 + random.uniform(1.0, 3.5))

# --- Eksekusi Utama ---
if tokens:
    # Nyalakan thread Mata Bot
    threading.Thread(target=listen_channel, daemon=True).start()
    
    # Nyalakan thread Pengirim Pesan
    for i, tkn in enumerate(tokens):
        threading.Thread(target=run_spammer_akun, args=(i, tkn), daemon=True).start()
    
    while True:
        time.sleep(10)
