import os
from dotenv import load_dotenv
import logging
import threading
from flask import Flask, request
import telebot
from bot import create_bot
from database_manager import DatabaseManager
from ai_service import AIService
from reminder_service import ReminderService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()

# Environment variables
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
WEBHOOK_URL = os.getenv('WEBHOOK_URL')
ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')

def get_app():
    """Creates and configures the Flask app."""
    if not TELEGRAM_TOKEN:
        logger.critical("TELEGRAM_TOKEN environment variable not set!")
        return None

    # Initialize services
    db_manager = DatabaseManager()
    ai_service = AIService()
    bot_instance = telebot.TeleBot(TELEGRAM_TOKEN)

    # Create the bot with its handlers
    create_bot(bot_instance, db_manager, ai_service)

    # Initialize and start the reminder service
    reminder_service = ReminderService(TELEGRAM_TOKEN, db_manager, ai_service)
    reminder_service.start()

    app = Flask(__name__)

    @app.route('/', methods=['POST'])
    def webhook():
        if request.headers.get('content-type') == 'application/json':
            json_str = request.get_data().decode('UTF-8')
            update = telebot.types.Update.de_json(json_str)
            bot_instance.process_new_updates([update])
            return '', 200
        else:
            return 'Unsupported Media Type', 415

    @app.route('/', methods=['GET'])
    def index():
        return "Fitness Bot is running!", 200

    bot_instance.remove_webhook()
    bot_instance.set_webhook(url=WEBHOOK_URL)
    logger.info(f"Webhook set to {WEBHOOK_URL}")

    return app

def run_polling():
    """Runs the bot in polling mode."""
    logger.info("Starting bot in development mode with polling...")
    if not TELEGRAM_TOKEN:
        logger.critical("TELEGRAM_TOKEN environment variable not set!")
        return

    db_manager = DatabaseManager()
    ai_service = AIService()
    bot_instance = telebot.TeleBot(TELEGRAM_TOKEN)
    create_bot(bot_instance, db_manager, ai_service)
    reminder_service = ReminderService(TELEGRAM_TOKEN, db_manager, ai_service)
    reminder_service.start()

    bot_instance.remove_webhook()  # Ensure webhook is removed for polling
    bot_instance.infinity_polling()

if __name__ == "__main__":
    if ENVIRONMENT == 'production':
        app = get_app()
        if app:
            port = int(os.environ.get('PORT', 5000))
            app.run(host='0.0.0.0', port=port)
    else:
        run_polling()