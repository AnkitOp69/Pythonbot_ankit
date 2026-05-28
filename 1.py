
import re
import sqlite3
from datetime import datetime

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup
)

from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    MessageHandler,
    CommandHandler,
    CallbackQueryHandler,
    filters
)

TOKEN = "8843386360:AAFCPzrVvD1tL0_sryX9JMslVkrsjvBINWs"

# =========================================
# DATABASE
# =========================================

conn = sqlite3.connect(
    "tracker.db",
    check_same_thread=False
)

cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_date TEXT,
    bot_name TEXT,
    youtube_channel TEXT,
    amount INTEGER,
    raw_message TEXT
)
""")

conn.commit()

# =========================================
# PATTERNS
# =========================================

BOT_PATTERNS = [
    r'@[\w_]+bot'
]

CHANNEL_PATTERNS = [

    r'CHANNEL NAME\s*[-:]?\s*(.+)',
    r'▶️\s*([A-Za-z0-9 _]+?)\s*▶️',
    r'Youtube Channel Name\s*(.+)',
    r'CHANNEL\s*[:\-]\s*(.+)',
    r'channel name\s*[:\-]\s*(.+)',
    r'CHENNEL NAME\s*[-:]?\s*(.+)',
    r'CHENNEL\s*[:\-]\s*(.+)',
]

AMOUNT_PATTERNS = [

    r'(\d+)\s*Rupees',
    r'(\d+)\s*Milega',
    r'₹\s*(\d+)',
    r'(\d+)₹',
]

# =========================================
# EXTRACT BOT
# =========================================

def extract_bot(text):

    for pattern in BOT_PATTERNS:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:
            return match.group(0)

    return "UnknownBot"

# =========================================
# EXTRACT CHANNEL
# =========================================

def extract_channel(text):

    for pattern in CHANNEL_PATTERNS:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:

            result = match.group(1).strip()

            result = result.replace("▶️", "")
            result = result.strip()

            return result

    return "UnknownChannel"

# =========================================
# EXTRACT AMOUNT
# =========================================

def extract_amount(text):

    for pattern in AMOUNT_PATTERNS:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:

            try:
                return int(match.group(1))
            except:
                pass

    return 0

# =========================================
# SAVE TASK
# =========================================

def save_task(bot_name, channel, amount, raw_message):

    today = datetime.now().strftime("%Y-%m-%d")

    cursor.execute("""
    INSERT INTO tasks (
        task_date,
        bot_name,
        youtube_channel,
        amount,
        raw_message
    )
    VALUES (?, ?, ?, ?, ?)
    """, (
        today,
        bot_name,
        channel,
        amount,
        raw_message
    ))

    conn.commit()

    # TXT LOG
    with open(
        "entries.txt",
        "a",
        encoding="utf-8"
    ) as f:

        f.write(
            f"{today} | "
            f"{bot_name} | "
            f"{channel} | "
            f"₹{amount}\n"
        )

# =========================================
# START
# =========================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    keyboard = [
        [
            InlineKeyboardButton(
                "📊 Today Stats",
                callback_data="today_stats"
            )
        ]
    ]

    inline_markup = InlineKeyboardMarkup(
        keyboard
    )

    permanent_keyboard = ReplyKeyboardMarkup(
        [
            ["/today", "/end"],
            ["/report", "/commands"],
            ["/pending", "/total"]
        ],
        resize_keyboard=True
    )

    await update.message.reply_text(
        "🔥 Smart Tracker Running 🔥",
        reply_markup=permanent_keyboard
    )

    await update.message.reply_text(
        "Choose option 👇",
        reply_markup=inline_markup
    )

# =========================================
# BUTTON HANDLER
# =========================================

async def button_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()

    if query.data == "today_stats":

        today = datetime.now().strftime("%Y-%m-%d")

        cursor.execute("""
        SELECT COUNT(*),
        COALESCE(SUM(amount),0)
        FROM tasks
        WHERE task_date = ?
        """, (today,))

        tasks, amount = cursor.fetchone()

        await query.message.reply_text(
            f"📊 TODAY\n\n"
            f"Tasks: {tasks}\n"
            f"Total ₹: {amount}"
        )

# =========================================
# TODAY
# =========================================

async def today_entries(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    today = datetime.now().strftime("%Y-%m-%d")

    cursor.execute("""
    SELECT bot_name,
    youtube_channel,
    amount
    FROM tasks
    WHERE task_date = ?
    ORDER BY id ASC
    """, (today,))

    rows = cursor.fetchall()

    if not rows:

        await update.message.reply_text(
            "❌ No entries today"
        )

        return

    total = 0
    lines = []

    for i, (bot, yt, amt) in enumerate(
        rows,
        start=1
    ):

        lines.append(
            f"{i}. {bot} - {yt} (₹{amt})"
        )

        total += amt

    full_text = (
        f"📅 TODAY ({today})\n\n"
        + "\n".join(lines)
        + f"\n\n💰 Total: ₹{total}"
    )

    chunk_size = 3500

    for i in range(
        0,
        len(full_text),
        chunk_size
    ):

        await update.message.reply_text(
            full_text[i:i+chunk_size]
        )

# =========================================
# END
# =========================================

async def end_day(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    today = datetime.now().strftime("%Y-%m-%d")

    cursor.execute("""
    SELECT COUNT(*),
    COALESCE(SUM(amount),0)
    FROM tasks
    WHERE task_date = ?
    """, (today,))

    total_tasks, total_amount = (
        cursor.fetchone()
    )

    await update.message.reply_text(
        f"📊 TODAY REPORT ({today})\n\n"
        f"📌 Total Tasks: {total_tasks}\n"
        f"💰 Total Amount: ₹{total_amount}"
    )

# =========================================
# REPORT
# =========================================

async def report(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    context.user_data[
        "awaiting_report_date"
    ] = True

    await update.message.reply_text(
        "📅 Send report date:\nYYYY-MM-DD"
    )

async def generate_report(
    update,
    selected_date
):

    cursor.execute("""
    SELECT bot_name,
    youtube_channel,
    amount
    FROM tasks
    WHERE task_date = ?
    ORDER BY bot_name ASC, id ASC
    """, (selected_date,))

    rows = cursor.fetchall()

    if not rows:

        await update.message.reply_text(
            "❌ No entries found"
        )

        return

    grouped = {}

    total = 0

    for bot, yt, amt in rows:

        if bot not in grouped:
            grouped[bot] = []

        grouped[bot].append(
            (yt, amt)
        )

        total += amt

    text = (
        f"📊 REPORT "
        f"({selected_date})\n\n"
    )

    counter = 1

    for bot in sorted(grouped.keys()):

        text += f"🔥 {bot}\n"

        for yt, amt in grouped[bot]:

            text += (
                f"{counter}. "
                f"{yt} (₹{amt})\n"
            )

            counter += 1

        text += "\n"

    text += f"💰 TOTAL = ₹{total}"

    chunk_size = 3500

    for i in range(
        0,
        len(text),
        chunk_size
    ):

        await update.message.reply_text(
            text[i:i+chunk_size]
        )

# =========================================
# TOTAL
# =========================================

async def total(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    cursor.execute("""
    SELECT COUNT(*),
    COALESCE(SUM(amount),0)
    FROM tasks
    """)

    tasks, amount = cursor.fetchone()

    await update.message.reply_text(
        f"📈 Lifetime Stats\n\n"
        f"Tasks: {tasks}\n"
        f"Total ₹: {amount}"
    )

# =========================================
# PENDING
# =========================================

async def pending(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await update.message.reply_text(
        "💸 Pending tracking disabled"
    )

# =========================================
# COMMANDS
# =========================================

async def commands_list(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    msg = (
        "📚 AVAILABLE COMMANDS\n\n"

        "/start → Open dashboard\n"
        "/today → Show today's entries\n"
        "/end → Show today's report\n"
        "/report → Show report of any date\n"
        "/pending → Pending amount\n"
        "/total → Lifetime total\n"
        "/commands → Show commands"
    )

    await update.message.reply_text(msg)

# =========================================
# HANDLE MESSAGE
# =========================================

async def handle_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    try:

        text = (
            update.message.text
            or update.message.caption
            or ""
        )

        print("RECEIVED:", text)

        if not text:
            return

        # IGNORE COMMANDS
        if text.startswith("/"):
            return

        # REPORT DATE MODE
        if context.user_data.get(
            "awaiting_report_date"
        ):

            context.user_data[
                "awaiting_report_date"
            ] = False

            await generate_report(
                update,
                text.strip()
            )

            return

        # EXTRACT
        bot_name = extract_bot(text)

        youtube_channel = (
            extract_channel(text)
        )

        amount = extract_amount(text)

        # SAVE
        save_task(
            bot_name,
            youtube_channel,
            amount,
            text
        )

        await update.message.reply_text(
            "✅ Task Saved\n\n"
            f"{bot_name}\n"
            f"{youtube_channel}\n"
            f"₹{amount}"
        )

    except Exception as e:

        print("ERROR:", e)

# =========================================
# APP
# =========================================

app = (
    ApplicationBuilder()
    .token(TOKEN)
    .build()
)

app.add_handler(
    CommandHandler("start", start)
)

app.add_handler(
    CommandHandler("today", today_entries)
)

app.add_handler(
    CommandHandler("end", end_day)
)

app.add_handler(
    CommandHandler("report", report)
)

app.add_handler(
    CommandHandler("pending", pending)
)

app.add_handler(
    CommandHandler("total", total)
)

app.add_handler(
    CommandHandler(
        "commands",
        commands_list
    )
)

app.add_handler(
    CallbackQueryHandler(
        button_handler
    )
)

app.add_handler(
    MessageHandler(
        filters.ALL,
        handle_message
    )
)

print("🔥 Smart Tracker Running...")

app.run_polling()

