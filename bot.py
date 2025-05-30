import discord
from discord.ext import commands
import json
import re
import os
import asyncio
from collections import defaultdict

# -------- CONFIG --------
SUBMISSION_CHANNEL = "ask-the-experts"
ANSWERING_CHANNEL = "question-reposting"
FINAL_ANSWER_CHANNEL = "answered-by-expert"
FAQ_LINK = "https://discord.com/channels/849784755388940290/1374490028549603408"
FINAL_ANSWER_LINK = "https://discord.com/channels/849784755388940290/1377375716286533823"

# -------- TIMING CONFIG --------
RECENT_MENTION_HOURS = 12  # How far back to check for recent mentions
RECENT_MENTION_LIMIT = 100  # How many messages to check per channel (reduced to help with rate limiting)
SELECTION_TIMEOUT = 30  # How long to wait for user selection (seconds)
PRE_SELECTION_DELAY = 0.5  # Small delay before posting selection message

# -------- SETUP INTENTS --------
intents = discord.Intents.default()
intents.guilds = True
intents.messages = True
intents.message_content = True  # Required for prefix commands

bot = commands.Bot(command_prefix="!", intents=intents)

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

# -------- TRACK ORIGINAL QUESTIONS --------
question_map = {}  # message_id: {"question": str, "asker_id": int}
pending_selections = {}  # user_id: {"message": Message, "players": [...], "original_question": str, "locked": bool}

# -------- PLAYER NAMES --------
players_data = []  # Will hold the MLB API data

# -------- UTILITY FUNCTIONS --------
def load_words_from_json(filename):
    try:
        with open(filename, "r", encoding="utf-8") as file:
            data = json.load(file)
            return [word.strip().lower() for word in data]
    except Exception as e:
        print(f"Error loading {filename}: {e}")
        return []

def load_players_from_json(filename):
    print(f"🔍 LOADING PLAYERS: Attempting to load {filename}")
    try:
        import os
        print(f"🔍 LOADING PLAYERS: Current working directory: {os.getcwd()}")
        print(f"🔍 LOADING PLAYERS: Files in directory: {os.listdir('.')}")
        
        if not os.path.exists(filename):
            print(f"❌ LOADING PLAYERS: File {filename} does not exist!")
            return []
            
        with open(filename, "r", encoding="utf-8") as file:
            data = json.load(file)
            print(f"🔍 LOADING PLAYERS: Successfully loaded JSON data")
            print(f"🔍 LOADING PLAYERS: Data type: {type(data)}")
            print(f"🔍 LOADING PLAYERS: Data length: {len(data) if isinstance(data, list) else 'not a list'}")
            
            if isinstance(data, list) and len(data) > 0:
                print(f"🔍 LOADING PLAYERS: First player: {data[0]}")
            
            return data if isinstance(data, list) else []
    except FileNotFoundError as e:
        print(f"❌ LOADING PLAYERS: File not found - {filename}: {e}")
        return []
    except json.JSONDecodeError as e:
        print(f"❌ LOADING PLAYERS: JSON decode error in {filename}: {e}")
        return []
    except Exception as e:
        print(f"❌ LOADING PLAYERS: Unexpected error loading {filename}: {e}")
        return []

def extract_potential_names(text):
    """Extract potential player names from text before fuzzy matching"""
    # Note: Reduced debug logging to minimize console spam
    
    # Remove common question words and phrases
    cleaned = text.lower()
    stop_words = ['how', 'is', 'was', 'are', 'were', 'doing', 'playing', 'performed', 'the', 'a', 'an', 'about', 'what', 'when', 'where', 'why', 'should', 'would', 'could', 'can', 'will', 'today', 'yesterday', 'tomorrow', 'this', 'that', 'these', 'those', 'season', 'year', 'game', 'games']
    
    # Split into words and remove stop words
    words = cleaned.split()
    filtered_words = [w for w in words if w not in stop_words and len(w) > 1]
    
    # Try to find name combinations (first + last name patterns)
    potential_names = []
    
    # Look for 2-word combinations that might be names
    for i in range(len(filtered_words) - 1):
        name_combo = f"{filtered_words[i]} {filtered_words[i+1]}"
        if len(name_combo) >= 6:  # Minimum reasonable name length
            potential_names.append(name_combo)
    
    # Also add individual words that might be last names
    for word in filtered_words:
        if len(word) >= 3:
            potential_names.append(word)
    
    # Add the original text as fallback
    potential_names.append(text.lower())
    
    print(f"🔍 NAME EXTRACTION: Found {len(potential_names)} potential names from '{text}'")
    return potential_names

def fuzzy_match_players(text, max_results=5):
    """Fuzzy match player names in text and return top matches - IMPROVED VERSION"""
    from difflib import SequenceMatcher
    
    print(f"🔍 FUZZY MATCH DEBUG: Starting fuzzy match for text: '{text}'")
    
    if not players_data:
        print("🔍 FUZZY MATCH DEBUG: No players data available")
        return []
    
    # Extract potential player names from the text
    potential_names = extract_potential_names(text)
    
    matches = []
    
    # Try fuzzy matching with each potential name
    for potential_name in potential_names:
        # Only log for important potential names to reduce spam
        if len(potential_name) >= 6:
            print(f"🔍 FUZZY MATCH DEBUG: Trying potential name: '{potential_name}'")
        
        for player in players_data:
            player_name = player['name'].lower()
            
            # Calculate similarity
            similarity = SequenceMatcher(None, potential_name, player_name).ratio()
            
            # Special handling for last names - if potential name matches last name well, boost score
            player_last_name = player_name.split()[-1] if ' ' in player_name else player_name
            last_name_similarity = SequenceMatcher(None, potential_name, player_last_name).ratio()
            
            # Check for exact last name match (case insensitive)
            exact_last_name_match = potential_name == player_last_name
            
            # Use the better of full name match or last name match, with bonus for exact last name
            if exact_last_name_match:
                best_similarity = 1.0  # Perfect match for exact last name
            else:
                best_similarity = max(similarity, last_name_similarity)
            
            # SMARTER FILTERING: Avoid partial word false positives
            # If potential name is much longer/shorter than player name, be more strict
            length_ratio = min(len(potential_name), len(player_name)) / max(len(potential_name), len(player_name))
            
            # Check for problematic substring matches (like "invest" matching "vest")
            is_problematic_substring = False
            if len(potential_name) > len(player_last_name) and player_last_name in potential_name:
                # potential_name contains the player's last name as substring (like "invest" contains "vest")
                is_problematic_substring = True
            elif len(player_last_name) > len(potential_name) and potential_name in player_last_name:
                # player's last name contains potential_name as substring
                is_problematic_substring = True
            
            # Adjust threshold based on various factors
            if exact_last_name_match:
                threshold = 0.7  # Keep lower threshold for exact last name matches
            elif is_problematic_substring:
                threshold = 0.95  # Very strict for substring false positives
            elif ' ' in player_name and ' ' not in potential_name:
                # Single word trying to match multi-word name - be stricter unless it's a good last name match
                threshold = 0.85 if last_name_similarity < 0.9 else 0.7
            elif length_ratio < 0.6:
                # Very different lengths - be much stricter
                threshold = 0.9
            else:
                threshold = 0.7
            
            if best_similarity >= threshold:
                matches.append((player, best_similarity))
                if exact_last_name_match:
                    print(f"🔍 FUZZY MATCH DEBUG: EXACT LAST NAME MATCH - '{potential_name}' = '{player_last_name}' (from {player_name}) = {best_similarity:.3f}")
                elif last_name_similarity > similarity:
                    print(f"🔍 FUZZY MATCH DEBUG: GOOD LAST NAME MATCH - '{potential_name}' vs '{player_last_name}' (from {player_name}) = {last_name_similarity:.3f}")
                else:
                    print(f"🔍 FUZZY MATCH DEBUG: GOOD MATCH - '{potential_name}' vs '{player_name}' = {similarity:.3f} (threshold: {threshold:.2f})")
            else:
                # Only log decent attempts to reduce spam
                if best_similarity >= 0.75:  # Increased threshold from 0.5 to reduce logging
                    print(f"🔍 FUZZY MATCH DEBUG: rejected - '{potential_name}' vs '{player_name}' = {best_similarity:.3f} (threshold: {threshold:.2f})")
    
    if not matches:
        print("🔍 FUZZY MATCH DEBUG: No matches found above threshold")
        return []
    
    print(f"🔍 FUZZY MATCH DEBUG: Found {len(matches)} total matches before deduplication")
    
    # Sort by score and remove duplicates by player NAME+TEAM (not just name)
    matches.sort(key=lambda x: x[1], reverse=True)
    seen_players = set()
    unique_matches = []
    
    for player, score in matches:
        # Create unique identifier using both name and team
        player_key = f"{player['name'].lower()}|{player['team'].lower()}"
        if player_key not in seen_players:
            unique_matches.append(player)
            seen_players.add(player_key)
            print(f"🔍 FUZZY MATCH DEBUG: Added unique player - {player['name']} ({player['team']}) - score: {score:.3f}")
            if len(unique_matches) >= max_results:
                break
        else:
            print(f"🔍 FUZZY MATCH DEBUG: Skipped exact duplicate - {player['name']} ({player['team']}) - score: {score:.3f}")
    
    print(f"🔍 FUZZY MATCH DEBUG: Returning {len(unique_matches)} unique matches")
    return unique_matches

def contains_banned_word(text):
    text_lower = text.lower()
    for category, data in banned_categories.items():
        for word in data["words"]:
            word_lower = word.lower()
            # Use word boundaries to match whole words only
            if re.search(rf"\b{re.escape(word_lower)}\b", text_lower):
                print(f"🚫 Found banned word '{word}' in category '{category}'")
                return category
    return None

def contains_mention(text):
    """Check if text contains any @mentions (users, roles, @everyone, @here)"""
    # Check for user mentions <@123456789>
    if re.search(r'<@!?\d+>', text):
        return True
    # Check for role mentions <@&123456789>
    if re.search(r'<@&\d+>', text):
        return True
    # Check for @everyone and @here
    if re.search(r'@(everyone|here)', text, re.IGNORECASE):
        return True
    # Check for plain @username mentions (even though they won't ping without proper formatting)
    if re.search(r'@\w+', text):
        return True
    return False

def contains_url(text):
    """Check if text contains any URLs"""
    # Check for https/http
    if re.search(r'https?://', text, re.IGNORECASE):
        return True
    # Check for common TLDs
    if re.search(r'\b\w+\.(com|org|net|edu|gov|io|co|me|app|ly|gg|tv|fm|tk|ml|ga|cf)\b', text, re.IGNORECASE):
        return True
    # Check for discord links specifically
    if re.search(r'discord\.(gg|com)', text, re.IGNORECASE):
        return True
    # Check for www prefix
    if re.search(r'\bwww\.\w+', text, re.IGNORECASE):
        return True
    return False

def check_player_mentioned(text):
    """Check if any player from the list is mentioned in the text using IMPROVED fuzzy matching"""
    print(f"🔍 CHECK PLAYER DEBUG: Looking for players in: '{text}'")
    
    if not players_data:
        print("🔍 CHECK PLAYER DEBUG: No players data available")
        return None
    
    # First, do a simple direct search for debugging
    text_lower = text.lower()
    direct_matches = []
    for player in players_data:
        player_name_lower = player['name'].lower()
        if player_name_lower in text_lower:
            direct_matches.append(player)
            print(f"🔍 CHECK PLAYER DEBUG: DIRECT MATCH found: {player['name']} ({player['team']})")
    
    print(f"🔍 CHECK PLAYER DEBUG: Found {len(direct_matches)} total direct matches")
    
    # For direct matches, we want to KEEP players with same name but different teams
    # Only remove exact duplicates (same name AND same team)
    if direct_matches:
        seen_players = set()
        unique_direct = []
        for player in direct_matches:
            # Create unique identifier using both name and team
            player_key = f"{player['name'].lower()}|{player['team'].lower()}"
            if player_key not in seen_players:
                unique_direct.append(player)
                seen_players.add(player_key)
                print(f"🔍 CHECK PLAYER DEBUG: Added unique direct match - {player['name']} ({player['team']})")
            else:
                print(f"🔍 CHECK PLAYER DEBUG: Skipped exact duplicate - {player['name']} ({player['team']})")
        
        print(f"🔍 CHECK PLAYER DEBUG: After deduplication: {len(unique_direct)} unique matches")
        
        if unique_direct:
            print(f"🔍 CHECK PLAYER DEBUG: Returning {len(unique_direct)} direct matches")
            return unique_direct
        else:
            print("🔍 CHECK PLAYER DEBUG: No unique direct matches after deduplication!")
    
    print("🔍 CHECK PLAYER DEBUG: No direct matches, trying fuzzy matching...")
    
    # If no direct matches, try fuzzy matching
    matches = fuzzy_match_players(text, max_results=5)
    
    if matches:
        print(f"🔍 CHECK PLAYER DEBUG: Fuzzy matching found {len(matches)} matches")
        return matches
    
    print("🔍 CHECK PLAYER DEBUG: No matches found at all")
    return None

async def check_recent_player_mentions(guild, players_to_check):
    """Check if any of the players were mentioned in the last X hours in bot messages only"""
    import datetime
    
    time_threshold = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=RECENT_MENTION_HOURS)
    recent_mentions = []
    
    # Get both channels
    final_channel = discord.utils.get(guild.text_channels, name=FINAL_ANSWER_CHANNEL)
    answering_channel = discord.utils.get(guild.text_channels, name=ANSWERING_CHANNEL)
    
    for player in players_to_check:
        player_name_lower = player['name'].lower()
        player_uuid = player['uuid'].lower()
        
        # Track where the player was found
        found_in_answering = False
        found_in_final = False
        
        # Check question reposting channel (answering channel) for BOT messages only
        if answering_channel:
            try:
                async for message in answering_channel.history(after=time_threshold, limit=RECENT_MENTION_LIMIT):
                    # Only check messages from the bot itself
                    if message.author == guild.me:  # guild.me is the bot
                        message_lower = message.content.lower()
                        if (re.search(rf"\b{re.escape(player_name_lower)}\b", message_lower) or 
                            player_uuid in message_lower):
                            print(f"🕒 Found {player['name']} in bot message in answering channel")
                            found_in_answering = True
                            break
            except Exception as e:
                print(f"❌ Error checking answering channel: {e}")
        
        # Check final answer channel for BOT messages only
        if final_channel:
            try:
                async for message in final_channel.history(after=time_threshold, limit=RECENT_MENTION_LIMIT):
                    # Only check messages from the bot itself
                    if message.author == guild.me:  # guild.me is the bot
                        message_lower = message.content.lower()
                        if (re.search(rf"\b{re.escape(player_name_lower)}\b", message_lower) or 
                            player_uuid in message_lower):
                            print(f"🕒 Found {player['name']} in bot message in final channel")
                            found_in_final = True
                            break
            except Exception as e:
                print(f"❌ Error checking final channel: {e}")
        
        # Determine status based on where the player was found
        status = None
        if found_in_answering and found_in_final:
            status = "answered"  # Asked and answered
            print(f"🕒 {player['name']} found in both channels - status: answered")
        elif found_in_answering and not found_in_final:
            status = "pending"   # Asked but not answered
            print(f"🕒 {player['name']} found only in answering channel - status: pending")
        elif not found_in_answering and found_in_final:
            status = "answered"  # Edge case: only in final (shouldn't happen normally)
            print(f"🕒 {player['name']} found only in final channel - status: answered (edge case)")
        # If not found in either channel, status remains None (no recent mention)
        
        # Add to results if found (avoid duplicates by name+team)
        if status:
            # Check if we already have this exact player (name + team)
            already_added = False
            for existing in recent_mentions:
                if (existing["player"]["name"].lower() == player["name"].lower() and 
                    existing["player"]["team"].lower() == player["team"].lower()):
                    already_added = True
                    print(f"🕒 Skipping duplicate recent mention for {player['name']} ({player['team']})")
                    break
            
            if not already_added:
                recent_mentions.append({
                    "player": player,
                    "status": status
                })
                print(f"🕒 Added recent mention: {player['name']} ({player['team']}) - {status}")
    
    return recent_mentions

async def process_approved_question(channel, user, question, original_message=None):
    """Process a question that has passed all checks"""
    # Delete the original message if provided
    if original_message:
        try:
            await original_message.delete()
            print("✅ Deleted original user message in process_approved_question")
        except Exception as e:
            print(f"❌ Failed to delete original message in process_approved_question: {e}")
    
    answering_channel = discord.utils.get(channel.guild.text_channels, name=ANSWERING_CHANNEL)
    
    if answering_channel:
        # Format the question for the answering channel
        asker_name = f"**{user.display_name}**"
        formatted_message = f"{asker_name} asked:\n> {question}\n\n❗ **Not Answered**\n\nReply to this message to answer."
        
        try:
            # Post to answering channel
            posted_message = await answering_channel.send(formatted_message)
            print(f"✅ Posted question to #{ANSWERING_CHANNEL}")
            
            # Store the question mapping for later reference
            question_map[posted_message.id] = {
                "question": question,
                "asker_id": user.id
            }
            print(f"✅ Stored question mapping for message ID {posted_message.id}")
            
            # Send confirmation message
            confirmation_msg = await channel.send(f"✅ Your question has been posted for experts to answer.")
            await confirmation_msg.delete(delay=5)
            print("✅ Confirmation message sent and will be deleted in 5 seconds")
            
        except Exception as e:
            print(f"❌ Failed to post question to answering channel: {e}")
            error_msg = await channel.send("❌ Failed to post your question. Please try again.")
            await error_msg.delete(delay=5)
    else:
        print(f"❌ Could not find #{ANSWERING_CHANNEL}")
        error_msg = await channel.send(f"❌ Could not find #{ANSWERING_CHANNEL}")
        await error_msg.delete(delay=5)

async def handle_selection_timeout(user_id, ctx):
    """Handle timeout for player selection"""
    await asyncio.sleep(SELECTION_TIMEOUT)  # Wait for configured timeout
    
    if user_id in pending_selections and not pending_selections[user_id]["locked"]:
        print(f"🕒 Selection timed out for user {user_id} after {SELECTION_TIMEOUT} seconds")
        data = pending_selections[user_id]
        
        # Clean up selection message
        try:
            await data["message"].delete()
            print("✅ Deleted timed-out selection message")
        except Exception as e:
            print(f"❌ Failed to delete timed-out message: {e}")
        
        # Clean up original message
        try:
            await data["original_user_message"].delete()
            print("✅ Deleted original user message after timeout")
        except Exception as e:
            print(f"❌ Failed to delete original message: {e}")
        
        # Remove from pending
        del pending_selections[user_id]
        
        # Handle different timeout types
        if data.get("type") == "block_selection":
            print("⏰ Block selection timed out - question blocked by default")
            return
        elif data.get("type") == "disambiguation_selection":
            print("⏰ Disambiguation selection timed out - blocking question")
            return
        
        # Fallback to normal processing (shouldn't happen with current logic)
        # Note: original message already deleted above, so pass None
        question = data["original_question"]
        await process_approved_question(ctx.channel, ctx.author, question, None)

# -------- EVENTS --------
@bot.event
async def on_ready():
    try:
        print("🔥🔥🔥 BOT IS STARTING UP - THIS SHOULD BE VISIBLE 🔥🔥🔥")
        print(f"✅ Logged in as {bot.user}")
        
        # Print timing configuration
        print(f"⚙️ Timing Config:")
        print(f"  - Recent mention window: {RECENT_MENTION_HOURS} hours")
        print(f"  - Message search limit: {RECENT_MENTION_LIMIT} per channel") 
        print(f"  - Selection timeout: {SELECTION_TIMEOUT} seconds")
        
        banned_categories["profanity"]["words"] = load_words_from_json("profanity.json")
        print(f"✅ Profanity list loaded: {len(banned_categories['profanity']['words'])} words")
        print(f"🔍 First few words: {banned_categories['profanity']['words'][:5]}")
        
        # Load player data
        global players_data
        players_data = load_players_from_json("players.json")
        print(f"✅ Player list loaded: {len(players_data)} players")
        if players_data:
            print(f"🔍 Sample players: {[p['name'] for p in players_data[:3]]}")
            
            # Test search for Joe Ryan specifically
            joe_ryan_found = False
            for player in players_data:
                if "joe ryan" in player['name'].lower():
                    print(f"🎯 FOUND JOE RYAN: {player['name']} - {player['team']}")
                    joe_ryan_found = True
                    break
            
            if not joe_ryan_found:
                print("❌ JOE RYAN NOT FOUND in players database!")
                # Show some Ryan players for debugging
                ryan_players = [p for p in players_data if "ryan" in p['name'].lower()]
                if ryan_players:
                    print(f"🔍 Found {len(ryan_players)} players with 'Ryan' in name:")
                    for rp in ryan_players[:5]:
                        print(f"   - {rp['name']} ({rp['team']})")
        else:
            print("❌ NO PLAYERS DATA LOADED AT ALL!")
        
        print(f"✅ Bot is ready and listening for messages")
        
    except Exception as e:
        print(f"❌ ERROR IN ON_READY: {e}")
        raise e

# -------- PREFIX COMMAND: !ask --------
@bot.command(name="ask")
async def ask_question(ctx, *, question: str = None):
    print(f"🚨 COMMAND HANDLER STARTED - !ask command in #{ctx.channel.name}")
    print(f"🔍 Question: {question}")
    print(f"🔍 Bot permissions in channel: {ctx.channel.permissions_for(ctx.guild.me)}")
    print(f"🔍 Can manage messages: {ctx.channel.permissions_for(ctx.guild.me).manage_messages}")
    
    if ctx.channel.name != SUBMISSION_CHANNEL:
        print(f"❌ Wrong channel: {ctx.channel.name} != {SUBMISSION_CHANNEL}")
        error_msg = await ctx.send(f"Please use this command in #{SUBMISSION_CHANNEL}")
        await error_msg.delete(delay=5)
        return

    if question is None:
        print("❌ No question provided")
        error_msg = await ctx.send("Please provide a question. Usage: `!ask your question here`")
        await error_msg.delete(delay=5)
        return

    print(f"🔍 Checking question length: {len(question)} characters")
    
    # Check character limit (increased to 300)
    if len(question) > 300:
        print(f"🚫 Question too long: {len(question)} characters")
        
        # Delete the user's message first
        try:
            await ctx.message.delete()
            print("✅ Deleted user's long message")
        except Exception as e:
            print(f"❌ Failed to delete user's message: {e}")
        
        error_msg = await ctx.send(f"Your question is too long ({len(question)} characters). Please keep questions under 300 characters.")
        await error_msg.delete(delay=5)
        return

    print(f"🔍 Checking for banned words in: {question}")
    
    # Check for server emotes in the question (custom server emotes only)
    if re.search(r'<a?:\w+:\d+>', question):
        print("🚫 Server emote detected in question")
        # Delete the user's message first
        try:
            await ctx.message.delete()
            print("✅ Deleted user's message with server emote")
        except Exception as e:
            print(f"❌ Failed to delete user's message: {e}")
        
        error_msg = await ctx.send("Server emotes are not allowed in questions. Please ask a text-based question.")
        await error_msg.delete(delay=5)
        return
    
    # Check for mentions in the question
    if contains_mention(question):
        print("🚫 @mention detected in question")
        # Delete the user's message first
        try:
            await ctx.message.delete()
            print("✅ Deleted user's message with @mention")
        except Exception as e:
            print(f"❌ Failed to delete user's message: {e}")
        
        error_msg = await ctx.send("@mentions are not allowed in questions. Please ask your question without mentioning anyone.")
        await error_msg.delete(delay=5)
        return
    
    # Check for URLs in the question
    if contains_url(question):
        print("🚫 URL detected in question")
        # Delete the user's message first
        try:
            await ctx.message.delete()
            print("✅ Deleted user's message with URL")
        except Exception as e:
            print(f"❌ Failed to delete user's message: {e}")
        
        error_msg = await ctx.send("URLs are not allowed in questions. Please ask your question without including any links.")
        await error_msg.delete(delay=5)
        return
    
    banned_category = contains_banned_word(question)
    if banned_category:
        print(f"🚫 Banned word found: {banned_category}")
        # Delete the user's message first
        try:
            await ctx.message.delete()
            print("✅ Deleted user's message with banned word")
        except Exception as e:
            print(f"❌ Failed to delete user's message: {e}")
        
        response = banned_categories[banned_category]["response"]
        error_msg = await ctx.send(response)
        await error_msg.delete(delay=5)
        return

    # Check for player names and fuzzy matching
    print(f"🔍 STARTING FUZZY MATCHING for: {question}")
    print(f"🔍 Total players in database: {len(players_data)}")
    if players_data:
        print(f"🔍 Sample player names: {[p.get('name', 'NO_NAME') for p in players_data[:3]]}")
    else:
        print("❌ NO PLAYERS DATA LOADED!")
        error_msg = await ctx.send("Player database is not available. Please try again later.")
        await error_msg.delete(delay=5)
        try:
            await ctx.message.delete()
        except:
            pass
        return
    
    matched_players = check_player_mentioned(question)
    print(f"🔍 Fuzzy matching returned: {matched_players}")
    
    if matched_players:
        print(f"🎯 Found {len(matched_players)} potential player matches")
        for player in matched_players:
            print(f"🎯 Matched player: {player.get('name', 'NO_NAME')} - {player.get('team', 'NO_TEAM')}")
        
        # Check if we have multiple players (need disambiguation)
        if len(matched_players) > 1:
            print(f"🤔 Multiple players found ({len(matched_players)}) - showing disambiguation selection")
            # Check if user already has a pending selection to avoid duplicates
            if ctx.author.id in pending_selections:
                print(f"⚠️ User {ctx.author.id} already has a pending selection, skipping duplicate")
                return
            
            selection_text = "Multiple players found. Which did you mean:\n"
            reactions = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]
            
            for i, player in enumerate(matched_players):
                if i < len(reactions):
                    selection_text += f"{reactions[i]} {player['name']} - {player['team']}\n"
                    print(f"🤔 Disambiguation option {i+1}: {player['name']} - {player['team']}")
            
            # Add a small delay before showing the selection
            await asyncio.sleep(PRE_SELECTION_DELAY)
            
            print(f"🤔 About to post disambiguation selection...")
            
            # Post selection message
            try:
                selection_msg = await ctx.send(selection_text)
                print(f"🤔 Posted disambiguation selection with ID: {selection_msg.id}")
            except Exception as e:
                print(f"❌ Failed to post disambiguation message: {e}")
                error_msg = await ctx.send("❌ Error creating player selection. Please try again.")
                await error_msg.delete(delay=5)
                return
            
            # Add reactions with delay to avoid rate limiting
            reactions_added = 0
            for i in range(min(len(matched_players), len(reactions))):
                try:
                    await selection_msg.add_reaction(reactions[i])
                    print(f"🤔 Added reaction {reactions[i]}")
                    reactions_added += 1
                    # Small delay between reactions to avoid rate limiting
                    if i < len(matched_players) - 1:  # Don't delay after the last reaction
                        await asyncio.sleep(0.2)
                except Exception as e:
                    print(f"❌ Failed to add reaction {reactions[i]}: {e}")
                    break  # Stop adding reactions if we hit an error
            
            # If we couldn't add any reactions, clean up and try to delete the message
            if reactions_added == 0:
                print("❌ Could not add any reactions, cleaning up")
                try:
                    await selection_msg.delete()
                    await ctx.message.delete()
                except:
                    pass
                error_msg = await ctx.send("❌ Error setting up player selection. Please try again.")
                await error_msg.delete(delay=5)
                return
            
            # Only store pending selection if we successfully added reactions
            pending_selections[ctx.author.id] = {
                "message": selection_msg,
                "players": matched_players,
                "original_question": question,
                "locked": False,
                "original_user_message": ctx.message,
                "type": "disambiguation_selection"  # This is for picking which player they meant
            }
            
            print(f"✅ Posted disambiguation selection with {len(matched_players)} options")
            print(f"✅ Stored pending disambiguation for user {ctx.author.id}")
            
            # Set up timeout
            asyncio.create_task(handle_selection_timeout(ctx.author.id, ctx))
            
            print("🚨 COMMAND HANDLER FINISHED - SHOWING DISAMBIGUATION")
            return
        
        # Check recent mentions for all matched players (only if we have a single player or proceeded past disambiguation)
        recent_mentions = await check_recent_player_mentions(ctx.guild, matched_players)
        
        if recent_mentions:
            print(f"🕒 Found {len(recent_mentions)} players with recent mentions")
            
            # If only one player with recent mentions - direct block
            if len(recent_mentions) == 1:
                mention = recent_mentions[0]
                player = mention["player"]
                status = mention["status"]
                
                print(f"🚫 Single player {player['name']} found with status: {status}")
                
                # Delete the user's message first
                try:
                    await ctx.message.delete()
                    print("✅ Deleted user's message - player recently mentioned")
                except Exception as e:
                    print(f"❌ Failed to delete user's message: {e}")
                
                if status == "answered":
                    error_msg = await ctx.send(f"This player has been asked about recently. There is an answer here: {FINAL_ANSWER_LINK}")
                else:  # pending
                    error_msg = await ctx.send("This player has been asked about recently, please be patient and wait for an answer.")
                
                await error_msg.delete(delay=8)
                print("🚨 COMMAND HANDLER FINISHED - BLOCKED RECENT MENTION")
                return
            
            # Multiple players with recent mentions - show selection dialog
            else:
                print(f"🤔 Multiple players with recent mentions, showing selection")
                print(f"🤔 Creating selection for {len(recent_mentions)} unique players")
                
                # Check if user already has a pending selection to avoid duplicates
                if ctx.author.id in pending_selections:
                    print(f"⚠️ User {ctx.author.id} already has a pending selection, skipping duplicate")
                    return
                
                selection_text = "Multiple players have been asked about recently. Which did you mean:\n"
                reactions = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]
                
                for i, mention in enumerate(recent_mentions):
                    player = mention["player"]
                    status = mention["status"]
                    status_text = "recently answered" if status == "answered" else "pending answer"
                    selection_text += f"{reactions[i]} {player['name']} - {player['team']} ({status_text})\n"
                    print(f"🤔 Selection option {i+1}: {player['name']} - {player['team']} ({status_text})")
                
                # Add a small delay before showing the selection to ensure message is posted
                await asyncio.sleep(PRE_SELECTION_DELAY)
                
                print(f"🤔 About to post selection message...")
                
                # Post selection message
                try:
                    selection_msg = await ctx.send(selection_text)
                    print(f"🤔 Posted selection message with ID: {selection_msg.id}")
                except Exception as e:
                    print(f"❌ Failed to post blocking selection message: {e}")
                    error_msg = await ctx.send("❌ Error creating player selection. Please try again.")
                    await error_msg.delete(delay=5)
                    return
                
                # Add reactions with delay to avoid rate limiting
                reactions_added = 0
                for i in range(len(recent_mentions)):
                    try:
                        await selection_msg.add_reaction(reactions[i])
                        print(f"🤔 Added reaction {reactions[i]}")
                        reactions_added += 1
                        # Small delay between reactions to avoid rate limiting
                        if i < len(recent_mentions) - 1:  # Don't delay after the last reaction
                            await asyncio.sleep(0.2)
                    except Exception as e:
                        print(f"❌ Failed to add reaction {reactions[i]}: {e}")
                        break  # Stop adding reactions if we hit an error
                
                # If we couldn't add any reactions, clean up and try to delete the message
                if reactions_added == 0:
                    print("❌ Could not add any reactions, cleaning up")
                    try:
                        await selection_msg.delete()
                        await ctx.message.delete()
                    except:
                        pass
                    error_msg = await ctx.send("❌ Error setting up player selection. Please try again.")
                    await error_msg.delete(delay=5)
                    return
                
                # Only store pending selection if we successfully added reactions (but for blocking purposes)
                pending_selections[ctx.author.id] = {
                    "message": selection_msg,
                    "players": [m["player"] for m in recent_mentions],
                    "mentions": recent_mentions,
                    "original_question": question,
                    "locked": False,
                    "original_user_message": ctx.message,
                    "type": "block_selection"  # This is for blocking, not approval
                }
                
                print(f"✅ Posted blocking selection message with {len(recent_mentions)} options")
                print(f"✅ Stored pending selection for user {ctx.author.id}")
                
                # Set up timeout
                asyncio.create_task(handle_selection_timeout(ctx.author.id, ctx))
                
                print("🚨 COMMAND HANDLER FINISHED - SHOWING SELECTION")
                return
        
        # No recent mentions found - continue with normal processing
        print("✅ No recent mentions found, continuing with normal question processing")
    else:
        print("🔍 No player matches found")

    # All checks passed - post question to answering channel
    print("✅ All checks passed, posting to answering channel")
    
    # Use the centralized function with original message for deletion
    await process_approved_question(ctx.channel, ctx.author, question, ctx.message)
        
    print("🚨 COMMAND HANDLER FINISHED - NORMAL PROCESSING")

# -------- MESSAGE LISTENER --------
@bot.event
async def on_message(message):
    if message.author.bot:
        return
    
    # Only process messages in specific channels we care about
    relevant_channels = [SUBMISSION_CHANNEL, ANSWERING_CHANNEL, FINAL_ANSWER_CHANNEL]
    
    if message.channel.name not in relevant_channels:
        # Ignore messages in channels we don't care about
        return
    
    print(f"📨 Message received in #{message.channel.name}: {message.content[:50]}...")

    # Handle submission channel - block non-commands only
    if message.channel.name == SUBMISSION_CHANNEL:
        # For !ask commands, do NOTHING here - let Discord.py process them naturally
        if message.content.startswith("!ask"):
            print("📝 !ask command detected - will be processed by Discord.py naturally")
            # DO NOT call bot.process_commands here - it will be called at the end
        else:
            # Block everything else: regular text, emojis, server emotes, attachments, etc.
            print(f"🚫 Blocking non-command message in {SUBMISSION_CHANNEL}: '{message.content}'")
            print(f"📎 Attachments: {len(message.attachments)}")
            
            # Delete the original message first
            try:
                await message.delete()
                print("✅ Original message deleted")
            except Exception as e:
                print(f"❌ Failed to delete message: {e}")
            
            error_msg = await message.channel.send(
                f"Only the `!ask` command is allowed in #{SUBMISSION_CHANNEL}."
            )
            await error_msg.delete(delay=5)
            # Don't process commands for blocked messages
            return

    # Handle expert answers (only in answering channel)
    elif message.channel.name == ANSWERING_CHANNEL and message.reference:
        print(f"🔍 Checking for referenced message in {ANSWERING_CHANNEL}")
        referenced = message.reference.resolved
        if referenced and referenced.id in question_map:
            print(f"✅ Found matching question, moving to final channel")
            meta = question_map.pop(referenced.id)
            final_channel = discord.utils.get(message.guild.text_channels, name=FINAL_ANSWER_CHANNEL)

            if final_channel:
                asker_mention = f"<@{meta['asker_id']}>"
                expert_name = message.author.display_name
                # Use dashes for clear visual separation
                formatted_answer = f"-----\n**Question:**\n{asker_mention} asked: {meta['question']}\n\n**{expert_name}** replied:\n{message.content}\n-----"
                await final_channel.send(formatted_answer)
                try:
                    # Fetch the message fresh from Discord to get current content
                    fresh_message = await message.channel.fetch_message(referenced.id)
                    original_content = fresh_message.content
                    print(f"🔍 Original content: {repr(original_content)}")
                    
                    # Replace the red exclamation and "Not Answered" with green check and "Answered"
                    # Also remove the "Reply to this message to answer" line
                    if "❗ **Not Answered**\n\nReply to this message to answer." in original_content:
                        updated_content = original_content.replace("❗ **Not Answered**\n\nReply to this message to answer.", "✅ **Answered**")
                        print("🔧 Replaced full section with reply instruction")
                    elif "❗ **Not Answered**\n" in original_content:
                        updated_content = original_content.replace("❗ **Not Answered**\n", "✅ **Answered**\n")
                        # Also remove the reply instruction if it exists separately
                        updated_content = updated_content.replace("\nReply to this message to answer.", "")
                        updated_content = updated_content.replace("Reply to this message to answer.", "")
                        print("🔧 Replaced with newline version and removed reply instruction")
                    elif "❗ **Not Answered**" in original_content:
                        updated_content = original_content.replace("❗ **Not Answered**", "✅ **Answered**")
                        # Also remove the reply instruction if it exists separately
                        updated_content = updated_content.replace("\nReply to this message to answer.", "")
                        updated_content = updated_content.replace("Reply to this message to answer.", "")
                        print("🔧 Replaced without newline version and removed reply instruction")
                    else:
                        # Fallback: append the answered status
                        updated_content = original_content + "\n\n✅ **Answered**\n"
                        print("🔧 Used fallback append method")
                    
                    print(f"🔍 Updated content: {repr(updated_content)}")
                    
                    # Check if content actually changed
                    if updated_content != original_content:
                        await fresh_message.edit(content=updated_content)
                        print("✅ Updated original message with answered status")
                    else:
                        print("⚠️ No changes detected in content")
                        
                except Exception as e:
                    print(f"❌ Failed to edit original message: {e}")
                    print(f"❌ Error details: {type(e).__name__}: {str(e)}")
            else:
                print(f"❌ Could not find #{FINAL_ANSWER_CHANNEL}")
        else:
            print("❌ No matching question found in question_map")
    
    # Process commands ONCE at the end for ALL messages
    await bot.process_commands(message)

# -------- REACTION HANDLER FOR PLAYER SELECTION --------
@bot.event
async def on_reaction_add(reaction, user):
    if user.bot:
        return
    
    # Check if this is a pending selection
    if user.id not in pending_selections:
        return
    
    selection_data = pending_selections[user.id]
    
    # Check if reaction is on the correct message
    if reaction.message.id != selection_data["message"].id:
        return
    
    # Check if already locked
    if selection_data["locked"]:
        return
    
    # Lock the selection
    selection_data["locked"] = True
    
    # Valid reactions
    reactions = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]
    
    if str(reaction.emoji) in reactions:
        selected_index = reactions.index(str(reaction.emoji))
        
        # Check if index is valid
        if selected_index < len(selection_data["players"]):
            selected_player = selection_data["players"][selected_index]
            print(f"🎯 User selected: {selected_player['name']}")
            
            # Clean up messages first
            try:
                await selection_data["message"].delete()
                print("✅ Deleted selection message")
            except Exception as e:
                print(f"❌ Failed to delete selection message: {e}")
            
            # Note: original_user_message will be deleted in process_approved_question
            
            # Remove from pending selections
            del pending_selections[user.id]
            
            # Handle different selection types
            if selection_data.get("type") == "block_selection":
                # This is a blocking selection - show appropriate block message
                # Find the selected player's status
                selected_mention = None
                for mention in selection_data["mentions"]:
                    if mention["player"]["uuid"] == selected_player["uuid"]:
                        selected_mention = mention
                        break
                
                if selected_mention:
                    status = selected_mention["status"]
                    if status == "answered":
                        error_msg = await reaction.message.channel.send(
                            f"This player has been asked about recently. There is an answer here: {FINAL_ANSWER_LINK}"
                        )
                    else:  # pending
                        error_msg = await reaction.message.channel.send(
                            "This player has been asked about recently, please be patient and wait for an answer."
                        )
                    
                    await error_msg.delete(delay=8)
                    return
            
            elif selection_data.get("type") == "disambiguation_selection":
                # This is a disambiguation selection - now check recent mentions for the selected player
                print(f"🎯 User disambiguated to: {selected_player['name']} ({selected_player['team']})")
                
                # Check recent mentions for this specific player
                recent_mentions = await check_recent_player_mentions(reaction.message.guild, [selected_player])
                
                if recent_mentions:
                    mention = recent_mentions[0]
                    status = mention["status"]
                    
                    print(f"🚫 Selected player {selected_player['name']} has recent mention with status: {status}")
                    
                    if status == "answered":
                        error_msg = await reaction.message.channel.send(
                            f"This player has been asked about recently. There is an answer here: {FINAL_ANSWER_LINK}"
                        )
                    else:  # pending
                        error_msg = await reaction.message.channel.send(
                            "This player has been asked about recently, please be patient and wait for an answer."
                        )
                    
                    await error_msg.delete(delay=8)
                    return
                else:
                    # No recent mentions - proceed with the question, adding selected player info
                    print(f"✅ Selected player {selected_player['name']} has no recent mentions - proceeding with question")
                    
                    # Append selected player info to make it clear which player they meant
                    modified_question = f"{selection_data['original_question']} ({selected_player['name']} - {selected_player['team']})"
                    print(f"🔧 Modified question: {modified_question}")
                    
                    await process_approved_question(
                        reaction.message.channel,
                        user,
                        modified_question,
                        selection_data["original_user_message"]
                    )
                    return
            
            # Fallback to normal processing (shouldn't happen with current logic)
            await process_approved_question(
                reaction.message.channel, 
                user, 
                selection_data["original_question"],
                selection_data.get("original_user_message")
            )
    
    # Invalid reaction - clean up and remove from pending
    else:
        try:
            await selection_data["message"].delete()
            await selection_data["original_user_message"].delete()
        except:
            pass
        del pending_selections[user.id]

# -------- RUN --------
bot.run(os.getenv('DISCORD_TOKEN'))