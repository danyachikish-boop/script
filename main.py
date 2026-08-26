from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

# Твой реальный вебхук Discord (он хранится ТОЛЬКО здесь на сервере)
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1542117153904394332/8hxNDlHKFk4Rjj4RcjAF6VU2g9YOX498hVvpBw7oAIOt2lpWPjTa5KjbsJyJxQQjNAtf"

# Секретный пароль, который знает только твой скрипт
SECRET_KEY = "Flor1xSuperSecretKey"

@app.route('/send_report', methods=['POST'])
def send_report():
    data = request.json or {}
    
    # Проверяем секретный ключ из Roblox
    if data.get("key") != SECRET_KEY:
        return jsonify({"error": "Unauthorized"}), 403

    user_name = data.get("username", "Unknown")
    user_id = data.get("user_id", "0")
    place_name = data.get("place", "Unknown")
    message = data.get("message", "")

    if not message:
        return jsonify({"error": "Empty message"}), 400

    # Собираем красивый Embed для Discord
    payload = {
        "username": "Ratnik Hub Reports (Protected)",
        "embeds": [{
            "title": "📩 Новый отклик / Баг-репорт",
            "color": 3447003,
            "fields": [
                {"name": "Игрок", "value": f"{user_name} (ID: {user_id})", "inline": True},
                {"name": "Игра", "value": f"{place_name}", "inline": True},
                {"name": "Сообщение", "value": message, "inline": False}
            ]
        }]
    }

    # Сервер сам шлет сообщение в Discord
    res = requests.post(DISCORD_WEBHOOK_URL, json=payload)
    
    if res.status_code in [200, 204]:
        return jsonify({"status": "ok"}), 200
    else:
        return jsonify({"error": "Discord error"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
