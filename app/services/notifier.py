import requests
from app.config import settings

def send_telegram_notification(text: str) -> bool:
    """
    Sends a message to the configured Telegram chat.
    If it fails, just logs to console (we don't want task to fail because of notification).
    """
    token = settings.TELEGRAM_BOT_TOKEN
    chat_id = settings.TELEGRAM_CHAT_ID
    
    if not token or not chat_id:
        print("Telegram notifications are not configured (missing token or chat_id).")
        return False
        
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"Failed to send Telegram notification: {e}")
        return False

def notify_task_failed(task_id: str, keyword: str, error_msg: str, site_name: str) -> None:
    text = (
        f"🚨 <b>Задача генерации завершилась с ошибкой!</b>\n\n"
        f"<b>Task ID:</b> {task_id}\n"
        f"<b>Keyword:</b> {keyword}\n"
        f"<b>Сайт:</b> {site_name}\n\n"
        f"<b>Ошибка:</b>\n<pre>{error_msg}</pre>"
    )
    send_telegram_notification(text)

def notify_task_success(task_id: str, keyword: str, site_name: str, word_count: int) -> None:
    text = (
        f"✅ <b>Статья успешно сгенерирована!</b>\n\n"
        f"<b>Keyword:</b> {keyword}\n"
        f"<b>Сайт:</b> {site_name}\n"
        f"<b>Объём:</b> {word_count} слов\n\n"
        f"Результат доступен в админ-панели (ID: {task_id})."
    )
    send_telegram_notification(text)
