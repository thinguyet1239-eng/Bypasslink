import sqlite3
from telebot import TeleBot, types

# CẤU HÌNH CHÍNH
TOKEN = "8528713769:AAFFDFiA_x3AzqYCgR0qttUf1Wim7WGizjI"
ADMIN_ID = 8766063561  # Thay bằng ID Telegram của Admin (Kiểu số)

bot = TeleBot(TOKEN)

# Khởi tạo cơ sở dữ liệu SQL
def init_db():
    conn = sqlite3.connect("bot_data.db")
    cursor = conn.cursor()
    # Bảng người dùng
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY,
                        bypass_count INTEGER DEFAULT 3,
                        status TEXT DEFAULT 'free'
                    )''')
    # Bảng cấu hình nhiệm vụ
    cursor.execute('''CREATE TABLE IF NOT EXISTS config (
                        key TEXT PRIMARY KEY,
                        value TEXT
                    )''')
    cursor.execute("INSERT OR IGNORE INTO config (key, value) VALUES ('task_desc', 'Hãy tham gia nhóm x và xem video y để nhận lượt!')")
    conn.commit()
    conn.close()

init_db()

# Các hàm phụ trợ DB
def get_user(user_id):
    conn = sqlite3.connect("bot_data.db")
    cursor = conn.cursor()
    cursor.execute("SELECT bypass_count FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if not row:
        cursor.execute("INSERT INTO users (user_id, bypass_count) VALUES (?, 3)", (user_id,))
        conn.commit()
        count = 3
    else:
        count = row[0]
    conn.close()
    return count

def update_bypass(user_id, amount):
    conn = sqlite3.connect("bot_data.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET bypass_count = bypass_count + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()
    conn.close()

def get_task():
    conn = sqlite3.connect("bot_data.db")
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM config WHERE key = 'task_desc'")
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else "Chưa có nhiệm vụ."

def update_task(new_desc):
    conn = sqlite3.connect("bot_data.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE config SET value = ? WHERE key = 'task_desc'", (new_desc,))
    conn.commit()
    conn.close()

# MENU BÀN PHÍM
def main_menu(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn_get = types.KeyboardButton("🔗 Bypass link rút gọn")
    btn_task = types.KeyboardButton("🎁 Nhận Lượt Bypass")
    btn_info = types.KeyboardButton("👤 Thông Tin")
    markup.add(btn_get, btn_task)
    markup.add(btn_info)
    if user_id == ADMIN_ID:
        btn_admin = types.KeyboardButton("⚙️ Cập Nhật Nhiệm Vụ")
        markup.add(btn_admin)
    return markup

# LỆNH /START
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    get_user(user_id)  # Khởi tạo user nếu chưa có
    bot.send_message(
        message.chat.id, 
        f"👋 Chào mừng bạn đến với Bot bypass link rút gọn!\n🔥 Bạn đang có: *{get_user(user_id)}* lượt bypass miễn phí.", 
        parse_mode="Markdown", 
        reply_markup=main_menu(user_id)
    )

# XỬ LÝ CLICK NÚT TRÊN MENU
@bot.message_handler(func=lambda message: True)
def handle_menu(message):
    user_id = message.from_user.id
    text = message.text

    if text == "🔗 Bypass link rút gọn":
        lượt = get_user(user_id)
        if lượt <= 0:
            return bot.send_message(message.chat.id, "❌ Bạn đã hết lượt bypass! Hãy bấm '🎁 Nhận Lượt Bypass' để làm thêm nhiệm vụ.")
        
        msg = bot.send_message(message.chat.id, "📝 Vui lòng gửi *Link cần bypass* của bạn vào đây:", parse_mode="Markdown", reply_markup=types.ForceReply(selective=True))
        bot.register_next_step_handler(msg, process_link_bypass)

    elif text == "🎁 Nhận Lượt Bypass":
        task_text = get_task()
        markup = types.InlineKeyboardMarkup()
        btn_done = types.InlineKeyboardButton("✅ Tôi Đã Hoàn Thành", callback_data=f"done_task_{user_id}")
        markup.add(btn_done)
        
        bot.send_message(
            message.chat.id, 
            f"📋 *Nhiệm vụ bắt buộc:*\n\n{task_text}\n\n_Sau khi làm xong, hãy bấm nút xác nhận bên dưới để gửi yêu cầu duyệt tới Admin._", 
            parse_mode="Markdown", 
            reply_markup=markup
        )

    elif text == "👤 Thông Tin":
        lượt = get_user(user_id)
        bot.send_message(message.chat.id, f"👤 *Tài Khoản:* `{user_id}`\n🎫 *Số lượt Bypass còn lại:* {lượt}", parse_mode="Markdown")

    elif text == "⚙️ Cập Nhật Nhiệm Vụ" and user_id == ADMIN_ID:
        msg = bot.send_message(ADMIN_ID, "📝 Hãy nhập nội dung nhiệm vụ mới (Hỗ trợ text, link...):", reply_markup=types.ForceReply(selective=True))
        bot.register_next_step_handler(msg, process_update_task)

# XỬ LÝ GỬI LINK BYPASS
def process_link_bypass(message):
    user_id = message.from_user.id
    link = message.text

    if not link or link.startswith('/'):
        return bot.send_message(message.chat.id, "❌ Huỷ yêu cầu hoặc link không hợp lệ.")

    # Trừ tạm thời 1 lượt
    update_bypass(user_id, -1)

    # Gửi thông báo cho Admin kèm nút bấm inline hành động
    admin_markup = types.InlineKeyboardMarkup()
    btn_approve = types.InlineKeyboardButton("✅ Hoàn Thành", callback_data=f"key_approve_{user_id}")
    btn_reject = types.InlineKeyboardButton("❌ Từ Chối", callback_data=f"key_reject_{user_id}")
    admin_markup.add(btn_approve, btn_reject)

    bot.send_message(
        ADMIN_ID, 
        f"📥 *YÊU CẦU BYPASS MỚI*\n👤 User: `{user_id}`\n🔗 Link: {link}", 
        parse_mode="Markdown", 
        reply_markup=admin_markup
    )
    bot.send_message(message.chat.id, "Đang tiến hành bypass link rút gọn...")

# XỬ LÝ NHẬP KEY SAU KHI ADMIN BẤM HOÀN THÀNH LINK
def process_input_key(message, target_user_id):
    key_value = message.text
    if not key_value or key_value.startswith('/'):
        return bot.send_message(ADMIN_ID, "❌ Đã huỷ gửi key.")

    # Gửi key trả về cho User
    bot.send_message(
        target_user_id, 
        f"🎉 *Bypass thành công ✔️*\n🔑 Link`{key_value}`\n_(Nhấp vào link để tự động sao chép)_", 
        parse_mode="Markdown"
    )
    bot.send_message(ADMIN_ID, f"✅ Đã gửi key thành công cho User `{target_user_id}`.")

# XỬ LÝ ADMIN CẬP NHẬT NHIỆM VỤ MỚI
def process_update_task(message):
    if message.from_user.id != ADMIN_ID: return
    new_desc = message.text
    update_task(new_desc)
    bot.send_message(ADMIN_ID, "✅ Đã cập nhật nội dung nhiệm vụ mới thành công!")

# XỬ LÝ CALLBACK TỪ CÁC NÚT BẤM INLINE (Duyệt/Từ chối)
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    data = call.data

    # --- Xử lý Admin Duyệt Link Get Key ---
    if data.startswith("key_approve_"):
        target_user_id = int(data.split("_")[2])
        # Yêu cầu Admin nhập Key vào chat
        msg = bot.send_message(ADMIN_ID, f"🔑 Hãy nhập *Key* cho User `{target_user_id}` để hệ thống gửi đi:", parse_mode="Markdown", reply_markup=types.ForceReply(selective=True))
        bot.register_next_step_handler(msg, process_input_key, target_user_id)
        bot.answer_callback_query(call.id)
        bot.delete_message(call.message.chat.id, call.message.message_id)

    elif data.startswith("key_reject_"):
        target_user_id = int(data.split("_")[2])
        # Hoàn lại lượt cho User vì bị từ chối
        update_bypass(target_user_id, 1)
        bot.send_message(target_user_id, "❌ Yêu cầu Bypass link của bạn đã thất bại (Link lỗi hoặc không hợp lệ). Lượt của bạn đã được hoàn lại.")
        bot.send_message(ADMIN_ID, f"❌ Đã từ chối yêu cầu Get Key của User `{target_user_id}`.")
        bot.answer_callback_query(call.id)
        bot.delete_message(call.message.chat.id, call.message.message_id)

    # --- Xử lý User Hoàn Thành Nhiệm Vụ & Admin Duyệt ---
    elif data.startswith("done_task_"):
        user_id = int(data.split("_")[2])
        
        # Gửi thông báo xét duyệt nhiệm vụ cho Admin
        task_markup = types.InlineKeyboardMarkup()
        btn_task_yes = types.InlineKeyboardButton("✅ Duyệt (+3 lượt)", callback_data=f"confirm_task_yes_{user_id}")
        btn_task_no = types.InlineKeyboardButton("❌ Từ Chối", callback_data=f"confirm_task_no_{user_id}")
        task_markup.add(btn_task_yes, btn_task_no)

        bot.send_message(ADMIN_ID, f"🔔 *YÊU CẦU DUYỆT NHIỆM VỤ*\n👤 User `{user_id}` báo cáo đã hoàn thành nhiệm vụ.", parse_mode="Markdown", reply_markup=task_markup)
        bot.edit_message_text("⏳ Đã gửi yêu cầu xác minh nhiệm vụ đến Admin. Vui lòng chờ!", call.message.chat.id, call.message.message_id)
        bot.answer_callback_query(call.id)

    elif data.startswith("confirm_task_yes_"):
        target_user_id = int(data.split("_")[3])
        update_bypass(target_user_id, 3) # Cộng 3 lượt bypass
        bot.send_message(target_user_id, "🎉 Admin đã duyệt nhiệm vụ của bạn! *Bạn được cộng thêm 3 lượt bypass.*", parse_mode="Markdown")
        bot.send_message(ADMIN_ID, f"✅ Đã duyệt nhiệm vụ và cộng 3 lượt cho User `{target_user_id}`.")
        bot.delete_message(call.message.chat.id, call.message.message_id)

    elif data.startswith("confirm_task_no_"):
        target_user_id = int(data.split("_")[3])
        bot.send_message(target_user_id, "❌ Yêu cầu duyệt nhiệm vụ bị từ chối. Vui lòng kiểm tra lại xem bạn đã làm đúng yêu cầu chưa.")
        bot.send_message(ADMIN_ID, f"❌ Đã từ chối nhiệm vụ của User `{target_user_id}`.")
        bot.delete_message(call.message.chat.id, call.message.message_id)

# CHẠY BOT
if __name__ == '__main__':
    print("Bot đang chạy...")
    bot.infinity_polling()
