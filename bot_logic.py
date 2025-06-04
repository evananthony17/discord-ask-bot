# Updated bot_logic.py for question_map change

import discord
from config import ANSWERING_CHANNEL, FINAL_ANSWER_LINK
from logging_system import log_error, log_analytics
from question_map_store import load_question_map, save_question_map, append_question

# -------- MULTI-PLAYER QUESTION PROCESSING --------

async def handle_multi_player_question(ctx, question, matched_players):
    """Handle questions about multiple players (e.g. 'How are Judge, Ohtani, and Acuña doing?')"""
    # Import here to avoid circular imports
    from recent_mentions import check_recent_player_mentions
    
    print(f"MULTI-PLAYER QUESTION: Found {len(matched_players)} players, processing all of them")
    
    # Log the multi-player detection
    await log_analytics("Question Processed",
        user_id=ctx.author.id,
        user_name=ctx.author.display_name,
        channel=ctx.channel.name,
        question=question,
        status="multi_player_detected",
        reason=f"found_{len(matched_players)}_players"
    )
    
    # Check recent mentions for ALL players
    recent_mentions = await check_recent_player_mentions(ctx.guild, matched_players)
    
    if recent_mentions:
        print(f"BLOCKING: {len(recent_mentions)} of the {len(matched_players)} players have recent mentions")
        
        # Block the question since some players were recently mentioned
        try:
            await ctx.message.delete()
        except:
            pass
        
        # Create a detailed blocking message with specific URLs
        if len(recent_mentions) == 1:
            mention = recent_mentions[0]
            player = mention["player"]
            status = mention["status"]
            
            if status == "answered":
                # 🔧 NEW: Use specific answer URL if available
                answer_url = mention.get("answer_url")
                if answer_url:
                    error_msg = await ctx.send(f"One of the players you asked about (**{player['name']}**) was answered recently: {answer_url}")
                else:
                    error_msg = await ctx.send(f"One of the players you asked about ({player['name']}) has been asked about recently. There is an answer here: {FINAL_ANSWER_LINK}")
            else:
                error_msg = await ctx.send(f"One of the players you asked about ({player['name']}) has been asked about recently, please be patient and wait for an answer.")
        else:
            # Multiple players with recent mentions - show count and generic message
            answered_players = [m for m in recent_mentions if m["status"] == "answered"]
            pending_players = [m for m in recent_mentions if m["status"] == "pending"]
            
            if answered_players and not pending_players:
                # All mentioned players were answered
                player_names = [f"{m['player']['name']}" for m in answered_players]
                players_text = ", ".join(player_names)
                error_msg = await ctx.send(f"Some of the players you asked about ({players_text}) have been answered recently. Check: {FINAL_ANSWER_LINK}")
            elif pending_players and not answered_players:
                # All mentioned players are pending
                player_names = [f"{m['player']['name']}" for m in pending_players]
                players_text = ", ".join(player_names)
                error_msg = await ctx.send(f"Some of the players you asked about ({players_text}) have been asked about recently, please be patient and wait for answers.")
            else:
                # Mix of answered and pending
                player_names = [f"{m['player']['name']}" for m in recent_mentions]
                players_text = ", ".join(player_names)
                error_msg = await ctx.send(f"Some of the players you asked about ({players_text}) have been asked about recently, please be patient and check for existing answers.")
        
        await error_msg.delete(delay=10)
        return True  # Blocked
    else:
        # No recent mentions for any player - approve the multi-player question
        print(f"APPROVING: Multi-player question with {len(matched_players)} players, no recent mentions")
        
        # Add all player names to the question for clarity
        player_list = ", ".join([f"{p['name']} ({p['team']})" for p in matched_players])
        modified_question = f"{question} [Players: {player_list}]"
        
        await process_approved_question(ctx.channel, ctx.author, modified_question, ctx.message)
        return False  # Not blocked, processed

# -------- SINGLE PLAYER QUESTION PROCESSING --------

async def handle_single_player_question(ctx, question, matched_players):
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
            await process_approved_question(ctx.channel, ctx.author, question, ctx.message)
            print("SINGLE PLAYER: Called process_approved_question")
            return False  # Not blocked, processed
            
    except Exception as e:
        print(f"SINGLE PLAYER ERROR: {e}")
        log_error(f"Error in handle_single_player_question: {e}")
        # Fallback - just approve the question
        await process_approved_question(ctx.channel, ctx.author, question, ctx.message)
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
        asker_name = f"**{user.display_name}**"
        formatted_message = f"{asker_name} asked:\n> {question}\n\n❗ **Not Answered**\n\nReply to this message to answer."
        
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