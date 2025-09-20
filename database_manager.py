import sqlite3
import json
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class DatabaseManager:
    def __init__(self, db_name='fitness_bot.db'):
        self.db_name = db_name
        self.init_database()

    def get_connection(self):
        return sqlite3.connect(self.db_name, check_same_thread=False)

    def init_database(self):
        """Initialize database with all required tables"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Users table with comprehensive profile data
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                age INTEGER,
                weight REAL,
                height REAL,
                gender TEXT,
                fitness_level TEXT,
                goals TEXT,
                medical_conditions TEXT,
                dietary_restrictions TEXT,
                workout_days INTEGER,
                workout_duration INTEGER,
                preferred_workout_time TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Workout plans with versioning
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS workout_plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                plan_data TEXT,
                plan_type TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')

        # Diet plans with meal details
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS diet_plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                plan_data TEXT,
                calories_target INTEGER,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')

        # Detailed progress tracking
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                weight REAL,
                workout_completed BOOLEAN DEFAULT 0,
                exercises_completed INTEGER DEFAULT 0,
                duration_minutes INTEGER DEFAULT 0,
                calories_burned INTEGER DEFAULT 0,
                notes TEXT,
                mood_rating INTEGER,
                date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')

        # Flexible reminder system
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                reminder_type TEXT,
                reminder_time TEXT,
                reminder_days TEXT,
                message TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')

        # Exercise database
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS exercises (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT,
                muscle_groups TEXT,
                equipment TEXT,
                difficulty_level TEXT,
                instructions TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # User achievements and milestones
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS achievements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                achievement_type TEXT,
                title TEXT,
                description TEXT,
                achieved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')

        conn.commit()
        conn.close()
        logger.info("Database initialized successfully")

    def save_user(self, user_data):
        """Save or update user profile"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            INSERT OR REPLACE INTO users 
            (user_id, username, first_name, age, weight, height, gender, fitness_level, 
             goals, medical_conditions, dietary_restrictions, workout_days, workout_duration, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', user_data)

        conn.commit()
        conn.close()
        logger.info(f"User {user_data[0]} profile saved/updated")

    def get_user(self, user_id):
        """Get user profile by ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        user = cursor.fetchone()
        conn.close()
        return user

    def save_workout_plan(self, user_id, plan_data, plan_type="general"):
        """Save workout plan for user"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Deactivate previous plans
        cursor.execute('UPDATE workout_plans SET is_active = 0 WHERE user_id = ?', (user_id,))

        # Insert new plan
        cursor.execute('''
            INSERT INTO workout_plans (user_id, plan_data, plan_type, is_active) 
            VALUES (?, ?, ?, 1)
        ''', (user_id, json.dumps(plan_data), plan_type))

        conn.commit()
        conn.close()
        logger.info(f"Workout plan saved for user {user_id}")

    def get_active_workout_plan(self, user_id):
        """Get current active workout plan"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT plan_data FROM workout_plans 
            WHERE user_id = ? AND is_active = 1 
            ORDER BY created_at DESC LIMIT 1
        ''', (user_id,))
        result = cursor.fetchone()
        conn.close()

        if result:
            return json.loads(result[0])
        return None

    def save_diet_plan(self, user_id, plan_data, calories_target=None):
        """Save diet plan for user"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Deactivate previous plans
        cursor.execute('UPDATE diet_plans SET is_active = 0 WHERE user_id = ?', (user_id,))

        # Insert new plan
        cursor.execute('''
            INSERT INTO diet_plans (user_id, plan_data, calories_target, is_active) 
            VALUES (?, ?, ?, 1)
        ''', (user_id, json.dumps(plan_data), calories_target))

        conn.commit()
        conn.close()
        logger.info(f"Diet plan saved for user {user_id}")

    def get_active_diet_plan(self, user_id):
        """Get current active diet plan"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT plan_data FROM diet_plans 
            WHERE user_id = ? AND is_active = 1 
            ORDER BY created_at DESC LIMIT 1
        ''', (user_id,))
        result = cursor.fetchone()
        conn.close()

        if result:
            return json.loads(result[0])
        return None

    def log_progress(self, user_id, weight=None, workout_completed=False,
                     exercises_completed=0, duration_minutes=0, calories_burned=0,
                     notes=None, mood_rating=None):
        """Log user progress"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO progress 
            (user_id, weight, workout_completed, exercises_completed, 
             duration_minutes, calories_burned, notes, mood_rating)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, weight, workout_completed, exercises_completed,
              duration_minutes, calories_burned, notes, mood_rating))

        conn.commit()
        conn.close()
        logger.info(f"Progress logged for user {user_id}")

    def get_progress_history(self, user_id, limit=10):
        """Get user progress history"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM progress 
            WHERE user_id = ? 
            ORDER BY date DESC 
            LIMIT ?
        ''', (user_id, limit))

        progress = cursor.fetchall()
        conn.close()
        return progress

    def save_reminder(self, user_id, reminder_type, reminder_time,
                      reminder_days=None, message=None):
        """Save user reminder preferences"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO reminders 
            (user_id, reminder_type, reminder_time, reminder_days, message)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, reminder_type, reminder_time,
              json.dumps(reminder_days) if reminder_days else None, message))

        conn.commit()
        conn.close()
        logger.info(f"Reminder saved for user {user_id}")

    def get_active_reminders(self):
        """Get all active reminders"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM reminders 
            WHERE is_active = 1
        ''')
        reminders = cursor.fetchall()
        conn.close()
        return reminders

    def add_achievement(self, user_id, achievement_type, title, description):
        """Add achievement for user"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO achievements (user_id, achievement_type, title, description)
            VALUES (?, ?, ?, ?)
        ''', (user_id, achievement_type, title, description))

        conn.commit()
        conn.close()
        logger.info(f"Achievement '{title}' added for user {user_id}")

    def get_user_achievements(self, user_id):
        """Get user achievements"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM achievements 
            WHERE user_id = ? 
            ORDER BY achieved_at DESC
        ''', (user_id,))

        achievements = cursor.fetchall()
        conn.close()
        return achievements

    def get_user_stats(self, user_id):
        """Get comprehensive user statistics"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Total workouts completed
        cursor.execute('''
            SELECT COUNT(*) FROM progress 
            WHERE user_id = ? AND workout_completed = 1
        ''', (user_id,))
        total_workouts = cursor.fetchone()[0]

        # Average workout duration
        cursor.execute('''
            SELECT AVG(duration_minutes) FROM progress 
            WHERE user_id = ? AND workout_completed = 1
        ''', (user_id,))
        avg_duration = cursor.fetchone()[0] or 0

        # Total calories burned
        cursor.execute('''
            SELECT SUM(calories_burned) FROM progress 
            WHERE user_id = ?
        ''', (user_id,))
        total_calories = cursor.fetchone()[0] or 0

        # Weight progress (first and last recorded)
        cursor.execute('''
            SELECT weight FROM progress 
            WHERE user_id = ? AND weight IS NOT NULL
            ORDER BY date ASC LIMIT 1
        ''', (user_id,))
        first_weight = cursor.fetchone()

        cursor.execute('''
            SELECT weight FROM progress 
            WHERE user_id = ? AND weight IS NOT NULL
            ORDER BY date DESC LIMIT 1
        ''', (user_id,))
        last_weight = cursor.fetchone()

        # Days since registration
        cursor.execute('''
            SELECT julianday('now') - julianday(created_at) as days
            FROM users WHERE user_id = ?
        ''', (user_id,))
        days_registered = cursor.fetchone()[0] or 0

        conn.close()

        weight_change = None
        if first_weight and last_weight:
            weight_change = last_weight[0] - first_weight[0]

        return {
            'total_workouts': total_workouts,
            'avg_duration': round(avg_duration, 1),
            'total_calories': total_calories,
            'weight_change': weight_change,
            'days_registered': int(days_registered)
        }

    def cleanup_old_data(self, days=90):
        """Clean up old progress data (optional maintenance)"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            DELETE FROM progress 
            WHERE date < datetime('now', '-{} days')
        '''.format(days))

        deleted_rows = cursor.rowcount
        conn.commit()
        conn.close()

        logger.info(f"Cleaned up {deleted_rows} old progress records")
        return deleted_rows