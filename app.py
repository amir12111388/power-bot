import logging
import random
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, CallbackQueryHandler, filters

# --- تنظیمات اولیه ---
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# ذخیره داده‌ها در حافظه (در پروژه‌های بزرگتر از Database استفاده شود)
user_data = {}  # {user_id: {'name': str, 'gems': int}}
active_games = {}  # {chat_id: {'type': str, 'players': dict, 'amount': int, 'status': str, 'turn': int}}

# --- توابع کمکی ---
def get_user_data(user_id, context):
    if user_id not in user_data:
        user_data[user_id] = {
            'name': context.effective_user.first_name,
            'gems': 100  # الماس اولیه
        }
    return user_data[user_id]

# --- دستورات اصلی ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    get_user_data(user.id, context)
    
    welcome_text = (
        f"👋 سلام {user.first_name} عزیز، به **Power Bot** خوش آمدی!\n\n"
        "🤖 من یک ربات سرگرمی هستم که می‌تونیم با هم بازی کنیم و الماس جمع کنیم.\n\n"
        "🛠 **دستورات و قابلیت‌ها:**\n"
        "• `سنگ کاغذ قیچی <مقدار>` - شروع بازی کلاسیک\n"
        "• `حدس عدد <مقدار>` - چالش حدس عدد\n"
        "• `موجودی` - مشاهده الماس‌های شما\n"
        "• `استخراج` - دریافت اطلاعات بیشتر\n"
        "• `بازی‌ها` - لیست بازی‌های موجود\n"
    )
    
    keyboard = [[InlineKeyboardButton("📖 راهنما", callback_data="help_guide")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(welcome_text, parse_mode="Markdown", reply_markup=reply_markup)

async def help_guide(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    guide_text = (
        "📖 **راهنمای استفاده از Power Bot**\n\n"
        "1️⃣ **بازی سنگ کاغذ قیچی:**\n"
        "بنویس: `سنگ کاغذ قیچی 50`\n"
        "(عدد ۵۰ یعنی شرط شما ۵۰ الماس است)\n\n"
        "2️⃣ **بازی حدس عدد:**\n"
        "بنویس: `حدس عدد 20`\n"
        "(عدد ۲۰ یعنی شرط شما ۲۰ الماس است)\n\n"
        "⚠️ **نکته:** همیشه دقت کنید که الماس کافی برای شرط خود داشته باشید!"
    )
    await query.edit_message_text(guide_text, parse_mode="Markdown")

async def check_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = get_user_data(user_id, context)
    await update.message.reply_text(f"💎 موجودی شما: `{data['gems']}` الماس", parse_mode="Markdown")

# --- سیستم تشخیص هوشمند (Regex) ---
async def smart_detector(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if not text: return
    
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    # تشخیص موجودی
    if re.search(r"(موجودی|الماس|پول)", text):
        await check_balance(update, context)
        return

    # تشخیص بازی سنگ کاغذ قیچی
    rock_paper_scissors_match = re.search(r"سنگ کاغذ قیچی\s+(\d+)", text)
    if rock_paper_scissors_match:
        amount = int(rock_paper_scissors_match.group(1))
        await start_rps_game(update, context, amount)
        return

    # تشخیص بازی حدس عدد
    guess_number_match = re.search(r"حدس عدد\s+(\d+)", text)
    if guess_number_match:
        amount = int(guess_number_match.group(1))
        await start_guess_number_game(update, context, amount)
        return

# --- منطق بازی سنگ کاغذ قیچی ---
async def start_rps_game(update: Update, context: ContextTypes.DEFAULT_TYPE, amount: int):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    user = get_user_data(user_id, context)

    if user['gems'] < amount:
        return await update.message.reply_text("❌ الماس کافی ندارید!")

    if chat_id in active_games:
        return await update.message.reply_text("❌ یک بازی در حال اجرا هست. اول اون رو تموم کن.")

    active_games[chat_id] = {
        'type': 'rps',
        'players': {user_id: {'name': user['name'], 'choice': None}},
        'amount': amount,
        'status': 'waiting',
        'turn': user_id
    }

    keyboard = [[InlineKeyboardButton("➕ شرکت در بازی", callback_data="join_game")]]
    await update.message.reply_text(
        f"🎮 **بازی سنگ کاغذ قیچی!**\n\n"
        f"💰 شرط: `{amount}` الماس\n"
        f"👤 بازیکن اول: {user['name']}\n"
        f"⏳ منتظر بازیکن دوم...",
        parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard)
    )

# --- منطق بازی حدس عدد ---
async def start_guess_number_game(update: Update, context: ContextTypes.DEFAULT_TYPE, amount: int):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    user = get_user_data(user_id, context)

    if user['gems'] < amount:
        return await update.message.reply_text("❌ الماس کافی ندارید!")

    if chat_id in active_games:
        return await update.message.reply_text("❌ یک بازی در حال اجرا هست.")

    active_games[chat_id] = {
        'type': 'number_guess',
        'players': {user_id: {'name': user['name'], 'choice': None}},
        'amount': amount,
        'status': 'waiting',
        'turn': user_id
    }

    keyboard = [[InlineKeyboardButton("➕ شرکت در بازی", callback_data="join_game")]]
    await update.message.reply_text(
        f"🔢 **بازی حدس عدد!**\n\n"
        f"💰 شرط: `{amount}` الماس\n"
        f"👤 بازیکن اول: {user['name']}\n"
        f"⏳ منتظر بازیکن دوم...",
        parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard)
    )

# --- هندلر دکمه‌های شیشه‌ای ---
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    chat_id = query.message.chat_id
    await query.answer()

    if query.data == "help_guide":
        await help_guide(update, context)
    
    elif query.data == "join_game":
        if chat_id not in active_games:
            return await query.edit_message_text("❌ بازی پیدا نشد.")
        
        game = active_games[chat_id]
        if user_id in game['players']:
            return await query.edit_message_text("❌ شما قبلاً در این بازی شرکت کردید.")
        
        # اضافه کردن بازیکن دوم
        user = get_user_data(user_id, context)
        if user['gems'] < game['amount']:
            return await query.edit_message_text("❌ الماس کافی برای شرکت ندارید!")

        game['players'][user_id] = {'name': user['name'], 'choice': None}
        game['status'] = 'ongoing'
        
        # شروع بازی بر اساس نوع
        if game['type'] == 'rps':
            keyboard = [
                [InlineKeyboardButton("🪨 سنگ", callback_data="rps_rock"),
                 InlineKeyboardButton("📄 کاغذ", callback_data="rps_paper"),
                 InlineKeyboardButton("✂️ قیچی", callback_data="rps_scissors")]
            ]
            await query.edit_message_text(f"🎮 بازی شروع شد!\nنوبت: {user['name']}\nلطفاً انتخاب کنید:", 
                                         reply_markup=InlineKeyboardMarkup(keyboard))
        
        elif game['type'] == 'number_guess':
            await query.edit_message_text(f"🔢 بازی حدس عدد شروع شد!\nنوبت: {user['name']}\nلطفاً در چت عدد خود را بنویسید (بین ۱ تا ۱۰۰).")

    elif query.data.startswith("rps_"):
        # مدیریت انتخاب‌های سنگ کاغذ قیچی
        if chat_id not in active_games or active_games[chat_id]['type'] != 'rps': return
        
        game = active_games[chat_id]
        choice_map = {"rps_rock": "🪨", "rps_paper": "📄", "rps_scissors": "✂️"}
        game['players'][user_id]['choice'] = choice_map[query.data]

        # بررسی وضعیت بازی
        p_ids = list(game['players'].keys())
        if len(p_ids) == 2 and game['players'][p_ids[0]]['choice'] and game['players'][p_ids[1]]['choice']:
            # پایان بازی RPS
            p1_id, p2_id = p_ids[0], p_ids[1]
            p1 = game['players'][p1_id]
            p2 = game['players'][p2_id]
            
            c1, c2 = p1['choice'], p2['choice']
            
            # منطق برنده
            if c1 == c2:
                res_text = "🤝 نتیجه مساوی شد!"
                winner = None
            elif (c1 == "🪨" and c2 == "✂️") or (c1 == "📄" and c2 == "🪨") or (c1 == "✂️" and c2 == "📄"):
                res_text = f"🏆 {p1['name']} برنده شد!"
                winner = p1_id
            else:
                res_text = f"🏆 {p2['name']} برنده شد!"
                winner = p2_id

            if winner:
                get_user_data(winner, context)['gems'] += game['amount'] * 2
            
            await query.edit_message_text(f"{res_text}\n\n{p1['name']}: {c1}\n{p2['name']}: {c2}\n💰 جایزه: {game['amount'] if winner else 0}")
            del active_games[chat_id]
        else:
            # نوبت به نفر بعدی داده می‌شود (در این حالت منتظر نفر دوم می‌مانیم)
            await query.edit_message_text(f"✅ انتخاب ثبت شد. منتظر بازیکن دوم...")

# --- مدیریت پیام‌های متنی (برای حدس عدد) ---
async def handle_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    text = update.message.text

    # اول چک کردن تشخیص هوشمند (موجودی و ...)
    await smart_detector(update, context)

    # اگر بازی حدس عدد در جریان بود
    if chat_id in active_games and active_games[chat_id]['type'] == 'number_guess':
        game = active_games[chat_id]
        if game['status'] == 'ongoing':
            # چک کردن نوبت
            if user_id != game['turn']:
                return # نوبت این کاربر نیست

            try:
                guess = int(text)
                if not (1 <= guess <= 100): raise ValueError
                game['players'][user_id]['choice'] = guess
                
                p_ids = list(game['players'].keys())
                if len(p_ids) == 2 and game['players'][p_ids[0]]['choice'] is not None and game['players'][p_ids[1]]['choice'] is not None:
                    # پایان بازی حدس عدد
                    p1_id, p2_id = p_ids[0], p_ids[1]
                    p1_data = game['players'][p1_id]
                    p2_data = game['players'][p2_id]
                    
                    winning_number = random.randint(1, 100)
                    
                    # محاسبه فاصله
                    diff1 = abs(p1_data['choice'] - winning_number)
                    diff2 = abs(p2_data['choice'] - winning_number)
                    
                    winner_id = None
                    if diff1 < diff2: winner_id = p1_id
                    elif diff2 < diff1: winner_id = p2_id
                    else: winner_id = random.choice([p1_id, p2_id])

                    # نمایش نتیجه با استفاده از f-string اصلاح شده برای جلوگیری از خطا
                    if winner_id == p1_id:
                        get_user_data(p1_id, context)['gems'] += game['amount'] * 2
                        w_name = p1_data['name']
                    else:
                        get_user_data(p2_id, context)['gems'] += game['amount'] * 2
                        w_name = p2_data['name']

                    res = (
                        f"🏆 {w_name} برنده شد!\n"
                        f"🔢 عدد برنده: {winning_number}\n"
                        f"👤 {p1_data['name']} حدس زد: {p1_data['choice']}\n"
                        f"👤 {p2_data['name']} حدس زد: {p2_data['choice']}\n\n"
                        f"💰 جایزه: {game['amount'] * 2} الماس"
                    )
                    await update.message.reply_text(res)
                    del active_games[chat_id]
                else:
                    # جابجایی نوبت
                    p_ids = list(game['players'].keys())
                    next_user = p_ids[1] if user_id == p_ids[0] else p_ids[0]
                    game['turn'] = next_user
                    await update.message.reply_text(f"✅ عدد ثبت شد. نوبت {game['players'][next_user]['name']} است.")
            
            except ValueError:
                await update.message.reply_text("❌ لطفاً فقط یک عدد بین ۱ تا ۱۰۰ وارد کنید.")

# --- اجرای اصلی ---
if __name__ == '__main__':
    # جایگزین کردن توکن خودت
    TOKEN = "8313663833:AAFs9OooWD5Nx54qE0dcTqz6KlCJVrgt7UU"
    
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_messages))

    print("🚀 Power Bot is running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)
