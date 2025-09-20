# "8496825737:AAEdOcQ70FnlyTxCKc_BPWOpGoHgZt5E41I"
# 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

import os
import logging
import sqlite3
import json
import asyncio
from datetime import datetime, timedelta
import requests
from typing import Dict, Any, Optional
import telebot
from telebot import types
import threading
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
WEBHOOK_URL = os.getenv('WEBHOOK_URL', '')

# Initialize bot
bot = telebot.TeleBot(TELEGRAM_TOKEN)


# Database setup
def init_database():
    conn = sqlite3.connect('fitness_bot.db', check_same_thread=False)
    cursor = conn.cursor()

    # Users table
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
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Workout plans table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS workout_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            plan_data TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')

    # Diet plans table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS diet_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            plan_data TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')

    # Progress tracking table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            weight REAL,
            workout_completed BOOLEAN,
            notes TEXT,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')

    # Reminders table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            reminder_type TEXT,
            reminder_time TEXT,
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')

    conn.commit()
    conn.close()


# Database helper functions
def get_db_connection():
    return sqlite3.connect('fitness_bot.db', check_same_thread=False)


def get_user(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user


def save_user(user_data):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        INSERT OR REPLACE INTO users 
        (user_id, username, first_name, age, weight, height, gender, fitness_level, 
         goals, medical_conditions, dietary_restrictions, workout_days, workout_duration, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
    ''', user_data)

    conn.commit()
    conn.close()


def save_workout_plan(user_id, plan_data):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO workout_plans (user_id, plan_data) VALUES (?, ?)',
                   (user_id, json.dumps(plan_data)))
    conn.commit()
    conn.close()


def save_diet_plan(user_id, plan_data):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO diet_plans (user_id, plan_data) VALUES (?, ?)',
                   (user_id, json.dumps(plan_data)))
    conn.commit()
    conn.close()


# OpenRouter API integration
def call_openrouter_api(prompt: str) -> str:
    """Call OpenRouter API for AI responses"""
    try:
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://fitness-bot.render.com",
            "X-Title": "Telegram Fitness Bot"
        }

        data = {
            "model": "openai/gpt-3.5-turbo",  # Free tier model
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 1000,
            "temperature": 0.7
        }

        response = requests.post(url, headers=headers, json=data, timeout=30)
        response.raise_for_status()

        result = response.json()
        return result['choices'][0]['message']['content']

    except Exception as e:
        logger.error(f"OpenRouter API error: {e}")
        return "Sorry, I couldn't generate a response right now. Please try again later."


# User state management
user_states = {}


class UserState:
    def __init__(self, user_id):
        self.user_id = user_id
        self.current_step = 'start'
        self.data = {}


def get_user_state(user_id):
    if user_id not in user_states:
        user_states[user_id] = UserState(user_id)
    return user_states[user_id]


# Bot handlers
@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.from_user.id
    user = get_user(user_id)

    if user:
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("📋 My Profile", callback_data="profile"),
            types.InlineKeyboardButton("💪 Workout Plan", callback_data="workout"),
            types.InlineKeyboardButton("🥗 Diet Plan", callback_data="diet"),
            types.InlineKeyboardButton("📊 Progress", callback_data="progress"),
            types.InlineKeyboardButton("⚙️ Settings", callback_data="settings")
        )
        bot.send_message(
            message.chat.id,
            f"Welcome back, {message.from_user.first_name}! 🏋️‍♂️\n\n"
            "What would you like to do today?",
            reply_markup=markup
        )
    else:
        bot.send_message(
            message.chat.id,
            "🏋️‍♂️ Welcome to your Personal Fitness Bot! 💪\n\n"
            "I'll help you create personalized workout and diet plans based on your goals and preferences.\n\n"
            "Let's start by setting up your profile. Please tell me your age:"
        )
        state = get_user_state(user_id)
        state.current_step = 'age'


@bot.message_handler(commands=['help'])
def help_command(message):
    help_text = """
🏋️‍♂️ **Fitness Bot Commands:**

/start - Start the bot or return to main menu
/help - Show this help message
/profile - View your profile
/workout - Get your workout plan
/diet - Get your diet plan
/progress - Log your progress
/reminder - Set workout reminders

**Features:**
• Personalized workout plans
• Custom diet recommendations
• Progress tracking
• Automated reminders
• AI-powered fitness advice
    """
    bot.send_message(message.chat.id, help_text, parse_mode='Markdown')


@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = call.from_user.id

    if call.data == "profile":
        show_profile(call.message, user_id)
    elif call.data == "workout":
        generate_workout_plan(call.message, user_id)
    elif call.data == "diet":
        generate_diet_plan(call.message, user_id)
    elif call.data == "progress":
        show_progress(call.message, user_id)
    elif call.data == "settings":
        show_settings(call.message, user_id)


def show_profile(message, user_id):
    user = get_user(user_id)
    if user:
        profile_text = f"""
👤 **Your Profile:**

• Age: {user[3]} years
• Weight: {user[4]} kg
• Height: {user[5]} cm
• Gender: {user[6]}
• Fitness Level: {user[7]}
• Goals: {user[8]}
• Workout Days/Week: {user[11]}
• Workout Duration: {user[12]} minutes
        """
        bot.send_message(message.chat.id, profile_text, parse_mode='Markdown')
    else:
        bot.send_message(message.chat.id, "Please complete your profile setup first using /start")


def generate_workout_plan(message, user_id):
    user = get_user(user_id)
    if not user:
        bot.send_message(message.chat.id, "Please complete your profile setup first using /start")
        return

    bot.send_message(message.chat.id, "🔄 Generating your personalized workout plan...")

    prompt = f"""
    Create a personalized workout plan for a user with the following details:
    - Age: {user[3]}
    - Weight: {user[4]} kg
    - Height: {user[5]} cm
    - Gender: {user[6]}
    - Fitness Level: {user[7]}
    - Goals: {user[8]}
    - Medical Conditions: {user[9] or 'None'}
    - Workout Days per Week: {user[11]}
    - Workout Duration: {user[12]} minutes

    Please provide a detailed weekly workout plan with exercises, sets, reps, and rest periods.
    Format it clearly for Telegram messaging.
    """

    plan = call_openrouter_api(prompt)
    save_workout_plan(user_id, {'plan': plan, 'generated_at': datetime.now().isoformat()})

    bot.send_message(message.chat.id, f"💪 **Your Workout Plan:**\n\n{plan}", parse_mode='Markdown')


def generate_diet_plan(message, user_id):
    user = get_user(user_id)
    if not user:
        bot.send_message(message.chat.id, "Please complete your profile setup first using /start")
        return

    bot.send_message(message.chat.id, "🔄 Generating your personalized diet plan...")

    prompt = f"""
    Create a personalized diet plan for a user with the following details:
    - Age: {user[3]}
    - Weight: {user[4]} kg
    - Height: {user[5]} cm
    - Gender: {user[6]}
    - Fitness Level: {user[7]}
    - Goals: {user[8]}
    - Dietary Restrictions: {user[10] or 'None'}

    Please provide a daily meal plan with breakfast, lunch, dinner, and snacks.
    Include approximate calories and macronutrients.
    Format it clearly for Telegram messaging.
    """

    plan = call_openrouter_api(prompt)
    save_diet_plan(user_id, {'plan': plan, 'generated_at': datetime.now().isoformat()})

    bot.send_message(message.chat.id, f"🥗 **Your Diet Plan:**\n\n{plan}", parse_mode='Markdown')


def show_progress(message, user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT * FROM progress WHERE user_id = ? ORDER BY date DESC LIMIT 5',
        (user_id,)
    )
    progress_records = cursor.fetchall()
    conn.close()

    if progress_records:
        progress_text = "📊 **Your Recent Progress:**\n\n"
        for record in progress_records:
            date = record[4].split()[0]  # Get date part
            progress_text += f"• {date}: Weight {record[2]}kg"
            if record[3]:
                progress_text += " ✅ Workout completed"
            progress_text += "\n"
    else:
        progress_text = "No progress recorded yet. Start logging your workouts!"

    bot.send_message(message.chat.id, progress_text, parse_mode='Markdown')


def show_settings(message, user_id):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔔 Set Reminders", callback_data="set_reminders"))
    markup.add(types.InlineKeyboardButton("📝 Update Profile", callback_data="update_profile"))

    bot.send_message(
        message.chat.id,
        "⚙️ **Settings:**\n\nWhat would you like to configure?",
        reply_markup=markup,
        parse_mode='Markdown'
    )


@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = message.from_user.id
    state = get_user_state(user_id)

    if state.current_step == 'age':
        try:
            age = int(message.text)
            if 13 <= age <= 100:
                state.data['age'] = age
                state.current_step = 'weight'
                bot.send_message(message.chat.id, "Great! Now please tell me your weight in kg:")
            else:
                bot.send_message(message.chat.id, "Please enter a valid age (13-100):")
        except ValueError:
            bot.send_message(message.chat.id, "Please enter a valid number for your age:")

    elif state.current_step == 'weight':
        try:
            weight = float(message.text)
            if 30 <= weight <= 300:
                state.data['weight'] = weight
                state.current_step = 'height'
                bot.send_message(message.chat.id, "Perfect! Now please tell me your height in cm:")
            else:
                bot.send_message(message.chat.id, "Please enter a valid weight (30-300 kg):")
        except ValueError:
            bot.send_message(message.chat.id, "Please enter a valid number for your weight:")

    elif state.current_step == 'height':
        try:
            height = float(message.text)
            if 100 <= height <= 250:
                state.data['height'] = height
                state.current_step = 'gender'
                markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True, one_time_keyboard=True)
                markup.add('Male', 'Female', 'Other')
                bot.send_message(message.chat.id, "Great! What's your gender?", reply_markup=markup)
            else:
                bot.send_message(message.chat.id, "Please enter a valid height (100-250 cm):")
        except ValueError:
            bot.send_message(message.chat.id, "Please enter a valid number for your height:")

    elif state.current_step == 'gender':
        if message.text.lower() in ['male', 'female', 'other']:
            state.data['gender'] = message.text.capitalize()
            state.current_step = 'fitness_level'
            markup = types.ReplyKeyboardMarkup(row_width=3, resize_keyboard=True, one_time_keyboard=True)
            markup.add('Beginner', 'Intermediate', 'Advanced')
            bot.send_message(message.chat.id, "What's your current fitness level?", reply_markup=markup)
        else:
            bot.send_message(message.chat.id, "Please select from: Male, Female, or Other")

    elif state.current_step == 'fitness_level':
        if message.text.lower() in ['beginner', 'intermediate', 'advanced']:
            state.data['fitness_level'] = message.text.capitalize()
            state.current_step = 'goals'
            bot.send_message(message.chat.id,
                             "What are your fitness goals? (e.g., lose weight, build muscle, improve endurance)")
        else:
            bot.send_message(message.chat.id, "Please select: Beginner, Intermediate, or Advanced")

    elif state.current_step == 'goals':
        state.data['goals'] = message.text
        state.current_step = 'medical_conditions'
        bot.send_message(message.chat.id,
                         "Do you have any medical conditions or injuries I should know about? (type 'none' if none)")

    elif state.current_step == 'medical_conditions':
        state.data['medical_conditions'] = message.text if message.text.lower() != 'none' else None
        state.current_step = 'dietary_restrictions'
        bot.send_message(message.chat.id,
                         "Any dietary restrictions or allergies? (type 'none' if none)")

    elif state.current_step == 'dietary_restrictions':
        state.data['dietary_restrictions'] = message.text if message.text.lower() != 'none' else None
        state.current_step = 'workout_days'
        markup = types.ReplyKeyboardMarkup(row_width=4, resize_keyboard=True, one_time_keyboard=True)
        markup.add('3', '4', '5', '6', '7')
        bot.send_message(message.chat.id, "How many days per week do you want to workout?", reply_markup=markup)

    elif state.current_step == 'workout_days':
        try:
            days = int(message.text)
            if 1 <= days <= 7:
                state.data['workout_days'] = days
                state.current_step = 'workout_duration'
                markup = types.ReplyKeyboardMarkup(row_width=3, resize_keyboard=True, one_time_keyboard=True)
                markup.add('30', '45', '60', '90')
                bot.send_message(message.chat.id, "How long should each workout be (in minutes)?", reply_markup=markup)
            else:
                bot.send_message(message.chat.id, "Please enter a number between 1 and 7:")
        except ValueError:
            bot.send_message(message.chat.id, "Please enter a valid number:")

    elif state.current_step == 'workout_duration':
        try:
            duration = int(message.text)
            if 15 <= duration <= 180:
                state.data['workout_duration'] = duration

                # Save user data
                user_data = (
                    user_id,
                    message.from_user.username,
                    message.from_user.first_name,
                    state.data['age'],
                    state.data['weight'],
                    state.data['height'],
                    state.data['gender'],
                    state.data['fitness_level'],
                    state.data['goals'],
                    state.data['medical_conditions'],
                    state.data['dietary_restrictions'],
                    state.data['workout_days'],
                    state.data['workout_duration']
                )

                save_user(user_data)
                state.current_step = 'complete'

                markup = types.ReplyKeyboardRemove()
                bot.send_message(
                    message.chat.id,
                    "🎉 Profile setup complete!\n\n"
                    "You can now:\n"
                    "• Get personalized workout plans\n"
                    "• Receive diet recommendations\n"
                    "• Track your progress\n"
                    "• Set workout reminders\n\n"
                    "Use /start to access the main menu!",
                    reply_markup=markup
                )
            else:
                bot.send_message(message.chat.id, "Please enter a duration between 15 and 180 minutes:")
        except ValueError:
            bot.send_message(message.chat.id, "Please enter a valid number:")


# Reminder system
def reminder_system():
    """Background task for sending reminders"""
    while True:
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            # Get users who need reminders (simplified logic)
            current_hour = datetime.now().hour
            if current_hour in [8, 18]:  # 8 AM and 6 PM reminders
                cursor.execute('''
                    SELECT DISTINCT u.user_id FROM users u
                    JOIN reminders r ON u.user_id = r.user_id
                    WHERE r.is_active = 1
                ''')
                users_to_remind = cursor.fetchall()

                for user_tuple in users_to_remind:
                    user_id = user_tuple[0]
                    if current_hour == 8:
                        bot.send_message(user_id,
                                         "🌅 Good morning! Ready for your workout today? 💪\n"
                                         "Type /workout to see your plan!")
                    else:
                        bot.send_message(user_id,
                                         "🌆 Evening reminder: Don't forget about your fitness goals! 🏋️‍♂️\n"
                                         "Check your progress with /progress")

            conn.close()
            time.sleep(3600)  # Check every hour

        except Exception as e:
            logger.error(f"Reminder system error: {e}")
            time.sleep(3600)


# Webhook setup for deployment
@bot.message_handler(func=lambda message: True, content_types=['text'])
def webhook_handler():
    pass


def setup_webhook():
    if WEBHOOK_URL:
        bot.remove_webhook()
        bot.set_webhook(url=WEBHOOK_URL)
        logger.info(f"Webhook set to {WEBHOOK_URL}")


if __name__ == "__main__":
    init_database()

    if os.getenv('ENVIRONMENT') == 'production':
        # Production mode with webhook
        setup_webhook()
        from flask import Flask, request

        app = Flask(__name__)


        @app.route('/', methods=['POST'])
        def webhook():
            json_str = request.get_data().decode('UTF-8')
            update = telebot.types.Update.de_json(json_str)
            bot.process_new_updates([update])
            return '', 200


        @app.route('/', methods=['GET'])
        def index():
            return "Fitness Bot is running!"


        # Start reminder system in background
        reminder_thread = threading.Thread(target=reminder_system, daemon=True)
        reminder_thread.start()

        port = int(os.environ.get('PORT', 5000))
        app.run(host='0.0.0.0', port=port)
    else:
        # Development mode with polling
        logger.info("Starting bot in polling mode...")

        # Start reminder system in background
        reminder_thread = threading.Thread(target=reminder_system, daemon=True)
        reminder_thread.start()

        bot.infinity_polling()