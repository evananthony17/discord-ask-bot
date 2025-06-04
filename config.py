import os

# -------- ENVIRONMENT VARIABLES --------
DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN")
WEBHOOK_LOGS_URL = os.environ.get("WEBHOOK_LOGS_URL", "")
WEBHOOK_ANALYTICS_URL = os.environ.get("WEBHOOK_ANALYTICS_URL", "")
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")

# -------- LOG LEVELS --------
LOG_LEVELS = {"DEBUG": 0, "INFO": 1, "WARNING": 2, "ERROR": 3}

# -------- CHANNEL NAMES --------
SUBMISSION_CHANNEL = "ask-the-experts"
ANSWERING_CHANNEL = "question-reposting"
FINAL_ANSWER_CHANNEL = "answered-by-expert"

# -------- LINKS --------
FAQ_LINK = "https://discord.com/channels/849784755388940290/1374490028549603408"
FINAL_ANSWER_LINK = "https://discord.com/channels/849784755388940290/1377375716286533823"

# -------- TIMING CONFIG --------
RECENT_MENTION_HOURS = 24
RECENT_MENTION_LIMIT = 200
SELECTION_TIMEOUT = 30
PRE_SELECTION_DELAY = 0.5

# -------- BANNED WORD CATEGORIES --------
banned_categories = {
    "profanity": {
        "words": [],
        "response": "Your question contains profanity and was removed."
    },
    "banned_topics": {
        "words": ["lock", "locks", "auto clicker", "clicker", "just pulled", "pulled", "who do I invest in", "NFT", "DM", "Crypto", "OnlyFans"],
        "response": f"This topic is not allowed, please consult the FAQs: {FAQ_LINK}"
    }
}

# -------- GLOBAL DATA STRUCTURES --------
pending_selections = {}  # user_id: {"message": Message, "players": [...], "original_question": str, "locked": bool}
timeout_tasks = {}  # user_id: asyncio.Task (for proper cleanup)
players_data = []  # Will hold the MLB API data
player_nicknames = {}  # Global variable to store loaded nicknames

# -------- REACTION EMOJIS --------
REACTIONS = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣"]

# -------- ALLOW OTHERS TO REACT --------
ALLOW_HELPER_REACTIONS = False  # Only original questioner can react to disambiguations