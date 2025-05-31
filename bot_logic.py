import discord
from config import ANSWERING_CHANNEL, question_map
from logging_system import log_error, log_analytics

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