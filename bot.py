import os
import random
import time
import threading
from datetime import datetime, timedelta, date
from telebot import TeleBot, types
from supabase import create_client
from flask import Flask, send_from_directory, request, jsonify

# --- КОНФИГ ---
TOKEN = "8869752953:AAF2gOnS-bFts-EGsS1PZZ4pfUrRXLwkN-M"
SUPABASE_URL = "https://jzscsndwuchzlellgqea.supabase.co"
SUPABASE_KEY = "sb_publishable_-kqOsr7gFZRi8ctCNPaLgg_4mjU-NZy"

# --- ИНИЦИАЛИЗАЦИЯ ---
bot = TeleBot(TOKEN)
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- FLASK ---
flask_app = Flask(__name__, static_folder='webapp')

# --- ДАННЫЕ В ПАМЯТИ ---
user_states = {}
game_data = {}
dice_cooldown = {}
last_message_time = {}

# --- ДАННЫЕ ПИТОМЦА ---
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

# --- БАЗА ДАННЫХ ---
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

def get_shop_items():
    response = supabase.table('shop_items').select('*').execute()
    if not response.data:
        return []
    seen = set()
    unique = []
    for item in response.data:
        if item['name'] not in seen:
            seen.add(item['name'])
            unique.append(item)
    return unique

def get_inventory(user_id):
    response = supabase.table('inventory').select('*').eq('user_id', user_id).execute()
    return response.data if response.data else []

def add_to_inventory(user_id, item_id, quantity=1):
    existing = supabase.table('inventory').select('*').eq('user_id', user_id).eq('item_id', item_id).execute()
    if existing.data:
        new_qty = existing.data[0]['quantity'] + quantity
        supabase.table('inventory').update({'quantity': new_qty}).eq('user_id', user_id).eq('item_id', item_id).execute()
    else:
        supabase.table('inventory').insert({
            'user_id': user_id,
            'item_id': item_id,
            'quantity': quantity
        }).execute()

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

# --- КОМАНДЫ БОТА ---
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
        remaining = int(60 - (now - dice_cooldown[user_id]))
        bot.send_message(message.chat.id, f"⏳ Подожди {remaining} секунд перед следующим броском!")
        return
    dice_cooldown[user_id] = now
    user_roll = random.randint(1, 6)
    bot_roll = random.randint(1, 6)
    dice_emojis = {1: '⚀', 2: '⚁', 3: '⚂', 4: '⚃', 5: '⚄', 6: '⚅'}
    text = f"🎲 Ты выбросил: {dice_emojis[user_roll]} ({user_roll})\n🎲 Я выбросил: {dice_emojis[bot_roll]} ({bot_roll})\n"
    if user_roll > bot_roll:
        series = pet.get('games_series', 0) + 1
        win_bonus = 5 * series if series <= 3 else 15
        text += f"✅ Ты выиграл! +{win_bonus} лапок! (Серия: {series})"
        update_pet(user_id, {
            'лапки': pet['лапки'] + win_bonus,
            'games_series': series,
            'games_played': pet.get('games_played', 0) + 1,
            'games_won': pet.get('games_won', 0) + 1,
            'total_lapki_earned': pet.get('total_lapki_earned', 0) + win_bonus
        })
    elif user_roll < bot_roll:
        text += "❌ Ты проиграл! Серия сброшена."
        update_pet(user_id, {
            'games_series': 0,
            'games_played': pet.get('games_played', 0) + 1
        })
    else:
        text += "🤝 Ничья! Серия сохраняется."
        update_pet(user_id, {
            'games_played': pet.get('games_played', 0) + 1
        })
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
    
    # Антиспам
    now = time.time()
    if user_id in last_message_time and now - last_message_time[user_id] < 2:
        return
    last_message_time[user_id] = now
    
    pet = get_pet(user_id)
    if not pet:
        return
    new_total = pet['total_messages'] + 1
    new_lapki = pet['лапки'] + 1
    update_pet(user_id, {'total_messages': new_total, 'лапки': new_lapki, 'total_lapki_earned': pet.get('total_lapki_earned', 0) + 1})
    check_achievements(user_id, get_pet(user_id))

# --- FLASK API ---
@flask_app.route('/')
def index():
    return send_from_directory('webapp', 'index.html')

@flask_app.route('/api/pet/<int:user_id>')
def api_pet(user_id):
    pet = get_pet(user_id)
    if not pet:
        return jsonify({'error': 'Нет питомца'}), 404
    return jsonify(pet)

@flask_app.route('/api/profile/<int:user_id>')
def api_profile(user_id):
    pet = get_pet(user_id)
    if not pet:
        return jsonify({'error': 'Нет питомца'}), 404
    achievements = get_user_achievements(user_id)
    all_achievements = get_achievements()
    return jsonify({
        'pet_name': pet.get('pet_name', 'Питомец'),
        'pet_type': pet.get('pet_type', 'кошка'),
        'stage': get_stage(pet.get('total_messages', 0)),
        'total_messages': pet.get('total_messages', 0),
        'голод': pet.get('голод', 0),
        'счастье': pet.get('счастье', 0),
        'гигиена': pet.get('гигиена', 0),
        'энергия': pet.get('энергия', 0),
        'дисциплина': pet.get('дисциплина', 0),
        'лапки': pet.get('лапки', 0),
        'total_lapki_earned': pet.get('total_lapki_earned', 0),
        'total_lapki_spent': pet.get('total_lapki_spent', 0),
        'games_played': pet.get('games_played', 0),
        'games_won': pet.get('games_won', 0),
        'games_series': pet.get('games_series', 0),
        'feed_count': pet.get('feed_count', 0),
        'wash_count': pet.get('wash_count', 0),
        'sleep_count': pet.get('sleep_count', 0),
        'train_count': pet.get('train_count', 0),
        'streak': pet.get('streak', 0),
        'joined_at': pet.get('joined_at', ''),
        'achievements': achievements,
        'achievements_total': len(all_achievements)
    })

@flask_app.route('/api/achievements')
def api_achievements():
    return jsonify(get_achievements())

@flask_app.route('/api/shop')
def api_shop():
    return jsonify(get_shop_items())

@flask_app.route('/api/inventory/<int:user_id>')
def api_inventory(user_id):
    inventory = get_inventory(user_id)
    items = get_shop_items()
    result = []
    for inv in inventory:
        for item in items:
            if inv['item_id'] == item['id']:
                result.append({
                    'id': item['id'],
                    'name': item['name'],
                    'emoji': item['emoji'],
                    'category': item['category'],
                    'quantity': inv['quantity']
                })
    return jsonify(result)

@flask_app.route('/api/buy/<int:user_id>/<int:item_id>', methods=['POST'])
def api_buy(user_id, item_id):
    pet = get_pet(user_id)
    if not pet:
        return jsonify({'error': 'Нет питомца'}), 404
    item_response = supabase.table('shop_items').select('*').eq('id', item_id).execute()
    if not item_response.data:
        return jsonify({'error': 'Товар не найден'}), 404
    item = item_response.data[0]
    if pet['лапки'] < item['price']:
        return jsonify({'error': 'Недостаточно лапок!'}), 400
    new_lapki = pet['лапки'] - item['price']
    new_spent = pet.get('total_lapki_spent', 0) + item['price']
    update_pet(user_id, {'лапки': new_lapki, 'total_lapki_spent': new_spent})
    add_to_inventory(user_id, item_id)
    return jsonify({'message': f'✅ {item["name"]} куплен!', 'lapki': new_lapki})

@flask_app.route('/api/feed/<int:user_id>', methods=['POST'])
def api_feed(user_id):
    pet = get_pet(user_id)
    if not pet:
        return jsonify({'error': 'Нет питомца'}), 404
    if pet.get('sleep_until') and datetime.fromisoformat(pet['sleep_until']) > datetime.now():
        return jsonify({'error': '😴 Питомец спит!'}), 400
    if pet['голод'] >= 100:
        return jsonify({'error': 'Я уже сыт! 🍖'}), 400
    new_val = min(100, pet['голод'] + 20)
    update_pet(user_id, {'голод': new_val, 'feed_count': pet.get('feed_count', 0) + 1})
    return jsonify({'голод': new_val, 'message': 'Покормлен! +20'})

@flask_app.route('/api/play/<int:user_id>', methods=['POST'])
def api_play(user_id):
    pet = get_pet(user_id)
    if not pet:
        return jsonify({'error': 'Нет питомца'}), 404
    if pet.get('sleep_until') and datetime.fromisoformat(pet['sleep_until']) > datetime.now():
        return jsonify({'error': '😴 Питомец спит!'}), 400
    if pet['энергия'] < 30:
        return jsonify({'error': 'Я слишком устал! 😴'}), 400
    new_s = min(100, pet['счастье'] + 15)
    new_h = max(0, pet['голод'] - 2)
    new_e = max(0, pet['энергия'] - 10)
    series = pet.get('games_series', 0) + 1
    if series >= 3:
        new_h = max(0, new_h - 5)
        series = 0
    update_pet(user_id, {'счастье': new_s, 'голод': new_h, 'энергия': new_e, 'games_series': series})
    return jsonify({'счастье': new_s, 'голод': new_h, 'энергия': new_e, 'message': 'Поиграл!'})

@flask_app.route('/api/wash/<int:user_id>', methods=['POST'])
def api_wash(user_id):
    pet = get_pet(user_id)
    if not pet:
        return jsonify({'error': 'Нет питомца'}), 404
    if pet.get('sleep_until') and datetime.fromisoformat(pet['sleep_until']) > datetime.now():
        return jsonify({'error': '😴 Питомец спит!'}), 400
    new_val = min(100, pet['гигиена'] + 25)
    update_pet(user_id, {'гигиена': new_val, 'wash_count': pet.get('wash_count', 0) + 1})
    return jsonify({'гигиена': new_val, 'message': 'Помыт! +25'})

@flask_app.route('/api/sleep/<int:user_id>', methods=['POST'])
def api_sleep(user_id):
    pet = get_pet(user_id)
    if not pet:
        return jsonify({'error': 'Нет питомца'}), 404
    if pet['энергия'] >= 100:
        return jsonify({'error': '😊 Не хочет спать!'}), 400
    sleep_until = (datetime.now() + timedelta(hours=1)).isoformat()
    update_pet(user_id, {'sleep_until': sleep_until, 'sleep_count': pet.get('sleep_count', 0) + 1})
    return jsonify({'message': '💤 Уснул на час!'})

@flask_app.route('/api/train/<int:user_id>', methods=['POST'])
def api_train(user_id):
    pet = get_pet(user_id)
    if not pet:
        return jsonify({'error': 'Нет питомца'}), 404
    if pet.get('sleep_until') and datetime.fromisoformat(pet['sleep_until']) > datetime.now():
        return jsonify({'error': '😴 Питомец спит!'}), 400
    if pet['энергия'] < 20:
        return jsonify({'error': 'Я устал для тренировки! 😴'}), 400
    new_val = min(100, pet['дисциплина'] + 15)
    update_pet(user_id, {'дисциплина': new_val})
    return jsonify({'дисциплина': new_val, 'message': 'Тренировка! +15'})

@flask_app.route('/api/dice/<int:user_id>', methods=['POST'])
def api_dice(user_id):
    pet = get_pet(user_id)
    if not pet:
        return jsonify({'error': 'Нет питомца'}), 404
    if pet.get('sleep_until') and datetime.fromisoformat(pet['sleep_until']) > datetime.now():
        return jsonify({'error': '😴 Питомец спит!'}), 400
    now = time.time()
    if user_id in dice_cooldown and now - dice_cooldown[user_id] < 60:
        remaining = int(60 - (now - dice_cooldown[user_id]))
        return jsonify({'error': f'⏳ Подожди {remaining} секунд!'}), 400
    dice_cooldown[user_id] = now
    user_roll = random.randint(1, 6)
    bot_roll = random.randint(1, 6)
    win = user_roll > bot_roll
    lose = user_roll < bot_roll
    draw = user_roll == bot_roll
    bonus = 0
    if win:
        series = pet.get('games_series', 0) + 1
        bonus = 5 * series if series <= 3 else 15
        update_pet(user_id, {
            'лапки': pet['лапки'] + bonus,
            'games_series': series,
            'games_played': pet.get('games_played', 0) + 1,
            'games_won': pet.get('games_won', 0) + 1,
            'total_lapki_earned': pet.get('total_lapki_earned', 0) + bonus
        })
    elif lose:
        update_pet(user_id, {
            'games_series': 0,
            'games_played': pet.get('games_played', 0) + 1
        })
    else:
        update_pet(user_id, {
            'games_played': pet.get('games_played', 0) + 1
        })
    return jsonify({
        'user_roll': user_roll,
        'bot_roll': bot_roll,
        'win': win,
        'lose': lose,
        'draw': draw,
        'bonus': bonus
    })

@flask_app.route('/api/guess/<int:user_id>', methods=['POST'])
def api_guess(user_id):
    data = request.get_json()
    guess = data.get('guess')
    pet = get_pet(user_id)
    if not pet:
        return jsonify({'error': 'Нет питомца'}), 404
    game = game_data.get(user_id)
    if not game:
        return jsonify({'error': 'Игра не начата'}), 400
    game['attempts'] += 1
    number = game['number']
    if guess == number:
        bonus = 25 if game['type'] == 'hard' else 5
        update_pet(user_id, {'лапки': pet['лапки'] + bonus, 'total_lapki_earned': pet.get('total_lapki_earned', 0) + bonus})
        game_data.pop(user_id, None)
        return jsonify({'win': True, 'bonus': bonus})
    if game['attempts'] >= game['max_attempts']:
        game_data.pop(user_id, None)
        return jsonify({'lose': True, 'number': number})
    hint = 'больше' if guess < number else 'меньше'
    return jsonify({
        'win': False,
        'lose': False,
        'hint': hint,
        'attempts_left': game['max_attempts'] - game['attempts']
    })

@flask_app.route('/api/start_guess/<int:user_id>/<string:mode>', methods=['POST'])
def api_start_guess(user_id, mode):
    pet = get_pet(user_id)
    if not pet:
        return jsonify({'error': 'Нет питомца'}), 404
    if pet.get('sleep_until') and datetime.fromisoformat(pet['sleep_until']) > datetime.now():
        return jsonify({'error': '😴 Питомец спит!'}), 400
    if mode == 'easy':
        number = random.randint(1, 10)
        max_attempts = 3
    else:
        number = random.randint(1, 100)
        max_attempts = 10
    game_data[user_id] = {
        'type': mode,
        'number': number,
        'attempts': 0,
        'max_attempts': max_attempts
    }
    return jsonify({'status': 'ok'})

@flask_app.route('/images/<path:filename>')
def serve_images(filename):
    return send_from_directory('webapp/images', filename)

# --- ЗАПУСК ---
def run_flask():
    port = int(os.environ.get('PORT', 10000))
    flask_app.run(host='0.0.0.0', port=port)

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