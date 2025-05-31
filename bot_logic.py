import discord
from config import ANSWERING_CHANNEL, FINAL_ANSWER_LINK, question_map
from logging_system import log_error, log_analytics

# -------- MULTI-PLAYER QUESTION PROCESSING --------

async def handle_multi_player_question(ctx, question, matched_players):
    """Handle questions about multiple players (e.g. 'How are Judge, Ohtani, and Acuña doing?')"""
    from recent_mentions import check_recent_player_mentions
    
    print(f"🎯 MULTI-PLAYER QUESTION: Found {len(matched_players)} players, processing all of them")
    
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
        print(f"🚫 BLOCKING: {len(recent_mentions)} of the {len(matched_players)} players have recent mentions")
        
        # Block the question since some players were recently mentioned
        try:
            await ctx.message.delete()
        except:
            pass
        
        # Create a detailed blocking message
        if len(recent_mentions) == 1:
            mention = recent_mentions[0]
            player = mention["player"]
            status = mention["status"]
            if status == "answered":
                error_msg = await ctx.send(f"One of the players you asked about ({player['name']}) has been asked about recently. There is an answer here: {FINAL_ANSWER_LINK}")
            else:
                error_msg = await ctx.send(f"One of the players you asked about ({player['name']}) has been asked about recently, please be patient and wait for an answer.")
        else:
            # Multiple players with recent mentions
            player_names = [f"{m['player']['name']}" for m in recent_mentions]
            players_text = ", ".join(player_names)
            error_msg = await ctx.send(f"Some of the players you asked about ({players_text}) have been asked about recently, please be patient and wait for answers.")
        
        await error_msg.delete(delay=10)
        return True  # Blocked
    else:
        # No recent mentions for any player - approve the multi-player question
        print(f"✅ APPROVING: Multi-player question with {len(matched_players)} players, no recent mentions")
        
        # Add all player names to the question for clarity
        player_list = ", ".join([f"{p['name']} ({p['team']})" for p in matched_players])
        modified_question = f"{question} [Players: {player_list}]"
        
        await process_approved_question(ctx.channel, ctx.author, modified_question, ctx.message)
        return False  # Not blocked, processed

# -------- SINGLE PLAYER QUESTION PROCESSING --------

async def handle_single_player_question(ctx, question, matched_players):
    """Handle questions about a single player"""
    from recent_mentions import check_recent_player_mentions
    
    # Single player - check recent mentions
    recent_mentions = await check_recent_player_mentions(ctx.guild, matched_players)
    
    if recent_mentions:
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
        return True  # Blocked
    else:
        # No recent mentions - approve the question
        await process_approved_question(ctx.channel, ctx.author, question, ctx.message)
        return False  # Not blocked, processed

# -------- QUESTION PROCESSING --------

async def process_approved_question(channel, user, question, original_message=None):
    """Process a question that has passed all checks"""
    # Delete the original message if provided
    if original_message:
        try:
            await original_message.delete()
            print("✅ Deleted original user message in process_approved_question")
        except Exception as e:
            print(f"❌ Failed to delete original message in process_approved_question: {e}")
    
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
            print("✅ Confirmation message sent and will be deleted in 5 seconds")
            
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