import os
import time
import random
import requests
import threading
from datetime import datetime
from colorama import Fore, init
import re
import base64
from http.server import BaseHTTPRequestHandler, HTTPServer

# ----------------- KONFIGURASI UTAMA -----------------
YESCAPTCHA_CLIENT_KEY = "4833cd9be06f143f76fc531a5312404bbdb09dc0100535"

# ⚠️ UBAH BAGIAN INI: MASUKKAN ID CHANNEL DISCORD KAMU! ⚠️
channel_id = "1293476303789494304" 

init(autoreset=True)
start_dt = datetime.now()

UA_LIST = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
]

colors = [Fore.CYAN, Fore.GREEN, Fore.MAGENTA, Fore.BLUE, Fore.YELLOW]

# ----------------- Server Web Mini (Wajib untuk Render) -----------------
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
    print(Fore.GREEN + f"✔ Web Server Render berjalan di port {port}")
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

if not tokens:
    print(Fore.RED + "Data token.txt kosong! Bot dihentikan.")
    exit()

lock = threading.Lock()
pause_spam = False
counters = {f"Token {i+1}": 0 for i in range(len(tokens))}
sapphire_counters = {f"Token {i+1}": 0 for i in range(len(tokens))}

# Variabel untuk fitur !ganti satu putaran
custom_message = None
custom_message_sent_by = set()

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
        return None, "API Key YesCaptcha kosong"
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
                return re.sub(r'[^A-Za-z0-9]', '', r.json().get("solution", {}).get("text", "")).upper(), None
    except: pass
    return None, "Timeout/Error YesCaptcha"

# ----------------- MATA BOT (Pendeteksi Chat & Captcha) -----------------
def get_target_token(msg, full_text=""):
    global last_sent_token
    for user in msg.get("mentions", []):
        if str(user.get("id")) in token_info: return token_info[str(user.get("id"))]
    for uid in re.findall(r'<@!?(\d+)>', full_text):
        if uid in token_info: return token_info[uid]
    return last_sent_token

def extract_sapphire(msg):
    text = msg.get("content", "") or (msg["embeds"][0].get("description", "") if msg.get("embeds") else "")
    match = re.search(r'(?:<a?:[a-zA-Z0-9_]+:\d+>|💎|🔷)\s*([\d,\.]+)', text) or re.search(r'([\d,\.]+)\s*sapphire', text, re.IGNORECASE)
    return int(match.group(1).replace(",", "").replace(".", "")) if match else 0

def listen_channel():
    global custom_message, custom_message_sent_by, pause_spam
    headers = {"Authorization": tokens[0], "User-Agent": random.choice(UA_LIST)}
    last_id = None
    UNBELIEVABOAT_ID = "292953664492929025"
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
                    full_txt = content + " " + (msg["embeds"][0].get("description", "") if msg.get("embeds") else "")
                    
                    # 1. PERINTAH !ganti (1 putaran)
                    if content.startswith("!ganti "):
                        with lock:
                            custom_message = content.replace("!ganti ", "", 1).strip()
                            custom_message_sent_by.clear() # Reset data pelacakan
                        print(Fore.CYAN + f"⚙ Perintah Diterima: Pesan '{custom_message}' ditambahkan untuk 1 putaran.")
                    
                    # 2. PERINTAH !data (Cek Sapphire)
                    elif content.strip() == "!data":
                        print(Fore.CYAN + "⚙ Perintah Diterima: Mengirim laporan Sapphire ke channel.")
                        msg_data = "📊 **Laporan Sapphire Saat Ini:**\n"
                        for t, amt in sapphire_counters.items():
                            msg_data += f"> **{t}**: {amt:,} 💎\n"
                        try:
                            # Token 1 akan membalas pesan !data tersebut
                            requests.post(f"https://discord.com/api/v9/channels/{channel_id}/messages", 
                                          json={'content': msg_data}, headers=headers, timeout=10)
                        except: pass
                        
                    # 3. MENDATA SAPPHIRE
                    elif a_id == UNBELIEVABOAT_ID:
                        amt = extract_sapphire(msg)
                        if amt > 0:
                            target = get_target_token(msg, full_txt)
                            sapphire_counters[target] += amt
                            print(Fore.GREEN + f"💰 [{target}] +{amt:,} Sapphire (Total: {sapphire_counters[target]:,})")
                    
                    # 4. DETEKSI CAPTCHA
                    elif a_id == MOTHICA_ID:
                        target = get_target_token(msg, full_txt)
                        pause_spam = True
                        print(Fore.YELLOW + f"🔒 [Mothica] Captcha muncul untuk {target}! Menjeda spam...")
                        
                        img_url = msg["attachments"][0]["url"] if msg.get("attachments") else (msg["embeds"][0].get("image", {}).get("url") if msg.get("embeds") else None)
                        ans = None
                        
                        if img_url:
                            print(Fore.MAGENTA + f"⏳ [YesCaptcha] Memecahkan gambar...")
                            ans, err = solve_image_captcha(img_url)
                        else:
                            m = re.search(r'(\d+)\s*([\+\-\*])\s*(\d+)', full_txt)
                            if m:
                                n1, op, n2 = int(m.group(1)), m.group(2), int(m.group(3))
                                ans = n1+n2 if op=='+' else (n1-n2 if op=='-' else n1*n2)
                        
                        if ans:
                            time.sleep(random.uniform(1.5, 3.0))
                            try:
                                t_headers = {'Authorization': token_strings[target], 'User-Agent': random.choice(UA_LIST)}
                                requests.post(f"https://discord.com/api/v9/channels/{channel_id}/typing", headers=t_headers, timeout=5)
                                time.sleep(random.uniform(1.0, 2.0))
                                requests.post(f"https://discord.com/api/v9/channels/{channel_id}/messages", json={'content': str(ans)}, headers=t_headers, timeout=10)
                                print(Fore.GREEN + f"✔ [{target}] Captcha Sukses Terjawab: {ans}")
                            except: pass
                        
                        time.sleep(4)
                        pause_spam = False
        except: pass
        time.sleep(2)

# ----------------- Loop Spammer Per Akun -----------------
def run_spammer_akun(idx, token):
    global last_sent_token, custom_message, custom_message_sent_by
    t_name = f"Token {idx+1}"
    color = colors[idx % len(colors)]
    
    # Stagger Start: Memisahkan jarak mulai antar akun
    time.sleep(idx * (30.0 / max(1, len(tokens)))) 
    
    while True:
        if pause_spam:
            time.sleep(1)
            continue
            
        headers = {'Authorization': token, 'Content-Type': 'application/json', 'User-Agent': random.choice(UA_LIST)}
        
        try:
            # 1. TRIGGER TYPING
            requests.post(f"https://discord.com/api/v9/channels/{channel_id}/typing", headers=headers, timeout=5)
            
            # 2. JEDA TYPING (0,5 Detik)
            time.sleep(0.5)
            
            if not pause_spam:
                is_custom_msg = False
                
                with lock:
                    # Tentukan pesan apa yang akan dikirim (Custom 1 putaran atau Random normal)
                    if custom_message and t_name not in custom_message_sent_by:
                        msg_send = custom_message
                        is_custom_msg = True
                    else:
                        msg_send = random.choice(words) if words else "Bot Active"
                
                # 3. KIRIM PESAN
                r = requests.post(f"https://discord.com/api/v9/channels/{channel_id}/messages", json={'content': msg_send}, headers=headers, timeout=10)
                
                now = datetime.now().strftime("%H:%M:%S")
                if r.status_code in [200, 201]:
                    counters[t_name] += 1
                    last_sent_token = t_name
                    print(color + f"[{now}] 🚀 {t_name} | Pesan ke-{counters[t_name]} Terkirim")
                    
                    # Jika berhasil mengirim pesan custom, catat akun ini
                    if is_custom_msg:
                        with lock:
                            custom_message_sent_by.add(t_name)
                            # Cek apakah SEMUA akun sudah mengirim pesan custom
                            if len(custom_message_sent_by) >= len(tokens):
                                print(Fore.CYAN + "🔄 Semua token selesai mengirim pesan !ganti. Kembali ke mode acak normal.")
                                custom_message = None
                                custom_message_sent_by.clear()
                                
                elif r.status_code == 429:
                    retry_after = r.json().get("retry_after", 5)
                    print(Fore.YELLOW + f"⚠️ [{t_name}] Rate Limit! Istirahat {retry_after}s")
                    time.sleep(retry_after)
                else:
                    print(Fore.RED + f"✖ [{t_name}] Error {r.status_code}: Gagal kirim.")
        except:
            print(Fore.RED + f"⚠️ [{t_name}] Gangguan jaringan.")
        
        # 4. JEDA WAJIB 30 DETIK + ACAK (0,5 - 3 detik)
        sleep_interval = 30.0 + random.uniform(0.5, 3.0)
        elapsed = 0
        
        while elapsed < sleep_interval:
            if pause_spam:
                time.sleep(1)
                continue
            time.sleep(0.5)
            elapsed += 0.5

# --- Eksekusi Utama ---
if tokens:
    threading.Thread(target=listen_channel, daemon=True).start()
    
    for i, tkn in enumerate(tokens):
        threading.Thread(target=run_spammer_akun, args=(i, tkn), daemon=True).start()
    
    while True:
        time.sleep(10)
