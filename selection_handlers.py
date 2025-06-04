import asyncio
from datetime import datetime
from config import SELECTION_TIMEOUT, pending_selections, timeout_tasks, FINAL_ANSWER_LINK
from logging_system import log_warning, log_error, log_debug, log_success, log_analytics, log_info

# -------- ENHANCED TIMEOUT HANDLER --------

async def handle_selection_timeout(user_id, ctx):
    """ENHANCED: Timeout handler with better cleanup and logging"""
    start_time = datetime.now()
    
    try:
        await asyncio.sleep(SELECTION_TIMEOUT)
        
        # Check if user still has pending selection
        if user_id not in pending_selections:
            log_debug(f"TIMEOUT: User {user_id} no longer has pending selection")
            return
        
        selection_data = pending_selections[user_id]
        
        # Check if already locked (user made selection)
        if selection_data.get("locked", False):
            log_debug(f"TIMEOUT: User {user_id} selection already locked")
            return
        
        # Lock to prevent race conditions
        selection_data["locked"] = True
        
        timeout_duration = (datetime.now() - start_time).total_seconds()
        
        log_warning(f"TIMEOUT: User {user_id} selection timed out after {timeout_duration}s")
        
        # Log analytics
        await log_analytics("User Selection", 
            user_id=user_id,
            user_name=getattr(ctx.author, 'display_name', 'Unknown'),
            channel=ctx.channel.name,
            question=selection_data.get("original_question", "Unknown"),
            timeout="timed_out",
            timeout_duration=int(timeout_duration),
            selection_type=selection_data.get("type", "unknown")
        )
        
        # Clean up messages
        messages_deleted = 0
        try:
            if "message" in selection_data:
                await selection_data["message"].delete()
                messages_deleted += 1
                log_debug("TIMEOUT: Deleted selection message")
        except Exception as e:
            log_error(f"TIMEOUT: Failed to delete selection message: {e}")
        
        try:
            if "original_user_message" in selection_data:
                await selection_data["original_user_message"].delete()
                messages_deleted += 1
                log_debug("TIMEOUT: Deleted original user message")
        except Exception as e:
            log_error(f"TIMEOUT: Failed to delete original message: {e}")
        
        # Send timeout notification
        try:
            timeout_msg = await ctx.send("⏰ Selection timed out. Please try your question again.")
            await timeout_msg.delete(delay=5)
            log_debug("TIMEOUT: Sent timeout notification")
        except Exception as e:
            log_error(f"TIMEOUT: Failed to send timeout message: {e}")
        
        # Remove from pending selections
        del pending_selections[user_id]
        
        # Clean up timeout task reference
        if user_id in timeout_tasks:
            del timeout_tasks[user_id]
        
        log_success(f"TIMEOUT: Cleaned up user {user_id} selection (deleted {messages_deleted} messages)")
        
    except asyncio.CancelledError:
        log_debug(f"TIMEOUT: Task cancelled for user {user_id} (user made selection)")
        # Clean up timeout task reference
        if user_id in timeout_tasks:
            del timeout_tasks[user_id]
    except Exception as e:
        log_error(f"TIMEOUT: Unexpected error for user {user_id}: {e}")
        # Emergency cleanup
        if user_id in pending_selections:
            del pending_selections[user_id]
        if user_id in timeout_tasks:
            del timeout_tasks[user_id]

# -------- SELECTION MANAGEMENT --------

def start_selection_timeout(user_id, ctx):
    """Start a timeout task for a user selection"""
    # Cancel existing timeout if any
    if user_id in timeout_tasks:
        timeout_tasks[user_id].cancel()
    
    # Start new timeout task
    timeout_tasks[user_id] = asyncio.create_task(handle_selection_timeout(user_id, ctx))
    log_debug(f"TIMEOUT: Started timeout task for user {user_id}")

def cancel_selection_timeout(user_id):
    """Cancel timeout task for a user"""
    if user_id in timeout_tasks:
        timeout_tasks[user_id].cancel()
        del timeout_tasks[user_id]
        log_debug(f"TIMEOUT: Cancelled timeout task for user {user_id}")

# -------- REACTION PROCESSING --------

async def handle_disambiguation_selection(reaction, user, selected_player, selection_data):
    """Handle disambiguation selection (user picking which player they meant)"""
    from recent_mentions import check_recent_player_mentions
    from bot_logic import process_approved_question
    from bot import question_map
    
    log_info(f"🎯 User disambiguated to: {selected_player['name']} ({selected_player['team']})")
    
    # Check recent mentions for this specific player
    recent_mentions = await check_recent_player_mentions(reaction.message.guild, [selected_player])
    
    # DEBUG LOGGING - This will show us what's happening
    log_info(f"🔧 DEBUG: recent_mentions returned: {recent_mentions}")
    log_info(f"🔧 DEBUG: recent_mentions is truthy: {bool(recent_mentions)}")
    log_info(f"🔧 DEBUG: Length of recent_mentions: {len(recent_mentions)}")
    
    if recent_mentions:
        log_info(f"🔧 DEBUG: Entering blocking logic")
        mention = recent_mentions[0]
        status = mention["status"]
        player_name = mention["player"]["name"]
        log_info(f"🔧 DEBUG: Status is: {status}")
        
        log_info(f"🚫 Selected player {selected_player['name']} has recent mention with status: {status}")
        
        # Send blocking message with specific URLs
        try:
            if status == "answered":
                # 🔧 NEW: Use the specific answer URL if available
                answer_url = mention.get("answer_url")
                if answer_url:
                    error_msg = await reaction.message.channel.send(
                        f"**{player_name}** was answered recently: {answer_url}"
                    )
                    log_info(f"🔧 SPECIFIC URL: Used specific answer URL for {player_name}")
                else:
                    # Fallback to generic channel link
                    error_msg = await reaction.message.channel.send(
                        f"This player has been asked about recently. There is an answer here: {FINAL_ANSWER_LINK}"
                    )
                    log_info(f"🔧 FALLBACK URL: Used generic channel link for {player_name}")
            else:  # pending
                error_msg = await reaction.message.channel.send(
                    "This player has been asked about recently, please be patient and wait for an answer."
                )
            
            await error_msg.delete(delay=8)
            log_info(f"✅ Sent and scheduled deletion of blocking message")
        except Exception as e:
            log_error(f"❌ Failed to send blocking message: {e}")
        
        # Delete the original user message - but don't let exceptions stop the blocking
        try:
            await selection_data["original_user_message"].delete()
            log_info("✅ Deleted original user message after blocking disambiguation")
        except Exception as e:
            log_error(f"❌ Failed to delete original user message: {e}")
        
        # ALWAYS return True when blocking, regardless of any exceptions above
        log_info(f"🔧 DEBUG: Returning True (blocked) for {selected_player['name']}")
        return True  # Blocked
    else:
        log_info(f"🔧 DEBUG: No recent mentions found, proceeding with question")
        # No recent mentions - proceed with the question, adding selected player info
        log_info(f"✅ Selected player {selected_player['name']} has no recent mentions - proceeding with question")
        
        # Append selected player info to make it clear which player they meant
        modified_question = f"{selection_data['original_question']} ({selected_player['name']} - {selected_player['team']})"
        log_info(f"🔧 Modified question: {modified_question}")
        
        await process_approved_question(
            reaction.message.channel,
            user,
            modified_question,
            selection_data["original_user_message"],
            question_map
        )
        
        log_info(f"🔧 DEBUG: Returning False (not blocked) for {selected_player['name']}")
        return False  # Not blocked, processed

async def handle_block_selection(reaction, user, selected_player, selection_data):
    """Handle block selection (user picking from recently mentioned players)"""
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
        # Delete the original user message as well
        try:
            await selection_data["original_user_message"].delete()
            log_info("✅ Deleted original user message after blocking")
        except Exception as e:
            log_error(f"❌ Failed to delete original user message: {e}")
        return True  # Blocked
    
    return False  # Not blocked (shouldn't happen)

def cleanup_invalid_selection(user_id, selection_data):
    """Clean up when user makes invalid reaction"""
    try:
        asyncio.create_task(selection_data["message"].delete())
        asyncio.create_task(selection_data["original_user_message"].delete())
    except:
        pass
    
    if user_id in pending_selections:
        del pending_selections[user_id]
    
    cancel_selection_timeout(user_id)

# Add this function to selection_handlers.py

async def create_player_disambiguation_prompt(ctx, question, matched_players):
    """Create a disambiguation prompt when multiple players match an ambiguous search"""
    from config import REACTIONS, pending_selections
    
    log_info(f"DISAMBIGUATION: Creating prompt for {len(matched_players)} players")
    
    # Log the disambiguation event
    await log_analytics("Question Processed",
        user_id=ctx.author.id,
        user_name=ctx.author.display_name,
        channel=ctx.channel.name,
        question=question,
        status="disambiguation_required",
        reason=f"found_{len(matched_players)}_players"
    )
    
    # Create the prompt message
    prompt_lines = ["**Which player did you mean?**\n"]
    
    for i, player in enumerate(matched_players[:len(REACTIONS)]):
        emoji = REACTIONS[i]
        prompt_lines.append(f"{emoji} {player['name']} ({player['team']})")
    
    prompt_text = "\n".join(prompt_lines)
    prompt_text += "\n\n*Click a reaction to select the player.*"
    
    try:
        # Send the disambiguation prompt
        prompt_message = await ctx.send(prompt_text)
        log_info(f"DISAMBIGUATION: Sent prompt message with ID {prompt_message.id}")
        
        # Add reaction emojis
        for i in range(len(matched_players[:len(REACTIONS)])):
            await prompt_message.add_reaction(REACTIONS[i])
            log_info(f"DISAMBIGUATION: Added reaction {REACTIONS[i]}")
        
        # Store in pending selections
        pending_selections[ctx.author.id] = {
            "message": prompt_message,
            "players": matched_players,
            "original_question": question,
            "original_user_message": ctx.message,
            "type": "disambiguation_selection",
            "locked": False
        }
        
        # Start timeout task
        start_selection_timeout(ctx.author.id, ctx)
        
        log_info(f"DISAMBIGUATION: Set up selection for user {ctx.author.id}")
        
        return True  # Successfully created prompt
        
    except Exception as e:
        log_error(f"DISAMBIGUATION: Failed to create prompt: {e}")
        return False