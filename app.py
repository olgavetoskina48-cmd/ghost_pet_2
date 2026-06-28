from flask import Flask, send_from_directory, request, jsonify
from supabase import create_client
import os
import random
import time
from datetime import datetime, timedelta

app = Flask(__name__, static_folder='webapp')

SUPABASE_URL = "https://jzscsndwuchzlellgqea.supabase.co"
SUPABASE_KEY = "sb_publishable_-kqOsr7gFZRi8ctCNPaLgg_4mjU-NZy"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

game_data = {}
dice_cooldown = {}

def get_pet(user_id):
    response = supabase.table('pets').select('*').eq('user_id', user_id).execute()
    if response.data:
        return response.data[0]
    return None

def update_pet(user_id, data):
    supabase.table('pets').update(data).eq('user_id', user_id).execute()

def get_user_achievements(user_id):
    response = supabase.table('user_achievements').select('achievement_id').eq('user_id', user_id).execute()
    return [a['achievement_id'] for a in response.data] if response.data else []

def get_achievements():
    response = supabase.table('achievements').select('*').execute()
    return response.data if response.data else []

def get_shop_items(category=None):
    query = supabase.table('shop_items').select('*')
    if category:
        query = query.eq('category', category)
    response = query.execute()
    return response.data if response.data else []

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

@app.route('/api/pet/<int:user_id>')
def api_pet(user_id):
    pet = get_pet(user_id)
    if not pet:
        return jsonify({'error': 'Нет питомца'}), 404
    return jsonify(pet)

@app.route('/api/profile/<int:user_id>')
def api_profile(user_id):
    pet = get_pet(user_id)
    if not pet:
        return jsonify({'error': 'Нет питомца'}), 404
    
    achievements = get_user_achievements(user_id)
    all_achievements = get_achievements()
    
    profile_data = {
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
        'feed_count': pet.get('feed_count', 0),
        'wash_count': pet.get('wash_count', 0),
        'sleep_count': pet.get('sleep_count', 0),
        'streak': pet.get('streak', 0),
        'joined_at': pet.get('joined_at', ''),
        'achievements': achievements,
        'achievements_total': len(all_achievements),
        'sleep_until': pet.get('sleep_until')
    }
    return jsonify(profile_data)

@app.route('/api/shop')
def api_shop():
    items = get_shop_items()
    return jsonify(items)

@app.route('/api/inventory/<int:user_id>')
def api_inventory(user_id):
    inventory = get_inventory(user_id)
    return jsonify(inventory)

@app.route('/api/buy/<int:user_id>/<int:item_id>', methods=['POST'])
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
    update_pet(user_id, {
        'лапки': new_lapki,
        'total_lapki_spent': new_spent
    })
    
    add_to_inventory(user_id, item_id)
    
    return jsonify({'message': f'✅ {item["name"]} куплен!', 'lapki': new_lapki})

@app.route('/api/feed/<int:user_id>', methods=['POST'])
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

@app.route('/api/play/<int:user_id>', methods=['POST'])
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

@app.route('/api/wash/<int:user_id>', methods=['POST'])
def api_wash(user_id):
    pet = get_pet(user_id)
    if not pet:
        return jsonify({'error': 'Нет питомца'}), 404
    if pet.get('sleep_until') and datetime.fromisoformat(pet['sleep_until']) > datetime.now():
        return jsonify({'error': '😴 Питомец спит!'}), 400
    new_val = min(100, pet['гигиена'] + 25)
    update_pet(user_id, {'гигиена': new_val, 'wash_count': pet.get('wash_count', 0) + 1})
    return jsonify({'гигиена': new_val, 'message': 'Помыт! +25'})

@app.route('/api/sleep/<int:user_id>', methods=['POST'])
def api_sleep(user_id):
    pet = get_pet(user_id)
    if not pet:
        return jsonify({'error': 'Нет питомца'}), 404
    if pet['энергия'] >= 100:
        return jsonify({'error': '😊 Не хочет спать!'}), 400
    sleep_until = (datetime.now() + timedelta(hours=1)).isoformat()
    update_pet(user_id, {'sleep_until': sleep_until, 'sleep_count': pet.get('sleep_count', 0) + 1})
    return jsonify({'message': '💤 Уснул на час!'})

@app.route('/api/train/<int:user_id>', methods=['POST'])
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

@app.route('/api/dice/<int:user_id>', methods=['POST'])
def api_dice(user_id):
    pet = get_pet(user_id)
    if not pet:
        return jsonify({'error': 'Нет питомца'}), 404
    if pet.get('sleep_until') and datetime.fromisoformat(pet['sleep_until']) > datetime.now():
        return jsonify({'error': '😴 Питомец спит!'}), 400
    now = time.time()
    if user_id in dice_cooldown and now - dice_cooldown[user_id] < 60:
        return jsonify({'error': '⏳ Подожди 60 секунд!'}), 400
    dice_cooldown[user_id] = now
    user_roll = random.randint(1, 6)
    bot_roll = random.randint(1, 6)
    win = user_roll > bot_roll
    lose = user_roll < bot_roll
    draw = user_roll == bot_roll
    bonus = 0
    if win:
        series = pet.get('games_series', 0) + 1
        bonus = 5 * series
        update_pet(user_id, {'лапки': pet['лапки'] + bonus, 'games_series': series, 'games_played': pet.get('games_played', 0) + 1, 'games_won': pet.get('games_won', 0) + 1, 'total_lapki_earned': pet.get('total_lapki_earned', 0) + bonus})
    elif lose:
        update_pet(user_id, {'games_series': 0, 'games_played': pet.get('games_played', 0) + 1})
    else:
        update_pet(user_id, {'games_played': pet.get('games_played', 0) + 1})
    return jsonify({
        'user_roll': user_roll,
        'bot_roll': bot_roll,
        'win': win,
        'lose': lose,
        'draw': draw,
        'bonus': bonus
    })

@app.route('/api/guess/<int:user_id>', methods=['POST'])
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

@app.route('/api/start_guess/<int:user_id>/<string:mode>', methods=['POST'])
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

@app.route('/images/<path:filename>')
def serve_images(filename):
    return send_from_directory('webapp/images', filename)

@app.route('/')
def index():
    return send_from_directory('webapp', 'index.html')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
