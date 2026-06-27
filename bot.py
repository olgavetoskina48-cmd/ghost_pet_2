import os
import random
import re
import time
import threading
from datetime import datetime, date
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

# --- ЗВУКИ ЖИВОТНЫХ ---
SOUNDS = {
    "кошка": ["мяу", "мур", "фыр"],
    "собака": ["гав", "тяф", "вуф"],
    "лиса": ["фыр", "кхе", "тяф"],
    "панда": ["хрум", "фырк", "пых"],
    "кролик": ["цок", "фыр", "хрум"],
    "ёжик": ["фырк", "пых", "цок"],
    "пингвин": ["фыр", "кхе", "цок"]
}

# --- ЭМОДЗИ ---
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

# --- ДОСТИЖЕНИЯ ---
ACHIEVEMENTS = [
    {"messages": 100, "name": "Начало истории", "emoji": "📖", "text": "Ты только начинаешь свой путь с питомцем!"},
    {"messages": 500, "name": "Человек питомцу друг", "emoji": "🐾", "text_dog": "Человек собаке друг — это знают все вокруг!", "text_other": "Человек питомцу друг! Ты настоящий друг!"},
    {"messages": 1000, "name": "Сердце питомца", "emoji": "❤️", "text": "Ты стал главным в жизни своего питомца, центром его мира!"},
    {"messages": 5000, "name": "Легенда", "emoji": "👑", "text": "Легенда! Ты и твой питомец — неразлучны!"},
    {"messages": 20000, "name": "Вечная связь", "emoji": "♾️", "text": "Вечная связь! Ты и твой питомец — одно целое."}
]

# --- СОСТОЯНИЯ ---
user_states = {}
game_data = {}
game_dice = {}  # для игры в кости

# --- БАЗА ДАННЫХ ---
def get_pet(user_id):
    response = supabase.table('pets').select('*').eq('user_id', user_id).execute()
    if response.data:
        return response.data[0]
    return None

def create_pet(user_id, pet_type, pet_name="Питомец"):
    supabase.table('pets').insert({
        'user_id': user_id,
        'pet_type': pet_type,
        'pet_name': pet_name,
        'stage': 'Зарождение',
        'total_messages': 0,
        'голод': 50,
        'счастье': 50,
        'гигиена': 50,
        'энергия': 50,
        'дисциплина': 50,
        'дни': 0,
        'лапки': 0,
        'daily_bonus': None,
        'games_played': 0,
        'games_won': 0,
        'games_lost': 0,
        'games_series': 0,
        'достижение_100': False,
        'достижение_500': False,
        'достижение_1000': False,
        'достижение_5000': False,
        'достижение_20000': False
    }).execute()

def update_pet(user_id, data):
    supabase.table('pets').update(data).eq('user_id', user_id).execute()

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
    for ach in ACHIEVEMENTS:
        field = f"достижение_{ach['messages']}"
        if not pet.get(field, False) and pet['total_messages'] >= ach['messages']:
            update_pet(user_id, {field: True})
            if ach['messages'] == 500 and pet['pet_type'] == "собака":
                text = ach['text_dog']
            elif ach['messages'] == 500:
                text = ach['text_other']
            else:
                text = ach['text']
            bot.send_message(user_id, f"🏆 ДОСТИЖЕНИЕ ПОЛУЧЕНО!\n{ach['emoji']} {ach['name']}!\n{text}")

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
    create_pet(user_id, pet_type)
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

@bot.message_handler(commands=['daily'])
def daily_bonus(message):
    user_id = message.from_user.id
    pet = get_pet(user_id)
    if not pet:
        bot.send_message(message.chat.id, "Сначала заведи питомца через /newpet")
        return
    today = date.today().isoformat()
    if pet.get('daily_bonus') == today:
        bot.send_message(message.chat.id, "Сегодня ты уже получил бонус! До встречи завтра)")
        return
    new_s = min(100, pet['счастье'] + 10)
    new_l = pet['лапки'] + 5
    update_pet(user_id, {'счастье': new_s, 'лапки': new_l, 'daily_bonus': today})
    bot.send_message(message.chat.id, f"🎁 Ежедневный бонус получен!\n{ATTR_EMOJIS['счастье']} Счастье +10\n{ATTR_EMOJIS['лапки']} Лапки +5")

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
    new_val = min(100, pet['голод'] + 20)
    update_pet(user_id, {'голод': new_val})
    sound = random.choice(SOUNDS.get(pet['pet_type'], ["мяу"]))
    bot.send_message(message.chat.id, f"🍽️ Покормлен! Голод +20\n{sound}!")

@bot.message_handler(commands=['play'])
def play(message):
    user_id = message.from_user.id
    pet = get_pet(user_id)
    if not pet:
        bot.send_message(message.chat.id, "Сначала /newpet")
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
    new_val = min(100, pet['гигиена'] + 25)
    update_pet(user_id, {'гигиена': new_val})
    sound = random.choice(SOUNDS.get(pet['pet_type'], ["мяу"]))
    bot.send_message(message.chat.id, f"🫧 Помыт! Гигиена +25\n{sound}!")

@bot.message_handler(commands=['sleep'])
def sleep(message):
    user_id = message.from_user.id
    pet = get_pet(user_id)
    if not pet:
        bot.send_message(message.chat.id, "Сначала /newpet")
        return
    new_val = min(100, pet['энергия'] + 30)
    update_pet(user_id, {'энергия': new_val})
    sound = random.choice(SOUNDS.get(pet['pet_type'], ["мяу"]))
    bot.send_message(message.chat.id, f"💤 Поспал! Энергия +30\n{sound}!")

@bot.message_handler(commands=['train'])
def train(message):
    user_id = message.from_user.id
    pet = get_pet(user_id)
    if not pet:
        bot.send_message(message.chat.id, "Сначала /newpet")
        return
    new_val = min(100, pet['дисциплина'] + 15)
    update_pet(user_id, {'дисциплина': new_val})
    sound = random.choice(SOUNDS.get(pet['pet_type'], ["мяу"]))
    bot.send_message(message.chat.id, f"⚡ Тренировка! Дисциплина +15\n{sound}!")

@bot.message_handler(commands=['app'])
def app_command(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(
        text="🐾 Открыть питомца",
        web_app=types.WebAppInfo(url="https://ghost-pet.onrender.com")
    ))
    bot.send_message(message.chat.id, "Нажми на кнопку, чтобы открыть питомца:", reply_markup=markup)

# --- ИГРЫ ---

# Кости
@bot.message_handler(func=lambda message: message.text and 'Скинь мне кубик!' in message.text)
def start_dice_game(message):
    user_id = message.from_user.id
    pet = get_pet(user_id)
    if not pet:
        bot.send_message(message.chat.id, "Сначала заведи питомца через /newpet")
        return
    game_dice[user_id] = None
    bot.send_message(message.chat.id, "🎲 Кидай кубик! Напиши 🎲")

@bot.message_handler(func=lambda message: message.text and '🎲' in message.text and message.from_user.id in game_dice)
def handle_dice_roll(message):
    user_id = message.from_user.id
    pet = get_pet(user_id)
    if not pet:
        bot.send_message(message.chat.id, "Сначала заведи питомца через /newpet")
        return
    
    user_roll = random.randint(1, 6)
    bot_roll = random.randint(1, 6)
    dice_emojis = {1: '⚀', 2: '⚁', 3: '⚂', 4: '⚃', 5: '⚄', 6: '⚅'}
    
    text = (
        f"🎲 Ты выбросил: {dice_emojis[user_roll]} ({user_roll})\n"
        f"🎲 Я выбросил: {dice_emojis[bot_roll]} ({bot_roll})\n"
    )
    
    if user_roll > bot_roll:
        series = pet.get('games_series', 0) + 1
        win_bonus = 5 * series
        text += f"✅ Ты выиграл! +{win_bonus} лапок!"
        update_pet(user_id, {'лапки': pet['лапки'] + win_bonus, 'games_series': series})
    elif user_roll < bot_roll:
        text += "❌ Ты проиграл! Ничего не заработал."
        update_pet(user_id, {'games_series': 0})
    else:
        text += "🤝 Ничья! Никто не получил лапок."
    
    game_dice.pop(user_id, None)
    bot.send_message(message.chat.id, text)

# Угадай число
@bot.message_handler(func=lambda message: message.text and message.text.isdigit() and message.from_user.id in game_data)
def handle_guess_number(message):
    user_id = message.from_user.id
    game = game_data[user_id]
    
    try:
        guess = int(message.text)
        game['attempts'] += 1
        
        if guess == game['number']:
            if game['type'] == 'easy':
                update_pet(user_id, {'лапки': get_pet(user_id)['лапки'] + 5})
                bot.send_message(message.chat.id, "🎉 Ты угадал! +5 лапок!")
            else:
                update_pet(user_id, {'лапки': get_pet(user_id)['лапки'] + 25})
                bot.send_message(message.chat.id, "🎉 Ты угадал! +25 лапок!")
            game_data.pop(user_id, None)
            return
        
        if guess < game['number']:
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

@bot.message_handler(func=lambda message: message.text and '🔢 Напиши число от 1 до 10' in message.text)
def start_guess_easy(message):
    user_id = message.from_user.id
    pet = get_pet(user_id)
    if not pet:
        bot.send_message(message.chat.id, "Сначала заведи питомца через /newpet")
        return
    number = random.randint(1, 10)
    game_data[user_id] = {'type': 'easy', 'number': number, 'attempts': 0, 'max_attempts': 3}
    bot.send_message(message.chat.id, "🔢 Я загадал число от 1 до 10. У тебя 3 попытки! Напиши число.")

@bot.message_handler(func=lambda message: message.text and '🧠 Напиши число от 1 до 100' in message.text)
def start_guess_hard(message):
    user_id = message.from_user.id
    pet = get_pet(user_id)
    if not pet:
        bot.send_message(message.chat.id, "Сначала заведи питомца через /newpet")
        return
    number = random.randint(1, 100)
    game_data[user_id] = {'type': 'hard', 'number': number, 'attempts': 0, 'max_attempts': 10}
    bot.send_message(message.chat.id, "🧠 Я загадал число от 1 до 100. У тебя 10 попыток! Напиши число.")

# --- ОБРАБОТЧИК СООБЩЕНИЙ (для подсчёта) ---
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
    update_pet(user_id, {'total_messages': new_total, 'лапки': new_lapki})
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
