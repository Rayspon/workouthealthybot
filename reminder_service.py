import schedule
import time
import threading
import logging
from datetime import datetime
import telebot
from database_manager import DatabaseManager
from ai_service import AIService

logger = logging.getLogger(__name__)

class ReminderService:
    def __init__(self, bot_token: str, db: DatabaseManager, ai: AIService):
        self.db = db
        self.ai = ai
        self.bot = telebot.TeleBot(bot_token)
        self.is_running = False
        self.scheduler_thread = None

    def start(self):
        """Start the reminder service in a background thread."""
        if not self.is_running:
            self.is_running = True
            self.scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
            self.scheduler_thread.start()
            logger.info("Reminder service started.")

    def stop(self):
        """Stop the reminder service."""
        self.is_running = False
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.scheduler_thread.join()
        logger.info("Reminder service stopped.")

    def _run_scheduler(self):
        # Schedule tasks
        schedule.every().day.at("08:00").do(self.send_morning_reminders)
        schedule.every().day.at("20:00").do(self.send_evening_reminders)
        schedule.every().sunday.at("18:00").do(self.send_weekly_summary)

        while self.is_running:
            try:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                time.sleep(300) # Wait longer after an error

    def send_morning_reminders(self):
        logger.info("Sending morning reminders...")
        try:
            users = self.db.get_all_users() # A new method to get all users
            for user in users:
                user_id = user[0]
                try:
                    user_profile = dict(zip([desc[0] for desc in self.db.get_connection().execute('PRAGMA table_info(users)').fetchall()], user))
                    motivation = self.ai.generate_motivation_message(user_profile, context="morning")
                    message = f"🌅 Good morning, {user[2]}!\n\n{motivation}"
                    self.bot.send_message(user_id, message)
                    time.sleep(1) # Avoid rate limiting
                except Exception as e:
                    logger.error(f"Failed to send morning reminder to user {user_id}: {e}")
        except Exception as e:
            logger.error(f"Error fetching users for morning reminders: {e}")

    def send_evening_reminders(self):
        logger.info("Sending evening reminders...")
        # Implement evening reminder logic (e.g., log progress)

    def send_weekly_summary(self):
        logger.info("Sending weekly summaries...")
        # Implement weekly summary logic
