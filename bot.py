import discord
from discord.ext import commands
import json
import re
import os

# -------- CONFIG --------
SUBMISSION_CHANNEL = "ask-the-experts"
ANSWERING_CHANNEL = "question-reposting"
FINAL_ANSWER_CHANNEL = "answered-by-expert"
FAQ_LINK = "https://discord.com/channels/849784755388940290/1374490028549603408"
FINAL_ANSWER_LINK = "https://discord.com/channels/849784755388940290/1377375716286533823"

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

# -------- UTILITY FUNCTIONS --------
def load_words_from_json(filename):
    try:
        with open(filename, "r", encoding="utf-8") as file:
            data = json.load(file)
            return [word.strip().lower() for word in data]
    except Exception as e:
        print(f"Error loading {filename}: {e}")
        return []

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

# -------- EVENTS --------
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    banned_categories["profanity"]["words"] = load_words_from_json("profanity.json")
    print(f"✅ Profanity list loaded: {len(banned_categories['profanity']['words'])} words")
    print(f"🔍 First few words: {banned_categories['profanity']['words'][:5]}")
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
                    if "❗ **Not Answered**\n" in original_content:
                        updated_content = original_content.replace("❗ **Not Answered**\n", "✅ **Answered**\n")
                        print("🔧 Replaced with newline version")
                    elif "❗ **Not Answered**" in original_content:
                        updated_content = original_content.replace("❗ **Not Answered**", "✅ **Answered**")
                        print("🔧 Replaced without newline version")
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

# -------- RUN --------
bot.run(os.getenv('DISCORD_TOKEN'))