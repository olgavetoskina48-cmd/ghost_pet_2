from flask import Flask, send_from_directory, request, jsonify
from supabase import create_client
import os
import random

app = Flask(__name__, static_folder='webapp')

SUPABASE_URL = "https://jzscsndwuchzlellgqea.supabase.co"
SUPABASE_KEY = "sb_publishable_-kqOsr7gFZRi8ctCNPaLgg_4mjU-NZy"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

game_data = {}

def get_pet(user_id):
    response = supabase.table('pets').select('*').eq('user_id', user_id).execute()
    if response.data:
        return response.data[0]
    return None

def update_pet(user_id, data):
    supabase.table('pets').update(data).eq('user_id', user_id).execute()

@app.route('/api/pet/<int:user_id>')
def api_pet(user_id):
    pet = get_pet(user_id)
    if not pet:
        return jsonify({'error': 'Нет питомца'}), 404
    return jsonify(pet)

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

@app.route('/api/dice/<int:user_id>', methods=['POST'])
def api_dice(user_id):
    pet = get_pet(user_id)
    if not pet:
        return jsonify({'error': 'Нет питомца'}), 404
    user_roll = random.randint(1, 6)
    bot_roll = random.randint(1, 6)
    win = user_roll > bot_roll
    lose = user_roll < bot_roll
    draw = user_roll == bot_roll
    bonus = 0
    if win:
        series = pet.get('games_series', 0) + 1
        bonus = 5 * series
        update_pet(user_id, {'лапки': pet['лапки'] + bonus, 'games_series': series})
    elif lose:
        update_pet(user_id, {'games_series': 0})
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
        update_pet(user_id, {'лапки': pet['лапки'] + bonus})
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

@app.route('/')
def index():
    return send_from_directory('webapp', 'index.html')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
