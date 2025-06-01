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
    print(f"✅ Logged in as {bot.user}")
    
    await log_analytics("Bot Health", event="startup", bot_name=str(bot.user), 
                        total_questions=0, blocked_questions=0, error_count=0)
    
    # Load data
    banned_categories["profanity"]["words"] = load_words_from_json("profanity.json")
    players_loaded = load_players_from_json("players.json")
    log_info(f"STARTUP: Player list loaded: {len(players_loaded)} players")
    
    load_nicknames_from_json("nicknames.json")
    log_success("Bot is ready and listening for messages!")

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
@bot.event
async def on_reaction_add(reaction, user):
    if user.bot or user.id not in pending_selections:
        return
    
    selection_data = pending_selections[user.id]
    
    if reaction.message.id != selection_data["message"].id or selection_data["locked"]:
        return
    
    # Lock the selection
    selection_data["locked"] = True
    
    # Cancel timeout task
    cancel_selection_timeout(user.id)
    
    if str(reaction.emoji) in REACTIONS:
        selected_index = REACTIONS.index(str(reaction.emoji))
        
        if selected_index < len(selection_data["players"]):
            selected_player = selection_data["players"][selected_index]
            
            # Log analytics for user selection
            await log_analytics("User Selection",
                user_id=user.id,
                user_name=getattr(user, 'display_name', 'Unknown'),
                channel=reaction.message.channel.name,
                question=selection_data.get("original_question", "Unknown"),
                selected_player=f"{selected_player['name']} ({selected_player['team']})",
                selection_type=selection_data.get("type", "unknown"),
                timeout="completed"
            )
            
            # Clean up messages
            try:
                await selection_data["message"].delete()
            except:
                pass
            
            # Remove from pending
            del pending_selections[user.id]
            
            # Handle different selection types
            if selection_data.get("type") == "block_selection":
                await handle_block_selection(reaction, user, selected_player, selection_data)
                return  # ALWAYS return after handling block selection
            
            elif selection_data.get("type") == "disambiguation_selection":
                blocked = await handle_disambiguation_selection(reaction, user, selected_player, selection_data)
                if blocked:
                    # Question was blocked - EXIT IMMEDIATELY, don't process further
                    log_info(f"🔧 RACE CONDITION FIX: Question blocked for {selected_player['name']}, returning early")
                    return
                else:
                    # Question was not blocked - EXIT IMMEDIATELY, it was already processed in the handler
                    log_info(f"🔧 RACE CONDITION FIX: Question processed for {selected_player['name']}, returning early") 
                    return
            
            # This fallback should NEVER execute with proper logic above
            log_error(f"🚨 RACE CONDITION BUG: Unexpected fallback execution for {selected_player['name']} - this should not happen!")
            return  # Don't process the question if we reach this point
    
    # Invalid reaction - clean up
    else:
        cleanup_invalid_selection(user.id, selection_data)

# -------- RUN --------
if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)