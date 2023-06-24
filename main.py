import dotenv
import os
import re
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from urllib.parse import urlparse, parse_qs

from ML import create_doc, get_subtitles_for_yt

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
            video_url = f'https://www.youtube.com/watch?v={video_id}'

            df, title = get_subtitles_for_yt(video_url)
            df.to_csv('gen_sub.csv')
            name_of_doc = 'output_doc.docx'
            create_doc(df, name_of_doc, title, video_url)
            await update.message.reply_document("output_doc.docx", caption="Вот!")
            return

        video_id = url_data.geturl().split('/')[-1]
        video_url = f'https://www.youtube.com/watch?v={video_id}'

        df, title = get_subtitles_for_yt(video_url)
        df.to_csv('gen_sub.csv')
        name_of_doc = 'output_doc.docx'
        create_doc(df, name_of_doc, title, video_url)
        await update.message.reply_document("output_doc.docx", caption="Вот!")


    else:
        await update.message.reply_text("Данный адрес не является ссылкой на youtube видео. Повторите снова.")

async def error(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f'Update {update} caused error {context.error}')

if __name__ == '__main__':
    dotenv.load_dotenv(".env")
    BOT_TOKEN = os.environ.get("BOT_TOKEN")
    BOT_USERNAME = os.environ.get("BOT_USERNAME")
    print(BOT_TOKEN)
    app = Application.builder().token(BOT_TOKEN).build()

    # Commands
    app.add_handler(CommandHandler('start', start_command))
    app.add_handler(CommandHandler('help', help_command))

    # Messages
    app.add_handler(MessageHandler(filters.TEXT, handle_message))

    # Errors
    app.add_error_handler(error)

    print('Загрузка...')
    app.run_polling(poll_interval=3)