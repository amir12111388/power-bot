import requests
import time
import json
import os

# --- تنظیمات اصلی ---
BOT_TOKEN = "518206178:crBnw-E77aTxoIGx0AhOPJ1cr1N7avhcGXM"
ADMIN_ID = 747113565  # آیدی عددی خودت را اینجا وارد کن
API_URL = f"https://tapi.bale.ai/bot{BOT_TOKEN}/"
DATA_FILE = "bot_data.json"

# --- سیستم مدیریت داده‌ها (ذخیره دائمی) ---
def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                return json.load(f)
        except:
            return {"users": [], "banned_users": []}
    return {"users": [], "banned_users": []}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

# بارگذاری اولیه داده‌ها
db = load_data()
users = set(db["users"])
banned_users = set(db["banned_users"])
admin_reply_to = None
last_update_id = 0

def send_message(chat_id, text, reply_markup=None):
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    try:
        requests.post(API_URL + "sendMessage", json=payload)
    except Exception as e:
        print(f"Error in sending message: {e}")

print("🚀 سیستم مدیریت پیشرفته فعال شد...")

while True:
    try:
        response = requests.get(API_URL + "getUpdates", params={"offset": last_update_id + 1, "timeout": 30}).json()
        
        if response.get("ok") and response.get("result"):
            for update in response["result"]:
                last_update_id = update["update_id"]
                
                if "message" in update:
                    msg = update["message"]
                    chat_id = msg["chat"]["id"]
                    text = msg.get("text", "")

                    # ۱. بررسی وضعیت مسدودی کاربر (Ban Check)
                    if chat_id in banned_users:
                        continue
                    
                    # ۲. ثبت کاربر جدید در دیتابیس
                    if chat_id not in users:
                        users.add(chat_id)
                        db["users"] = list(users)
                        save_data(db)

                    # ۳. مدیریت پاسخ‌دهی ادمین به کاربران
                    if chat_id == ADMIN_ID and admin_reply_to is not None:
                        send_message(admin_reply_to, f"✉️ <b>پاسخ مدیریت:</b>\n\n{text}")
                        send_message(ADMIN_ID, "✅ پیام شما با موفقیت ارسال شد.")
                        admin_reply_to = None
                        continue

                    # ۴. پنل مدیریت ادمین (فقط با دستور فعال می‌شود)
                    if chat_id == ADMIN_ID:
                        if text == "/start":
                            admin_menu = ("🛠 <b>پنل مدیریت اختصاصی</b>\n\n"
                                          "📊 /stats - مشاهده آمار کلی\n"
                                          "👥 /users - مشاهده لیست کاربران\n"
                                          "🚫 /banned - مشاهده لیست کاربران مسدود شده\n"
                                          "🔨 /ban [id] - مسدود کردن کاربر\n"
                                          "🔓 /unban [id] - رفع مسدودسازی کاربر\n"
                                          "📢 /broadcast [text] - ارسال پیام به همه کاربران")
                            send_message(chat_id, admin_menu)
                            continue
                        
                        elif text == "/stats":
                            send_message(chat_id, f"📊 <b>گزارش وضعیت سیستم:</b>\n\n👤 کاربران فعال: {len(users)}\n🚫 کاربران مسدود شده: {len(banned_users)}")
                            continue

                        elif text == "/users":
                            user_list = "\n".join(map(str, list(users)[:100]))
                            send_message(chat_id, f"👥 <b>لیست آیدی کاربران:</b>\n\n<code>{user_list}</code>")
                            continue

                        elif text == "/banned":
                            ban_list = "\n".join(map(str, list(banned_users)[:100]))
                            send_message(chat_id, f"🚫 <b>لیست کاربران مسدود شده:</b>\n\n<code>{ban_list}</code>")
                            continue

                        elif text.startswith("/ban "):
                            try:
                                target_id = int(text.split(" ")[1])
                                banned_users.add(target_id)
                                db["banned_users"] = list(banned_users)
                                save_data(db)
                                send_message(chat_id, f"🚫 کاربر <code>{target_id}</code> با موفقیت مسدود شد.")
                            except:
                                send_message(chat_id, "⚠️ خطا در دستور. مثال: `/ban 123456`")
                            continue

                        elif text.startswith("/unban "):
                            try:
                                target_id = int(text.split(" ")[1])
                                if target_id in banned_users:
                                    banned_users.remove(target_id)
                                    db["banned_users"] = list(banned_users)
                                    save_data(db)
                                    send_message(chat_id, f"🔓 کاربر <code>{target_id}</code> از لیست مسدودسازی خارج شد.")
                                else:
                                    send_message(chat_id, "❌ این کاربر در لیست مسدود شده نیست.")
                            except:
                                send_message(chat_id, "⚠️ خطا در دستور. مثال: `/unban 123456`")
                            continue

                        elif text.startswith("/broadcast "):
                            msg_content = text.split(" ", 1)[1]
                            success_count = 0
                            for u in users:
                                if u != ADMIN_ID:
                                    try:
                                        send_message(u, f"📢 <b>اطلاعیه مدیریت:</b>\n\n{msg_content}")
                                        success_count += 1
                                    except: pass
                            send_message(chat_id, f"✅ پیام به {success_count} کاربر ارسال شد.")
                            continue

                    # ۵. بخش کاربران عادی (User Interface)
                    if text == "/start":
                        kb = {"keyboard": [[{"text": "ارسال اعتراف 🔥"}]], "resize_keyboard": True}
                        welcome_text = ("💎 <b>به ربات اعتراف ناشناس خوش آمدید</b>\n\n"
                                        "در این ربات می‌توانید بدون افشای هویت خود، پیام خود را برای مدیریت ارسال کنید.\n\n"
                                        "📢 کانال رسمی ما: @Eteraf\n\n"
                                        "👇 برای شروع از دکمه زیر استفاده کنید:")
                        send_message(chat_id, welcome_text, kb)
                        continue

                    elif text == "ارسال اعتراف 🔥":
                        send_message(chat_id, "📝 <b>لطفاً متن اعتراف خود را بنویسید:</b>")
                    
                    elif chat_id != ADMIN_ID:
                        # ارسال پیام کاربر به ادمین با دکمه‌های عملیاتی
                        admin_kb = {"inline_keyboard": [[
                            {"text": "💬 پاسخ به کاربر", "callback_data": f"reply_{chat_id}"},
                            {"text": "🚫 مسدودسازی", "callback_data": f"ban_{chat_id}"}
                        ]]}
                        send_message(ADMIN_ID, f"📩 <b>پیام جدید از کاربر ناشناس:</b>\n\n<code>{text}</code>", admin_kb)
                        send_message(chat_id, "✅ پیام شما با موفقیت برای مدیریت ارسال شد.")

                # ۶. مدیریت کلیک‌های دکمه‌های شیشه‌ای (Callback Query)
                elif "callback_query" in update:
                    cb = update["callback_query"]
                    data = cb.get("data", "")
                    sender_id = cb["from"]["id"]

                    if sender_id == ADMIN_ID:
                        if data.startswith("reply_"):
                            admin_reply_to = int(data.split("_")[1])
                            send_message(ADMIN_ID, f"📝 <b>در حال پاسخ‌دهی به کاربر:</b> <code>{admin_reply_to}</code>\n\nلطفاً متن پاسخ را ارسال کنید:")
                        
                        elif data.startswith("ban_"):
                            uid = int(data.split("_")[1])
                            if uid not in banned_users:
                                banned_users.add(uid)
                                db["banned_users"] = list(banned_users)
                                save_data(db)
                                send_message(ADMIN_ID, f"🚫 کاربر <code>{uid}</code> با موفقیت مسدود شد.")
                            else:
                                send_message(ADMIN_ID, "⚠️ این کاربر از قبل در لیست مسدودسازی قرار دارد.")

    except Exception as e:
        print(f"Critical Error: {e}")
        time.sleep(2)
