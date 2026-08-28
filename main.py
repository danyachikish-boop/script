import os
import time
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

user_cooldowns = {}
USER_COOLDOWN_SECONDS = 240

global_report_timestamps = []
MAX_GLOBAL_REPORTS = 100
GLOBAL_WINDOW_SECONDS = 600

# Тексты ошибок на двух языках
MESSAGES = {
    "ru": {
        "invalid_data": "Некорректные данные!",
        "structure_error": "Ошибка структуры репорта!",
        "too_short": "Сообщение слишком короткое! Напишите хотя бы 3 символа.",
        "too_long": "Сообщение слишком длинное! Максимум 1000 символов.",
        "user_cooldown": "Вы можете отправлять репорт только 1 раз в 4 минуты! Подождите еще {time}.",
        "global_limit": "Достигнут лимит сервера! Попробуйте через {time} сек.",
        "success": "Репорт успешно отправлен!",
        "discord_error": "Ошибка отправки в Discord.",
        "connection_error": "Ошибка соединения с вебхуком."
    },
    "en": {
        "invalid_data": "Invalid request data!",
        "structure_error": "Report structure validation failed!",
        "too_short": "Message is too short! Minimum 3 characters required.",
        "too_long": "Message is too long! Maximum 1000 characters allowed.",
        "user_cooldown": "You can only send a report once every 4 minutes! Please wait {time}.",
        "global_limit": "Global server report limit reached! Please try again in {time}s.",
        "success": "Report sent successfully!",
        "discord_error": "Failed to send report to Discord.",
        "connection_error": "Webhook connection error."
    }
}

@app.route("/", methods=["GET"])
def home():
    return "Server is running!", 200

@app.route("/send_report", methods=["POST"])
def send_report():
    data = request.get_json()

    # Определение языка клиента (по умолчанию английский)
    lang_code = str(data.get("language", "en")).lower() if data else "en"
    lang = "ru" if lang_code.startswith("ru") else "en"
    txt = MESSAGES[lang]

    if not data or not isinstance(data, dict):
        return jsonify({"status": "error", "message": txt["invalid_data"]}), 400

    user_name = str(data.get("user_name", "Unknown")).strip()
    user_id = str(data.get("user_id", "0")).strip()
    place_name = str(data.get("place_name", "Unknown")).strip()
    place_id = str(data.get("place_id", "0")).strip()
    message_text = str(data.get("message", "")).strip()

    required_keywords = ["Игрок", "Игра", "Сообщение"]
    full_payload_text = f"{user_name} {place_name} {message_text} Игрок Игра Сообщение"
    
    if not all(keyword in full_payload_text for keyword in required_keywords):
        return jsonify({"status": "error", "message": txt["structure_error"]}), 400

    if len(message_text) < 3:
        return jsonify({"status": "error", "message": txt["too_short"]}), 400

    if len(message_text) > 1000:
        return jsonify({"status": "error", "message": txt["too_long"]}), 400

    current_time = time.time()

    # Личный лимит
    last_user_time = user_cooldowns.get(user_id, 0)
    user_time_passed = current_time - last_user_time

    if user_time_passed < USER_COOLDOWN_SECONDS:
        remaining = int(USER_COOLDOWN_SECONDS - user_time_passed)
        minutes = remaining // 60
        seconds = remaining % 60
        
        if lang == "ru":
            time_str = f"{minutes} мин. {seconds} сек." if minutes > 0 else f"{seconds} сек."
        else:
            time_str = f"{minutes}m {seconds}s" if minutes > 0 else f"{seconds}s"
            
        return jsonify({"status": "error", "message": txt["user_cooldown"].format(time=time_str)}), 429

    # Глобальный лимит
    global global_report_timestamps
    global_report_timestamps = [t for t in global_report_timestamps if current_time - t < GLOBAL_WINDOW_SECONDS]

    if len(global_report_timestamps) >= MAX_GLOBAL_REPORTS:
        oldest_time = global_report_timestamps[0]
        wait_time = max(1, int(GLOBAL_WINDOW_SECONDS - (current_time - oldest_time)))
        return jsonify({"status": "error", "message": txt["global_limit"].format(time=wait_time)}), 429

    # Отправка в Discord
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
            user_cooldowns[user_id] = current_time
            global_report_timestamps.append(current_time)
            return jsonify({"status": "success", "message": txt["success"]}), 200
        else:
            return jsonify({"status": "error", "message": txt["discord_error"]}), 500
    except Exception:
        return jsonify({"status": "error", "message": txt["connection_error"]}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
