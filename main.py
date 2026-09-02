import logging
import sqlite3
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# ===== CONFIG =====
BOT_TOKEN = "8950977940:AAEtNtUrPI322WdCKOJFwRikO3myRA9hNXo"
OWNER_ID = 7860500580  # آیدی عددی خودتو بذار اینجا

# ===== DATABASE =====
conn = sqlite3.connect("prime_stars.db", check_same_thread=False)
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    joined_date TEXT,
    coins INTEGER DEFAULT 0,
    referrals INTEGER DEFAULT 0,
    orders INTEGER DEFAULT 0,
    is_admin INTEGER DEFAULT 0,
    is_banned INTEGER DEFAULT 0,
    warnings INTEGER DEFAULT 0
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS user_states (
    user_id INTEGER PRIMARY KEY,
    state TEXT,
    temp_data TEXT
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS pending_orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    gift_name TEXT,
    gift_price INTEGER
)
""")

conn.commit()

# ===== FIX OLD DATABASE =====
def fix_db():
    try:
        c.execute("SELECT joined_date FROM users LIMIT 1")
    except:
        c.execute("ALTER TABLE users ADD COLUMN joined_date TEXT")
    try:
        c.execute("SELECT coins FROM users LIMIT 1")
    except:
        c.execute("ALTER TABLE users ADD COLUMN coins INTEGER DEFAULT 0")
    try:
        c.execute("SELECT referrals FROM users LIMIT 1")
    except:
        c.execute("ALTER TABLE users ADD COLUMN referrals INTEGER DEFAULT 0")
    try:
        c.execute("SELECT orders FROM users LIMIT 1")
    except:
        c.execute("ALTER TABLE users ADD COLUMN orders INTEGER DEFAULT 0")
    try:
        c.execute("SELECT is_admin FROM users LIMIT 1")
    except:
        c.execute("ALTER TABLE users ADD COLUMN is_admin INTEGER DEFAULT 0")
    try:
        c.execute("SELECT is_banned FROM users LIMIT 1")
    except:
        c.execute("ALTER TABLE users ADD COLUMN is_banned INTEGER DEFAULT 0")
    try:
        c.execute("SELECT warnings FROM users LIMIT 1")
    except:
        c.execute("ALTER TABLE users ADD COLUMN warnings INTEGER DEFAULT 0")
    conn.commit()

fix_db()

# ===== GIFTS =====
gifts = {
    "gift1": ("تدی معمولی 🧸", 10),
    "gift2": ("قلب 💝", 11),
    "gift3": ("تدی عید پاک 🐰", 30),
    "gift4": ("باکس 🎁", 21),
    "gift5": ("گل 🌹", 21),
}

# ===== KEYBOARDS (همه کیبوردی) =====
def main_kb():
    keyboard = [
        [KeyboardButton("دعوت دوستان 👥"), KeyboardButton("گیفت ها 🎁")],
        [KeyboardButton("حساب کاربری 👤")],
        [KeyboardButton("پشتیبانی ☎️")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def admin_kb():
    keyboard = [
        [KeyboardButton("آمار ربات 📊"), KeyboardButton("افزودن ادمین ➕")],
        [KeyboardButton("حذف ادمین ➖"), KeyboardButton("بن 🚫")],
        [KeyboardButton("آن بن 🔘"), KeyboardButton("افزایش سکه 💰")],
        [KeyboardButton("کسر سکه 💸"), KeyboardButton("پیام همگانی 💬")],
        [KeyboardButton("اخطار ⚠️"), KeyboardButton("حذف اخطار ✅")],
        [KeyboardButton("در انتظار تأیید ⏳")],
        [KeyboardButton("🔙 برگشت به منو")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def cancel_kb():
    keyboard = [[KeyboardButton("کنسل ❌")]]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# ===== INLINE KEYBOARDS (فقط برای تأیید/رد و پیام‌ها) =====
def confirm_ikb(order_id):
    keyboard = [
        [InlineKeyboardButton("✅ عطا کردن", callback_data=f"confirm_{order_id}")],
        [InlineKeyboardButton("❌ سیک", callback_data=f"reject_{order_id}")],
    ]
    return InlineKeyboardMarkup(keyboard)

def support_ikb(user_id):
    keyboard = [
        [InlineKeyboardButton("پاسخ ↩️", callback_data=f"reply_{user_id}")],
        [InlineKeyboardButton("بن 🚫", callback_data=f"ban_{user_id}")],
        [InlineKeyboardButton("اخطار ⚠️", callback_data=f"warn_{user_id}")],
    ]
    return InlineKeyboardMarkup(keyboard)

def confirm_ban_ikb(user_id):
    keyboard = [
        [InlineKeyboardButton("✅ سیک", callback_data=f"confirm_ban_{user_id}")],
        [InlineKeyboardButton("❌ cansel", callback_data=f"cancel_ban_{user_id}")],
    ]
    return InlineKeyboardMarkup(keyboard)
    # ===== DATABASE FUNCTIONS =====
def get_user(user_id):
    return c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()

def create_user(user_id, username, first_name):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("INSERT OR IGNORE INTO users (user_id, username, first_name, joined_date, coins, referrals, orders, is_admin, is_banned, warnings) VALUES (?,?,?,?,0,0,0,0,0,0)",
              (user_id, username, first_name, now))
    conn.commit()

def set_state(user_id, state, temp_data=""):
    c.execute("INSERT OR REPLACE INTO user_states (user_id, state, temp_data) VALUES (?,?,?)",
              (user_id, state, temp_data))
    conn.commit()

def get_state(user_id):
    return c.execute("SELECT state, temp_data FROM user_states WHERE user_id = ?", (user_id,)).fetchone()

def clear_state(user_id):
    c.execute("DELETE FROM user_states WHERE user_id = ?", (user_id,))
    conn.commit()

def is_admin(user_id):
    u = get_user(user_id)
    return u and (u[7] == 1 or user_id == OWNER_ID)

# ===== HANDLERS =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    create_user(user.id, user.username, user.first_name)
    
    # چک کردن رفرال
    args = context.args
    if args and args[0].startswith("ref_"):
        try:
            ref_id = int(args[0].replace("ref_", ""))
            if ref_id != user.id:
                ref_user = get_user(ref_id)
                if ref_user:
                    c.execute("UPDATE users SET coins = coins + 1, referrals = referrals + 1 WHERE user_id = ?", (ref_id,))
                    c.execute("UPDATE users SET coins = coins + 1 WHERE user_id = ?", (user.id,))
                    conn.commit()
                    await context.bot.send_message(ref_id, f"🎉 کاربر جدیدی با لینک شما عضو شد!\n1 سکه به حساب شما اضافه شد.")
        except:
            pass
    
    # پیام استارت اول
    await update.message.reply_text(
        f"به ربات 💫 Prime Stars 💫 خوش آمدید 👋"
    )
    
    # پیام استارت دوم
    await update.message.reply_text(
        "با دعوت دوستان خود میتوانید گیفت دریافت کنید\n"
        "پس منتظر چی هستی همین الان با دکمه ی زیر شروع به دعوت کن 👇",
        reply_markup=main_kb()
    )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text
    
    # چک کردن بن
    u = get_user(user.id)
    if u and u[8] == 1:
        await update.message.reply_text(
            f"کاربر {u[2]} حساب کاربریه شما تعلیق شده است 🚫"
        )
        return
    
    # چک کردن state
    state = get_state(user.id)
    if state:
        s, temp = state
        if text == "کنسل ❌":
            clear_state(user.id)
            if is_admin(user.id):
                await update.message.reply_text("✅ عملیات لغو شد.", reply_markup=admin_kb())
            else:
                await update.message.reply_text("✅ عملیات لغو شد.", reply_markup=main_kb())
            return
        
        # ===== پشتیبانی - دریافت پیام از کاربر =====
        if s == "support_reply":
            admins = c.execute("SELECT user_id FROM users WHERE is_admin = 1 OR user_id = ?", (OWNER_ID,)).fetchall()
            for (admin_id,) in admins:
                try:
                    await context.bot.send_message(
                        admin_id,
                        f"📩 **پیام پشتیبانی جدید**\n\n👤 کاربر: {user.first_name} (`{user.id}`)\n📝 پیام: {text}",
                        reply_markup=support_ikb(user.id)
                    )
                except:
                    pass
            clear_state(user.id)
            await update.message.reply_text("✅ پیام شما به پشتیبانی ارسال شد.", reply_markup=main_kb())
            return
        
        # ===== پاسخ ادمین به کاربر =====
        if s == "admin_reply":
            target_id = int(temp)
            try:
                await context.bot.send_message(target_id, f"📩 **پاسخ پشتیبانی:**\n\n{text}")
                await update.message.reply_text("✅ پاسخ شما ارسال شد.", reply_markup=admin_kb())
            except:
                await update.message.reply_text("❌ خطا در ارسال پیام.", reply_markup=admin_kb())
            clear_state(user.id)
            return
        
        # ===== پیام همگانی =====
        if s == "broadcast":
            users = c.execute("SELECT user_id FROM users").fetchall()
            sent = 0
            for (uid,) in users:
                try:
                    await context.bot.send_message(uid, f"📢 **پیام همگانی:**\n\n{text}")
                    sent += 1
                except:
                    pass
            clear_state(user.id)
            await update.message.reply_text(f"✅ پیام برای {sent} کاربر ارسال شد.", reply_markup=admin_kb())
            return
          # ===== افزودن ادمین =====
        if s == "add_admin":
            target = c.execute("SELECT * FROM users WHERE user_id = ? OR username = ?", (text, text.replace("@", ""))).fetchone()
            if target:
                c.execute("UPDATE users SET is_admin = 1 WHERE user_id = ?", (target[0],))
                conn.commit()
                await update.message.reply_text(f"✅ کاربر {target[2]} ادمین شد.")
                try:
                    await context.bot.send_message(target[0], "🎉 شما به عنوان ادمین انتخاب شدید!")
                except:
                    pass
            else:
                await update.message.reply_text("❌ کاربر یافت نشد! (حتماً باید ربات رو استارت زده باشه)")
            clear_state(user.id)
            await update.message.reply_text("🔐 **پنل مدیریت:**", reply_markup=admin_kb())
            return
        
        # ===== حذف ادمین =====
        if s == "remove_admin":
            target = c.execute("SELECT * FROM users WHERE user_id = ? OR username = ?", (text, text.replace("@", ""))).fetchone()
            if target:
                c.execute("UPDATE users SET is_admin = 0 WHERE user_id = ?", (target[0],))
                conn.commit()
                await update.message.reply_text(f"✅ دسترسی ادمین از {target[2]} گرفته شد.")
                try:
                    await context.bot.send_message(target[0], "❌ شما از مقام ادمینی حذف شدید.")
                except:
                    pass
            else:
                await update.message.reply_text("❌ کاربر یافت نشد!")
            clear_state(user.id)
            await update.message.reply_text("🔐 **پنل مدیریت:**", reply_markup=admin_kb())
            return
        
        # ===== بن کردن =====
        if s == "ban":
            target = c.execute("SELECT * FROM users WHERE user_id = ? OR username = ?", (text, text.replace("@", ""))).fetchone()
            if target:
                c.execute("UPDATE users SET is_banned = 1 WHERE user_id = ?", (target[0],))
                conn.commit()
                await update.message.reply_text(f"✅ کاربر {target[2]} بن شد.")
                try:
                    await context.bot.send_message(target[0], "🚫 شما بن شدید!")
                except:
                    pass
            else:
                await update.message.reply_text("❌ کاربر یافت نشد!")
            clear_state(user.id)
            await update.message.reply_text("🔐 **پنل مدیریت:**", reply_markup=admin_kb())
            return
        
        # ===== آن بن =====
        if s == "unban":
            target = c.execute("SELECT * FROM users WHERE user_id = ? OR username = ?", (text, text.replace("@", ""))).fetchone()
            if target:
                c.execute("UPDATE users SET is_banned = 0 WHERE user_id = ?", (target[0],))
                conn.commit()
                await update.message.reply_text(f"✅ کاربر {target[2]} آن بن شد.")
                try:
                    await context.bot.send_message(target[0], "✅ شما آن بن شدید!")
                except:
                    pass
            else:
                await update.message.reply_text("❌ کاربر یافت نشد!")
            clear_state(user.id)
            await update.message.reply_text("🔐 **پنل مدیریت:**", reply_markup=admin_kb())
            return
        
        # ===== افزایش سکه =====
        if s == "add_coin":
            parts = text.split()
            if len(parts) == 2:
                target_id = parts[0]
                amount = int(parts[1])
                target = c.execute("SELECT * FROM users WHERE user_id = ? OR username = ?", (target_id, target_id.replace("@", ""))).fetchone()
                if target:
                    c.execute("UPDATE users SET coins = coins + ? WHERE user_id = ?", (amount, target[0]))
                    conn.commit()
                    await update.message.reply_text(f"✅ {amount} سکه به {target[2]} اضافه شد.")
                    try:
                        await context.bot.send_message(target[0], f"💰 {amount} سکه به حساب شما واریز شد!")
                    except:
                        pass
                else:
                    await update.message.reply_text("❌ کاربر یافت نشد!")
            else:
                await update.message.reply_text("❌ فرمت: آیدی مقدار")
            clear_state(user.id)
            await update.message.reply_text("🔐 **پنل مدیریت:**", reply_markup=admin_kb())
            return
        
        # ===== کسر سکه =====
        if s == "remove_coin":
            parts = text.split()
            if len(parts) == 2:
                target_id = parts[0]
                amount = int(parts[1])
                target = c.execute("SELECT * FROM users WHERE user_id = ? OR username = ?", (target_id, target_id.replace("@", ""))).fetchone()
                if target:
                    c.execute("UPDATE users SET coins = coins - ? WHERE user_id = ?", (amount, target[0]))
                    conn.commit()
                    await update.message.reply_text(f"✅ {amount} سکه از {target[2]} کم شد.")
                    try:
                        await context.bot.send_message(target[0], f"💸 {amount} سکه از حساب شما کسر شد.")
                    except:
                        pass
                else:
                    await update.message.reply_text("❌ کاربر یافت نشد!")
            else:
                await update.message.reply_text("❌ فرمت: آیدی مقدار")
            clear_state(user.id)
            await update.message.reply_text("🔐 **پنل مدیریت:**", reply_markup=admin_kb())
            return
        
        # ===== اخطار =====
        if s == "warn":
            parts = text.split()
            if len(parts) == 2:
                target_id = parts[0]
                count = int(parts[1])
                target = c.execute("SELECT * FROM users WHERE user_id = ? OR username = ?", (target_id, target_id.replace("@", ""))).fetchone()
                if target:
                    new_warnings = target[9] + count
                    c.execute("UPDATE users SET warnings = ? WHERE user_id = ?", (new_warnings, target[0]))
                    if new_warnings >= 10:
                        c.execute("UPDATE users SET is_banned = 1 WHERE user_id = ?", (target[0],))
                        conn.commit()
                        await update.message.reply_text(f"⚠️ کاربر {target[2]} به 10 اخطار رسید و بن شد!")
                        try:
                            await context.bot.send_message(target[0], f"🚫 شما به 10 اخطار رسیدید و بن شدید!")
                        except:
                            pass
                    else:
                        conn.commit()
                        await update.message.reply_text(f"⚠️ {count} اخطار به {target[2]} داده شد. ({new_warnings}/10)")
                        try:
                            await context.bot.send_message(target[0], f"⚠️ شما {count} اخطار دریافت کردید! ({new_warnings}/10)")
                        except:
                            pass
                else:
                    await update.message.reply_text("❌ کاربر یافت نشد!")
            else:
                await update.message.reply_text("❌ فرمت: آیدی تعداد")
            clear_state(user.id)
            await update.message.reply_text("🔐 **پنل مدیریت:**", reply_markup=admin_kb())
            return
        
        # ===== حذف اخطار =====
        if s == "remove_warn":
            parts = text.split()
            if len(parts) == 2:
                target_id = parts[0]
                count = int(parts[1])
                target = c.execute("SELECT * FROM users WHERE user_id = ? OR username = ?", (target_id, target_id.replace("@", ""))).fetchone()
                if target:
                    new_warnings = max(0, target[9] - count)
                    c.execute("UPDATE users SET warnings = ? WHERE user_id = ?", (new_warnings, target[0]))
                    conn.commit()
                    await update.message.reply_text(f"✅ {count} اخطار از {target[2]} حذف شد. ({new_warnings}/10)")
                    try:
                        await context.bot.send_message(target[0], f"✅ {count} اخطار از شما حذف شد. ({new_warnings}/10)")
                    except:
                        pass
                else:
                    await update.message.reply_text("❌ کاربر یافت نشد!")
            else:
                await update.message.reply_text("❌ فرمت: آیدی تعداد")
            clear_state(user.id)
            await update.message.reply_text("🔐 **پنل مدیریت:**", reply_markup=admin_kb())
            return
                  # ===== MAIN MENU (کیبوردی) =====
    if text == "دعوت دوستان 👥":
        link = f"https://t.me/PRIMESTSRSBOT?start=ref_{user.id}"
        await update.message.reply_text(
            f"🤝 **دعوت دوستان**\n\n"
            f"با دعوت هر دوست، 1 سکه 🪙 دریافت میکنید!\n\n"
            f"🔗 **لینک دعوت شما:**\n{link}\n\n"
            f"این لینک رو برای دوستانت بفرست و سکه جمع کن! 💰"
        )
    
    elif text == "گیفت ها 🎁":
        await update.message.reply_text(
            "🎁 **گیفت های موجود:**\n\n"
            "یکی از گزینه های زیر رو انتخاب کنید 👇",
            reply_markup=ReplyKeyboardMarkup([
                [KeyboardButton("تدی معمولی 🧸 - 10 سکه")],
                [KeyboardButton("قلب 💝 - 11 سکه")],
                [KeyboardButton("تدی عید پاک 🐰 - 30 سکه")],
                [KeyboardButton("باکس 🎁 - 21 سکه")],
                [KeyboardButton("گل 🌹 - 21 سکه")],
                [KeyboardButton("🔙 برگشت")],
            ], resize_keyboard=True)
        )
    
    elif text == "حساب کاربری 👤":
        u = get_user(user.id)
        if u:
            await update.message.reply_text(
                f"👤 **شناسه کاربری** : `{user.id}`\n"
                f"📆 **تاریخ عضویت** : {u[3]}\n"
                f"🛍 **تعداد سفارشات** : {u[6]}\n"
                f"👥 **تعداد زیرمجموعه** : {u[5]}\n"
                f"💰 **موجودی حساب** : {u[4]} سکه"
            )
    
    elif text == "پشتیبانی ☎️":
        set_state(user.id, "support_reply")
        await update.message.reply_text("لطفاً پیام خود را ارسال کنید 📝", reply_markup=cancel_kb())
    
    # ===== گیفت‌ها (کیبوردی) =====
    elif text == "تدی معمولی 🧸 - 10 سکه":
        await buy_gift(update, "gift1")
    elif text == "قلب 💝 - 11 سکه":
        await buy_gift(update, "gift2")
    elif text == "تدی عید پاک 🐰 - 30 سکه":
        await buy_gift(update, "gift3")
    elif text == "باکس 🎁 - 21 سکه":
        await buy_gift(update, "gift4")
    elif text == "گل 🌹 - 21 سکه":
        await buy_gift(update, "gift5")
    elif text == "🔙 برگشت":
        await update.message.reply_text("منوی اصلی:", reply_markup=main_kb())
    
    # ===== ADMIN PANEL (کیبوردی) =====
    elif text == "/owner" and user.id == OWNER_ID:
        c.execute("UPDATE users SET is_admin = 1 WHERE user_id = ?", (user.id,))
        conn.commit()
        await update.message.reply_text("🔐 **پنل مدیریت (Owner):**", reply_markup=admin_kb())
    
    elif text == "/admin" and is_admin(user.id):
        await update.message.reply_text("🔐 **پنل مدیریت:**", reply_markup=admin_kb())
    
    elif text == "آمار ربات 📊" and is_admin(user.id):
        total_users = c.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        total_orders = c.execute("SELECT COUNT(*) FROM pending_orders").fetchone()[0]
        total_coins = c.execute("SELECT SUM(coins) FROM users").fetchone()[0] or 0
        online_users = 0  # تقریبی
        await update.message.reply_text(
            f"📊 **آمار ربات:**\n\n"
            f"👥 کل کاربران: {total_users}\n"
            f"🟢 آنلاین‌ها: {online_users}\n"
            f"🎁 سفارشات در انتظار: {total_orders}\n"
            f"🪙 کل سکه‌ها: {total_coins}"
        )
    
    elif text == "افزودن ادمین ➕" and is_admin(user.id):
        if user.id == OWNER_ID:
            set_state(user.id, "add_admin")
            await update.message.reply_text("آیدی عددی کاربر مورد نظر را وارد کنید:", reply_markup=cancel_kb())
        else:
            await update.message.reply_text("❌ این مورد فقط مخصوص owner ساخته شده و شما مجوز استفاده از این دکمه هارو ندارید!")
    
    elif text == "حذف ادمین ➖" and is_admin(user.id):
        if user.id == OWNER_ID:
            set_state(user.id, "remove_admin")
            await update.message.reply_text("آیدی عددی کاربر مورد نظر را وارد کنید:", reply_markup=cancel_kb())
        else:
            await update.message.reply_text("❌ این مورد فقط مخصوص owner ساخته شده و شما مجوز استفاده از این دکمه هارو ندارید!")
    
    elif text == "بن 🚫" and is_admin(user.id):
        set_state(user.id, "ban")
        await update.message.reply_text("آیدی عددی کاربر مورد نظر را وارد کنید:", reply_markup=cancel_kb())
    
    elif text == "آن بن 🔘" and is_admin(user.id):
        set_state(user.id, "unban")
        await update.message.reply_text("آیدی عددی کاربر مورد نظر را وارد کنید:", reply_markup=cancel_kb())
    
    elif text == "افزایش سکه 💰" and is_admin(user.id):
        if user.id == OWNER_ID:
            set_state(user.id, "add_coin")
            await update.message.reply_text("فرمت: آیدی مقدار\nمثال: 123456 100", reply_markup=cancel_kb())
        else:
            await update.message.reply_text("❌ این مورد فقط مخصوص owner ساخته شده و شما مجوز استفاده از این دکمه هارو ندارید!")
    
    elif text == "کسر سکه 💸" and is_admin(user.id):
        if user.id == OWNER_ID:
            set_state(user.id, "remove_coin")
            await update.message.reply_text("فرمت: آیدی مقدار\nمثال: 123456 100", reply_markup=cancel_kb())
        else:
            await update.message.reply_text("❌ این مورد فقط مخصوص owner ساخته شده و شما مجوز استفاده از این دکمه هارو ندارید!")
    
    elif text == "پیام همگانی 💬" and is_admin(user.id):
        set_state(user.id, "broadcast")
        await update.message.reply_text("متن پیام همگانی را وارد کنید:", reply_markup=cancel_kb())
    
    elif text == "اخطار ⚠️" and is_admin(user.id):
        set_state(user.id, "warn")
        await update.message.reply_text("فرمت: آیدی تعداد\nمثال: 123456 2", reply_markup=cancel_kb())
    
    elif text == "حذف اخطار ✅" and is_admin(user.id):
        set_state(user.id, "remove_warn")
        await update.message.reply_text("فرمت: آیدی تعداد\nمثال: 123456 2", reply_markup=cancel_kb())
    
    elif text == "در انتظار تأیید ⏳" and is_admin(user.id):
        orders = c.execute("SELECT * FROM pending_orders").fetchall()
        if orders:
            for order in orders:
                user_info = get_user(order[1])
                name = user_info[2] if user_info else "نامشخص"
                await update.message.reply_text(
                    f"🆔 کاربر: `{order[1]}` ({name})\n"
                    f"🎁 درخواست {order[2]} را دارد\n"
                    f"💰 قیمت: {order[3]} سکه\n\n"
                    "عطا میکنید یا درخواست رو رد میکنید؟",
                    reply_markup=confirm_ikb(order[0])
                )
        else:
            await update.message.reply_text("📭 درخواستی در انتظار تأیید نیست.")
    
    elif text == "🔙 برگشت به منو":
        await update.message.reply_text("منوی اصلی:", reply_markup=main_kb())

# ===== BUY GIFT =====
async def buy_gift(update: Update, gift_key):
    user = update.effective_user
    name, price = gifts[gift_key]
    u = get_user(user.id)
    if u and u[4] >= price:
        c.execute("UPDATE users SET coins = coins - ?, orders = orders + 1 WHERE user_id = ?", (price, user.id))
        c.execute("INSERT INTO pending_orders (user_id, gift_name, gift_price) VALUES (?,?,?)", (user.id, name, price))
        conn.commit()
        await update.message.reply_text(
            f"✅ گیفت شما در حال تأیید ادمین است لطفاً شکیبا باشید ♥️\n\n"
            f"🎁 {name}\n💰 {price} سکه"
        )
        # اطلاع به ادمین‌ها
        admins = c.execute("SELECT user_id FROM users WHERE is_admin = 1 OR user_id = ?", (OWNER_ID,)).fetchall()
        for (admin_id,) in admins:
            try:
                order_id = c.execute("SELECT id FROM pending_orders WHERE user_id = ? ORDER BY id DESC LIMIT 1", (user.id,)).fetchone()[0]
                await context.bot.send_message(
                    admin_id,
                    f"🆔 کاربر: `{user.id}` ({user.first_name})\n"
                    f"🎁 درخواست {name} را دارد\n"
                    f"💰 قیمت: {price} سکه\n\n"
                    "عطا میکنید یا درخواست رو رد میکنید؟",
                    reply_markup=confirm_ikb(order_id)
                )
            except:
                pass
    else:
        await update.message.reply_text(
            "❌ موجودی شما کافی نیست!\n"
            "میتوانید از بخش دعوت دوستان سکه جمع آوری کنید ❗"
        )

# ===== CALLBACK HANDLER =====
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    data = query.data
    
    # تأیید گیفت
    if data.startswith("confirm_"):
        if is_admin(user.id):
            order_id = int(data.replace("confirm_", ""))
            order = c.execute("SELECT * FROM pending_orders WHERE id = ?", (order_id,)).fetchone()
            if order:
                c.execute("DELETE FROM pending_orders WHERE id = ?", (order_id,))
                conn.commit()
                await query.edit_message_text(
                    "سازنده هنوز متنی برای این دکمه انتخواب نکرده منتظر آپدیت های بعدی باشید ♥️"
                )
    
    # رد گیفت
    elif data.startswith("reject_"):
        if is_admin(user.id):
            order_id = int(data.replace("reject_", ""))
            order = c.execute("SELECT * FROM pending_orders WHERE id = ?", (order_id,)).fetchone()
            if order:
                c.execute("UPDATE users SET coins = coins + ? WHERE user_id = ?", (order[3], order[1]))
                c.execute("DELETE FROM pending_orders WHERE id = ?", (order_id,))
                conn.commit()
                await query.edit_message_text(f"❌ درخواست رد شد و حذف گردید.")
    
    # پاسخ به کاربر
    elif data.startswith("reply_"):
        if is_admin(user.id):
            target_id = data.replace("reply_", "")
            set_state(user.id, "admin_reply", target_id)
            await query.edit_message_text("پاسخ خود را بنویسید:", reply_markup=cancel_kb())
    
    # بن از پشتیبانی
    elif data.startswith("ban_"):
        if is_admin(user.id):
            target_id = data.replace("ban_", "")
            await query.edit_message_text(
                f"مطمئنی میخواهی کاربر {target_id} رو مسدود کنی؟",
                reply_markup=confirm_ban_ikb(target_id)
            )
    
    # تأیید بن
    elif data.startswith("confirm_ban_"):
        if is_admin(user.id):
            target_id = int(data.replace("confirm_ban_", ""))
            c.execute("UPDATE users SET is_banned = 1 WHERE user_id = ?", (target_id,))
            conn.commit()
            await query.edit_message_text(f"✅ کاربر {target_id} بن شد.")
            try:
                await context.bot.send_message(target_id, "🚫 حساب کاربریه شما تعلیق شده است!")
            except:
                pass
    
    # کنسل بن
    elif data.startswith("cancel_ban_"):
        await query.edit_message_text("✅ عملیات لغو شد.")
    
    # اخطار از پشتیبانی
    elif data.startswith("warn_"):
        if is_admin(user.id):
            target_id = int(data.replace("warn_", ""))
            target = get_user(target_id)
            if target:
                new_warnings = target[9] + 1
                c.execute("UPDATE users SET warnings = ? WHERE user_id = ?", (new_warnings, target_id))
                if new_warnings >= 10:
                    c.execute("UPDATE users SET is_banned = 1 WHERE user_id = ?", (target_id,))
                    conn.commit()
                    await query.edit_message_text(f"⚠️ کاربر به 10 اخطار رسید و بن شد!")
                    try:
                        await context.bot.send_message(target_id, "🚫 شما به 10 اخطار رسیدید و بن شدید!")
                    except:
                        pass
                else:
                    conn.commit()
                    await query.edit_message_text(f"⚠️ اخطار داده شد. ({new_warnings}/10)")
                    try:
                        await context.bot.send_message(target_id, f"⚠️ شما یک اخطار دریافت کردید! ({new_warnings}/10)")
                    except:
                        pass

# ===== MAIN =====
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(CallbackQueryHandler(handle_callback))
    
    print("🤖 Prime Stars Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
      
