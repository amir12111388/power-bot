import time
import random
import sqlite3
from selenium import webdriver
from selenium.webdriver.common.by import By
import undetected_chromedriver as uc 
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, CallbackQueryHandler

# --- تنظیمات ---
TOKEN = "887772753:PoZnCJDYWukKmJ2FQmiD-YVRtadE018GV2w"
ADMIN_ID = 1949738322  # آیدی شما

# وضعیت‌های گفتگو
SETTING_USER, SETTING_PASS, WAITING_FOR_DATA, WAITING_FOR_ID_SEARCH, ADMIN_MANAGE_ID = range(5)

# --- مدیریت دیتابیس ---
def init_db():
    conn = sqlite3.connect('users_data.db')
    c = conn.cursor()
    # جدول کاربران: اضافه شدن ستون is_approved
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (user_id INTEGER PRIMARY KEY, username TEXT, password TEXT, is_approved INTEGER DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS cargo 
                 (user_id INTEGER, driver_id TEXT, weight TEXT, origin TEXT, dest TEXT, hour TEXT)''')
    conn.commit()
    conn.close()

def check_approval(user_id):
    conn = sqlite3.connect('users_data.db')
    c = conn.cursor()
    c.execute("SELECT is_approved FROM users WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else 0

def set_approval(user_id, status):
    conn = sqlite3.connect('users_data.db')
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO users (user_id, is_approved) VALUES (?, ?)", (user_id, status))
    conn.commit()
    conn.close()

# (توابع ذخیره یوزر/پسورد و بارها مشابه قبل هستند اما با چک کردن مجوز)
def save_user_credentials(user_id, username, password):
    conn = sqlite3.connect('users_data.db')
    c = conn.cursor()
    c.execute("UPDATE users SET username = ?, password = ? WHERE user_id = ?", (username, password, user_id))
    conn.commit()
    conn.close()

def get_user_credentials(user_id):
    conn = sqlite3.connect('users_data.db')
    c = conn.cursor()
    c.execute("SELECT username, password FROM users WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    conn.close()
    return result

def save_cargo(user_id, driver_id, weight, origin, dest, hour):
    conn = sqlite3.connect('users_data.db')
    c = conn.cursor()
    c.execute("INSERT INTO cargo VALUES (?, ?, ?, ?, ?, ?)", (user_id, driver_id, weight, origin, dest, hour))
    conn.commit()
    conn.close()

def get_user_cargos(user_id):
    conn = sqlite3.connect('users_data.db')
    c = conn.cursor()
    c.execute("SELECT driver_id, weight, origin, dest, hour FROM cargo WHERE user_id = ?", (user_id,))
    results = c.fetchall()
    conn.close()
    return results

def clear_user_cargos(user_id):
    conn = sqlite3.connect('users_data.db')
    c = conn.cursor()
    c.execute("DELETE FROM cargo WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

# --- بخش اتوماسیون سایت (بدون تغییر) ---
def process_baarbarg_entries(user_id):
    creds = get_user_credentials(user_id)
    if not creds: return "❌ ابتدا یوزر و پسورد را تنظیم کنید."
    username, password = creds
    cargos = get_user_cargos(user_id)
    if not cargos: return "⚠️ باری برای ثبت نیست."
    
    options = uc.ChromeOptions()
    options.add_argument('--headless')
    try:
        driver = uc.Chrome(options=options)
        driver.get("https://baarbarg.ir/login")
        time.sleep(2)
        driver.find_element(By.NAME, "username").send_keys(username)
        driver.find_element(By.NAME, "password").send_keys(password)
        driver.find_element(By.ID, "login-button").click()
        time.sleep(3)
        success = 0
        for cargo in cargos:
            driver.get(f"https://baarbarg.ir/entry/{cargo[0]}")
            time.sleep(2)
            driver.find_element(By.ID, "weight").send_keys(cargo[1])
            driver.find_element(By.ID, "origin").send_keys(cargo[2])
            driver.find_element(By.ID, "destination").send_keys(cargo[3])
            driver.find_element(By.ID, "hour").send_keys(cargo[4])
            driver.find_element(By.ID, "submit").click()
            success += 1
            time.sleep(3)
        return f"✅ {success} مورد ثبت شد."
    except Exception as e: return f"❌ خطا: {str(e)}"
    finally: driver.quit()

# --- دکمه‌ها ---
def main_menu_keyboard():
    return ReplyKeyboardMarkup([[KeyboardButton("⚙️ تنظیمات حساب")], [KeyboardButton("➕ افزودن بار")], [KeyboardButton("🚀 ارسال به سایت")], [KeyboardButton("🔍 سرچ راننده")], [KeyboardButton("❓ راهنما")]], resize_keyboard=True)

def admin_keyboard():
    return ReplyKeyboardMarkup([[KeyboardButton("📊 آمار کاربران")], [KeyboardButton("👁️ نظارت بر فعالیت‌ها")], [KeyboardButton("🆔 مدیریت مجوزها")], [KeyboardButton("🏠 بازگشت به منوی کاربر")]], resize_keyboard=True)

# --- توابع ربات ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_name = update.message.from_user.full_name

    if user_id == ADMIN_ID:
        await update.message.reply_text("👋 خوش آمدید رئیس! شما به عنوان ادمین شناخته شدید.", reply_markup=admin_keyboard())
        return

    # بررسی مجوز کاربر
    if check_approval(user_id) == 1:
        await update.message.reply_text("👋 خوش آمدید! دسترسی شما تایید شده است.", reply_markup=main_menu_keyboard())
    else:
        # ذخیره کاربر در دیتابیس با وضعیت تایید نشده
        conn = sqlite3.connect('users_data.db')
        conn.execute("INSERT OR IGNORE INTO users (user_id, is_approved) VALUES (?, 0)", (user_id,))
        conn.commit()
        conn.close()

        await update.message.reply_text("⚠️ این ربات اشتراکی است. درخواست شما برای سازنده ارسال شد. در صورت تایید، مجوز استفاده برای شما فعال خواهد شد.")
        
        # ارسال اعلان برای ادمین
        keyboard = [
            [InlineKeyboardButton("✅ تایید", callback_data=f"approve_{user_id}"),
             InlineKeyboardButton("❌ رد", callback_data=f"reject_{user_id}")]
        ]
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"🔔 **درخواست جدید!**\n\nکاربر: {user_name}\nآیدی: `{user_id}`\nآیا مجوز استفاده را می‌دهید؟",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    await query.answer()

    if data.startswith("approve_"):
        user_id = int(data.split("_")[1])
        set_approval(user_id, 1)
        await query.edit_message_text(f"✅ کاربر {user_id} تایید شد.")
        await context.bot.send_message(chat_id=user_id, text="🎉 تبریک! دسترسی شما به ربات تایید شد. حالا می‌توانید با زدن /start وارد شوید.")

    elif data.startswith("reject_"):
        user_id = int(data.split("_")[1])
        await query.edit_message_text(f"❌ درخواست کاربر {user_id} رد شد.")
        await context.bot.send_message(chat_id=user_id, text="😔 متاسفانه درخواست شما رد شد.")

async def handle_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.message.from_user.id

    if user_id == ADMIN_ID:
        if text == "📊 آمار کاربران":
            conn = sqlite3.connect('users_data.db')
            count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            approved = conn.execute("SELECT COUNT(*) FROM users WHERE is_approved=1").fetchone()[0]
            conn.close()
            await update.message.reply_text(f"📈 کل کاربران: {count}\n✅ کاربران تایید شده: {approved}")
            return
        elif text == "👁️ نظارت بر فعالیت‌ها":
            conn = sqlite3.connect('users_data.db')
            logs = conn.execute("SELECT user_id, driver_id, weight FROM cargo LIMIT 10").fetchall()
            conn.close()
            log_text = "\n".join([f"👤 کاربر {l[0]} در حال ثبت بار برای {l[1]} (وزن: {l[2]})" for l in logs])
            await update.message.reply_text(f"👀 آخرین فعالیت‌ها:\n\n{log_text if log_text else 'فعالیتی یافت نشد.'}")
            return
        elif text == "🆔 مدیریت مجوزها":
            await update.message.reply_text("لطفاً آیدی عددی کاربر را بفرستید تا مجوز او را تغییر دهم:")
            return ADMIN_MANAGE_ID
        elif text == "🏠 بازگشت به منوی کاربر":
            await update.message.reply_text("بازگشت به منوی کاربر...", reply_markup=main_menu_keyboard())
            return

    # چک کردن مجوز برای کاربران عادی
    if check_approval(user_id) == 0:
        await update.message.reply_text("❌ شما هنوز مجوز استفاده از ربات را ندارید.")
        return

    if text == "⚙️ تنظیمات حساب":
        await update.message.reply_text("نام کاربری سایت را وارد کنید:")
        return SETTING_USER
    elif text == "➕ افزودن بار":
        await update.message.reply_text("فرمت: `آیدی, وزن, مبدا, مقصد, ساعت`", parse_mode='Markdown')
        return WAITING_FOR_DATA
    elif text == "🚀 ارسال به سایت":
        await update.message.reply_text("⏳ در حال ارسال...")
        res = process_baarbarg_entries(user_id)
        await update.message.reply_text(res)
        if "✅" in res: clear_user_cargos(user_id)
    elif text == "🔍 سرچ راننده":
        await update.message.reply_text("آیدی راننده را بفرستید:")
        return WAITING_FOR_ID_SEARCH

async def manage_id_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        target_id = int(update.message.text)
        set_approval(target_id, 1)
        await update.message.reply_text(f"✅ مجوز برای کاربر {target_id} فعال شد.")
    except:
        await update.message.reply_text("⚠️ لطفاً فقط آیدی عددی را بفرستید.")
    return ConversationHandler.END

# (توابع set_user, set_pass, handle_add_data مشابه کد قبلی هستند)
async def set_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['temp_user'] = update.message.text
    await update.message.reply_text("رمز عبور سایت را وارد کنید:")
    return SETTING_PASS

async def set_pass(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    save_user_credentials(user_id, context.user_data['temp_user'], update.message.text)
    await update.message.reply_text("✅ حساب ذخیره شد!", reply_markup=main_menu_keyboard())
    return ConversationHandler.END

async def handle_add_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    try:
        p = [x.strip() for x in update.message.text.split(',')]
        if len(p) < 5: raise ValueError
        save_cargo(user_id, p[0], p[1], p[2], p[3], p[4])
        await update.message.reply_text(f"📦 ذخیره شد.", reply_markup=main_menu_keyboard())
    except: await update.message.reply_text("⚠️ فرمت اشتباه!")
    return ConversationHandler.END

def main():
    init_db()
    app = Application.builder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.TEXT & ~filters.COMMAND, handle_menu)],
        states={
            SETTING_USER: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_user)],
            SETTING_PASS: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_pass)],
            WAITING_FOR_DATA: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_add_data)],
            ADMIN_MANAGE_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, manage_id_action)],
        },
        fallbacks=[CommandHandler('start', start)],
    )

    app.add_handler(CommandHandler('start', start))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(conv_handler)
    app.run_polling()

if __name__ == "__main__":
    main()
  
