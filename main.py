import os
import time
import random
import requests
import threading
from datetime import datetime
from colorama import Fore, init
import re
from collections import deque
import base64

# ----------------- Banner -----------------
def print_banner():
    print(Fore.GREEN + " __  __    _   _   _ _  ")
    print(Fore.GREEN + "|  \\/  |  / \\ | | | | | ")
    print(Fore.GREEN + "| |\\/| | / _ \\| | | | |    ")
    print(Fore.GREEN + "| |  | |/ ___ \\ |_| | |___ ")
    print(Fore.GREEN + "|_|  |_/_/   \\_\\___/|_____|")
    print(Fore.CYAN + "=================================================")
    print(Fore.YELLOW + "KEBELET BERAK - YESCAPTCHA UNIVERSAL (MOBILE)")
    print(Fore.CYAN + "=================================================\n")

# ----------------- Inisialisasi -----------------
init(autoreset=True)
print_banner()
time.sleep(1)

start_dt = datetime.now()
start_time = start_dt.strftime("%Y-%m-%d %H:%M:%S")

# ----------------- KONFIGURASI YESCAPTCHA -----------------
YESCAPTCHA_CLIENT_KEY = "4833cd9be06f143f76fc531a5312404bbdb09dc0100535"

# ----------------- PENGATURAN OTOMATIS (CLOUD/VPS) -----------------
# ⚠️ SILAKAN UBAH DUA BAGIAN DI BAWAH INI SEBELUM DI-UPLOAD KE GITHUB
channel_id = "MASUKKAN_ID_CHANNEL_DISCORD_KAMU"   # <-- Ganti dengan ID Channel Discord kamu (tetap gunakan tanda kutip)
waktu2 = 5000                                      # <-- Jeda kirim pesan dalam milidetik (contoh: 5000 artinya 5 detik)

for n in [3, 2, 1]:
    print(f"Mulai dalam {n}...")
    time.sleep(1)

# ----------------- Load Data -----------------
with open("pesan.txt", "r", encoding="utf-8") as f:
    words = [line.strip() for line in f if line.strip()]

with open("token.txt", "r") as f:
    tokens = [line.strip() for line in f if line.strip()]

if not words or not tokens:
    print(Fore.RED + "Data pesan.txt atau token.txt kosong!")
    exit()

colors = [Fore.CYAN, Fore.GREEN, Fore.MAGENTA, Fore.BLUE, Fore.YELLOW, Fore.RED]

# ----------------- Global State & Variabel -----------------
lock = threading.Lock()
pause_spam = False
last_sent_token = "Token 1" 

counters = {f"Token {i+1}": 0 for i in range(len(tokens))}
sapphire_counters = {f"Token {i+1}": 0 for i in range(len(tokens))}
logs = deque(maxlen=15)
current_message = random.choice(words)

# ----------------- Verifikasi & Mapping User -----------------
token_info = {}
token_strings = {}

print(Fore.YELLOW + "Memverifikasi token akun...")
for i, token in enumerate(tokens):
    t_name = f"Token {i+1}"
    token_strings[t_name] = token
    try:
        r = requests.get("https://discord.com/api/v9/users/@me", headers={"Authorization": token}, timeout=10)
        if r.status_code == 200:
            data = r.json()
            uid = str(data["id"])
            uname = data["username"]
            gname = data.get("global_name") or uname
            
            token_info[uid] = t_name
            token_info[uname.lower()] = t_name
            if gname:
                token_info[gname.lower()] = t_name
            print(Fore.GREEN + f"✔ [{t_name}] Terhubung: {uname}")
        else:
            print(Fore.RED + f"✖ [{t_name}] Token Invalid/Mati")
    except:
        print(Fore.RED + f"✖ [{t_name}] Error koneksi verifikasi")

time.sleep(2)

# ----------------- FUNGSI SOLVER YESCAPTCHA (POLLING ASYNC) -----------------
def solve_image_captcha(image_url):
    if not YESCAPTCHA_CLIENT_KEY or "MASUKKAN" in YESCAPTCHA_CLIENT_KEY:
        return None, "API Key YesCaptcha belum diisi"

    headers_dl = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    try:
        img_resp = requests.get(image_url, headers=headers_dl, timeout=15)
        if img_resp.status_code != 200:
            return None, f"Gagal unduh gambar (HTTP {img_resp.status_code})"
    except:
        return None, "Koneksi unduh timeout"

    img_base64 = base64.b64encode(img_resp.content).decode('utf-8')
    
    create_url = "https://api.yescaptcha.com/createTask"
    payload_create = {
        "clientKey": YESCAPTCHA_CLIENT_KEY,
        "task": {
            "type": "ImageToTextTask",
            "body": img_base64
        }
    }
    
    try:
        res = requests.post(create_url, json=payload_create, timeout=15)
        data = res.json()
        if data.get("errorId") != 0:
            return None, f"CreateTask Error: {data.get('errorCode', 'UNKNOWN')}"
            
        task_id = data.get("taskId")
        if not task_id:
            return None, "Gagal mendapatkan Task ID dari YesCaptcha"
    except:
        return None, "Koneksi createTask timeout/error"

    result_url = "https://api.yescaptcha.com/getTaskResult"
    payload_result = {
        "clientKey": YESCAPTCHA_CLIENT_KEY,
        "taskId": task_id
    }
    
    start_poll = time.time()
    while time.time() - start_poll < 15: 
        time.sleep(1.5)
        try:
            r = requests.post(result_url, json=payload_result, timeout=10)
            res_data = r.json()
            if res_data.get("errorId") != 0:
                return None, f"GetResult Error: {res_data.get('errorCode', 'UNKNOWN')}"
                
            if res_data.get("status") == "ready":
                raw_answer = res_data.get("solution", {}).get("text", "")
                clean_answer = re.sub(r'[^A-Za-z0-9]', '', raw_answer).upper()
                return clean_answer, None
        except: pass
        
    return None, "Waktu tunggu YesCaptcha habis (timeout)"

# ----------------- Ekstraksi Data Pesan -----------------
def get_target_token(msg, full_text=""):
    global last_sent_token
    for user in msg.get("mentions", []):
        uid = str(user.get("id"))
        if uid in token_info: return token_info[uid]
    
    for uid in re.findall(r'<@!?(\d+)>', full_text):
        if uid in token_info: return token_info[uid]

    if msg.get("embeds"):
        author = msg["embeds"][0].get("author", {})
        m = re.search(r'/avatars/(\d+)/', author.get("icon_url", ""))
        if m and m.group(1) in token_info: return token_info[m.group(1)]
        if author.get("name", "").lower() in token_info: return token_info[author.get("name", "").lower()]

    for key, t_name in token_info.items():
        if not key.isdigit() and key.lower() in full_text.lower():
            return t_name
            
    return last_sent_token

def extract_sapphire(msg):
    text = msg.get("content", "")
    if not text and msg.get("embeds"):
        text = msg["embeds"][0].get("description", "")
    if not text: return 0

    match = re.search(r'(?:<a?:[a-zA-Z0-9_]+:\d+>|💎|🔷)\s*([\d,\.]+)', text)
    if not match:
        match = re.search(r'([\d,\.]+)\s*sapphire', text, re.IGNORECASE)
    if match:
        try: return int(match.group(1).replace(",", "").replace(".", ""))
        except: return 0
    return 0

# ----------------- Runtime & Tampilan -----------------
def get_runtime():
    delta = datetime.now() - start_dt
    hours, remainder = divmod(int(delta.total_seconds()), 3600)
    m, s = divmod(remainder, 60)
    return f"{hours:02}:{m:02}:{s:02}"

def show_screen():
    while True:
        # Dioptimalkan untuk Koyeb Logs: Menghindari penumpukan karakter pembersih layar virtual
        print("\n" + "="*40) 
        runtime = get_runtime()
        status_str = Fore.RED + "PAUSED (Merespons Captcha)" if pause_spam else Fore.GREEN + "RUNNING"
        
        print(Fore.YELLOW + f"=== STATISTIK BOT (CLOUD LOG VIEW) ===")
        print(Fore.CYAN + f"Status : {status_str}")
        print(Fore.CYAN + f"Solver : YesCaptcha Universal")
        print(Fore.CYAN + f"Durasi : {runtime}")
        print(Fore.YELLOW + "-----------------------------------")
        
        total_msgs = 0
        total_saph = 0
        
        for t, count in counters.items():
            saph = sapphire_counters[t]
            avg = saph / count if count > 0 else 0
            total_msgs += count
            total_saph += saph
            print(f"{Fore.GREEN}▶ {t.ljust(8)} {Fore.WHITE}| Pesan: {str(count).ljust(4)} | 💎: {str(saph).ljust(5)}")
            
        print(Fore.YELLOW + "-----------------------------------")
        print(Fore.YELLOW + "[LOG TERBARU]:")
        if logs:
            print(list(logs)[-1]) # Hanya menampilkan log baris terakhir di Cloud agar hemat penyimpanan log
            
        time.sleep(10) # Diperlama menjadi 10 detik agar log tidak membengkak di dashboard Koyeb

threading.Thread(target=show_screen, daemon=True).start()

# ----------------- Listener Channel -----------------
def listen_channel():
    global current_message, pause_spam
    l_token = tokens[0] 
    headers = {"Authorization": l_token}
    last_id = None
    
    UNBELIEVABOAT_ID = "292953664492929025"
    MOTHICA_ID = "1357551261494415431"

    while True:
        try:
            r = requests.get(f"https://discord.com/api/v9/channels/{channel_id}/messages?limit=30", headers=headers, timeout=10)
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
                    
                    embed_desc = ""
                    if msg.get("embeds"): embed_desc = msg["embeds"][0].get("description", "")
                    full_txt = content + " " + embed_desc
                    
                    if content.startswith("!ganti "):
                        current_message = content.replace("!ganti ", "", 1).strip()
                        logs.append(Fore.YELLOW + f"[ADMIN] Pesan diubah: {current_message}")

                    elif a_id == UNBELIEVABOAT_ID:
                        amt = extract_sapphire(msg)
                        if amt > 0:
                            target = get_target_token(msg, full_txt)
                            sapphire_counters[target] += amt
                            logs.append(Fore.GREEN + f"[{target}] +{amt:,} 💎 Sapphire")

                    elif a_id == MOTHICA_ID:
                        target = get_target_token(msg, full_txt)
                        pause_spam = True 
                        
                        img_url = None
                        if msg.get("attachments"): img_url = msg["attachments"][0]["url"]
                        elif msg.get("embeds") and msg["embeds"][0].get("image"): img_url = msg["embeds"][0]["image"]["url"]
                        
                        ans = None
                        
                        if img_url:
                            logs.append(Fore.MAGENTA + f"⏳ [YesCaptcha] Menyelesaikan gambar untuk {target}...")
                            ans, err_reason = solve_image_captcha(img_url)
                            if ans: 
                                logs.append(Fore.MAGENTA + f"💡 [YesCaptcha] Sukses: {ans}")
                            else: 
                                logs.append(Fore.RED + f"✖ [YesCaptcha] Gagal: {err_reason}")
                        else:
                            m = re.search(r'(\d+)\s*([\+\-\*])\s*(\d+)', full_txt)
                            if m:
                                logs.append(Fore.MAGENTA + f"⏳ [Math] Menghitung soal untuk {target}...")
                                n1, op, n2 = int(m.group(1)), m.group(2), int(m.group(3))
                                ans = n1+n2 if op=='+' else (n1-n2 if op=='-' else n1*n2)
                        
                        if ans:
                            time.sleep(random.uniform(1.0, 2.5))
                            try:
                                res = requests.post(
                                    f"https://discord.com/api/v9/channels/{channel_id}/messages", 
                                    json={'content': str(ans)}, headers={'Authorization': token_strings[target]},
                                    timeout=10
                                )
                                if res.status_code in [200, 201]:
                                    logs.append(Fore.GREEN + f"✔ [{target}] Berhasil membalas Captcha!")
                                else:
                                    logs.append(Fore.RED + f"✖ [{target}] Gagal membalas (HTTP {res.status_code})")
                            except:
                                logs.append(Fore.RED + f"✖ [{target}] Error koneksi saat membalas")
                        
                        time.sleep(3 if ans else 10)
                        pause_spam = False

        except: pass
        time.sleep(1.5)

threading.Thread(target=listen_channel, daemon=True).start()

# ----------------- Loop Utama (Spammer) -----------------
idx = 0
while True:
    while pause_spam:
        time.sleep(0.5)
    
    if not tokens:
        time.sleep(1)
        continue

    t_name = f"Token {idx+1}"
    color = colors[idx % len(colors)]
    headers = {'Authorization': tokens[idx]}
    now = datetime.now().strftime("%H:%M:%S")
    
    with lock:
        msg_send = current_message
        
    try:
        r = requests.post(f"https://discord.com/api/v9/channels/{channel_id}/messages", json={'content': msg_send}, headers=headers, timeout=10)
        if r.status_code in [200, 201]:
            counters[t_name] += 1
            last_sent_token = t_name 
            logs.append(color + f"[{t_name} | {now}] Pesan terkirim")
        elif r.status_code == 401:
            logs.append(Fore.RED + f"[{t_name}] Token invalid/mati!")
    except:
        logs.append(Fore.RED + f"[{t_name}] Error koneksi API")
    
    idx = (idx + 1) % len(tokens)
    
    sleep_interval = waktu2 / 1000
    elapsed = 0
    while elapsed < sleep_interval:
        if pause_spam: break
        time.sleep(0.2)
        elapsed += 0.2
