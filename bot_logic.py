# Updated bot_logic.py for question_map change

import discord
import asyncio
from config import ANSWERING_CHANNEL, FINAL_ANSWER_LINK
from logging_system import log_error, log_analytics, log_info, log_success
from question_map_store import load_question_map, save_question_map, append_question

# -------- MULTI-PLAYER QUESTION PROCESSING --------

async def handle_multi_player_question(ctx, question, matched_players, question_map):
    """🔧 FIXED: Handle questions about multiple players with single player policy enforcement"""
    # Import here to avoid circular imports
    from recent_mentions import check_recent_player_mentions
    from player_matching import capture_all_raw_player_detections
    
    print(f"MULTI-PLAYER QUESTION: Found {len(matched_players)} players, applying single player policy")
    
    # 🔧 NEW: Single Player Policy Enforcement
    log_info(f"🚫 SINGLE PLAYER POLICY: Question detected {len(matched_players)} validated players: {[p['name'] for p in matched_players]}")
    
    # Capture raw detections for enhanced blocker message
    all_raw_detections = capture_all_raw_player_detections(question)
    log_info(f"🚫 SINGLE PLAYER POLICY: Raw detections were: {all_raw_detections}")
    
    # Create enhanced blocker message showing ALL detected names (including false positives)
    if all_raw_detections:
        detected_names_str = ", ".join(all_raw_detections)
        blocker_message = f"You may only ask about one player. Your question has been blocked as you asked about [{detected_names_str}]"
    else:
        # Fallback if raw detection failed
        validated_names_str = ", ".join([p['name'] for p in matched_players])
        blocker_message = f"You may only ask about one player. Your question has been blocked as you asked about [{validated_names_str}]"
    
    try:
        await ctx.message.delete()
    except:
        pass
    
    error_msg = await ctx.send(blocker_message)
    await error_msg.delete(delay=10)
    
    # Log the single player policy violation
    await log_analytics("Single Player Policy",
        user_id=ctx.author.id,
        user_name=ctx.author.display_name,
        channel=ctx.channel.name,
        question=question,
        validated_players=len(matched_players),
        raw_detections=len(all_raw_detections) if all_raw_detections else 0,
        detected_names=all_raw_detections if all_raw_detections else [p['name'] for p in matched_players],
        status="blocked_multi_player"
    )
    
    return True  # Always blocked - single player policy

# -------- SINGLE PLAYER QUESTION PROCESSING --------

async def handle_single_player_question(ctx, question, matched_players, question_map):
    """Handle questions about a single player"""
    try:
        print(f"SINGLE PLAYER: Starting to handle single player question")
        print(f"SINGLE PLAYER: Players to check: {[p['name'] for p in matched_players]}")
        
        # Import here to avoid circular imports
        from recent_mentions import check_recent_player_mentions
        
        print(f"SINGLE PLAYER: About to check recent mentions")
        
        # Single player - check recent mentions
        recent_mentions = await check_recent_player_mentions(ctx.guild, matched_players)
        
        print(f"SINGLE PLAYER: Recent mentions result: {len(recent_mentions) if recent_mentions else 0}")
        
        if recent_mentions:
            mention = recent_mentions[0]
            player = mention["player"]
            status = mention["status"]
            
            print(f"BLOCKING: Due to recent mention - {player['name']} ({status})")
            
            try:
                await ctx.message.delete()
                print("SINGLE PLAYER: Deleted original message")
            except Exception as e:
                print(f"SINGLE PLAYER: Failed to delete message: {e}")
            
            if status == "answered":
                # 🔧 NEW: Use specific answer URL if available
                answer_url = mention.get("answer_url")
                if answer_url:
                    error_msg = await ctx.send(f"**{player['name']}** was answered recently: {answer_url}")
                    print(f"SINGLE PLAYER: Used specific answer URL for {player['name']}")
                else:
                    error_msg = await ctx.send(f"This player has been asked about recently. There is an answer here: {FINAL_ANSWER_LINK}")
                    print(f"SINGLE PLAYER: Used generic answer link for {player['name']}")
            else:
                error_msg = await ctx.send("This player has been asked about recently, please be patient and wait for an answer.")
            
            await error_msg.delete(delay=8)
            print("SINGLE PLAYER: Sent blocking message")
            return True  # Blocked
        else:
            print("SINGLE PLAYER: No recent mentions, approving question")
            # No recent mentions - approve the question
            await process_approved_question(ctx.channel, ctx.author, question, ctx.message, question_map)
            print("SINGLE PLAYER: Called process_approved_question")
            return False  # Not blocked, processed
            
    except Exception as e:
        print(f"SINGLE PLAYER ERROR: {e}")
        log_error(f"Error in handle_single_player_question: {e}")
        # Fallback - just approve the question
        await process_approved_question(ctx.channel, ctx.author, question, ctx.message, question_map)
        return False

# -------- QUESTION PROCESSING --------

async def process_approved_question(channel, user, question, original_message=None, question_map=None):
    """Process a question that has passed all checks"""
    # Delete the original message if provided
    if original_message:
        try:
            await original_message.delete()
            print("Deleted original user message in process_approved_question")
        except Exception as e:
            print(f"Failed to delete original message in process_approved_question: {e}")
    
    answering_channel = discord.utils.get(channel.guild.text_channels, name=ANSWERING_CHANNEL)
    
    if answering_channel:
        # Format the question for the answering channel
        asker_mention = f"<@{user.id}>"
        formatted_message = f"{asker_mention} asked:\n> {question}\n\n❗ **Not Answered**\n\nReply to this message to answer."
        
        try:
            # Post to answering channel
            posted_message = await answering_channel.send(formatted_message)
            print(f"Posted question to #{ANSWERING_CHANNEL}")
            
            # Store the question mapping for later reference
            append_question(question_map, str(posted_message.id), {
                "question": question,
                "asker_id": user.id
            })
            print(f"Stored question mapping for message ID {posted_message.id}")
            
            # ENHANCED: Log analytics for approved question
            await log_analytics("Question Processed",
                user_id=user.id,
                user_name=user.display_name,
                channel=channel.name,
                question=question,
                status="approved",
                reason="passed_all_checks"
            )
            
            # Send confirmation message
            confirmation_msg = await channel.send(f"✅ Your question has been posted for experts to answer.")
            await confirmation_msg.delete(delay=5)
            print("Confirmation message sent and will be deleted in 5 seconds")
            
        except Exception as e:
            log_error(f"Failed to post question to answering channel: {e}")
            error_msg = await channel.send("❌ Failed to post your question. Please try again.")
            await error_msg.delete(delay=5)
    else:
        log_error(f"Could not find #{ANSWERING_CHANNEL}")
        error_msg = await channel.send(f"❌ Could not find #{ANSWERING_CHANNEL}")
        await error_msg.delete(delay=5)

async def schedule_answered_message_cleanup(original_message, reply_message, delay_seconds=15):
    """Schedule deletion of answered question and expert reply after specified delay"""
    try:
        log_info(f"AUTO-DELETE: Scheduled cleanup for question {original_message.id} and reply {reply_message.id} in {delay_seconds}s")
        
        await asyncio.sleep(delay_seconds)
        
        # Delete both messages
        deleted_count = 0
        try:
            await original_message.delete()
            deleted_count += 1
            log_info(f"AUTO-DELETE: Deleted question {original_message.id}")
        except discord.NotFound:
            log_info(f"AUTO-DELETE: Question {original_message.id} already deleted")
        except Exception as e:
            log_error(f"AUTO-DELETE: Failed to delete question {original_message.id}: {e}")
        
        try:
            await reply_message.delete()  
            deleted_count += 1
            log_info(f"AUTO-DELETE: Deleted reply {reply_message.id}")
        except discord.NotFound:
            log_info(f"AUTO-DELETE: Reply {reply_message.id} already deleted")
        except Exception as e:
            log_error(f"AUTO-DELETE: Failed to delete reply {reply_message.id}: {e}")
            
        log_success(f"AUTO-DELETE: Cleanup completed - {deleted_count}/2 messages deleted")
        
    except Exception as e:
        log_error(f"AUTO-DELETE: Unexpected error: {e}")

# -------- QUESTION FALLBACK CHECK --------

def get_potential_player_words(question):
    """Extract potential player words for fallback checking"""
    from utils import normalize_name
    
    normalized_text = normalize_name(question)
    words = normalized_text.split()
    potential_player_words = [w for w in words if len(w) >= 4 and w not in {
        'playing', 'projection', 'stats', 'performance', 'update', 'news', 'info', 'question', 'about'
    }]
    
    return potential_player_words
