from flask import Flask, send_from_directory, request, jsonify
from supabase import create_client
import os
import random
import requests

app = Flask(__name__, static_folder='webapp')

# --- SUPABASE ---
SUPABASE_URL = "https://jzscsndwuchzlellgqea.supabase.co"
SUPABASE_KEY = "sb_publishable_-kqOsr7gFZRi8ctCNPaLgg_4mjU-NZy"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- ТОКЕН БОТА ---
TOKEN = "8869752953:AAF2gOnS-bFts-EGsS1PZZ4pfUrRXLwkN-M"

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

# --- API ---
def get_pet(user_id):
    response = supabase.table('pets').select('*').eq('user_id', user_id).execute()
    if response.data:
        return response.data[0]
    return None

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

@app.route('/api/pet/<int:user_id>')
def api_pet(user_id):
    pet = get_pet(user_id)
    if not pet:
        return jsonify({'error': 'Нет питомца'}), 404
    return jsonify(pet)

@app.route('/api/send_message', methods=['POST'])
def api_send_message():
    data = request.get_json()
    user_id = data.get('user_id')
    text = data.get('text')
    
    if not user_id or not text:
        return jsonify({'error': 'Не хватает данных'}), 400
    
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        'chat_id': user_id,
        'text': text
    }
    
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            return jsonify({'status': 'ok'})
        else:
            return jsonify({'error': 'Ошибка отправки'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/feed/<int:user_id>', methods=['POST'])
def api_feed(user_id):
    pet = get_pet(user_id)
    if not pet:
        return jsonify({'error': 'Нет питомца'}), 404
    new_val = min(100, pet['голод'] + 20)
    update_pet(user_id, {'голод': new_val})
    return jsonify({'голод': new_val, 'message': 'Покормлен! +20'})

@app.route('/api/play/<int:user_id>', methods=['POST'])
def api_play(user_id):
    pet = get_pet(user_id)
    if not pet:
        return jsonify({'error': 'Нет питомца'}), 404
    new_s = min(100, pet['счастье'] + 15)
    new_h = max(0, pet['голод'] - 2)
    new_e = max(0, pet['энергия'] - 10)
    series = pet.get('games_series', 0) + 1
    if series >= 3:
        new_h = max(0, new_h - 5)
        series = 0
    update_pet(user_id, {'счастье': new_s, 'голод': new_h, 'энергия': new_e, 'games_series': series})
    return jsonify({'счастье': new_s, 'голод': new_h, 'энергия': new_e, 'message': 'Поиграл!'})

@app.route('/api/wash/<int:user_id>', methods=['POST'])
def api_wash(user_id):
    pet = get_pet(user_id)
    if not pet:
        return jsonify({'error': 'Нет питомца'}), 404
    new_val = min(100, pet['гигиена'] + 25)
    update_pet(user_id, {'гигиена': new_val})
    return jsonify({'гигиена': new_val, 'message': 'Помыт! +25'})

@app.route('/api/sleep/<int:user_id>', methods=['POST'])
def api_sleep(user_id):
    pet = get_pet(user_id)
    if not pet:
        return jsonify({'error': 'Нет питомца'}), 404
    new_val = min(100, pet['энергия'] + 30)
    update_pet(user_id, {'энергия': new_val})
    return jsonify({'энергия': new_val, 'message': 'Поспал! +30'})

@app.route('/api/train/<int:user_id>', methods=['POST'])
def api_train(user_id):
    pet = get_pet(user_id)
    if not pet:
        return jsonify({'error': 'Нет питомца'}), 404
    new_val = min(100, pet['дисциплина'] + 15)
    update_pet(user_id, {'дисциплина': new_val})
    return jsonify({'дисциплина': new_val, 'message': 'Тренировка! +15'})

@app.route('/')
def index():
    return send_from_directory('webapp', 'index.html')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
