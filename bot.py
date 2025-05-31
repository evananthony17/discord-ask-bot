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
from bot_logic import process_approved_question, get_potential_player_words

# -------- SETUP INTENTS --------
intents = discord.Intents.default()
intents.guilds = True
intents.messages = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

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
        # Multiple players - need disambiguation
        if len(matched_players) > 1:
            if ctx.author.id in pending_selections:
                return
            
            selection_text = "Multiple players found. Which did you mean:\n"
            
            for i, player in enumerate(matched_players):
                if i < len(REACTIONS):
                    selection_text += f"{REACTIONS[i]} {player['name']} - {player['team']}\n"
            
            await asyncio.sleep(PRE_SELECTION_DELAY)
            
            try:
                selection_msg = await ctx.send(selection_text)
            except Exception as e:
                log_error(f"Failed to post disambiguation message: {e}")
                error_msg = await ctx.send("❌ Error creating player selection. Please try again.")
                await error_msg.delete(delay=5)
                return
            
            # Add reactions
            reactions_added = 0
            for i in range(min(len(matched_players), len(REACTIONS))):
                try:
                    await selection_msg.add_reaction(REACTIONS[i])
                    reactions_added += 1
                    if i < len(matched_players) - 1:
                        await asyncio.sleep(0.2)
                except Exception as e:
                    log_error(f"Failed to add reaction {REACTIONS[i]}: {e}")
                    break
            
            if reactions_added == 0:
                try:
                    await selection_msg.delete()
                    await ctx.message.delete()
                except:
                    pass
                error_msg = await ctx.send("❌ Error setting up player selection. Please try again.")
                await error_msg.delete(delay=5)
                return
            
            # Store pending selection
            pending_selections[ctx.author.id] = {
                'players': matched_players,
                'question': question,
                'message_id': selection_msg.id,
                'expires_at': datetime.now() + timedelta(minutes=2),
                'created_at': datetime.now(),
                "message": selection_msg,
                "original_question": question,
                "locked": False,
                "original_user_message": ctx.message,
                "type": "disambiguation_selection"
            }
            
            start_selection_timeout(ctx.author.id, ctx)
            return
        
        # Single player - check recent mentions
        recent_mentions = await check_recent_player_mentions(ctx.guild, matched_players)
        
        if recent_mentions:
            if len(recent_mentions) == 1:
                mention = recent_mentions[0]
                player = mention["player"]
                status = mention["status"]
                
                try:
                    await ctx.message.delete()
                except:
                    pass
                
                if status == "answered":
                    error_msg = await ctx.send(f"This player has been asked about recently. There is an answer here: {FINAL_ANSWER_LINK}")
                else:
                    error_msg = await ctx.send("This player has been asked about recently, please be patient and wait for an answer.")
                
                await error_msg.delete(delay=8)
                return
            
            # Multiple players with recent mentions
            else:
                if ctx.author.id in pending_selections:
                    return
                
                selection_text = "Multiple players have been asked about recently. Which did you mean:\n"
                
                for i, mention in enumerate(recent_mentions):
                    player = mention["player"]
                    status = mention["status"]
                    status_text = "recently answered" if status == "answered" else "pending answer"
                    selection_text += f"{REACTIONS[i]} {player['name']} - {player['team']} ({status_text})\n"
                
                await asyncio.sleep(PRE_SELECTION_DELAY)
                
                try:
                    selection_msg = await ctx.send(selection_text)
                except Exception as e:
                    log_error(f"Failed to post blocking selection: {e}")
                    error_msg = await ctx.send("❌ Error creating player selection. Please try again.")
                    await error_msg.delete(delay=5)
                    return
                
                # Add reactions
                reactions_added = 0
                for i in range(len(recent_mentions)):
                    try:
                        await selection_msg.add_reaction(REACTIONS[i])
                        reactions_added += 1
                        if i < len(recent_mentions) - 1:
                            await asyncio.sleep(0.2)
                    except Exception as e:
                        log_error(f"Failed to add reaction: {e}")
                        break
                
                if reactions_added == 0:
                    try:
                        await selection_msg.delete()
                        await ctx.message.delete()
                    except:
                        pass
                    error_msg = await ctx.send("❌ Error setting up player selection. Please try again.")
                    await error_msg.delete(delay=5)
                    return
                
                # Store blocking selection
                pending_selections[ctx.author.id] = {
                    "message": selection_msg,
                    "players": [m["player"] for m in recent_mentions],
                    "mentions": recent_mentions,
                    "original_question": question,
                    "locked": False,
                    "original_user_message": ctx.message,
                    "type": "block_selection"
                }
                
                start_selection_timeout(ctx.author.id, ctx)
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
                return
            
            elif selection_data.get("type") == "disambiguation_selection":
                blocked = await handle_disambiguation_selection(reaction, user, selected_player, selection_data)
                if not blocked:
                    return  # Question was processed
            
            # Fallback - shouldn't happen with current logic
            await process_approved_question(
                reaction.message.channel, 
                user, 
                selection_data["original_question"],
                selection_data.get("original_user_message")
            )
    
    # Invalid reaction - clean up
    else:
        cleanup_invalid_selection(user.id, selection_data)

# -------- RUN --------
if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)