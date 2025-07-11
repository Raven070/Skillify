

## To create a text message  

async def admin_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Broadcast a message to all users by admin command."""
    # Check if the user is the admin
    if update.message.from_user.id == 1048189213:
        # The message to be broadcasted
        message = "This is an important announcement from the admin!"
        
        for chat_id in user_chat_ids:
            try:
                await context.bot.send_message(chat_id=chat_id, text=message)
            except Exception as e:
                logger.error(f"Failed to send message to {chat_id}: {e}")

#--------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------

#to create poll 

from telegram import Update, Poll
from telegram.ext import ContextTypes

async def admin_broadcast_polls(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Broadcast multiple quiz polls to all users by admin command."""
    if update.message.from_user.id == 1048189213:
        # Poll 1
        question1 = "What is the rarest transition element?"
        options1 = ["Sc", "Ti", "Fe", "Mn"]
        correct_option_id1 = 0

        # Poll 2
        question2 = "Two successive transition elements X and Y form the first transition series. If you know that the atomic mass of X is greater than Y, and the density of Y is greater than X, which of the following statements is true?"
        options2 = [
            "Element Y has 12 radioactive isotopes, while Element X has five stable isotopes",
            "The magnetic moment of element Y is greater than the magnetic moment of element X",
            "Element Y forms rechargeable battery with cadmium",
            "Element X forms with steel an acid-resistant alloy"
        ]
        correct_option_id2 = 1

        # Poll 3
        question3 = "A and B are two iron oxides, both of them have a black color. B has higher magnetic properties than A. When heating one mole of them in the air, after heating, we find that:"
        options3 = [
            "The increase in mass of A = the increase in mass of B",
            "The increase in mass of B > the increase in mass of A",
            "The increase in mass of A > the increase in mass of B",
            "There is no change in the mass of either A or B"
        ]
        correct_option_id3 = 0

        # Poll 4
        question4 = "Which of the following involves oxidation of iron (or its ion) and a decrease in the number of unpaired electrons?"
        options4 = [
            "Fe2O3 + 2NaOH → 2NaFeO2 + H2O",
            "2Fe + 3Cl2 → 2FeCl3",
            "NaFeO2 + 4HNO3 → Fe(NO3)3 + NaNO3 + 2H2O",
            "Fe2O3 + 4NaOH + 3NaOCl → 2Na2FeO4 + 3NaCl + 2H2O"
        ]
        correct_option_id4 = 3

        # List of polls
        polls = [
            (question1, options1, correct_option_id1),
            (question2, options2, correct_option_id2),
            (question3, options3, correct_option_id3),
            (question4, options4, correct_option_id4)
        ]

        for chat_id in user_chat_ids:
            for question, options, correct_option_id in polls:
                try:
                    await context.bot.send_poll(
                        chat_id=chat_id,
                        question=question,
                        options=options,
                        type=Poll.QUIZ,
                        correct_option_id=correct_option_id,
                        is_anonymous=True
                    )
                except Exception as e:
                    logger.error(f"Failed to send poll to {chat_id}: {e}")

#=================================================================================

#to sent a voice note  

async def admin_broadcast_video_note(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Broadcast a video note to all users by admin command."""
    if update.message.from_user.id == 1048189213:
        video_note_file_id = "your_video_note_file_id_here"  # Replace with your actual video note file ID

        for chat_id in user_chat_ids:
            try:
                await context.bot.send_video_note(chat_id=chat_id, video_note=video_note_file_id)
            except Exception as e:
                logger.error(f"Failed to send video note to {chat_id}: {e}")

#========================================================


#to sent a video note  

async def admin_broadcast_video_note(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Broadcast a video note to all users by admin command."""
    if update.message.from_user.id == 1048189213:
        video_note_file_id = "your_video_note_file_id_here"  # Replace with your actual video note file ID

        for chat_id in user_chat_ids:
            try:
                await context.bot.send_video_note(chat_id=chat_id, video_note=video_note_file_id)
            except Exception as e:
                logger.error(f"Failed to send video note to {chat_id}: {e}")


#========================================================


#to sent a image with caption  
async def admin_broadcast_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Broadcast a photo to all users by admin command."""
    if update.message.from_user.id == 1048189213:
        photo_file_id = "your_photo_file_id_here"  # Replace with your actual photo file ID
        caption = "Here is an important photo from the admin!"

        for chat_id in user_chat_ids:
            try:
                await context.bot.send_photo(chat_id=chat_id, photo=photo_file_id, caption=caption)
            except Exception as e:
                logger.error(f"Failed to send photo to {chat_id}: {e}")
