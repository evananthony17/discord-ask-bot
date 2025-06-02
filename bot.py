import discord
from discord.ext import commands
import asyncio
from datetime import datetime, timedelta

# Import all our modules
from config import (
    DISCORD_TOKEN, SUBMISSION_CHANNEL, ANSWERING_CHANNEL, FINAL_ANSWER_CHANNEL,
    FINAL_ANSWER_LINK, PRE_SELECTION_DELAY, REACTIONS, 
    banned_categories, question_map, pending_selections, timeout_tasks, players_data
)
from logging_system import log_info, log_error, log_success, log_analytics
from utils import load_words_from_json, load_players_from_json, load_nicknames_from_json, is_likely_player_request
from validation import validate_question
from player_matching import check_player_mentioned
from recent_mentions import check_recent_player_mentions, check_fallback_recent_mentions
from selection_handlers import start_selection_timeout, cancel_selection_timeout, handle_disambiguation_selection, handle_block_selection, cleanup_invalid_selection
from bot_logic import process_approved_question, get_potential_player_words, handle_multi_player_question, handle_single_player_question

# -------- DUPLICATE PREVENTION --------
processing_users = set()

# -------- SETUP INTENTS --------
intents = discord.Intents.default()
intents.guilds = True
intents.messages = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# -------- HELPER FUNCTIONS --------
def is_ambiguous_single_player_question(question, matched_players):
    """Determine if this is an ambiguous single-player question requiring disambiguation"""
    
    # If only 2 players found, it's likely ambiguous (like "acuna" finding both Acuñas)
    if len(matched_players) == 2:
        return True
    
    # Look for multi-player indicators in the question
    multi_player_indicators = ['and', '&', ',', 'both', 'all', 'compare', 'vs', 'versus']
    question_lower = question.lower()
    
    # If question contains multi-player words, it's intentional
    if any(indicator in question_lower for indicator in multi_player_indicators):
        return False
    
    # If 3+ players but no multi-player indicators, probably ambiguous
    if len(matched_players) >= 3:
        return True
    
    # Default to ambiguous for safety
    return True

# -------- EVENTS --------
@bot.event
async def on_ready():
    # Original startup logic (KEEP THIS!)
    print(f"✅ Logged in as {bot.user}")
    
    await log_analytics("Bot Health", event="startup", bot_name=str(bot.user), 
                        total_questions=0, blocked_questions=0, error_count=0)
    
    # Load data (CRITICAL - this was missing!)
    banned_categories["profanity"]["words"] = load_words_from_json("profanity.json")
    players_loaded = load_players_from_json("players.json")
    log_info(f"STARTUP: Player list loaded: {len(players_loaded)} players")
    
    load_nicknames_from_json("nicknames.json")
    log_success("Bot is ready and listening for messages!")
    
    # NEW: Add cleanup feature
    log_info("BOT READY: Cleaning up orphaned disambiguation messages")
    pending_selections.clear()

@bot.event  
async def on_message(message):
    if message.author.bot:
        return
    
    relevant_channels = [SUBMISSION_CHANNEL, ANSWERING_CHANNEL, FINAL_ANSWER_CHANNEL]
    if message.channel.name not in relevant_channels:
        return

    # Handle submission channel
    if message.channel.name == SUBMISSION_CHANNEL:
        if message.content.startswith("!ask"):
            pass  # Let Discord.py process the command
        else:
            try:
                await message.delete()
            except:
                pass
            error_msg = await message.channel.send(f"Only the `!ask` command is allowed in #{SUBMISSION_CHANNEL}.")
            await error_msg.delete(delay=5)
            return

    # Handle expert answers
    elif message.channel.name == ANSWERING_CHANNEL and message.reference:
        referenced = message.reference.resolved
        if referenced and referenced.id in question_map:
            meta = question_map.pop(referenced.id)
            final_channel = discord.utils.get(message.guild.text_channels, name=FINAL_ANSWER_CHANNEL)

            if final_channel:
                asker_mention = f"<@{meta['asker_id']}>"
                expert_name = message.author.display_name
                formatted_answer = f"-----\n**Question:**\n{asker_mention} asked: {meta['question']}\n\n**{expert_name}** replied:\n{message.content}\n-----"
                await final_channel.send(formatted_answer)
                
                try:
                    fresh_message = await message.channel.fetch_message(referenced.id)
                    original_content = fresh_message.content
                    
                    if "❗ **Not Answered**\n\nReply to this message to answer." in original_content:
                        updated_content = original_content.replace("❗ **Not Answered**\n\nReply to this message to answer.", "✅ **Answered**")
                    elif "❗ **Not Answered**" in original_content:
                        updated_content = original_content.replace("❗ **Not Answered**", "✅ **Answered**")
                        updated_content = updated_content.replace("\nReply to this message to answer.", "").replace("Reply to this message to answer.", "")
                    else:
                        updated_content = original_content + "\n\n✅ **Answered**\n"
                    
                    if updated_content != original_content:
                        await fresh_message.edit(content=updated_content)
                except Exception as e:
                    log_error(f"Failed to edit original message: {e}")
    
    await bot.process_commands(message)

# -------- COMMAND: !ask --------
@bot.command(name="ask")
async def ask_question(ctx, *, question: str = None):
    if ctx.channel.name != SUBMISSION_CHANNEL:
        error_msg = await ctx.send(f"Please use this command in #{SUBMISSION_CHANNEL}")
        await error_msg.delete(delay=5)
        return

    if question is None:
        error_msg = await ctx.send("Please provide a question. Usage: `!ask your question here`")
        await error_msg.delete(delay=5)
        return

    # DUPLICATE PREVENTION - Check if user is already being processed
    if ctx.author.id in processing_users:
        log_info(f"DUPLICATE PREVENTION: User {ctx.author.id} already being processed, ignoring duplicate")
        return
    
    # Add user to processing set
    processing_users.add(ctx.author.id)
    
    try:
        # Prevent duplicate processing - check if user already has pending selection
        if ctx.author.id in pending_selections:
            log_info(f"DUPLICATE PREVENTION: User {ctx.author.id} already has pending selection, ignoring")
            return

        # Validate question through all checks
        is_valid, error_message, error_category = validate_question(question)
        if not is_valid:
            try:
                await ctx.message.delete()
            except:
                pass
            error_msg = await ctx.send(error_message)
            await error_msg.delete(delay=5)
            return

        # Check for player names
        if not players_data:
            error_msg = await ctx.send("Player database is not available. Please try again later.")
            await error_msg.delete(delay=5)
            try:
                await ctx.message.delete()
            except:
                pass
            return
        
        matched_players = check_player_mentioned(question)
        
        # Fallback check for potential player words
        fallback_recent_check = False
        if not matched_players and is_likely_player_request(question):
            potential_player_words = get_potential_player_words(question)
            if potential_player_words:
                fallback_recent_check = True

        if matched_players:
            # Handle multiple players
            if len(matched_players) > 1:
                # Check if this is an ambiguous single-player question vs intentional multi-player
                if is_ambiguous_single_player_question(question, matched_players):
                    # Show disambiguation prompt
                    from selection_handlers import create_player_disambiguation_prompt
                    await create_player_disambiguation_prompt(ctx, question, matched_players)
                    return
                else:
                    # True multi-player question - process all players
                    await handle_multi_player_question(ctx, question, matched_players)
                    return
            
            # Handle single player
            else:
                await handle_single_player_question(ctx, question, matched_players)
                return
            
        elif fallback_recent_check:
            # Fallback recent mentions check
            potential_player_words = get_potential_player_words(question)
            found_recent_mention = await check_fallback_recent_mentions(ctx.guild, potential_player_words)
            
            if found_recent_mention:
                try:
                    await ctx.message.delete()
                except:
                    pass
                error_msg = await ctx.send("This topic has been asked about recently, please be patient and wait for an answer.")
                await error_msg.delete(delay=8)
                return

        # All checks passed - post question
        await process_approved_question(ctx.channel, ctx.author, question, ctx.message)
        
    finally:
        # Always remove user from processing set when done
        processing_users.discard(ctx.author.id)

# -------- REACTION HANDLER --------
# -------- ENHANCED REACTION HANDLER WITH SAFEGUARDS --------

# Configuration option
ALLOW_HELPER_REACTIONS = False  # Set to True if you want to allow helpers

@bot.event
async def on_reaction_add(reaction, user):
    if user.bot:
        return
    
    message_id = reaction.message.id
    
    # Find the selection data
    selection_data = None
    original_user_id = None
    storage_key = None
    
    if message_id in pending_selections:
        selection_data = pending_selections[message_id]
        original_user_id = selection_data.get("user_id")
        storage_key = message_id
    else:
        # Fallback: check if stored by user ID
        for user_key, data in pending_selections.items():
            if isinstance(user_key, int) and data.get("message") and data["message"].id == message_id:
                selection_data = data
                original_user_id = user_key
                storage_key = user_key
                break
    
    # No pending selection found
    if not selection_data:
        return
    
    # 🔧 SAFEGUARD 1: Check if original user is still in server
    guild = reaction.message.guild
    original_user = None
    if guild:
        try:
            original_user = await guild.fetch_member(original_user_id)
        except discord.NotFound:
            log_info(f"ORPHANED SELECTION: Original user {original_user_id} no longer in server, allowing helper reactions")
            # Allow anyone to react if original user left
            original_user_id = user.id
        except Exception as e:
            log_error(f"ERROR checking if user {original_user_id} is in server: {e}")
    
    # 🔧 SAFEGUARD 2: User validation with helper option
    if user.id != original_user_id:
        # Option 1: Strict mode - only original user
        if not ALLOW_HELPER_REACTIONS and original_user:
            log_info(f"REACTION BLOCKED: User {user.id} ({user.display_name}) tried to react to question from user {original_user_id}")
            
            # Try to remove reaction, but don't fail if we can't
            try:
                await reaction.remove(user)
                log_info(f"REACTION REMOVED: Removed unauthorized reaction from {user.display_name}")
            except discord.errors.Forbidden:
                # Bot lacks permission - log but continue
                log_info(f"REACTION: Bot lacks permission to remove reaction from {user.display_name}, but continuing")
            except Exception as e:
                log_error(f"REACTION: Error removing reaction from {user.display_name}: {e}")
            
            # Send helpful message with @mention to original user
            try:
                original_mention = f"<@{original_user_id}>" if original_user else "the original questioner"
                await reaction.message.channel.send(
                    f"{user.mention} Only {original_mention} can select from these options. "
                    f"If you'd like to help, you can ask them to make a selection!", 
                    delete_after=8
                )
            except:
                pass
                
            return
        
        # Option 2: Helper mode - allow with notification
        elif ALLOW_HELPER_REACTIONS:
            log_info(f"HELPER REACTION: User {user.id} ({user.display_name}) helping with question from user {original_user_id}")
            # Continue processing but log it as helper assistance
    
    # Verify message and lock status
    message_obj = selection_data.get("message")
    if not message_obj or reaction.message.id != message_obj.id or selection_data.get("locked"):
        return
    
    # Lock the selection
    selection_data["locked"] = True
    log_info(f"REACTION PROCESSING: User {user.id} ({user.display_name}) processing selection")
    
    # 🔧 SAFEGUARD 3: Enhanced timeout cancellation
    try:
        cancel_selection_timeout(original_user_id)
        # Also try to cancel by message_id if that's how timeouts are stored
        cancel_selection_timeout(message_id)
    except Exception as e:
        log_error(f"ERROR canceling timeout: {e}")
    
    if str(reaction.emoji) in REACTIONS:
        selected_index = REACTIONS.index(str(reaction.emoji))
        
        if selected_index < len(selection_data["players"]):
            selected_player = selection_data["players"][selected_index]
            
            # 🔧 SAFEGUARD 4: Enhanced analytics with helper tracking
            selection_type = selection_data.get("type", "unknown")
            if user.id != original_user_id:
                selection_type += "_helper_assisted"
            
            await log_analytics("User Selection",
                user_id=original_user_id,  # Always log original user
                helper_user_id=user.id if user.id != original_user_id else None,
                user_name=getattr(user, 'display_name', 'Unknown'),
                channel=reaction.message.channel.name,
                question=selection_data.get("original_question", "Unknown"),
                selected_player=f"{selected_player['name']} ({selected_player['team']})",
                selection_type=selection_type,
                timeout="completed"
            )
            
            # Clean up messages
            try:
                await selection_data["message"].delete()
                log_info(f"CLEANUP: Deleted disambiguation message after selection")
            except Exception as e:
                log_error(f"CLEANUP: Error deleting disambiguation message: {e}")
            
            # 🔧 SAFEGUARD 5: Robust cleanup
            # Remove from all possible storage locations
            keys_to_remove = []
            if message_id in pending_selections:
                keys_to_remove.append(message_id)
            if original_user_id in pending_selections:
                keys_to_remove.append(original_user_id)
            if storage_key and storage_key not in keys_to_remove:
                keys_to_remove.append(storage_key)
            
            for key in keys_to_remove:
                try:
                    del pending_selections[key]
                    log_info(f"CLEANUP: Removed pending selection key {key}")
                except KeyError:
                    pass
            
            # Handle different selection types
            if selection_data.get("type") == "block_selection":
                await handle_block_selection(reaction, user, selected_player, selection_data)
                return
            
            elif selection_data.get("type") == "disambiguation_selection":
                blocked = await handle_disambiguation_selection(reaction, user, selected_player, selection_data)
                if blocked:
                    log_info(f"🔧 RACE CONDITION FIX: Question blocked for {selected_player['name']}, returning early")
                    return
                else:
                    log_info(f"🔧 RACE CONDITION FIX: Question processed for {selected_player['name']}, returning early") 
                    return
            
            log_error(f"🚨 RACE CONDITION BUG: Unexpected fallback execution for {selected_player['name']}")
            return
    
    # Invalid reaction - clean up
    else:
        cleanup_invalid_selection(original_user_id, selection_data)
        log_info(f"CLEANUP: Invalid reaction from user {user.id}, cleaned up selection")


# 🔧 SAFEGUARD 6: Cleanup orphaned selections on bot restart
'''@bot.event
async def on_ready():
    """Clean up any orphaned disambiguation messages on restart"""
    log_info("BOT READY: Cleaning up orphaned disambiguation messages")
    
    # Clear the pending_selections dict since bot restarted
    pending_selections.clear()
    
    # Optional: You could scan recent messages and delete any that look like
    # orphaned disambiguation messages, but this might be overkill'''


# 🔧 SAFEGUARD 7: Admin command to force-clear stuck selections
@bot.command(name='clear_stuck')
@commands.has_permissions(administrator=True)
async def clear_stuck_selections(ctx, user_id: int = None):
    """Admin command to clear stuck disambiguation selections"""
    if user_id:
        # Clear specific user
        removed = 0
        keys_to_remove = []
        for key, data in pending_selections.items():
            if data.get("user_id") == user_id:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del pending_selections[key]
            removed += 1
        
        await ctx.send(f"✅ Cleared {removed} stuck selections for user {user_id}")
    else:
        # Clear all
        count = len(pending_selections)
        pending_selections.clear()
        await ctx.send(f"✅ Cleared all {count} pending selections")
    
    log_info(f"ADMIN CLEAR: {ctx.author.display_name} cleared stuck selections")

# -------- RUN --------
if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)