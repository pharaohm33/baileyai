import openai
import time
import random
import threading
import os
from telegram import Update, LabeledPrice, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, CallbackQueryHandler, PreCheckoutQueryHandler

# Environment variables for API keys
openai.api_key = os.getenv('sk-proj-DBE6hdXF4mR0ifNMUR5lT3BlbkFJN5gtsbrwCp76rRiDuRrD')
telegram_bot_token = os.getenv('7301232519:AAGHn3nTOJaqVgi9jf71_aeZgMseXJq-pHw')
payment_provider_token = os.getenv('pk_live_51M8DGiC6a8KiXQCVYJnuTZhBREmk96tIx2jgqwOJl17KFFE8VAlK13IR8OBzVPmudTHNWc09auk7d5BjEwSZzicB00k2z9MPdN')

# Debug statement to check token retrieval (Remove after testing)
print(f"Retrieved Telegram Bot Token: {telegram_bot_token}")

# Admin user IDs
admin_user_ids = [1032127276, 7301232519]  # Replace with actual admin Telegram user IDs

# A dictionary to track user message counts and last interaction timestamp
user_data = {}
# List of file IDs for pictures
picture_file_ids = []
# Custom feed for users
custom_feeds = {}

# Function to send follow-up messages every 24 hours of inactivity
def send_follow_up(updater):
    while True:
        current_time = time.time()
        for user_id, data in list(user_data.items()):
            last_active = data.get('last_active', 0)
            if current_time - last_active > 24 * 3600:  # 24 hours
                try:
                    response = openai.ChatCompletion.create(
                        model="gpt-3.5-turbo",
                        messages=[
                            {"role": "system", "content": "You are a dominant and flirtatious girlfriend."},
                            {"role": "user", "content": "How can I encourage users to come back after being inactive?"}
                        ]
                    )
                    suggestion = response['choices'][0]['message']['content'].strip()
                    updater.bot.send_message(user_id, f"We miss you! {suggestion}")
                    user_data[user_id]['last_active'] = current_time
                except Exception as e:
                    print(f"Error sending follow-up message: {e}")
        time.sleep(3600)  # Check every hour

def check_bot_permissions(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    bot = context.bot
    bot_member = bot.get_chat_member(chat_id, bot.id)

    print(f"Bot status: {bot_member.status}")
    print(f"Permissions: {bot_member}")

    if bot_member.status not in ['administrator', 'creator']:
        update.message.reply_text("I need to be an admin to send photos and perform other actions.")
        return False
    else:
        update.message.reply_text("I have the necessary permissions.")
        return True

def start(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    if not check_bot_permissions(update, context):
        return
    user_data[chat_id] = {'message_count': 0, 'last_active': time.time(), 'custom_feed': False}
    update.message.reply_text("Hey baby. Tell me what you like and makes you excited.")

def generate_image(prompt):
    response = openai.Image.create(
        prompt=prompt,
        n=1,
        size="1024x1024"
    )
    image_url = response['data'][0]['url']
    return image_url

def chat(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    if chat_id not in user_data:
        user_data[chat_id] = {'message_count': 0, 'last_active': time.time(), 'custom_feed': False}
    user_data[chat_id]['message_count'] += 1
    user_data[chat_id]['last_active'] = time.time()
    message_count = user_data[chat_id]['message_count']

    user_message = update.message.text
    if "generate image of" in user_message.lower():
        prompt = user_message.lower().replace("generate image of", "").strip()
        try:
            image_url = generate_image(prompt)
            context.bot.send_photo(chat_id, image_url, caption=f"Here's the image for: {prompt}")
        except Exception as e:
            print(f"Error generating image: {e}")
            update.message.reply_text("Sorry, I couldn't generate the image.")
        return

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a dominant and flirtatious girlfriend."},
            {"role": "user", "content": user_message}
        ]
    )
    bot_reply = response['choices'][0]['message']['content']
    update.message.reply_text(bot_reply)

    if message_count % 3 == 0 and picture_file_ids:
        picture_index = random.randint(0, len(picture_file_ids) - 1)
        picture_file_id = picture_file_ids[picture_index]
        try:
            context.bot.send_photo(chat_id, picture_file_id, caption="Here's a picture!")
        except Exception as e:
            print(f"Error sending photo: {e}")
            context.bot.send_message(chat_id, "Unable to send photo. Please try again later.")

def send_picture(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    if not picture_file_ids:
        context.bot.send_message(chat_id, "No pictures are available right now.")
        return

    picture_index = random.randint(0, len(picture_file_ids) - 1)
    picture_file_id = picture_file_ids[picture_index]
    try:
        context.bot.send_photo(chat_id, picture_file_id, caption="Here's your requested picture!")
    except Exception as e:
        print(f"Error sending picture: {e}")
        context.bot.send_message(chat_id, "Unable to send picture. Please try again later.")

def handle_photo(update: Update, context: CallbackContext):
    try:
        chat_id = update.message.chat_id
        user_id = update.message.from_user.id

        if user_id in admin_user_ids:
            photo_file_id = update.message.photo[-1].file_id
            picture_file_ids.append(photo_file_id)
            context.bot.send_message(chat_id, "Photo saved successfully!")
        else:
            context.bot.send_message(chat_id, "Sorry, only admins can upload photos.")

    except Exception as e:
        print(f"Error in handle_photo: {e}")

def all_pictures(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    user_id = update.message.from_user.id

    if user_id not in admin_user_ids:
        context.bot.send_message(chat_id, "You do not have permission to view all pictures.")
        return

    if not picture_file_ids:
        context.bot.send_message(chat_id, "No pictures have been saved.")
    else:
        message = "Saved Pictures:\n"
        for index, file_id in enumerate(picture_file_ids, start=1):
            message += f"{index}. {file_id}\n"
        context.bot.send_message(chat_id, message)

def delete_pictures(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    user_id = update.message.from_user.id

    if user_id not in admin_user_ids:
        context.bot.send_message(chat_id, "You do not have permission to delete pictures.")
        return

    try:
        picture_numbers = context.args
        indices_to_delete = [int(num) - 1 for num in picture_numbers]
        indices_to_delete.sort(reverse=True)

        for index in indices_to_delete:
            if 0 <= index < len(picture_file_ids):
                del picture_file_ids[index]

        context.bot.send_message(chat_id, "Selected pictures have been deleted.")
    except ValueError:
        context.bot.send_message(chat_id, "Please provide valid picture numbers.")
    except Exception as e:
        context.bot.send_message(chat_id, f"Error occurred while deleting pictures: {e}")

def custom_feed(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    if chat_id not in custom_feeds:
        custom_feeds[chat_id] = []
    context.bot.send_message(chat_id, "You can now upload your custom feed. Send pictures to add to your feed.")

def exit_custom_feed(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    if chat_id in custom_feeds:
        del custom_feeds[chat_id]
        context.bot.send_message(chat_id, "You have exited the custom feed mode.")
    else:
        context.bot.send_message(chat_id, "You are not in custom feed mode.")

def delete_custom_feed(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    if chat_id in custom_feeds:
        del custom_feeds[chat_id]
        context.bot.send_message(chat_id, "Your custom feed has been deleted.")
    else:
        context.bot.send_message(chat_id, "You do not have a custom feed.")

def buy_content(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    prices = [LabeledPrice("Lifetime Access", 2500)]  # Set appropriate price
    context.bot.send_invoice(
        chat_id, "Buy Content", "Lifetime access to all pics/vids + unlimited content added over time.", "buy-content",
        payment_provider_token, "USD", prices
    )

def precheckout_callback(update: Update, context: CallbackContext):
    query = update.pre_checkout_query
    if query.invoice_payload not in ["voluntary-support", "mandatory-support", "buy-content"]:
        query.answer(ok=False, error_message="Something went wrong...")
    else:
        query.answer(ok=True)

def successful_payment_callback(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    user_data[chat_id]['message_count'] = 0
    update.message.reply_text("Thank you for your support! Your message count has been reset.")

def button(update: Update, context: CallbackContext):
    query = update.callback_query
    chat_id = query.message.chat_id
    query.answer()

    if query.data == 'pay_25':
        prices = [LabeledPrice("Mandatory Payment", 2500)]
        context.bot.send_invoice(
            chat_id, "Mandatory Payment", "Support to continue chatting", "mandatory-support",
            payment_provider_token, "USD", prices
        )
    elif query.data == 'pay_5':
        prices = [LabeledPrice("20 More Messages", 500)]
        context.bot.send_invoice(
            chat_id, "20 More Messages", "Payment for 20 more messages", "mandatory-support",
            payment_provider_token, "USD", prices
        )

def main():
    print("Bot is starting...")
    updater = Updater(telegram_bot_token, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("sendpicture", send_picture))
    dp.add_handler(CommandHandler("customfeed", custom_feed))
    dp.add_handler(CommandHandler("exitcustomfeed", exit_custom_feed))
    dp.add_handler(CommandHandler("deletecustomfeed", delete_custom_feed))
    dp.add_handler(CommandHandler("buycontent", buy_content))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, chat))
    dp.add_handler(MessageHandler(Filters.photo, handle_photo))
    dp.add_handler(CommandHandler("allpictures", all_pictures))
    dp.add_handler(CommandHandler("deletepictures", delete_pictures, pass_args=True))
    dp.add_handler(CallbackQueryHandler(button))
    dp.add_handler(PreCheckoutQueryHandler(precheckout_callback))
    dp.add_handler(MessageHandler(Filters.successful_payment, successful_payment_callback))

    print("Handlers added...")
    threading.Thread(target=send_follow_up, args=(updater,), daemon=True).start()

    print("Starting polling...")
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
