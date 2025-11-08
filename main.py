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

app = Flask(__name__)

def setup_bot():
    """Creates and configures the bot."""
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

    return bot_instance

bot_instance = setup_bot()

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

def run_polling():
    """Runs the bot in polling mode."""
    logger.info("Starting bot in development mode with polling...")
    if not TELEGRAM_TOKEN:
        logger.critical("TELEGRAM_TOKEN environment variable not set!")
        return

    # The bot is already set up, so we just need to start polling
    bot_instance.remove_webhook()  # Ensure webhook is removed for polling
    bot_instance.infinity_polling()

if __name__ == "__main__":
    if ENVIRONMENT == 'production':
        if bot_instance:
            bot_instance.remove_webhook()
            bot_instance.set_webhook(url=WEBHOOK_URL)
            logger.info(f"Webhook set to {WEBHOOK_URL}")
            port = int(os.environ.get('PORT', 5000))
            app.run(host='0.0.0.0', port=port)
    else:
        run_polling()