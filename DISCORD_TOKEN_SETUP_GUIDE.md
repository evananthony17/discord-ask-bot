# 🔑 Discord Token Setup Guide

## Current Status
Your Discord bot is configured to read the token from an environment variable, but it's not currently set.

## Where Your Discord Token Should Be Located

### 📍 Current Configuration
In your `config.py` file, the token is configured as:
```python
DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN")
```

This means your bot expects the token to be stored as an environment variable named `DISCORD_TOKEN`.

## 🔧 How to Set Up Your Discord Token

### Option 1: Create a .env File (Recommended for Development)

1. **Create a `.env` file** in your project root directory:
   ```
   c:/Users/17034/discord-bots/.env
   ```

2. **Add your token to the .env file**:
   ```
   DISCORD_TOKEN=your_actual_discord_token_here
   WEBHOOK_LOGS_URL=your_webhook_url_here
   WEBHOOK_ANALYTICS_URL=your_analytics_webhook_url_here
   ```

3. **Install python-dotenv** (if not already installed):
   ```bash
   pip install python-dotenv
   ```

4. **Update your bot.py** to load the .env file (add this at the top):
   ```python
   from dotenv import load_dotenv
   load_dotenv()  # This loads the .env file
   ```

### Option 2: Set Environment Variables Directly

#### Windows PowerShell (Current Session Only):
```powershell
$env:DISCORD_TOKEN = "your_actual_discord_token_here"
$env:WEBHOOK_LOGS_URL = "your_webhook_url_here"
$env:WEBHOOK_ANALYTICS_URL = "your_analytics_webhook_url_here"
```

#### Windows PowerShell (Permanent - User Level):
```powershell
[Environment]::SetEnvironmentVariable("DISCORD_TOKEN", "your_actual_discord_token_here", "User")
[Environment]::SetEnvironmentVariable("WEBHOOK_LOGS_URL", "your_webhook_url_here", "User")
[Environment]::SetEnvironmentVariable("WEBHOOK_ANALYTICS_URL", "your_analytics_webhook_url_here", "User")
```

#### Windows Command Prompt (Current Session Only):
```cmd
set DISCORD_TOKEN=your_actual_discord_token_here
set WEBHOOK_LOGS_URL=your_webhook_url_here
set WEBHOOK_ANALYTICS_URL=your_analytics_webhook_url_here
```

### Option 3: Production Environment (Render, Heroku, etc.)

For production deployment, set environment variables in your hosting platform:

#### Render:
1. Go to your service dashboard
2. Navigate to "Environment" tab
3. Add environment variables:
   - `DISCORD_TOKEN`: your_token_here
   - `WEBHOOK_LOGS_URL`: your_webhook_url
   - `WEBHOOK_ANALYTICS_URL`: your_analytics_webhook_url

#### Heroku:
```bash
heroku config:set DISCORD_TOKEN=your_token_here
heroku config:set WEBHOOK_LOGS_URL=your_webhook_url
heroku config:set WEBHOOK_ANALYTICS_URL=your_analytics_webhook_url
```

## 🔍 How to Get Your Discord Token

### If You Don't Have a Discord Bot Yet:

1. **Go to Discord Developer Portal**: https://discord.com/developers/applications
2. **Create New Application** or select existing one
3. **Go to "Bot" section** in the left sidebar
4. **Click "Reset Token"** to generate a new token
5. **Copy the token** (you won't be able to see it again!)

### If You Have an Existing Bot:

1. **Go to Discord Developer Portal**: https://discord.com/developers/applications
2. **Select your application**
3. **Go to "Bot" section**
4. **Click "Reset Token"** to generate a new token
5. **Copy the token**

## 🛡️ Security Best Practices

### ✅ DO:
- Store tokens in environment variables
- Use `.env` files for local development
- Add `.env` to your `.gitignore` (already done ✅)
- Use different tokens for development and production
- Regenerate tokens if they're accidentally exposed

### ❌ DON'T:
- Hard-code tokens in your source code
- Commit tokens to version control
- Share tokens in chat or email
- Use production tokens for development

## 🔧 Quick Setup Script

Here's a quick setup script you can run:

```powershell
# Create .env file with template
@"
DISCORD_TOKEN=your_discord_token_here
WEBHOOK_LOGS_URL=your_webhook_url_here
WEBHOOK_ANALYTICS_URL=your_analytics_webhook_url_here
LOG_LEVEL=INFO
"@ | Out-File -FilePath ".env" -Encoding UTF8

Write-Host "Created .env file. Please edit it with your actual tokens."
```

## 🧪 Testing Your Setup

After setting up your token, test it with:

```python
import os
from dotenv import load_dotenv  # If using .env file

load_dotenv()  # If using .env file

token = os.environ.get("DISCORD_TOKEN")
if token:
    print("✅ Discord token is loaded")
    print(f"Token starts with: {token[:10]}...")
else:
    print("❌ Discord token is not set")
```

## 🚨 Current Issue

Your bot is currently configured correctly, but the `DISCORD_TOKEN` environment variable is not set. You need to:

1. **Get your Discord bot token** from the Discord Developer Portal
2. **Set it as an environment variable** using one of the methods above
3. **Restart your terminal/IDE** after setting environment variables
4. **Test your bot** to ensure it can connect

## 📁 File Locations Summary

- **Configuration**: `c:/Users/17034/discord-bots/config.py` ✅
- **Environment file**: `c:/Users/17034/discord-bots/.env` (create this)
- **Git ignore**: `c:/Users/17034/discord-bots/.gitignore` ✅ (already ignores .env files)

Your setup is secure and follows best practices - you just need to add the actual token value!
