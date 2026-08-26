import os
import time
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")
SECRET_KEY = os.environ.get("SECRET_KEY", "Flor1xSuperSecretKey")

# Словарь для хранения времени последнего репорта от каждого игрока {user_id: timestamp}
user_cooldowns = {}
COOLDOWN_SECONDS = 60  # 1 минута

@app.route("/", methods=["GET"])
def home():
    return "Server is running!", 200

@app.route("/send_report", methods=["POST"])
def send_report():
    data = request.get_json()

    if not data or data.get("secret") != SECRET_KEY:
        return jsonify({"status": "error", "message": "Unauthorized"}), 403

    user_name = str(data.get("user_name", "Unknown"))
    user_id = str(data.get("user_id", "0"))
    place_name = str(data.get("place_name", "Unknown"))
    place_id = str(data.get("place_id", "0"))
    message_text = str(data.get("message", "")).strip()

    if not message_text:
        return jsonify({"status": "error", "message": "Сообщение не может быть пустым!"}), 400

    # === ЗАЩИТА ОТ СПАМА (Кулдаун 1 минута) ===
    current_time = time.time()
    last_report_time = user_cooldowns.get(user_id, 0)
    time_passed = current_time - last_report_time

    if time_passed < COOLDOWN_SECONDS:
        remaining = int(COOLDOWN_SECONDS - time_passed)
        return jsonify({
            "status": "error", 
            "message": f"Подождите ещё {remaining} сек. перед следующей отправкой!"
        }), 429

    # === ЖЁСТКАЯ СТРУКТУРА DISCORD (Игрок не может её изменить) ===
    payload = {
        "username": "Ratnik Hub Reports",
        "embeds": [{
            "title": "📩 Новый отклик / Баг-репорт",
            "color": 3447003,
            "fields": [
                {"name": "Игрок", "value": f"{user_name} (ID: {user_id})", "inline": True},
                {"name": "Игра", "value": f"{place_name} (ID: {place_id})", "inline": True},
                {"name": "Сообщение", "value": message_text, "inline": False}
            ]
        }]
    }

    response = requests.post(WEBHOOK_URL, json=payload)

    if response.status_code in [200, 204]:
        user_cooldowns[user_id] = current_time  # Обновляем время отправки
        return jsonify({"status": "success", "message": "Репорт отправлен!"}), 200
    else:
        return jsonify({"status": "error", "message": "Ошибка отправки в Discord"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
