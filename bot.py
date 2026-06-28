import os
import random
import time
import threading
from datetime import datetime, timedelta, date
from telebot import TeleBot, types
from supabase import create_client
from flask import Flask, send_from_directory

# --- FLASK ДЛЯ ПОРТА ---
flask_app = Flask(__name__, static_folder='webapp')

@flask_app.route('/')
def home():
    return send_from_directory('webapp', 'index.html')

@flask_app.route('/ping')
def ping():
    return "pong", 200

def run_flask():
    port = int(os.environ.get('PORT', 10000))
    flask_app.run(host='0.0.0.0', port=port)

# --- НАСТРОЙКИ ---
TOKEN = "8869752953:AAF2gOnS-bFts-EGsS1PZZ4pfUrRXLwkN-M"
SUPABASE_URL = "https://jzscsndwuchzlellgqea.supabase.co"
SUPABASE_KEY = "sb_publishable_-kqOsr7gFZRi8ctCNPaLgg_4mjU-NZy"

bot = TeleBot(TOKEN)
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- ЗВУКИ ---
SOUNDS = {
    "кошка": ["мяу", "мур", "фыр"],
    "собака": ["гав", "тяф", "вуф"],
    "лиса": ["фыр", "кхе", "тяф"],
    "панда": ["хрум", "фырк", "пых"],
    "кролик": ["цок", "фыр", "хрум"],
    "ёжик": ["фырк", "пых", "цок"],
    "пингвин": ["фыр", "кхе", "цок"]
}

PET_EMOJIS = {
    "кошка": "🐱",
    "собака": "🐶",
    "лиса": "🦊",
    "панда": "🐼",
    "кролик": "🐇",
    "ёжик": "🦔",
    "пингвин": "🐧"
}

ATTR_EMOJIS = {
    "голод": "🥩",
    "счастье": "🍽",
    "гигиена": "🫧",
    "энергия": "⚡",
    "дисциплина": "📏",
    "лапки": "🐾"
}

# --- ДАННЫЕ ---
user_states = {}
game_data = {}
dice_cooldown = {}

# --- БАЗА ---
def get_pet(user_id):
    response = supabase.table('pets').select('*').eq('user_id', user_id).execute()
    if response.data:
        return response.data[0]
    return None

def update_pet(user_id, data):
    supabase.table('pets').update(data).eq('user_id', user_id).execute()

def get_achievements():
    response = supabase.table('achievements').select('*').execute()
    return response.data if response.data else []

def get_user_achievements(user_id):
    response = supabase.table('user_achievements').select('achievement_id').eq('user_id', user_id).execute()
    return [a['achievement_id'] for a in response.data] if response.data else []

def unlock_achievement(user_id, achievement_id):
    supabase.table('user_achievements').insert({
        'user_id': user_id,
        'achievement_id': achievement_id,
        'unlocked_at': datetime.now().isoformat()
    }).execute()

def check_achievements(user_id, pet):
    achievements = get_achievements()
    user_ach = get_user_achievements(user_id)
    for ach in achievements:
        if ach['id'] in user_ach:
            continue
        unlocked = False
        cond = ach['condition_type']
        val = ach['condition_value']
        if cond == 'messages' and pet['total_messages'] >= val:
            unlocked = True
        elif cond == 'dice_games' and pet.get('games_played', 0) >= val:
            unlocked = True
        elif cond == 'dice_wins' and pet.get('games_won', 0) >= val:
            unlocked = True
        elif cond == 'guess_games' and pet.get('guess_games', 0) >= val:
            unlocked = True
        elif cond == 'guess_hard_wins' and pet.get('guess_hard_wins', 0) >= val:
            unlocked = True
        elif cond == 'guess_wins' and pet.get('guess_wins', 0) >= val:
            unlocked = True
        elif cond == 'total_games' and pet.get('games_played', 0) >= val:
            unlocked = True
        elif cond == 'feed_count' and pet.get('feed_count', 0) >= val:
            unlocked = True
        elif cond == 'wash_count' and pet.get('wash_count', 0) >= val:
            unlocked = True
        elif cond == 'sleep_count' and pet.get('sleep_count', 0) >= val:
            unlocked = True
        elif cond == 'train_count' and pet.get('train_count', 0) >= val:
            unlocked = True
        elif cond == 'total_actions' and pet.get('total_actions', 0) >= val:
            unlocked = True
        elif cond == 'lapki_earned' and pet.get('total_lapki_earned', 0) >= val:
            unlocked = True
        elif cond == 'streak' and pet.get('streak', 0) >= val:
            unlocked = True
        if unlocked:
            unlock_achievement(user_id, ach['id'])
            bot.send_message(user_id, f"🏆 {ach['emoji']} {ach['name']}!\n{ach['description']}")

def get_stage(messages):
    if messages < 100:
        return "Зарождение ✨"
    elif messages < 251:
        return "Яйцо 🥚"
    elif messages < 501:
        return "Малыш 🐣"
    elif messages < 1001:
        return "Подросток 🧒"
    else:
        return "Взрослый 🧑"

# --- КОМАНДЫ ---
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id,
        "🐾 Приветик! Я твой призрачный питомец!\n"
        "Вот список команд, которые я могу тебе предложить!)\n\n"
        "/newpet — выбрать кем я буду\n"
        "/status — мое состояние\n"
        "/name — дай мне кличку\n"
        "/feed — покормить\n"
        "/play — поиграть\n"
        "/wash — помыть\n"
        "/sleep — уложить спать\n"
        "/train — тренировать\n"
        "/daily — ежедневный бонус\n"
        "/app — посмотреть на меня\n"
        "/help — список команд"
    )

@bot.message_handler(commands=['help'])
def help_command(message):
    start(message)

@bot.message_handler(commands=['newpet'])
def new_pet(message):
    user_id = message.from_user.id
    if get_pet(user_id):
        bot.send_message(message.chat.id, "У тебя уже есть питомец!")
        return
    text = (
        "Какого питомца заведем? 🐾\n\n"
        "Выбери своего нового друга из списка:\n\n"
        "🐱 кошка — ласковая, мурлыкает\n"
        "🐶 собака — верная, любит играть\n"
        "🦊 лиса — хитрая, игривая\n"
        "🐼 панда — уютная, медлительная\n"
        "🐇 кролик — пушистый, шустрый\n"
        "🦔 ёжик — милый, немного колючий\n"
        "🐧 пингвин — забавный, любит снег\n\n"
        "Расскажи мне, кого ты хочешь завести?\n"
        "Просто напиши название:\n"
        "кошка, собака, лиса, панда, кролик, ёжик или пингвин 🐾"
    )
    bot.send_message(message.chat.id, text)
    user_states[user_id] = 'awaiting_pet_type'

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == 'awaiting_pet_type')
def set_pet_type(message):
    user_id = message.from_user.id
    pet_type = message.text.lower().strip()
    if pet_type not in PET_EMOJIS:
        bot.send_message(message.chat.id, "❌ Неверный тип. Напиши: кошка, собака, лиса, панда, кролик, ёжик или пингвин")
        return
    supabase.table('pets').insert({
        'user_id': user_id,
        'pet_type': pet_type,
        'pet_name': 'Питомец',
        'stage': 'Зарождение',
        'total_messages': 0,
        'голод': 50,
        'счастье': 50,
        'гигиена': 50,
        'энергия': 50,
        'дисциплина': 50,
        'дни': 0,
        'лапки': 0,
        'joined_at': date.today().isoformat(),
        'streak': 1
    }).execute()
    user_states.pop(user_id, None)
    bot.send_message(message.chat.id, f"✅ Ты выбрал {PET_EMOJIS[pet_type]} {pet_type.capitalize()}! Чтобы он вылупился, нужно 100 сообщений.")

@bot.message_handler(commands=['status'])
def status(message):
    user_id = message.from_user.id
    pet = get_pet(user_id)
    if not pet:
        bot.send_message(message.chat.id, "Нет питомца. /newpet")
        return
    emoji = PET_EMOJIS.get(pet['pet_type'], "🐾")
    stage = get_stage(pet['total_messages'])
    text = (
        f"Питомец {emoji}\n"
        f"Стадия: {stage}\n"
        f"{ATTR_EMOJIS['голод']} Голод: {pet['голод']}\n"
        f"{ATTR_EMOJIS['счастье']} Счастье: {pet['счастье']}\n"
        f"{ATTR_EMOJIS['гигиена']} Гигиена: {pet['гигиена']}\n"
        f"{ATTR_EMOJIS['энергия']} Энергия: {pet['энергия']}\n"
        f"{ATTR_EMOJIS['дисциплина']} Дисциплина: {pet['дисциплина']}\n"
        f"{ATTR_EMOJIS['лапки']} Лапки: {pet['лапки']}"
    )
    bot.send_message(message.chat.id, text)

@bot.message_handler(commands=['name'])
def set_name(message):
    user_id = message.from_user.id
    pet = get_pet(user_id)
    if not pet:
        bot.send_message(message.chat.id, "Сначала заведи питомца через /newpet")
        return
    bot.send_message(message.chat.id, "✏️ Напиши новое имя для своего питомца:")
    user_states[user_id] = 'awaiting_name'

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == 'awaiting_name')
def save_name(message):
    user_id = message.from_user.id
    name = message.text.strip()
    if len(name) > 20:
        bot.send_message(message.chat.id, "❌ Имя слишком длинное (максимум 20 символов)")
        return
    update_pet(user_id, {'pet_name': name})
    user_states.pop(user_id, None)
    bot.send_message(message.chat.id, f"✅ Отлично! Теперь твоего питомца зовут {name}!")

@bot.message_handler(commands=['feed'])
def feed(message):
    user_id = message.from_user.id
    pet = get_pet(user_id)
    if not pet:
        bot.send_message(message.chat.id, "Сначала /newpet")
        return
    if pet.get('sleep_until') and datetime.fromisoformat(pet['sleep_until']) > datetime.now():
        bot.send_message(message.chat.id, "😴 Питомец спит! Подожди, пока он проснётся.")
        return
    if pet['голод'] >= 100:
        bot.send_message(message.chat.id, "Я уже сыт! Не корми меня больше 🍖")
        return
    new_val = min(100, pet['голод'] + 20)
    update_pet(user_id, {'голод': new_val, 'feed_count': pet.get('feed_count', 0) + 1})
    sound = random.choice(SOUNDS.get(pet['pet_type'], ["мяу"]))
    bot.send_message(message.chat.id, f"🍽️ Покормлен! Голод +20\n{sound}!")

@bot.message_handler(commands=['play'])
def play(message):
    user_id = message.from_user.id
    pet = get_pet(user_id)
    if not pet:
        bot.send_message(message.chat.id, "Сначала /newpet")
        return
    if pet.get('sleep_until') and datetime.fromisoformat(pet['sleep_until']) > datetime.now():
        bot.send_message(message.chat.id, "😴 Питомец спит! Подожди, пока он проснётся.")
        return
    if pet['энергия'] < 30:
        bot.send_message(message.chat.id, "Я слишком устал! Дай мне поспать 😴")
        return
    new_s = min(100, pet['счастье'] + 15)
    new_h = max(0, pet['голод'] - 2)
    new_e = max(0, pet['энергия'] - 10)
    series = pet.get('games_series', 0) + 1
    if series >= 3:
        new_h = max(0, new_h - 5)
        series = 0
    update_pet(user_id, {'счастье': new_s, 'голод': new_h, 'энергия': new_e, 'games_series': series})
    sound = random.choice(SOUNDS.get(pet['pet_type'], ["мяу"]))
    bot.send_message(message.chat.id, f"⚾ Поиграл! Счастье +15, Энергия -10, Голод -2\n{sound}!")

@bot.message_handler(commands=['wash'])
def wash(message):
    user_id = message.from_user.id
    pet = get_pet(user_id)
    if not pet:
        bot.send_message(message.chat.id, "Сначала /newpet")
        return
    if pet.get('sleep_until') and datetime.fromisoformat(pet['sleep_until']) > datetime.now():
        bot.send_message(message.chat.id, "😴 Питомец спит! Подожди, пока он проснётся.")
        return
    new_val = min(100, pet['гигиена'] + 25)
    update_pet(user_id, {'гигиена': new_val, 'wash_count': pet.get('wash_count', 0) + 1})
    sound = random.choice(SOUNDS.get(pet['pet_type'], ["мяу"]))
    bot.send_message(message.chat.id, f"🫧 Помыт! Гигиена +25\n{sound}!")

@bot.message_handler(commands=['sleep'])
def sleep_command(message):
    user_id = message.from_user.id
    pet = get_pet(user_id)
    if not pet:
        bot.send_message(message.chat.id, "Сначала /newpet")
        return
    if pet['энергия'] >= 100:
        bot.send_message(message.chat.id, "😊 Питомец не хочет спать! У него полная энергия.")
        return
    sleep_until = (datetime.now() + timedelta(hours=1)).isoformat()
    update_pet(user_id, {'sleep_until': sleep_until, 'sleep_count': pet.get('sleep_count', 0) + 1})
    bot.send_message(message.chat.id, "💤 Питомец уснул! Он проснётся через час.")

@bot.message_handler(commands=['train'])
def train(message):
    user_id = message.from_user.id
    pet = get_pet(user_id)
    if not pet:
        bot.send_message(message.chat.id, "Сначала /newpet")
        return
    if pet.get('sleep_until') and datetime.fromisoformat(pet['sleep_until']) > datetime.now():
        bot.send_message(message.chat.id, "😴 Питомец спит! Подожди, пока он проснётся.")
        return
    if pet['энергия'] < 20:
        bot.send_message(message.chat.id, "Я слишком устал для тренировки! 😴")
        return
    new_val = min(100, pet['дисциплина'] + 15)
    update_pet(user_id, {'дисциплина': new_val})
    sound = random.choice(SOUNDS.get(pet['pet_type'], ["мяу"]))
    bot.send_message(message.chat.id, f"⚡ Тренировка! Дисциплина +15\n{sound}!")

@bot.message_handler(commands=['dice'])
def dice_game(message):
    user_id = message.from_user.id
    pet = get_pet(user_id)
    if not pet:
        bot.send_message(message.chat.id, "Сначала заведи питомца через /newpet")
        return
    if pet.get('sleep_until') and datetime.fromisoformat(pet['sleep_until']) > datetime.now():
        bot.send_message(message.chat.id, "😴 Питомец спит! Подожди, пока он проснётся.")
        return
    now = time.time()
    if user_id in dice_cooldown and now - dice_cooldown[user_id] < 60:
        bot.send_message(message.chat.id, "⏳ Подожди 60 секунд перед следующим броском!")
        return
    dice_cooldown[user_id] = now
    user_roll = random.randint(1, 6)
    bot_roll = random.randint(1, 6)
    dice_emojis = {1: '⚀', 2: '⚁', 3: '⚂', 4: '⚃', 5: '⚄', 6: '⚅'}
    text = f"🎲 Ты выбросил: {dice_emojis[user_roll]} ({user_roll})\n🎲 Я выбросил: {dice_emojis[bot_roll]} ({bot_roll})\n"
    if user_roll > bot_roll:
        series = pet.get('games_series', 0) + 1
        win_bonus = 5 * series
        text += f"✅ Ты выиграл! +{win_bonus} лапок!"
        update_pet(user_id, {'лапки': pet['лапки'] + win_bonus, 'games_series': series, 'games_played': pet.get('games_played', 0) + 1, 'games_won': pet.get('games_won', 0) + 1, 'total_lapki_earned': pet.get('total_lapki_earned', 0) + win_bonus})
    elif user_roll < bot_roll:
        text += "❌ Ты проиграл! Ничего не заработал."
        update_pet(user_id, {'games_series': 0, 'games_played': pet.get('games_played', 0) + 1})
    else:
        text += "🤝 Ничья! Никто не получил лапок."
        update_pet(user_id, {'games_played': pet.get('games_played', 0) + 1})
    bot.send_message(message.chat.id, text)

@bot.message_handler(commands=['guess_easy'])
def guess_easy(message):
    user_id = message.from_user.id
    pet = get_pet(user_id)
    if not pet:
        bot.send_message(message.chat.id, "Сначала заведи питомца через /newpet")
        return
    if pet.get('sleep_until') and datetime.fromisoformat(pet['sleep_until']) > datetime.now():
        bot.send_message(message.chat.id, "😴 Питомец спит! Подожди, пока он проснётся.")
        return
    number = random.randint(1, 10)
    game_data[user_id] = {'type': 'easy', 'number': number, 'attempts': 0, 'max_attempts': 3}
    bot.send_message(message.chat.id, "🔢 Я загадал число от 1 до 10. У тебя 3 попытки! Напиши число.")

@bot.message_handler(commands=['guess_hard'])
def guess_hard(message):
    user_id = message.from_user.id
    pet = get_pet(user_id)
    if not pet:
        bot.send_message(message.chat.id, "Сначала заведи питомца через /newpet")
        return
    if pet.get('sleep_until') and datetime.fromisoformat(pet['sleep_until']) > datetime.now():
        bot.send_message(message.chat.id, "😴 Питомец спит! Подожди, пока он проснётся.")
        return
    number = random.randint(1, 100)
    game_data[user_id] = {'type': 'hard', 'number': number, 'attempts': 0, 'max_attempts': 10}
    bot.send_message(message.chat.id, "🧠 Я загадал число от 1 до 100. У тебя 10 попыток! Напиши число.")

@bot.message_handler(func=lambda message: message.from_user.id in game_data and message.text.isdigit())
def guess_game(message):
    user_id = message.from_user.id
    pet = get_pet(user_id)
    if not pet:
        return
    try:
        guess = int(message.text)
        game = game_data[user_id]
        game['attempts'] += 1
        if guess == game['number']:
            if game['type'] == 'easy':
                update_pet(user_id, {'лапки': pet['лапки'] + 5, 'total_lapki_earned': pet.get('total_lapki_earned', 0) + 5})
                bot.send_message(message.chat.id, "🎉 Ты угадал! +5 лапок!")
            else:
                update_pet(user_id, {'лапки': pet['лапки'] + 25, 'total_lapki_earned': pet.get('total_lapki_earned', 0) + 25})
                bot.send_message(message.chat.id, "🎉 Ты угадал! +25 лапок!")
            game_data.pop(user_id, None)
            return
        elif guess < game['number']:
            msg = "📈 Загаданное число больше"
        else:
            msg = "📉 Загаданное число меньше"
        if game['attempts'] >= game['max_attempts']:
            bot.send_message(message.chat.id, f"❌ Ты не угадал! Загаданное число было {game['number']}.")
            game_data.pop(user_id, None)
            return
        bot.send_message(message.chat.id, f"{msg}. Осталось попыток: {game['max_attempts'] - game['attempts']}")
    except:
        pass

@bot.message_handler(commands=['daily'])
def daily_bonus(message):
    user_id = message.from_user.id
    pet = get_pet(user_id)
    if not pet:
        bot.send_message(message.chat.id, "Сначала заведи питомца через /newpet")
        return
    today = date.today().isoformat()
    if pet.get('last_daily') == today:
        bot.send_message(message.chat.id, "Сегодня ты уже получил бонус! До встречи завтра)")
        return
    new_s = min(100, pet['счастье'] + 10)
    new_l = pet['лапки'] + 5
    update_pet(user_id, {'счастье': new_s, 'лапки': new_l, 'last_daily': today})
    bot.send_message(message.chat.id, f"🎁 Ежедневный бонус получен!\n{ATTR_EMOJIS['счастье']} Счастье +10\n{ATTR_EMOJIS['лапки']} Лапки +5")

@bot.message_handler(commands=['app'])
def app_command(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(
        text="🐾 Открыть питомца",
        web_app=types.WebAppInfo(url="https://ghost-pet.onrender.com")
    ))
    bot.send_message(message.chat.id, "Нажми на кнопку, чтобы открыть питомца:", reply_markup=markup)

@bot.message_handler(func=lambda message: True)
def handle_messages(message):
    if message.text and message.text.startswith('/'):
        return
    user_id = message.from_user.id
    pet = get_pet(user_id)
    if not pet:
        return
    new_total = pet['total_messages'] + 1
    new_lapki = pet['лапки'] + 1
    update_pet(user_id, {'total_messages': new_total, 'лапки': new_lapki, 'total_lapki_earned': pet.get('total_lapki_earned', 0) + 1})
    check_achievements(user_id, get_pet(user_id))

# --- ЗАПУСК ---
if __name__ == '__main__':
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    try:
        bot.delete_webhook()
        print("✅ Вебхук удалён")
    except Exception as e:
        print(f"⚠️ Ошибка при удалении вебхука: {e}")
    
    print("✅ Бот Питомец запущен!")
    bot.polling(none_stop=True)
