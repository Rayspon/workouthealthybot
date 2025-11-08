#!/bin/bash

# Telegram Fitness Bot Deployment Script
# This script helps set up and deploy the bot to Render

echo "🏋️‍♂️ Telegram Fitness Bot Deployment Setup"
echo "=========================================="

# Check if required files exist
echo "📋 Checking required files..."

required_files=("main.py" "bot.py" "requirements.txt" "render.yaml" "database_manager.py" "ai_service.py" "reminder_service.py")
missing_files=()

for file in "${required_files[@]}"; do
    if [ ! -f "$file" ]; then
        missing_files+=("$file")
    fi
done

if [ ${#missing_files[@]} -ne 0 ]; then
    echo "❌ Missing required files:"
    printf '%s\n' "${missing_files[@]}"
    echo "Please ensure all files are in the current directory."
    exit 1
fi

echo "✅ All required files found!"

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "📝 Creating .env file..."
    cp .env.example .env
    echo "✅ Created .env file. Please edit it with your actual tokens and keys."
    echo ""
    echo "You need to set:"
    echo "1. TELEGRAM_TOKEN (from @BotFather)"
    echo "2. OPENROUTER_API_KEY (from openrouter.ai)"
    echo "3. WEBHOOK_URL (your Render app URL)"
    echo ""
    read -p "Press Enter after you've configured your .env file..."
fi

# Validate environment variables
echo "🔍 Validating environment variables..."
source .env 2>/dev/null || true

if [ -z "$TELEGRAM_TOKEN" ] || [ "$TELEGRAM_TOKEN" = "your_telegram_bot_token_here" ]; then
    echo "❌ TELEGRAM_TOKEN not set properly in .env file"
    echo "Get your token from @BotFather on Telegram"
    exit 1
fi

if [ -z "$OPENROUTER_API_KEY" ] || [ "$OPENROUTER_API_KEY" = "your_openrouter_api_key_here" ]; then
    echo "❌ OPENROUTER_API_KEY not set properly in .env file"
    echo "Get your API key from https://openrouter.ai/"
    exit 1
fi

echo "✅ Environment variables configured!"

# Initialize git repository if needed
if [ ! -d ".git" ]; then
    echo "📦 Initializing Git repository..."
    git init
    git add .
    git commit -m "Initial commit - Telegram Fitness Bot"
    echo "✅ Git repository initialized!"
fi

# Create .gitignore if it doesn't exist
if [ ! -f ".gitignore" ]; then
    echo "📝 Creating .gitignore..."
    cat > .gitignore << EOF
# Environment variables
.env

# Database
*.db
*.sqlite
*.sqlite3

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual environments
virtualenv/
env/
ENV/

# IDE
.vscode/
.idea/
*.swp
*.swo

# Logs
*.log

# OS
.DS_Store
Thumbs.db
EOF
    echo "✅ .gitignore created!"
fi

# Test bot locally (optional)
echo ""
read -p "🧪 Do you want to test the bot locally first? (y/n): " test_local

if [ "$test_local" = "y" ] || [ "$test_local" = "Y" ]; then
    echo "🚀 Starting local test..."
    echo "Press Ctrl+C to stop the test"
    export ENVIRONMENT=development
    python main.py &
    bot_pid=$!

    echo "Bot is running locally. Test it by messaging your bot on Telegram."
    read -p "Press Enter when you're done testing..."

    kill $bot_pid 2>/dev/null
    echo "✅ Local test completed!"
fi

# Deployment instructions
echo ""
echo "🚀 DEPLOYMENT INSTRUCTIONS"
echo "========================="
echo ""
echo "1. Create a Render account at https://render.com"

echo ""
echo "2. Create a new Web Service:"
   echo "   - Connect your GitHub repository"
   echo "   - Choose 'Python' as the environment"
   echo "   - Build Command: pip install -r requirements.txt"
   echo "   - Start Command: gunicorn main:app"

echo ""
echo "3. Set Environment Variables in Render:"
   echo "   - ENVIRONMENT = production"
   echo "   - TELEGRAM_TOKEN = $TELEGRAM_TOKEN"
   echo "   - OPENROUTER_API_KEY = $OPENROUTER_API_KEY"
   echo "   - WEBHOOK_URL = https://your-app-name.onrender.com/"

echo ""
echo "4. Deploy your service!"

echo ""
echo "📋 IMPORTANT NOTES:"
echo "==================="
echo "• Replace 'your-app-name' with your actual Render app name"
echo "• The webhook URL must end with a forward slash (/)"
echo "• Free Render services may sleep after 15 minutes of inactivity"
echo "• The database will be reset when the service restarts (use persistent storage for production)"

echo ""
echo "🔧 OPTIONAL IMPROVEMENTS:"
echo "======================="
echo "• Add persistent PostgreSQL database"
echo "• Set up monitoring and logging"
echo "• Implement backup strategies"
echo "• Add more advanced AI features"


# Create README if it doesn't exist
if [ ! -f "README.md" ]; then
    echo "📖 Creating README.md..."
    cat > README.md << 'EOF'
# Telegram Fitness Bot 🏋️‍♂️

A personalized fitness bot that creates custom workout and diet plans using AI, tracks progress, and sends motivational reminders.

## Features

- 🤖 AI-powered personalized workout plans
- 🥗 Custom diet recommendations
- 📊 Progress tracking and analytics
- 🔔 Automated reminders and motivation
- 🏆 Achievement system
- 📱 User-friendly Telegram interface

## Setup

### Prerequisites

1. Python 3.8+
2. Telegram Bot Token (from [@BotFather](https://t.me/botfather))
3. OpenRouter API Key (from [openrouter.ai](https://openrouter.ai))

### Local Development

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Copy `.env.example` to `.env` and configure your tokens
4. Run the bot:
   ```bash
   python main.py
   ```

### Deployment to Render

1. Push your code to GitHub
2. Connect your repository to Render
3. Set the environment variables
4. Deploy as a Web Service

See `deploy.sh` for detailed deployment instructions.

## Usage

1. Start a chat with your bot on Telegram
2. Use `/start` to begin setup
3. Complete your fitness profile
4. Get personalized workout and diet plans
5. Track your progress and earn achievements

## Commands

- `/start` - Initialize bot and show main menu
- `/help` - Show available commands
- `/profile` - View your fitness profile
- `/workout` - Get your workout plan
- `/diet` - Get your diet plan
- `/progress` - Log and view progress
- `/reminder` - Set workout reminders

## Architecture

- `main.py` - Entry point of the application
- `bot.py` - Main bot logic and handlers
- `database_manager.py` - SQLite database operations
- `ai_service.py` - OpenRouter AI integration
- `reminder_service.py` - Automated reminder system

## License

MIT License - see LICENSE file for details.
EOF
    echo "✅ README.md created!"
fi

echo ""
echo "🎉 Setup complete! Your bot is ready for deployment."

echo ""
echo "Next steps:"
echo "1. Push your code to GitHub"
echo "2. Follow the deployment instructions above"
echo "3. Test your deployed bot"

echo ""
echo "Good luck with your fitness bot! 💪"
