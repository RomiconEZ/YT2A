import re
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from urllib.parse import urlparse, parse_qs

from ML.main import extract_picture_from_yt_video

BOT_TOKEN = "5827586590:AAEyJ6WLaTogaIgs7NT5fFAPgQZXXXV2_Ng"
BOT_USERNAME = "@yt2abot"

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Чтобы получить статью по youtube видео, отправь мне ссылку на него!")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Сервис принимает ссылку на youtube видео и возвращает docx файл, содержащий статью, созданную по данному видео.")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text

    youtube_regex = (
        r'(https?://)?(www\.)?'
        '(youtube|youtu|youtube-nocookie)\.(be|com)/'
        '(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})')


    if re.match(youtube_regex, url):

        url_data = urlparse(url)
        query = parse_qs(url_data.query)
        if "v" in query.keys():
            video_id = query["v"][0]

            extract_picture_from_yt_video(f'https://www.youtube.com/watch?v={video_id}', start_time = "00:01:00.000")
            await update.message.reply_animation("output.jpg", caption="Держи залупу")
            return

        video_id = url_data.geturl().split('/')[-1]
        extract_picture_from_yt_video(f'https://www.youtube.com/watch?v={video_id}', start_time = "00:01:00.000")
        await update.message.reply_animation("output.jpg", caption="Держи залупу")


    else:
        await update.message.reply_text("Данный адрес не является ссылкой на youtube видео. Повторите снова.")

async def error(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f'Update {update} caused error {context.error}')

if __name__ == '__main__':
    app = Application.builder().token(BOT_TOKEN).build()

    # Commands
    app.add_handler(CommandHandler('start', start_command))
    app.add_handler(CommandHandler('help', help_command))

    # Messages
    app.add_handler(MessageHandler(filters.TEXT, handle_message))

    # Errors
    app.add_error_handler(error)

    print('Polling...')
    app.run_polling(poll_interval=3)