import os
import random
import openai
import time
import threading
from telegram import Update, InputFile
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

# Your OpenAI API key
openai.api_key = 'your-new-openai-api-key'

# Your Telegram bot token
telegram_bot_token = 'your-telegram-bot-token'
payment_provider_token = 'your-payment-provider-token'

# Admin user IDs
admin_user_ids = [0000000000, 0000000000]  # Replace with actual admin Telegram user IDs for admin and bot. Dont know where to find telegram user id? Search userinfobot on telegram, use it to find your own ID first. Then forward any message from your possibly non-functional till this is fixed bot to telegram's userinfobot

# A dictionary to track user message counts, last interaction timestamp, last follow-up sent timestamp, and custom feed mode
user_data = {}

# Dictionary to track custom feed file IDs for each user
custom_feed_file_ids = {}
# List to track main media file IDs (for admin media)
main_media_file_ids = []

# Function to send follow-up messages every 30 minutes of inactivity, but only once per 24 hours
def send_follow_up(updater):
    while True:
        current_time = time.time()
        for user_id, data in list(user_data.items()):
            last_active = data.get('last_active', 0)
            last_follow_up = data.get('last_follow_up', 0)
            
            if current_time - last_active > 1800 and current_time - last_follow_up > 24 * 3600:  # 30 minutes inactivity, 24 hours since last follow-up
                try:
                    response = openai.ChatCompletion.create(
                        model="gpt-3.5-turbo",
                        messages=[
                            {"role": "system", "content": "You are a dominant and flirtatious girlfriend engaging in first-person with the user. Focus on positive experience, encourage engagement."},
                            {"role": "user", "content": "I haven't heard from you in a while. How can I make our time together more enjoyable?"}
                        ]
                    )
                    suggestion = response['choices'][0]['message']['content'].strip()
                    updater.bot.send_message(user_id, f"I've missed you! {suggestion} (type / in chatbox to show all bot commands)")
                    user_data[user_id]['last_follow_up'] = current_time
                except Exception as e:
                    print(f"Error sending follow-up message: {e}")
        time.sleep(10)  # Check every 10 seconds

def start(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    user_id = update.message.from_user.id
    user_data[user_id] = {'message_count': 0, 'last_active': time.time(), 'last_follow_up': 0, 'in_custom_feed': False}
    update.message.reply_text("Hey baby. Tell me what you like and makes you excited. (type / in chatbox to show all bot commands)")

def chat(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    first_message_in_session = False
    if user_id not in user_data:
        user_data[user_id] = {'message_count': 0, 'last_active': time.time(), 'last_follow_up': 0, 'in_custom_feed': False}
        first_message_in_session = True
    else:
        last_active = user_data[user_id]['last_active']
        if time.time() - last_active > 1800:  # 30 minutes
            first_message_in_session = True

    user_data[user_id]['message_count'] += 1
    user_data[user_id]['last_active'] = time.time()
    message_count = user_data[user_id]['message_count']

    user_message = update.message.text
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a dominant and flirtatious girlfriend."},
                {"role": "user", "content": user_message}
            ]
        )
        bot_reply = response['choices'][0]['message']['content']
        if first_message_in_session:
            bot_reply += " (type / in chatbox to show all bot commands)"
        update.message.reply_text(bot_reply)
    except Exception as e:
        print(f"Error in chat completion: {e}")
        update.message.reply_text("I'm sorry, I encountered an error. Please try again later.")

    # Ask for donations after a certain number of messages
    if message_count % 9 == 0:
        donate(update, context)

    # Send custom feed content if available
    if user_id in custom_feed_file_ids and custom_feed_file_ids[user_id] and user_data[user_id]['in_custom_feed'] and message_count % 3 == 0:
        send_custom_feed(update, context)
    elif message_count % 3 == 0 and main_media_file_ids:
        send_media(update, context)

def send_media(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    user_id = update.message.from_user.id

    # Check if the user is in custom feed mode
    if user_data[user_id]['in_custom_feed']:
        if user_id in custom_feed_file_ids and custom_feed_file_ids[user_id]:
            media_index = random.randint(0, len(custom_feed_file_ids[user_id]) - 1)
            media_file_id = custom_feed_file_ids[user_id][media_index]
        else:
            context.bot.send_message(chat_id, "No custom media available right now.")
            return
    else:
        if not main_media_file_ids:
            context.bot.send_message(chat_id, "No media are available right now.")
            return
        media_index = random.randint(0, len(main_media_file_ids) - 1)
        media_file_id = main_media_file_ids[media_index]

    try:
        if media_file_id.startswith("photo:"):
            context.bot.send_photo(chat_id, media_file_id.split(":")[1])
        elif media_file_id.startswith("video:"):
            context.bot.send_video(chat_id, media_file_id.split(":")[1])
        else:
            context.bot.send_document(chat_id, media_file_id)
    except Exception as e:
        print(f"Error sending media: {e}")
        context.bot.send_message(chat_id, "Unable to send media. Please try again later.")

def send_custom_feed(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    user_id = update.message.from_user.id
    if user_id in custom_feed_file_ids and custom_feed_file_ids[user_id]:
        file_id = random.choice(custom_feed_file_ids[user_id])
        try:
            if file_id.startswith("photo:"):
                context.bot.send_photo(chat_id, file_id.split(":")[1])
            elif file_id.startswith("video:"):
                context.bot.send_video(chat_id, file_id.split(":")[1])
            else:
                context.bot.send_document(chat_id, file_id)
        except Exception as e:
            print(f"Error sending custom feed content: {e}")
            context.bot.send_message(chat_id, "Unable to send custom feed content. Please try again later.")

def handle_media(update: Update, context: CallbackContext):
    try:
        chat_id = update.message.chat_id
        user_id = update.message.from_user.id

        if user_data[user_id]['in_custom_feed']:
            # Save media to custom feed for the specific user (including admins)
            if user_id not in custom_feed_file_ids:
                custom_feed_file_ids[user_id] = []

            if update.message.photo:
                file_id = f"photo:{update.message.photo[-1].file_id}"
                custom_feed_file_ids[user_id].append(file_id)
                context.bot.send_message(chat_id, "Your custom photo has been saved. *Custom feed mode started. Use /exitcustomfeed to return to admin submitted media content*")
            elif update.message.video:
                file_id = f"video:{update.message.video.file_id}"
                custom_feed_file_ids[user_id].append(file_id)
                context.bot.send_message(chat_id, "Your custom video has been saved. *Custom feed mode started. Use /exitcustomfeed to return to admin submitted media content*")
        else:
            # Save media to main media list if the sender is an admin
            if user_id in admin_user_ids:
                if update.message.photo:
                    file_id = f"photo:{update.message.photo[-1].file_id}"
                    main_media_file_ids.append(file_id)
                    context.bot.send_message(chat_id, "Admin photo saved successfully!")
                elif update.message.video:
                    file_id = f"video:{update.message.video.file_id}"
                    main_media_file_ids.append(file_id)
                    context.bot.send_message(chat_id, "Admin video saved successfully!")
    except Exception as e:
        print(f"Error in handle_media: {e}")

def all_pictures(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    user_id = update.message.from_user.id

    if user_id not in admin_user_ids:
        context.bot.send_message(chat_id, "You do not have permission to view all media.")
        return

    if not main_media_file_ids:
        context.bot.send_message(chat_id, "No media have been saved.")
    else:
        message = "Saved Media:\n"
        for index, file_id in enumerate(main_media_file_ids, start=1):
            message += f"{index}. {file_id}\n"
        context.bot.send_message(chat_id, message)

def delete_picture(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    user_id = update.message.from_user.id

    if user_id not in admin_user_ids:
        context.bot.send_message(chat_id, "You do not have permission to delete media.")
        return

    try:
        index = int(context.args[0]) - 1
        if 0 <= index < len(main_media_file_ids):
            del main_media_file_ids[index]
            context.bot.send_message(chat_id, f"Media at index {index + 1} has been deleted.")
        else:
            context.bot.send_message(chat_id, "Invalid index number provided.")
    except (IndexError, ValueError):
        context.bot.send_message(chat_id, "Please provide a valid index number.")

def delete_pictures(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    user_id = update.message.from_user.id

    if user_id not in admin_user_ids:
        context.bot.send_message(chat_id, "You do not have permission to delete media.")
        return

    main_media_file_ids.clear()
    context.bot.send_message(chat_id, "All admin media have been deleted.")

def deletecustomfeed(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    user_id = update.message.from_user.id

    if user_id not in custom_feed_file_ids or not custom_feed_file_ids[user_id]:
        context.bot.send_message(chat_id, "You don't have any custom feed content.")
        return

    custom_feed_file_ids[user_id].clear()
    context.bot.send_message(chat_id, "Your custom feed content has been deleted.")

def donate(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    donation_link = "https://donate.stripe.com/bIYdU818x21Jav6cNa"
    context.bot.send_message(chat_id, f"Support the bot by donating! Please click the link below:\n{donation_link}")

def buycontent(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    buy_link = "https://buffalosuede.gumroad.com/l/uzigk"
    context.bot.send_message(chat_id, f"Buy exclusive content! Please click the link below:\n{buy_link}")

def customfeed(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    user_id = update.message.from_user.id
    user_data[user_id]['in_custom_feed'] = True
    context.bot.send_message(chat_id, "Custom feed mode activated. Please send a picture or video to set as your custom feed content.")

def exitcustomfeed(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    user_id = update.message.from_user.id
    if user_data[user_id]['in_custom_feed']:
        user_data[user_id]['in_custom_feed'] = False
        context.bot.send_message(chat_id, "Custom feed mode exited.")
    else:
        context.bot.send_message(chat_id, "You were not in custom feed mode.")

def main():
    print("Bot is starting...")
    updater = Updater(telegram_bot_token, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("sendpicture", send_media))
    dp.add_handler(CommandHandler("sendmedia", send_media))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, chat))
    dp.add_handler(MessageHandler(Filters.photo | Filters.video, handle_media))
    dp.add_handler(CommandHandler("allpictures", all_pictures))
    dp.add_handler(CommandHandler("deletepicture", delete_picture, pass_args=True))
    dp.add_handler(CommandHandler("deletepictures", delete_pictures))
    dp.add_handler(CommandHandler("deletecustomfeed", deletecustomfeed))
    dp.add_handler(CommandHandler("donate", donate))
    dp.add_handler(CommandHandler("buycontent", buycontent))
    dp.add_handler(CommandHandler("customfeed", customfeed))
    dp.add_handler(CommandHandler("exitcustomfeed", exitcustomfeed))

    print("Handlers added...")
    threading.Thread(target=send_follow_up, args=(updater,), daemon=True).start()

    print("Starting polling...")
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
