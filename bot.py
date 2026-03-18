# Updated bot.py for questoin_map change

import discord
from discord.ext import commands
import asyncio
import logging
import uuid
import time
from question_map_store import load_question_map, save_question_map, append_question


# Set up flow tracing logger
logger = logging.getLogger(__name__)


# Import all our modules
from config import (
    DISCORD_TOKEN, SUBMISSION_CHANNEL, ANSWERING_CHANNEL, FINAL_ANSWER_CHANNEL,
    FINAL_ANSWER_LINK, PRE_SELECTION_DELAY, REACTIONS, 
    banned_categories, pending_selections, timeout_tasks, players_data
)
from logging_system import log_info, log_error, log_success, log_analytics, start_batching
from utils import load_words_from_json, load_players_from_json, load_nicknames_from_json, is_likely_player_request, normalize_name
from validation import validate_question
from player_matching import check_player_mentioned, has_multi_player_keywords_enhanced, validate_suspicious_names_strict
from recent_mentions import check_recent_player_mentions, check_fallback_recent_mentions
from selection_handlers import start_selection_timeout, cancel_selection_timeout, handle_disambiguation_selection, handle_block_selection, cleanup_invalid_selection
from bot_logic import process_approved_question, get_potential_player_words, handle_multi_player_question, handle_single_player_question, schedule_answered_message_cleanup

# -------- PERSISTENT QUESTION_ID STORAGE --------
question_map = load_question_map()

# -------- DUPLICATE PREVENTION --------
processing_users = set()

# -------- SETUP INTENTS --------
intents = discord.Intents.default()
intents.guilds = True
intents.messages = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# -------- HELPER FUNCTIONS --------
# (Old disambiguation logic removed - now handled inline with proper last name analysis)

# -------- EVENTS --------
@bot.event
async def on_ready():
    """Enhanced startup with comprehensive error handling and verification"""
    try:
        print(f"✅ Bot logged in as {bot.user}")
        
        # CRITICAL: Start batching first
        start_batching()
        log_info("STARTUP: Log batching started")
        
        # CRITICAL: Load player data with comprehensive error handling
        log_info("STARTUP: Beginning player data loading...")
        
        try:
            # Load profanity words
            log_info("STARTUP: Loading profanity words...")
            profanity_words = load_words_from_json("profanity.json")
            banned_categories["profanity"]["words"] = profanity_words
            log_info(f"STARTUP: Loaded {len(profanity_words)} profanity words")
            
            # Load players with detailed logging
            log_info("STARTUP: Loading players from JSON...")
            players_loaded = load_players_from_json("players.json")
            log_info(f"STARTUP: load_players_from_json returned {len(players_loaded)} players")
            
            # CRITICAL: Verify the global players_data was updated
            log_info(f"STARTUP: Checking global players_data length: {len(players_data)}")
            
            if len(players_data) == 0:
                log_error("CRITICAL STARTUP ERROR: players_data is empty after loading!")
                log_error("STARTUP: Attempting emergency player data fix...")
                
                # Emergency fix: directly extend the global list
                players_data.extend(players_loaded)
                log_info(f"STARTUP: Emergency fix applied, players_data now has {len(players_data)} players")
            
            # Verify all modules have the data
            import utils
            import player_matching
            log_info(f"STARTUP: Verification - bot.py players_data: {len(players_data)}")
            log_info(f"STARTUP: Verification - utils.players_data: {len(utils.players_data)}")
            log_info(f"STARTUP: Verification - player_matching.players_data: {len(player_matching.players_data)}")
            
            # Check if they're the same object (they should be)
            log_info(f"STARTUP: Object identity check - same object: {players_data is utils.players_data}")
            
            if len(players_data) != len(players_loaded):
                log_error(f"STARTUP ERROR: Length mismatch - loaded {len(players_loaded)}, have {len(players_data)}")
            else:
                log_success(f"STARTUP: Successfully loaded {len(players_data)} players")
            
            # Load nicknames
            log_info("STARTUP: Loading nicknames...")
            load_nicknames_from_json("nicknames.json")
            log_info("STARTUP: Nicknames loaded successfully")
            
        except Exception as e:
            log_error(f"CRITICAL STARTUP ERROR in data loading: {e}")
            import traceback
            log_error(f"STARTUP ERROR TRACEBACK: {traceback.format_exc()}")
            # Don't return - continue with startup even if data loading fails
        
        # Final verification
        log_info("STARTUP: Performing final verification...")
        if len(players_data) > 0:
            log_success(f"STARTUP COMPLETE: Bot ready with {len(players_data)} players loaded")
            print(f"🎉 STARTUP SUCCESS: {len(players_data)} players loaded and verified")
        else:
            log_error("STARTUP WARNING: Bot started but no player data available")
            print("⚠️ STARTUP WARNING: No player data loaded")
        
        # Cleanup
        log_info("STARTUP: Cleaning up orphaned disambiguation messages")
        pending_selections.clear()
        
        log_success("Bot startup sequence completed!")
        
    except Exception as e:
        log_error(f"CRITICAL STARTUP FAILURE: {e}")
        import traceback
        log_error(f"STARTUP FAILURE TRACEBACK: {traceback.format_exc()}")
        print(f"💥 STARTUP FAILED: {e}")
        # Don't re-raise - let the bot continue even with startup issues
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
        
        # Try to get from question_map first (for new messages)
        meta = None
        if referenced and str(referenced.id) in question_map:
            meta = question_map.pop(str(referenced.id))
            save_question_map(question_map)  # Save after popping to keep it updated
        
        # If not in question_map (older messages), extract info from the message content
        if not meta and referenced:
            try:
                # Parse the message content to extract question and asker
                content = referenced.content
                
                # Look for the pattern: "Username asked:\nquestion text"
                if " asked:\n" in content:
                    lines = content.split('\n')
                    first_line = lines[0]
                    
                    # Extract the asker info
                    if first_line.endswith(" asked:"):
                        asker_part = first_line.replace(" asked:", "")
                        
                        # Try to extract user ID from @ mention
                        extracted_user_id = None
                        if asker_part.startswith("<@") and asker_part.endswith(">"):
                            try:
                                # Extract user ID from <@123456789> format
                                extracted_user_id = int(asker_part.replace("<@", "").replace(">", ""))
                            except ValueError:
                                pass
                        
                        # Find the question (skip status lines)
                        question_lines = []
                        for line in lines[1:]:
                            if not line.startswith("❗") and not line.startswith("✅") and line.strip():
                                if not line.startswith("Reply to this message"):
                                    question_lines.append(line)
                        
                        question = "\n".join(question_lines).strip()
                        
                        # Create meta object
                        meta = {
                            'question': question,
                            'asker_id': extracted_user_id,  # Will be None if we couldn't extract it
                            'asker_name': asker_part if not extracted_user_id else None
                        }
            except Exception as e:
                log_error(f"Failed to parse old message format: {e}")
        
        if meta:
            final_channel = discord.utils.get(message.guild.text_channels, name=FINAL_ANSWER_CHANNEL)

            if final_channel:
                # Use asker_id if available (creates proper @ mention), otherwise use name
                if meta.get('asker_id'):
                    asker_mention = f"<@{meta['asker_id']}>"
                else:
                    asker_mention = f"**{meta.get('asker_name', 'Unknown User')}**"
                
                expert_name = message.author.display_name
                formatted_answer = f"-----\n**Question:**\n{asker_mention} asked: {meta['question']}\n\n**{expert_name}** replied:\n{message.content}\n-----"
                
                print(f"meta: {meta}")
                print(f"asker_mention: {asker_mention}")
                print(f"formatted_answer: {formatted_answer}")

                await final_channel.send(formatted_answer)

            '''if referenced and referenced.id in question_map:
                return'''

            # Update status regardless of whether it was in question_map
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
                    asyncio.create_task(schedule_answered_message_cleanup(fresh_message, message))

            except Exception as e:
                log_error(f"Failed to edit original message: {e}")
    
    await bot.process_commands(message)

# -------- COMMAND: !ask --------


@bot.command(name="ask")
async def ask_question(ctx, *, question: str = None):
    request_id = str(uuid.uuid4())[:8]
    start_time = time.time()

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

        # Handle blocking result
        if matched_players == "BLOCKED":
            
            try:
                await ctx.message.delete()
            except:
                pass
            
            error_msg = await ctx.send(
                f"**Single Player Policy**: Your question appears to reference multiple players. "
                f"Please ask about one player at a time. If this seems incorrect, please contact a mod."
            )
            await error_msg.delete(delay=8)
            return
        
        # Fallback check for potential player words - but respect validation
        fallback_recent_check = False
        if not matched_players and is_likely_player_request(question):
            potential_player_words = get_potential_player_words(question)
            if potential_player_words:
                # 🔧 FIX: Validate potential player words before bypassing
                from player_matching_validator import validate_player_matches
                mock_players = [{'name': word, 'team': 'Unknown'} for word in potential_player_words]
                validated_words = validate_player_matches(question, mock_players)
                
                if validated_words:
                    log_info(f"FALLBACK VALIDATION: Approved fallback for validated words: {[p['name'] for p in validated_words]}")
                    fallback_recent_check = True
                else:
                    log_info(f"FALLBACK VALIDATION: Rejected fallback - potential words failed validation: {potential_player_words}")
                    fallback_recent_check = False

        if matched_players:
            # Handle multiple players
            if len(matched_players) > 1:
                last_names = set()
                for player in matched_players:
                    last_name = normalize_name(player['name']).split()[-1]
                    last_names.add(last_name)
                
                log_info(f"DECISION LOGIC: Found {len(matched_players)} players with {len(last_names)} unique last names")
                log_info(f"DECISION LOGIC: Players: {[p['name'] for p in matched_players]}")
                log_info(f"DECISION LOGIC: Last names: {list(last_names)}")
                
                if len(last_names) == 1:
                    # Same last name = ambiguous single player = DISAMBIGUATE
                    from selection_handlers import create_player_disambiguation_prompt
                    await create_player_disambiguation_prompt(ctx, question, matched_players)
                    return
                else:
                    # Multiple distinct last names = true multi-player question = BLOCK
                    await handle_multi_player_question(ctx, question, matched_players, question_map)
                    return

            # Handle single player
            else:
                await handle_single_player_question(ctx, question, matched_players, question_map)
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
        await process_approved_question(ctx.channel, ctx.author, question, ctx.message, question_map)
        duration = time.time() - start_time
        logger.info(f"REQUEST {request_id} completed in {duration:.2f}s")

    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"REQUEST {request_id} failed after {duration:.2f}s: {str(e)}")
        raise

    finally:
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

# -------- ADMIN CORRECTION COMMAND --------
@bot.command(name="correct")
@commands.check_any(
    commands.has_permissions(administrator=True),
    commands.has_any_role("Stub Savant", "ModSquad")
)
async def correct_answer(ctx, message_link: str, *, correction: str):
    """
    Admin command to replace a bot message with a correction
    Usage: !correct https://discord.com/channels/.../... This is the corrected response
    """
    try:
        # Extract message ID from Discord link
        message_id = int(message_link.split('/')[-1])
        
        # Try to find the message in final answer channel
        final_channel = discord.utils.get(ctx.guild.text_channels, name=FINAL_ANSWER_CHANNEL)
        if not final_channel:
            await ctx.send("❌ Could not find final answer channel")
            return
            
        original_message = await final_channel.fetch_message(message_id)
        
        # Verify it's a bot message
        if original_message.author != bot.user:
            await ctx.send("❌ Can only correct bot messages")
            return
        
        # Use surgical replacement - find everything up to "replied:" and preserve it
        original_content = original_message.content
        
        if "replied:" in original_content:
            # Find everything up to and including "replied:"
            before_reply = original_content.split("replied:")[0] + "replied:"
            
            # Create the corrected content with surgical replacement
            corrected_content = before_reply + f"\n{correction}\n\n*This answer was updated by {ctx.author.display_name}*\n-----"
            
            # Edit the original message
            await original_message.edit(content=corrected_content)
            
            # Clean up - delete the command message
            await ctx.message.delete()
            
            # Log it (no confirmation message)
            log_info(f"CORRECTION: {ctx.author.display_name} corrected message {message_id}")
            
        else:
            await ctx.send("❌ Could not find reply section in message")
            return
        
    except ValueError:
        await ctx.send("❌ Invalid message link format")
    except discord.NotFound:
        await ctx.send("❌ Message not found")
    except Exception as e:
        await ctx.send(f"❌ Error: {e}")
        log_error(f"Correction command error: {e}")

# -------- RUN --------
if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
