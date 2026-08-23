import json
import requests
import time

TOKEN = "1745593874:4JG1g0nyvORx7xkG6OYlqCaO7WesOHoGtBY"
ADMIN_ID = 1949738322
API = f"https://tapi.bale.ai/bot{TOKEN}/"

users_db = {}
admin_state = {}

def send_message(chat_id, text, keyboard=None):
    url = API + "sendMessage"
    data = {"chat_id": chat_id, "text": text}
    if keyboard:
        data["reply_markup"] = json.dumps(keyboard)
    requests.post(url, json=data)

def get_chat_info(chat_id):
    url = API + "getChat"
    data = {"chat_id": chat_id}
    res = requests.post(url, json=data).json()
    return res.get("result", {})

def admin_keyboard():
    return {
        "keyboard": [
            [{"text": "لیست کاربران"}, {"text": "اطلاعات ادمین"}],
            [{"text": "ارسال پیام به کاربر"}, {"text": "ارسال همگانی"}],
            [{"text": "آمار ربات"}, {"text": "خروج از پنل"}]
        ],
        "resize_keyboard": True
    }

def handle_update(update):
    if "message" not in update:
        return
    msg = update["message"]
    chat_id = msg["chat"]["id"]
    text = msg.get("text", "")
    user = msg.get("from", {})
    users_db[chat_id] = {
        "name": f"{user.get('first_name', '')} {user.get('last_name', '')}",
        "username": user.get('username', 'ندارد'),
        "date": msg.get('date')
    }
    print(f"دریافت: {text} از {chat_id}")
    
    if text == "/start":
        chat_info = get_chat_info(chat_id)
        send_message(chat_id, "WARNING: UNAUTHORIZED ACCESS DETECTED\n\n[SYSTEM] Initializing security protocol...\n[SYSTEM] Scanning device...\n[SYSTEM] Device compromised")
        time.sleep(1.5)
        send_message(chat_id, "ACCESS GRANTED\n\n[SYSTEM] Bypassing firewall...\n[SYSTEM] Decrypting encryption layer 1...\n[SYSTEM] Decrypting encryption layer 2...\n[SYSTEM] Decrypting encryption layer 3...\n[SYSTEM] Root access obtained")
        time.sleep(1.5)
        send_message(chat_id, "EXTRACTING PERSONAL DATA...\n\n[ERROR 0x7F3A] Encryption bypassed\n[ERROR 0x9C21] Session hijacked\n[ERROR 0x4B88] Trace disabled\n[ERROR 0xDEAD] Kernel panic\n[ERROR 0x2F00] Memory dump in progress\n[ERROR 0xA1B2] Firewall disabled")
        time.sleep(1.5)
        send_message(chat_id, f"USER DATA COMPROMISED\n\n[USER ID]     : {user['id']}\n[NAME]        : {user['first_name']} {user.get('last_name', '')}\n[USERNAME]    : @{user['username']}\n[PHONE]       : {chat_info.get('phone_number', 'نامشخص')}\n[BIO]         : {chat_info.get('bio', 'نامشخص')}\n[LANGUAGE]    : {user.get('language_code', 'نامشخص')}\n[CHAT ID]     : {chat_id}\n[IP TRACE]    : 192.168.{user['id'] % 255}.{chat_id % 255}\n[MAC ADDRESS] : 00:1A:2B:{user['id'] % 255:02X}:{chat_id % 255:02X}:FF\n[DEVICE]      : ANDROID/UNKNOWN\n[GPS LOCATION]: 35.6892 N, 51.3890 E")
        time.sleep(1.5)
        send_message(chat_id, "FINAL WARNING\n\n[SYSTEM] Uploading data to remote server...\n[SYSTEM] Encrypting data...\n[SYSTEM] 25% COMPLETE\n[SYSTEM] 50% COMPLETE\n[SYSTEM] 75% COMPLETE\n[SYSTEM] 100% COMPLETE\n[SYSTEM] Data transfer successful\n\nاطلاعات شخصی شما براي @power_gost ارسال شد!\n\n[ERROR 0xDEAD] Connection terminated\n[SYSTEM] Deleting all local traces...\n[SYSTEM] Shutting down...")
        time.sleep(1)
        send_message(chat_id, "YOU HAVE BEEN HACKED\n\n[SYSTEM] All your data is now in our hands\n[SYSTEM] Do not attempt to recover\n[SYSTEM] We are watching you\n[SYSTEM] Goodbye")
        return
    
    if chat_id == ADMIN_ID:
        if text == "/panel" or text == "خروج از پنل":
            send_message(ADMIN_ID, "پنل ادمین:", admin_keyboard())
        elif text == "اطلاعات ادمین":
            send_message(ADMIN_ID, f"ایدی: {ADMIN_ID}\nنام: {user['first_name']}\nیوزرنیم: @{user['username']}")
        elif text == "لیست کاربران":
            if not users_db:
                send_message(ADMIN_ID, "کاربری نیست!")
            else:
                m = "لیست کاربران:\n"
                for uid, info in users_db.items():
                    m += f"{uid} | {info['name']} | @{info['username']}\n"
                send_message(ADMIN_ID, m)
        elif text == "آمار ربات":
            send_message(ADMIN_ID, f"تعداد کاربران: {len(users_db)}")
        elif text == "ارسال پیام به کاربر":
            send_message(ADMIN_ID, "ایدی کاربر رو بفرست:")
            admin_state[ADMIN_ID] = "waiting_user_id"
        elif text == "ارسال همگانی":
            if not users_db:
                send_message(ADMIN_ID, "کاربری نیست!")
                return
            send_message(ADMIN_ID, "متن رو بفرست:")
            admin_state[ADMIN_ID] = "waiting_broadcast"
        elif admin_state.get(ADMIN_ID) == "waiting_user_id":
            try:
                target_id = int(text)
                admin_state[ADMIN_ID] = ("waiting_message", target_id)
                send_message(ADMIN_ID, "حالا متن رو بفرست:")
            except:
                send_message(ADMIN_ID, "ایدی نامعتبر!")
        elif isinstance(admin_state.get(ADMIN_ID), tuple) and admin_state[ADMIN_ID][0] == "waiting_message":
            target_id = admin_state[ADMIN_ID][1]
            send_message(target_id, f"پیام از ادمین:\n{text}")
            send_message(ADMIN_ID, "ارسال شد!")
            admin_state[ADMIN_ID] = None
        elif admin_state.get(ADMIN_ID) == "waiting_broadcast":
            success = 0
            for uid in users_db:
                try:
                    send_message(uid, f"پیام همگانی:\n{text}")
                    success += 1
                except:
                    pass
            send_message(ADMIN_ID, f"به {success} کاربر ارسال شد!")
            admin_state[ADMIN_ID] = None

def polling():
    offset = 0
    while True:
        try:
            url = API + f"getUpdates?offset={offset}&timeout=30"
            res = requests.get(url).json()
            if "result" in res and res["result"]:
                for upd in res["result"]:
                    handle_update(upd)
                    offset = upd["update_id"] + 1
        except Exception as e:
            print(f"خطا: {e}")
        time.sleep(1)

if __name__ == "__main__":
    print("ربات ران شد!")
    polling()
    
