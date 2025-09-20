import schedule
import time
import threading
import logging
from datetime import datetime, timedelta
import json
from database_manager import DatabaseManager
from ai_service import AIService
import telebot
import os

logger = logging.getLogger(__name__)


class ReminderService:
    def __init__(self, bot_token: str):
        self.db = DatabaseManager()
        self.ai = AIService()
        self.bot = telebot.TeleBot(bot_token)
        self.is_running = False
        self.reminder_thread = None

    def start(self):
        """Start the reminder service"""
        if not self.is_running:
            self.is_running = True
            self.reminder_thread = threading.Thread(target=self._run_scheduler, daemon=True)
            self.reminder_thread.start()
            logger.info("Reminder service started")

    def stop(self):
        """Stop the reminder service"""
        self.is_running = False
        if self.reminder_thread:
            self.reminder_thread.join()
        logger.info("Reminder service stopped")

    def _run_scheduler(self):
        """Run the scheduler in a separate thread"""
        # Schedule different types of reminders
        schedule.every().day.at("08:00").do(self._send_morning_reminders)
        schedule.every().day.at("18:00").do(self._send_evening_reminders)
        schedule.every().sunday.at("20:00").do(self._send_weekly_progress_reminders)
        schedule.every().day.at("12:00").do(self._send_hydration_reminders)

        while self.is_running:
            try:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                time.sleep(60)

    def _send_morning_reminders(self):
        """Send morning workout reminders"""
        try:
            current_day = datetime.now().strftime('%A').lower()
            users = self._get_users_for_reminder('workout', 'morning')

            for user_id in users:
                try:
                    user = self.db.get_user(user_id)
                    if not user:
                        continue

                    user_profile = {
                        'goals': user[8],
                        'fitness_level': user[7],
                        'workout_days': user[11]
                    }

                    # Generate personalized motivation message
                    motivation = self.ai.generate_motivation_message(user_profile, "morning")

                    message = f"🌅 Good morning! \n\n{motivation}\n\n💪 Ready for today's workout? Use /workout to see your plan!"

                    self.bot.send_message(user_id, message)
                    logger.info(f"Morning reminder sent to user {user_id}")

                    # Small delay to avoid rate limiting
                    time.sleep(0.5)

                except Exception as e:
                    logger.error(f"Error sending morning reminder to {user_id}: {e}")

        except Exception as e:
            logger.error(f"Morning reminder service error: {e}")

    def _send_evening_reminders(self):
        """Send evening reminders"""
        try:
            users = self._get_users_for_reminder('general', 'evening')

            for user_id in users:
                try:
                    user = self.db.get_user(user_id)
                    if not user:
                        continue

                    # Check if user worked out today
                    today_progress = self._get_today_progress(user_id)

                    if today_progress and today_progress.get('workout_completed'):
                        message = "🎉 Great job completing your workout today! 💪\n\nDon't forget to log your progress and stay hydrated! 💧"
                    else:
                        message = "🌆 Evening check-in! \n\nIf you haven't worked out yet, there's still time! Even a short 15-minute session counts. 🏃‍♂️\n\nUse /workout to see your plan or /progress to log your day."

                    self.bot.send_message(user_id, message)
                    logger.info(f"Evening reminder sent to user {user_id}")
                    time.sleep(0.5)

                except Exception as e:
                    logger.error(f"Error sending evening reminder to {user_id}: {e}")

        except Exception as e:
            logger.error(f"Evening reminder service error: {e}")

    def _send_weekly_progress_reminders(self):
        """Send weekly progress summary"""
        try:
            users = self._get_all_active_users()

            for user_id in users:
                try:
                    user = self.db.get_user(user_id)
                    if not user:
                        continue

                    # Get user's progress for the past week
                    week_progress = self._get_week_progress(user_id)
                    user_stats = self.db.get_user_stats(user_id)

                    workouts_this_week = sum(1 for p in week_progress if p.get('workout_completed'))
                    target_workouts = user[11]  # workout_days from profile

                    progress_text = f"📊 **Weekly Progress Summary**\n\n"
                    progress_text += f"🏋️‍♂️ Workouts completed: {workouts_this_week}/{target_workouts}\n"
                    progress_text += f"⏱️ Total workout time: {sum(p.get('duration_minutes', 0) for p in week_progress)} minutes\n"
                    progress_text += f"🔥 Calories burned: {sum(p.get('calories_burned', 0) for p in week_progress)}\n\n"

                    if workouts_this_week >= target_workouts:
                        progress_text += "🎉 Fantastic! You hit your weekly goal! Keep up the amazing work! 💪"
                    elif workouts_this_week > 0:
                        progress_text += f"👍 Good effort this week! Try to reach your goal of {target_workouts} workouts next week."
                    else:
                        progress_text += "💙 New week, new opportunities! Let's make this week count. You've got this! 🚀"

                    progress_text += f"\n\n📈 Total workouts since joining: {user_stats['total_workouts']}"

                    self.bot.send_message(user_id, progress_text, parse_mode='Markdown')
                    logger.info(f"Weekly progress reminder sent to user {user_id}")
                    time.sleep(0.5)

                except Exception as e:
                    logger.error(f"Error sending weekly reminder to {user_id}: {e}")

        except Exception as e:
            logger.error(f"Weekly reminder service error: {e}")

    def _send_hydration_reminders(self):
        """Send hydration reminders"""
        try:
            users = self._get_users_for_reminder('hydration', 'midday')

            hydration_messages = [
                "💧 Hydration check! Have you been drinking enough water today?",
                "🚰 Remember to stay hydrated! Your body needs water to perform at its best.",
                "💦 Quick reminder: drink some water! Your muscles will thank you.",
                "🌊 Hydration = better performance! Time for a water break!"
            ]

            import random

            for user_id in users:
                try:
                    message = random.choice(hydration_messages)
                    self.bot.send_message(user_id, message)
                    time.sleep(0.5)

                except Exception as e:
                    logger.error(f"Error sending hydration reminder to {user_id}: {e}")

        except Exception as e:
            logger.error(f"Hydration reminder service error: {e}")

    def _get_users_for_reminder(self, reminder_type: str, time_of_day: str):
        """Get users who should receive specific reminders"""
        reminders = self.db.get_active_reminders()
        user_ids = []

        for reminder in reminders:
            if reminder[2] == reminder_type and time_of_day in reminder[3]:
                user_ids.append(reminder[1])

        # If no specific reminders set, send to all active users
        if not user_ids and reminder_type == 'workout':
            user_ids = self._get_all_active_users()

        return user_ids

    def _get_all_active_users(self):
        """Get all users who have been active in the last 30 days"""
        conn = self.db.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT DISTINCT u.user_id FROM users u
            LEFT JOIN progress p ON u.user_id = p.user_id
            WHERE u.created_at > datetime('now', '-30 days')
            OR p.date > datetime('now', '-30 days')
        ''')

        users = [row[0] for row in cursor.fetchall()]
        conn.close()
        return users

    def _get_today_progress(self, user_id):
        """Get user's progress for today"""
        conn = self.db.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT workout_completed, duration_minutes, calories_burned
            FROM progress 
            WHERE user_id = ? AND date >= date('now')
            ORDER BY date DESC LIMIT 1
        ''', (user_id,))

        result = cursor.fetchone()
        conn.close()

        if result:
            return {
                'workout_completed': result[0],
                'duration_minutes': result[1] or 0,
                'calories_burned': result[2] or 0
            }
        return None

    def _get_week_progress(self, user_id):
        """Get user's progress for the past week"""
        conn = self.db.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT workout_completed, duration_minutes, calories_burned, date
            FROM progress 
            WHERE user_id = ? AND date >= datetime('now', '-7 days')
            ORDER BY date DESC
        ''', (user_id,))

        results = cursor.fetchall()
        conn.close()

        return [{
            'workout_completed': row[0],
            'duration_minutes': row[1] or 0,
            'calories_burned': row[2] or 0,
            'date': row[3]
        } for row in results]

    def set_user_reminder(self, user_id, reminder_type, reminder_time, days=None):
        """Set custom reminder for user"""
        try:
            self.db.save_reminder(user_id, reminder_type, reminder_time, days)
            return True
        except Exception as e:
            logger.error(f"Error setting reminder for user {user_id}: {e}")
            return False

    def send_custom_reminder(self, user_id, message):
        """Send custom reminder to specific user"""
        try:
            self.bot.send_message(user_id, message)
            return True
        except Exception as e:
            logger.error(f"Error sending custom reminder to user {user_id}: {e}")
            return False

    def send_achievement_notification(self, user_id, achievement_title, achievement_description):
        """Send achievement notification"""
        try:
            message = f"🏆 **Achievement Unlocked!**\n\n**{achievement_title}**\n{achievement_description}\n\nKeep up the great work! 💪"
            self.bot.send_message(user_id, message, parse_mode='Markdown')
            return True
        except Exception as e:
            logger.error(f"Error sending achievement notification to user {user_id}: {e}")
            return False

    def check_and_award_achievements(self, user_id):
        """Check if user deserves any achievements"""
        try:
            user_stats = self.db.get_user_stats(user_id)
            existing_achievements = self.db.get_user_achievements(user_id)
            existing_types = [ach[2] for ach in existing_achievements]

            # First workout achievement
            if user_stats['total_workouts'] >= 1 and 'first_workout' not in existing_types:
                self.db.add_achievement(user_id, 'first_workout',
                                        'First Steps', 'Completed your first workout!')
                self.send_achievement_notification(user_id, 'First Steps', 'Completed your first workout!')

            # Consistency achievements
            if user_stats['total_workouts'] >= 10 and 'consistent_10' not in existing_types:
                self.db.add_achievement(user_id, 'consistent_10',
                                        'Getting Strong', 'Completed 10 workouts!')
                self.send_achievement_notification(user_id, 'Getting Strong', 'Completed 10 workouts!')

            if user_stats['total_workouts'] >= 50 and 'consistent_50' not in existing_types:
                self.db.add_achievement(user_id, 'consistent_50',
                                        'Fitness Warrior', 'Completed 50 workouts!')
                self.send_achievement_notification(user_id, 'Fitness Warrior', 'Completed 50 workouts!')

            # Weight loss achievement
            if user_stats['weight_change'] and user_stats[
                'weight_change'] <= -5 and 'weight_loss_5kg' not in existing_types:
                self.db.add_achievement(user_id, 'weight_loss_5kg',
                                        'Transformation', 'Lost 5kg or more!')
                self.send_achievement_notification(user_id, 'Transformation', 'Lost 5kg or more!')

            # Long-term commitment
            if user_stats['days_registered'] >= 30 and 'month_commitment' not in existing_types:
                self.db.add_achievement(user_id, 'month_commitment',
                                        'Committed', 'One month of fitness journey!')
                self.send_achievement_notification(user_id, 'Committed', 'One month of fitness journey!')

        except Exception as e:
            logger.error(f"Error checking achievements for user {user_id}: {e}")


# Scheduler utility functions for manual reminder management
class ReminderManager:
    def __init__(self, db_manager, reminder_service):
        self.db = db_manager
        self.reminder_service = reminder_service

    def schedule_workout_reminder(self, user_id, time_str, days_of_week=None):
        """Schedule a workout reminder for specific days and time"""
        if days_of_week is None:
            days_of_week = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']

        return self.reminder_service.set_user_reminder(
            user_id, 'workout', time_str, days_of_week
        )

    def schedule_progress_reminder(self, user_id, time_str='20:00', day='sunday'):
        """Schedule weekly progress reminder"""
        return self.reminder_service.set_user_reminder(
            user_id, 'progress', time_str, [day]
        )

    def send_motivational_blast(self, message, target_users=None):
        """Send motivational message to all or specific users"""
        if target_users is None:
            target_users = self.reminder_service._get_all_active_users()

        success_count = 0
        for user_id in target_users:
            if self.reminder_service.send_custom_reminder(user_id, message):
                success_count += 1

        return success_count

    def get_reminder_stats(self):
        """Get statistics about reminders"""
        conn = self.db.get_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT COUNT(*) FROM reminders WHERE is_active = 1')
        active_reminders = cursor.fetchone()[0]

        cursor.execute('SELECT COUNT(DISTINCT user_id) FROM reminders WHERE is_active = 1')
        users_with_reminders = cursor.fetchone()[0]

        cursor.execute('SELECT reminder_type, COUNT(*) FROM reminders WHERE is_active = 1 GROUP BY reminder_type')
        reminder_types = dict(cursor.fetchall())

        conn.close()

        return {
            'active_reminders': active_reminders,
            'users_with_reminders': users_with_reminders,
            'reminder_types': reminder_types
        }