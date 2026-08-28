import os
import time
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

# --- 1. Личные кулдауны игроков {user_id: timestamp} ---
user_cooldowns = {}
USER_COOLDOWN_SECONDS = 240  # 4 минуты на 1 игрока

# --- 2. Глобальный лимит сервера ---
global_report_timestamps = []
MAX_GLOBAL_REPORTS = 100     # Максимум 100 репортов
GLOBAL_WINDOW_SECONDS = 600   # За 10 минут (600 секунд)

@app.route("/", methods=["GET"])
def home():
    return "Server is running!", 200

@app.route("/send_report", methods=["POST"])
def send_report():
    data = request.get_json()

    if not data or not isinstance(data, dict):
        return jsonify({"status": "error", "message": "Некорректные данные!"}), 400

    user_name = str(data.get("user_name", "Unknown")).strip()
    user_id = str(data.get("user_id", "0")).strip()
    place_name = str(data.get("place_name", "Unknown")).strip()
    place_id = str(data.get("place_id", "0")).strip()
    message_text = str(data.get("message", "")).strip()

    # ==================== 1. ПРОВЕРКА КЛЮЧЕВЫХ СЛОВ ====================
    required_keywords = ["Игрок", "Игра", "Сообщение"]
    full_payload_text = f"{user_name} {place_name} {message_text} Игрок Игра Сообщение"
    
    if not all(keyword in full_payload_text for keyword in required_keywords):
        return jsonify({
            "status": "error", 
            "message": "Ошибка структуры репорта! Не пройден первичный фильтр."
        }), 400

    # ==================== 2. ПРОВЕРКА ДЛИНЫ ====================
    if len(message_text) < 3:
        return jsonify({
            "status": "error", 
            "message": "Сообщение слишком короткое! Напишите хотя бы 3 символа."
        }), 400

    if len(message_text) > 1000:
        return jsonify({
            "status": "error", 
            "message": "Сообщение слишком длинное! Максимум 1000 символов."
        }), 400

    current_time = time.time()

    # ==================== 3. ЛИЧНЫЙ ЛИМИТ (4 МИНУТЫ НА ИГРОКА) ====================
    last_user_time = user_cooldowns.get(user_id, 0)
    user_time_passed = current_time - last_user_time

    if user_time_passed < USER_COOLDOWN_SECONDS:
        remaining = int(USER_COOLDOWN_SECONDS - user_time_passed)
        minutes = remaining // 60
        seconds = remaining % 60
        time_str = f"{minutes} мин. {seconds} сек." if minutes > 0 else f"{seconds} сек."
        return jsonify({
            "status": "error", 
            "message": f"Вы можете отправлять репорт только 1 раз в 4 минуты! Подождите еще {time_str}."
        }), 429

    # ==================== 4. ГЛОБАЛЬНЫЙ ЛИМИТ (100 РЕПОРТОВ / 10 МИНУТ НА ВЕСЬ СЕРВЕР) ====================
    global global_report_timestamps
    # Удаляем репорты старше 10 минут (600 секунд)
    global_report_timestamps = [t for t in global_report_timestamps if current_time - t < GLOBAL_WINDOW_SECONDS]

    if len(global_report_timestamps) >= MAX_GLOBAL_REPORTS:
        oldest_time = global_report_timestamps[0]
        wait_time = int(GLOBAL_WINDOW_SECONDS - (current_time - oldest_time))
        if wait_time < 1:
            wait_time = 1
        return jsonify({
            "status": "error", 
            "message": f"Достигнут глобальный лимит сервера (100 репортов за 10 мин)! Попробуйте через {wait_time} сек."
        }), 429

    # ==================== ОТПРАВКА В DISCORD ====================
    payload = {
        "username": "Ratnik Hub Reports",
        "embeds": [{
            "title": "📩 Новый отклик / Баг-репорт",
            "color": 3447003,
            "fields": [
                {"name": "Игрок", "value": f"**{user_name}** (ID: `{user_id}`)", "inline": True},
                {"name": "Игра", "value": f"**{place_name}** (ID: `{place_id}`)", "inline": True},
                {"name": "Сообщение", "value": message_text, "inline": False}
            ]
        }]
    }

    try:
        response = requests.post(WEBHOOK_URL, json=payload, timeout=5)
        if response.status_code in [200, 204]:
            # Обновляем оба таймера
            user_cooldowns[user_id] = current_time
            global_report_timestamps.append(current_time)
            return jsonify({"status": "success", "message": "Репорт успешно отправлен!"}), 200
        else:
            return jsonify({"status": "error", "message": "Ошибка отправки в Discord."}), 500
    except Exception:
        return jsonify({"status": "error", "message": "Ошибка соединения с вебхуком."}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
