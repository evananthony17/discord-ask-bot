# Updated bot.py for questoin_map change

import discord
from discord.ext import commands
import asyncio
import logging
import uuid
import time
import os
from datetime import datetime, timedelta
from question_map_store import load_question_map, save_question_map, append_question

# Set up flow tracing logger
logger = logging.getLogger(__name__)

# -------- SIMPLE RESOURCE MONITORING --------
def log_resource_usage(stage, request_id=None):
    """Log resource usage checkpoint using built-in modules"""
    try:
        import gc
        import sys
        
        # Get object count as a proxy for memory usage
        obj_count = len(gc.get_objects())
        # Get reference count for tracking potential memory leaks
        ref_count = sys.gettotalrefcount() if hasattr(sys, 'gettotalrefcount') else 'N/A'
        
        if request_id:
            logger.info(f"📊 RESOURCE_TRACE [{request_id}]: {stage} - Objects: {obj_count}, Refs: {ref_count}")
        else:
            logger.info(f"📊 RESOURCE_TRACE: {stage} - Objects: {obj_count}, Refs: {ref_count}")
    except Exception as e:
        if request_id:
            logger.warning(f"📊 RESOURCE_TRACE [{request_id}]: Could not get resource usage for {stage}: {e}")
        else:
            logger.warning(f"📊 RESOURCE_TRACE: Could not get resource usage for {stage}: {e}")

# -------- STAGE MONITORING UTILITY --------
def log_stage_info(stage, request_id=None):
    """Log processing stage for debugging (no external dependencies)"""
    if request_id:
        logger.info(f"📍 STAGE_TRACE [{request_id}]: {stage}")
    else:
        logger.info(f"� STAGE_TRACE: {stage}")

# Import all our modules
from config import (
    DISCORD_TOKEN, SUBMISSION_CHANNEL, ANSWERING_CHANNEL, FINAL_ANSWER_CHANNEL,
    FINAL_ANSWER_LINK, PRE_SELECTION_DELAY, REACTIONS, 
    banned_categories, pending_selections, timeout_tasks, players_data
)
from logging_system import log_info, log_error, log_success, log_analytics, start_batching, log_memory_usage
from utils import load_words_from_json, load_players_from_json, load_nicknames_from_json, is_likely_player_request, normalize_name
from validation import validate_question
from player_matching import check_player_mentioned, process_multi_player_query_fixed
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
    # Original startup logic (KEEP THIS!)
    print(f"✅ Logged in as {bot.user}")
    start_batching()  # Start batching logs
    
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
    # 🆔 REQUEST TRACKING: Generate unique request ID and start timing
    request_id = str(uuid.uuid4())[:8]
    start_time = time.time()
    logger.info(f"🆔 REQUEST_TRACE: Starting request {request_id}")
    logger.info(f"🔵 FLOW_TRACE [{request_id}]: Starting message processing for: '{question[:50] if question else 'None'}...'")
    log_memory_usage("Request Start", request_id)
    
    if ctx.channel.name != SUBMISSION_CHANNEL:
        logger.info(f"🔴 FLOW_TRACE [{request_id}]: Wrong channel, exiting early")
        error_msg = await ctx.send(f"Please use this command in #{SUBMISSION_CHANNEL}")
        await error_msg.delete(delay=5)
        return

    if question is None:
        logger.info(f"🔴 FLOW_TRACE [{request_id}]: No question provided, exiting early")
        error_msg = await ctx.send("Please provide a question. Usage: `!ask your question here`")
        await error_msg.delete(delay=5)
        return

    # DUPLICATE PREVENTION - Check if user is already being processed
    if ctx.author.id in processing_users:
        logger.info(f"🔴 FLOW_TRACE [{request_id}]: Duplicate prevention triggered, exiting early")
        log_info(f"DUPLICATE PREVENTION: User {ctx.author.id} already being processed, ignoring duplicate")
        return
    
    # Add user to processing set
    processing_users.add(ctx.author.id)
    logger.info(f"🟡 FLOW_TRACE [{request_id}]: Added user to processing set, continuing with validation")
    
    try:
        # Prevent duplicate processing - check if user already has pending selection
        if ctx.author.id in pending_selections:
            log_info(f"DUPLICATE PREVENTION: User {ctx.author.id} already has pending selection, ignoring")
            return

        # Validate question through all checks
        logger.info(f"🟡 FLOW_TRACE [{request_id}]: Starting question validation")
        is_valid, error_message, error_category = validate_question(question)
        if not is_valid:
            logger.info(f"🔴 FLOW_TRACE [{request_id}]: Question validation failed: {error_category}")
            try:
                await ctx.message.delete()
            except:
                pass
            error_msg = await ctx.send(error_message)
            await error_msg.delete(delay=5)
            return

        # Check for player names
        if not players_data:
            logger.info(f"🔴 FLOW_TRACE [{request_id}]: No player data available, exiting")
            error_msg = await ctx.send("Player database is not available. Please try again later.")
            await error_msg.delete(delay=5)
            try:
                await ctx.message.delete()
            except:
                pass
            return
        
        # 🔧 NEW: Early multi-player detection to prevent fallback bypass
        logger.info(f"🟡 FLOW_TRACE [{request_id}]: Starting early multi-player detection")
        log_resource_usage("Before Multi-Player Check", request_id)
        
        try:
            should_allow, detected_players = process_multi_player_query_fixed(question)
            if not should_allow:
                # 🔧 CRITICAL FIX: Check if this could be a disambiguation case before blocking
                if detected_players and len(detected_players) > 1:
                    # Check if all players have the same last name (disambiguation case)
                    last_names = set()
                    for player in detected_players:
                        last_name = normalize_name(player['name']).split()[-1]
                        last_names.add(last_name)
                    
                    if len(last_names) == 1:
                        # Same last name = disambiguation case = ALLOW to continue to disambiguation logic
                        logger.info(f"🔄 FLOW_TRACE [{request_id}]: Early multi-player check found same last name, allowing for disambiguation")
                    else:
                        # Different last names = true multi-player = BLOCK
                        logger.info(f"🚫 FLOW_TRACE [{request_id}]: Multi-player query blocked early - different last names")
                        
                        try:
                            await ctx.message.delete()
                        except:
                            pass
                        
                        player_names = [p.get('name', 'Unknown') for p in detected_players]
                        error_msg = await ctx.send(
                            f"🚫 **Single Player Policy**: Your question appears to reference multiple players "
                            f"({', '.join(player_names)}). Please ask about one player at a time."
                        )
                        await error_msg.delete(delay=8)
                        return
                else:
                    # Fallback block for edge cases
                    logger.info(f"🚫 FLOW_TRACE [{request_id}]: Multi-player query blocked early - fallback")
                    return
            
            logger.info(f"✅ FLOW_TRACE [{request_id}]: Multi-player check passed, continuing with normal detection")
        except Exception as e:
            logger.warning(f"⚠️ FLOW_TRACE [{request_id}]: Multi-player check failed, falling back to normal detection: {e}")
        
        logger.info(f"🟡 FLOW_TRACE [{request_id}]: Starting player detection")
        log_resource_usage("Before Player Detection", request_id)
        matched_players = check_player_mentioned(question)
        logger.info(f"🟡 FLOW_TRACE [{request_id}]: Player detection completed, moving to decision logic")
        log_resource_usage("After Player Detection", request_id)
        
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
            logger.info(f"🟠 FLOW_TRACE [{request_id}]: Entering decision routing with {len(matched_players)} detected players")
            log_resource_usage("Before Decision Routing", request_id)
            
            # Handle multiple players
            if len(matched_players) > 1:
                logger.info(f"🟠 FLOW_TRACE [{request_id}]: Multiple players detected, analyzing last names")
                
                # 🔧 FIXED: Proper decision logic for disambiguation vs multi-player blocking
                
                # 🔧 CRITICAL FIX: Use normalize_name() instead of .lower() for accent handling
                last_names = set()
                for player in matched_players:
                    last_name = normalize_name(player['name']).split()[-1]
                    last_names.add(last_name)
                
                log_info(f"DECISION LOGIC: Found {len(matched_players)} players with {len(last_names)} unique last names")
                log_info(f"DECISION LOGIC: Players: {[p['name'] for p in matched_players]}")
                log_info(f"DECISION LOGIC: Last names: {list(last_names)}")
                
                if len(last_names) == 1:
                    # All players share same last name = ambiguous single player = DISAMBIGUATE
                    logger.info(f"🟢 FLOW_TRACE [{request_id}]: Same last name detected → DISAMBIGUATION")
                    log_info(f"DECISION LOGIC: Same last name detected → DISAMBIGUATION")
                    from selection_handlers import create_player_disambiguation_prompt
                    await create_player_disambiguation_prompt(ctx, question, matched_players)
                    logger.info(f"✅ FLOW_TRACE [{request_id}]: Disambiguation prompt created successfully")
                    return
                else:
                    # Multiple distinct last names = true multi-player question = BLOCK
                    logger.info(f"🟢 FLOW_TRACE [{request_id}]: Multiple distinct last names → MULTI-PLAYER BLOCK")
                    log_info(f"DECISION LOGIC: Multiple distinct last names → MULTI-PLAYER BLOCK")
                    await handle_multi_player_question(ctx, question, matched_players, question_map)
                    logger.info(f"✅ FLOW_TRACE [{request_id}]: Multi-player block executed successfully")
                    return
            
            # Handle single player
            else:
                logger.info(f"🟢 FLOW_TRACE [{request_id}]: Single player detected, processing")
                await handle_single_player_question(ctx, question, matched_players, question_map)
                logger.info(f"✅ FLOW_TRACE [{request_id}]: Single player processing completed")
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
        logger.info(f"🟢 FLOW_TRACE [{request_id}]: All checks passed, posting approved question")
        log_resource_usage("Before Question Posting", request_id)
        await process_approved_question(ctx.channel, ctx.author, question, ctx.message, question_map)
        logger.info(f"✅ FLOW_TRACE [{request_id}]: Question posted successfully")
        
        # Final completion logging
        duration = time.time() - start_time
        logger.info(f"🆔 REQUEST_TRACE: Completed request {request_id} in {duration:.2f}s")
        logger.info(f"✅ FLOW_TRACE [{request_id}]: Message processing complete")
        log_resource_usage("After Processing Complete", request_id)
        
    except Exception as e:
        # Exception handling with flow tracing
        duration = time.time() - start_time
        logger.error(f"❌ FLOW_TRACE [{request_id}]: Exception occurred in message processing: {str(e)}")
        logger.error(f"🆔 REQUEST_TRACE: Failed request {request_id} after {duration:.2f}s - {str(e)}")
        log_memory_usage("Exception Occurred", request_id)
        
        # Re-raise the exception to maintain existing error handling
        raise
        
    finally:
        # Always remove user from processing set when done
        processing_users.discard(ctx.author.id)
        logger.info(f"🧹 FLOW_TRACE [{request_id}]: Cleaned up processing user from set")

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
