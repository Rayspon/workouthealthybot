import requests
import json
import logging
from typing import Dict, Any, Optional
import os

logger = logging.getLogger(__name__)


class AIService:
    def __init__(self):
        self.api_key = os.getenv('OPENROUTER_API_KEY')
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://fitness-bot.render.com",
            "X-Title": "Telegram Fitness Bot"
        }

    def _make_request(self, messages: list, model: str = "openai/gpt-3.5-turbo",
                      max_tokens: int = 1500, temperature: float = 0.7) -> str:
        """Make request to OpenRouter API"""
        try:
            data = {
                "model": model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature
            }

            response = requests.post(self.base_url, headers=self.headers,
                                     json=data, timeout=30)
            response.raise_for_status()

            result = response.json()
            return result['choices'][0]['message']['content']

        except requests.exceptions.RequestException as e:
            logger.error(f"API request error: {e}")
            return "Sorry, I'm experiencing technical difficulties. Please try again later."
        except KeyError as e:
            logger.error(f"API response format error: {e}")
            return "Sorry, I couldn't process the response. Please try again."
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return "An unexpected error occurred. Please try again later."

    def generate_workout_plan(self, user_profile: Dict[str, Any]) -> str:
        """Generate personalized workout plan"""
        system_prompt = """You are a certified personal trainer and fitness expert. Create detailed, safe, and effective workout plans based on user profiles. Always include:
- Warm-up and cool-down
- Proper form instructions
- Progressive difficulty
- Rest periods
- Alternative exercises for different fitness levels
Format your response clearly for mobile reading."""

        user_prompt = f"""
        Create a comprehensive weekly workout plan for:

        **User Profile:**
        - Age: {user_profile.get('age', 'N/A')} years
        - Weight: {user_profile.get('weight', 'N/A')} kg
        - Height: {user_profile.get('height', 'N/A')} cm
        - Gender: {user_profile.get('gender', 'N/A')}
        - Fitness Level: {user_profile.get('fitness_level', 'N/A')}
        - Goals: {user_profile.get('goals', 'N/A')}
        - Medical Conditions: {user_profile.get('medical_conditions') or 'None'}
        - Available Days: {user_profile.get('workout_days', 'N/A')} days per week
        - Workout Duration: {user_profile.get('workout_duration', 'N/A')} minutes per session

        Please provide:
        1. Weekly schedule overview
        2. Detailed daily workouts with exercises, sets, reps
        3. Progression recommendations
        4. Safety tips specific to their profile

        Keep the response under 1200 words and format for easy mobile reading.
        """

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        return self._make_request(messages)

    def generate_diet_plan(self, user_profile: Dict[str, Any]) -> str:
        """Generate personalized diet plan"""
        system_prompt = """You are a qualified nutritionist. Create balanced, healthy meal plans based on user profiles. Always include:
- Caloric requirements calculation
- Macro and micronutrient balance
- Meal timing suggestions
- Hydration recommendations
- Practical preparation tips
Consider dietary restrictions and fitness goals."""

        # Calculate BMR for caloric needs
        age = user_profile.get('age', 25)
        weight = user_profile.get('weight', 70)
        height = user_profile.get('height', 170)
        gender = user_profile.get('gender', 'Male')

        # Harris-Benedict equation
        if gender.lower() == 'male':
            bmr = 88.362 + (13.397 * weight) + (4.799 * height) - (5.677 * age)
        else:
            bmr = 447.593 + (9.247 * weight) + (3.098 * height) - (4.330 * age)

        # Activity factor based on workout frequency
        workout_days = user_profile.get('workout_days', 3)
        if workout_days <= 2:
            activity_factor = 1.2
        elif workout_days <= 4:
            activity_factor = 1.375
        else:
            activity_factor = 1.55

        daily_calories = int(bmr * activity_factor)

        user_prompt = f"""
        Create a comprehensive daily meal plan for:

        **User Profile:**
        - Age: {age} years
        - Weight: {weight} kg
        - Height: {height} cm  
        - Gender: {gender}
        - Fitness Goals: {user_profile.get('goals', 'General fitness')}
        - Dietary Restrictions: {user_profile.get('dietary_restrictions') or 'None'}
        - Estimated Daily Calories Needed: {daily_calories}

        Please provide:
        1. Daily meal structure (breakfast, lunch, dinner, snacks)
        2. Sample meals with approximate calories
        3. Macronutrient breakdown
        4. Pre/post workout nutrition tips
        5. Hydration guidelines
        6. Weekly meal prep suggestions

        Consider their fitness goals and any dietary restrictions.
        Keep response under 1200 words and mobile-friendly format.
        """

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        return self._make_request(messages)

    def generate_exercise_explanation(self, exercise_name: str, user_level: str = "beginner") -> str:
        """Generate detailed exercise explanation"""
        system_prompt = """You are a fitness instructor. Provide clear, safe exercise instructions with proper form cues and common mistakes to avoid."""

        user_prompt = f"""
        Explain how to perform "{exercise_name}" exercise for a {user_level} level person.

        Include:
        1. Step-by-step instructions
        2. Proper form and breathing
        3. Common mistakes to avoid
        4. Modifications for different levels
        5. Muscles targeted

        Keep it concise but comprehensive (under 400 words).
        """

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        return self._make_request(messages, max_tokens=500)

    def analyze_progress(self, progress_data: list, user_profile: Dict[str, Any]) -> str:
        """Analyze user progress and provide insights"""
        system_prompt = """You are a fitness coach analyzing client progress. Provide encouraging, constructive feedback with specific recommendations."""

        # Format progress data for analysis
        progress_summary = []
        for record in progress_data:
            progress_summary.append({
                'date': record[4],
                'weight': record[2],
                'workout_completed': record[3],
                'duration': record[5] if len(record) > 5 else None,
                'calories_burned': record[6] if len(record) > 6 else None
            })

        user_prompt = f"""
        Analyze the fitness progress for a user with goals: "{user_profile.get('goals', 'General fitness')}"

        **Recent Progress Data:**
        {json.dumps(progress_summary, indent=2)}

        **User Profile:**
        - Fitness Level: {user_profile.get('fitness_level', 'Beginner')}
        - Target Workout Days: {user_profile.get('workout_days', 3)}/week

        Please provide:
        1. Progress assessment
        2. Areas of improvement
        3. Specific recommendations
        4. Motivational feedback
        5. Goal adjustments if needed

        Keep response encouraging and actionable (under 600 words).
        """

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        return self._make_request(messages, max_tokens=800)

    def generate_motivation_message(self, user_profile: Dict[str, Any], context: str = "daily") -> str:
        """Generate motivational messages"""
        system_prompt = """You are an enthusiastic fitness coach. Create short, personalized motivational messages that inspire action."""

        user_prompt = f"""
        Create a motivational message for a person with fitness goals: "{user_profile.get('goals', 'staying healthy')}"

        Context: {context}
        Fitness Level: {user_profile.get('fitness_level', 'Beginner')}

        Make it personal, encouraging, and action-oriented.
        Keep it under 100 words.
        """

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        return self._make_request(messages, max_tokens=150, temperature=0.8)

    def answer_fitness_question(self, question: str, user_profile: Dict[str, Any]) -> str:
        """Answer general fitness questions"""
        system_prompt = """You are a knowledgeable fitness expert. Provide accurate, helpful answers to fitness questions. Always prioritize safety and suggest consulting professionals for medical concerns."""

        user_prompt = f"""
        User question: "{question}"

        User context:
        - Fitness Level: {user_profile.get('fitness_level', 'Beginner')}
        - Goals: {user_profile.get('goals', 'General fitness')}
        - Age: {user_profile.get('age', 'N/A')}

        Provide a helpful, accurate answer. If it's medical-related, recommend consulting a healthcare professional.
        Keep response under 500 words.
        """

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        return self._make_request(messages, max_tokens=600)