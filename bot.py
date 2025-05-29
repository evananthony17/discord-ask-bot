import discord
from discord.ext import commands
import json
import re
import os
import asyncio

# -------- CONFIG --------
SUBMISSION_CHANNEL = "ask-the-experts"
ANSWERING_CHANNEL = "question-reposting"
FINAL_ANSWER_CHANNEL = "answered-by-expert"
FAQ_LINK = "https://discord.com/channels/849784755388940290/1374490028549603408"
FINAL_ANSWER_LINK = "https://discord.com/channels/849784755388940290/1377375716286533823"

# -------- TIMING CONFIG --------
RECENT_MENTION_HOURS = 12  # How far back to check for recent mentions
RECENT_MENTION_LIMIT = 200  # How many messages to check per channel
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
    try:
        with open(filename, "r", encoding="utf-8") as file:
            data = json.load(file)
            # Expecting array of player objects from MLB API
            return data if isinstance(data, list) else []
    except Exception as e:
        print(f"Error loading {filename}: {e}")
        return []

def fuzzy_match_players(text, max_results=5):
    """Fuzzy match player names in text and return top matches"""
    from difflib import SequenceMatcher
    
    if not players_data:
        return []
    
    matches = []
    text_lower = text.lower()
    
    # Extract potential player names from text (simple approach)
    words = re.findall(r'\b[A-Za-z]+\b', text)
    search_terms = []
    
    # Create search terms from consecutive words
    for i in range(len(words)):
        for j in range(i + 1, min(i + 4, len(words) + 1)):  # Up to 3-word combinations
            search_terms.append(' '.join(words[i:j]))
    
    # Also add individual words
    search_terms.extend(words)
    
    # Score each player against search terms
    for player in players_data:
        player_name = player['name'].lower()
        player_uuid = player['uuid'].lower()
        best_score = 0
        
        # Check name matching
        for term in search_terms:
            name_score = SequenceMatcher(None, term.lower(), player_name).ratio()
            uuid_score = SequenceMatcher(None, term.lower(), player_uuid[:8]).ratio()  # First 8 chars of UUID
            best_score = max(best_score, name_score, uuid_score)
        
        # Only include if similarity is above threshold
        if best_score > 0.6:  # Adjust threshold as needed
            matches.append((player, best_score))
    
    # Sort by score and remove duplicates by UUID
    matches.sort(key=lambda x: x[1], reverse=True)
    seen_uuids = set()
    unique_matches = []
    
    for player, score in matches:
        if player['uuid'] not in seen_uuids:
            unique_matches.append(player)
            seen_uuids.add(player['uuid'])
            if len(unique_matches) >= max_results:
                break
    
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
    """Check if any player from the list is mentioned in the text using fuzzy matching"""
    matches = fuzzy_match_players(text, max_results=5)
    return matches if matches else None

async def check_recent_player_mentions(guild, players_to_check):
    """Check if any of the players were mentioned in the last X hours in answering or final channels"""
    import datetime
    
    time_threshold = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=RECENT_MENTION_HOURS)
    recent_mentions = []
    
    # Get both channels
    final_channel = discord.utils.get(guild.text_channels, name=FINAL_ANSWER_CHANNEL)
    answering_channel = discord.utils.get(guild.text_channels, name=ANSWERING_CHANNEL)
    
    for player in players_to_check:
        player_name_lower = player['name'].lower()
        player_uuid = player['uuid'].lower()
        found_status = None
        
        # Check final answer channel first (answered)
        if final_channel and not found_status:
            try:
                async for message in final_channel.history(after=time_threshold, limit=RECENT_MENTION_LIMIT):
                    message_lower = message.content.lower()
                    if (re.search(rf"\b{re.escape(player_name_lower)}\b", message_lower) or 
                        player_uuid in message_lower):
                        print(f"🕒 Found recent mention of {player['name']} in final channel")
                        found_status = "answered"
                        break
            except Exception as e:
                print(f"❌ Error checking final channel: {e}")
        
        # Check question reposting channel (pending)
        if answering_channel and not found_status:
            try:
                async for message in answering_channel.history(after=time_threshold, limit=RECENT_MENTION_LIMIT):
                    message_lower = message.content.lower()
                    if (re.search(rf"\b{re.escape(player_name_lower)}\b", message_lower) or 
                        player_uuid in message_lower):
                        print(f"🕒 Found recent mention of {player['name']} in answering channel")
                        found_status = "pending"
                        break
            except Exception as e:
                print(f"❌ Error checking answering channel: {e}")
        
        # Add to results if found
        if found_status:
            recent_mentions.append({
                "player": player,
                "status": found_status
            })
    
    return recent_mentions

async def process_approved_question(channel, user, question):
    """Process a question that has passed all checks"""
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
        
        # For blocking selections, timeout means no action (question is blocked by default)
        if data.get("type") == "block_selection":
            print("⏰ Block selection timed out - question blocked by default")
            return
        
        # This shouldn't happen with new logic, but fallback to normal processing
        question = data["original_question"]
        await process_approved_question(ctx.channel, ctx.author, question)

# -------- EVENTS --------
@bot.event
async def on_ready():
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
    
    print(f"✅ Bot is ready and listening for messages")

# -------- PREFIX COMMAND: !ask --------
@bot.command(name="ask")
async def ask_question(ctx, *, question: str = None):
    print(f"🎯 !ask command triggered in #{ctx.channel.name}")
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
    print(f"🔍 Checking for player mentions in: {question}")
    matched_players = check_player_mentioned(question)
    if matched_players:
        print(f"🎯 Found {len(matched_players)} potential player matches")
        
        # Check recent mentions for all matched players
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
                    error_msg = await ctx.send(f"This player has been asked about recently. There is an answer in #answered-by-expert {FINAL_ANSWER_LINK}")
                else:  # pending
                    error_msg = await ctx.send("This player has been asked about recently, please be patient and wait for an answer.")
                
                await error_msg.delete(delay=8)
                return
            
            # Multiple players with recent mentions - show selection dialog
            else:
                print(f"🤔 Multiple players with recent mentions, showing selection")
                selection_text = "Multiple players have been asked about recently. Which did you mean:\n"
                reactions = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]
                
                for i, mention in enumerate(recent_mentions):
                    player = mention["player"]
                    status = mention["status"]
                    status_text = "recently answered" if status == "answered" else "pending answer"
                    selection_text += f"{reactions[i]} {player['name']} - {player['team']} ({status_text})\n"
                
                # Add a small delay before showing the selection to ensure message is posted
                await asyncio.sleep(PRE_SELECTION_DELAY)
                
                # Post selection message
                selection_msg = await ctx.send(selection_text)
                
                # Add reactions
                for i in range(len(recent_mentions)):
                    await selection_msg.add_reaction(reactions[i])
                
                # Store pending selection (but for blocking purposes)
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
                
                # Set up 15-second timeout
                asyncio.create_task(handle_selection_timeout(ctx.author.id, ctx))
                
                return
        
        # No recent mentions found - continue with normal processing
        print("✅ No recent mentions found, continuing with normal question processing")
    
    # No player matches or no recent mentions - continue normal processing

    # All checks passed - post question to answering channel
    print("✅ All checks passed, posting to answering channel")
    answering_channel = discord.utils.get(ctx.guild.text_channels, name=ANSWERING_CHANNEL)
    
    if answering_channel:
        # Format the question for the answering channel
        asker_name = f"**{ctx.author.display_name}**"
        formatted_message = f"{asker_name} asked:\n> {question}\n\n❗ **Not Answered**\n\nReply to this message to answer."
        
        try:
            # Post to answering channel
            posted_message = await answering_channel.send(formatted_message)
            print(f"✅ Posted question to #{ANSWERING_CHANNEL}")
            
            # Store the question mapping for later reference
            question_map[posted_message.id] = {
                "question": question,
                "asker_id": ctx.author.id
            }
            print(f"✅ Stored question mapping for message ID {posted_message.id}")
            
            # Delete the original message
            try:
                await ctx.message.delete()
                print("✅ Deleted original user message")
            except Exception as e:
                print(f"❌ Failed to delete original message: {e}")
            
            # Send confirmation message
            confirmation_msg = await ctx.send(f"✅ Your question has been posted for experts to answer.")
            await confirmation_msg.delete(delay=5)
            print("✅ Confirmation message sent and will be deleted in 5 seconds")
            
        except Exception as e:
            print(f"❌ Failed to post question to answering channel: {e}")
            error_msg = await ctx.send("❌ Failed to post your question. Please try again.")
            await error_msg.delete(delay=5)
    else:
        print(f"❌ Could not find #{ANSWERING_CHANNEL}")
        error_msg = await ctx.send(f"❌ Could not find #{ANSWERING_CHANNEL}")
        await error_msg.delete(delay=5)

# -------- MESSAGE LISTENER --------
@bot.event
async def on_message(message):
    if message.author.bot:
        return
    
    # Only process messages in the submission channel or answering channel
    if message.channel.name not in [SUBMISSION_CHANNEL, ANSWERING_CHANNEL]:
        await bot.process_commands(message)
        return
    
    print(f"📨 Message received in #{message.channel.name}: {message.content[:50]}...")

    # Check if someone sends any message other than !ask in the submission channel
    if message.channel.name == SUBMISSION_CHANNEL:
        # Allow !ask commands to be processed normally
        if message.content.startswith("!ask"):
            # Let the command handler deal with validation
            pass
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
            return

    # Handle expert answers (only in answering channel)
    if message.channel.name == ANSWERING_CHANNEL and message.reference:
        print(f"🔍 Checking for referenced message in {ANSWERING_CHANNEL}")
        referenced = message.reference.resolved
        if referenced and referenced.id in question_map:
            print(f"✅ Found matching question, moving to final channel")
            meta = question_map.pop(referenced.id)
            final_channel = discord.utils.get(message.guild.text_channels, name=FINAL_ANSWER_CHANNEL)

            if final_channel:
                asker_mention = f"<@{meta['asker_id']}>"
                expert_name = message.author.display_name
                await final_channel.send(
                    f"{asker_mention} asked:\n> {meta['question']}\n\n**{expert_name}** answered:\n{message.content}\n\n"
                )
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
            
            try:
                await selection_data["original_user_message"].delete()
                print("✅ Deleted original user message")
            except Exception as e:
                print(f"❌ Failed to delete original user message: {e}")
            
            # Remove from pending selections
            del pending_selections[user.id]
            
            # This is a blocking selection - show appropriate block message
            if selection_data.get("type") == "block_selection":
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
                            f"This player has been asked about recently. There is an answer in #answered-by-expert {FINAL_ANSWER_LINK}"
                        )
                    else:  # pending
                        error_msg = await reaction.message.channel.send(
                            "This player has been asked about recently, please be patient and wait for an answer."
                        )
                    
                    await error_msg.delete(delay=8)
                    return
            
            # This shouldn't happen with the new logic, but fallback to normal processing
            await process_approved_question(
                reaction.message.channel, 
                user, 
                selection_data["original_question"]
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