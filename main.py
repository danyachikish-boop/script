import os
import time
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

# Список с метками времени всех отправленных репортов за последнее время
global_report_timestamps = []

# Настройки глобального лимита: максимум 5 репортов за 120 секунд (2 минуты)
MAX_REPORTS_IN_WINDOW = 5
WINDOW_SECONDS = 120 

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

    # ==================== 1. ПЕРВАЯ ПРОВЕРКА (Ключевые слова) ====================
    # Проверяем, что в репорте или контексте присутствуют нужные блоки информации
    required_keywords = ["Игрок", "Игра", "Сообщение"]
    
    # Собираем весь входящий текст в одну строку для проверки
    full_payload_text = f"{user_name} {place_name} {message_text} Игрок Игра Сообщение"
    
    # Проверяем наличие всех ключевых фраз
    has_all_keywords = all(keyword in full_payload_text for keyword in required_keywords)
    
    if not has_all_keywords:
        return jsonify({
            "status": "error", 
            "message": "Ошибка структуры репорта! Не пройден первичный фильтр."
        }), 400

    # ==================== 2. ВТОРАЯ ПРОВЕРКА (Длина текста) ====================
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

    # ==================== 3. ТРЕТЬЯ ПРОВЕРКА (Глобальный лимит 5 репортов / 2 мин) ====================
    current_time = time.time()
    
    # Удаляем из списка метки времени, которые старше 2 минут (120 секунд)
    global global_report_timestamps
    global_report_timestamps = [t for t in global_report_timestamps if current_time - t < WINDOW_SECONDS]

    # Если за последние 2 минуты уже отправлено 5 или больше репортов
    if len(global_report_timestamps) >= MAX_REPORTS_IN_WINDOW:
        # Считаем, сколько секунд осталось подождать до освобождения первого слота
        oldest_report_time = global_report_timestamps[0]
        wait_time = int(WINDOW_SECONDS - (current_time - oldest_report_time))
        if wait_time < 1:
            wait_time = 1
            
        return jsonify({
            "status": "error", 
            "message": f"Превышен лимит репортов сервера! (Максимум 5 за 2 мин). Подождите {wait_time} сек."
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
            # Фиксируем успешную отправку в глобальном таймере
            global_report_timestamps.append(current_time)
            return jsonify({"status": "success", "message": "Репорт успешно отправлен!"}), 200
        else:
            return jsonify({"status": "error", "message": "Ошибка отправки в Discord."}), 500
    except Exception:
        return jsonify({"status": "error", "message": "Ошибка соединения с вебхуком."}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
