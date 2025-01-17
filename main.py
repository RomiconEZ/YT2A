import os
import re
from enum import Enum
from urllib.parse import parse_qs, urlparse

import dotenv
from telegram import InputMediaDocument, Message, Update
from telegram.ext import (Application, CommandHandler, ContextTypes,
                          MessageHandler, filters)


class State(Enum):
    wait_for_youtube_link = 0  # Пользователь ещё не отправил ссылку на видео
    wait_for_article_length = 1  # Пользователь не отправил длину статьи
    wait_for_annotation_length = 2  # Пользователь не отправил


from ML import get_all_articles


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["state"] = State.wait_for_youtube_link
    await update.message.reply_text(
        "Привет! Чтобы получить статью по youtube видео, отправь мне ссылку на него!"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Сервис принимает ссылку на youtube видео и возвращает docx файл, содержащий статью, созданную по данному видео."
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = context.user_data.get("state", State.wait_for_youtube_link)

    match state:
        case State.wait_for_youtube_link:
            url = update.message.text

            youtube_regex = (
                r"(https?://)?(www\.)?"
                "(youtube|youtu|youtube-nocookie)\.(be|com)/"
                "(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})"
            )

            if re.match(youtube_regex, url):
                context.user_data["state"] = State.wait_for_article_length

                # msg: Message = await update.message.reply_text("Ожидайте")

                url_data = urlparse(url)
                query = parse_qs(url_data.query)
                video_id = ""
                if "v" in query.keys():
                    video_id = query["v"][0]
                else:
                    video_id = url_data.geturl().split("/")[-1]

                context.user_data["video_id"] = video_id

                await update.message.reply_text(
                    "Отправьте максимальное количество слов в статье. Если ограничений нет, то отправьте -1."
                )
            else:
                context.user_data["state"] = State.wait_for_youtube_link
                await update.message.reply_text(
                    "Данный адрес не является ссылкой на youtube видео. Попробуйте снова."
                )

        case State.wait_for_article_length:
            article_length = update.message.text

            if (
                article_length.isnumeric()
                or article_length[1:].isnumeric()
                and article_length[0] == "-"
            ):
                article_length = int(article_length)
                if article_length == -1:
                    context.user_data["annotation_length"] = 150000
                else:
                    context.user_data["annotation_length"] = article_length
            else:
                context.user_data["state"] = State.wait_for_article_length
                await update.message.reply_text(
                    "Длина статьи должна быть положительным числом либо -1 в случае отсутствия ограничений. Попробуйте снова."
                )
                return

            context.user_data["state"] = State.wait_for_annotation_length
            await update.message.reply_text(
                "Отправьте максимальное количество слов в аннотации. Если ограничений нет, то отправьте -1."
            )

        case State.wait_for_annotation_length:
            annotation_length = update.message.text

            if (
                annotation_length.isnumeric()
                or annotation_length[1:].isnumeric()
                and annotation_length[0] == "-"
            ):
                annotation_length = int(annotation_length)
                if annotation_length == -1:
                    context.user_data["annotation_length"] = 150000
                else:
                    context.user_data["annotation_length"] = annotation_length
            else:
                context.user_data["state"] = State.wait_for_annotation_length
                await update.message.reply_text(
                    "Длина аннотации должна быть положительным числом либо -1 в случае отсутствия ограничений. Попробуйте снова."
                )
                return

            msg: Message = await update.message.reply_text(
                "Ваш запрос был принят. Ожидайте."
            )

            video_url = f'https://www.youtube.com/watch?v={context.user_data.get("video_id", "")}'
            name_of_doc, name_of_gen_doc, annotation = get_all_articles(
                video_url,
                word_limit_annotation=context.user_data.get(
                    "annotation_length", 150000
                ),
                limit_article_length=context.user_data.get("article_length", 150000),
            )
            await msg.delete()
            media_group = []
            media_group.append(
                InputMediaDocument(
                    open(name_of_doc, "rb"), caption="Краткий пересказ:\n" + annotation
                )
            )
            media_group.append(InputMediaDocument(open(name_of_gen_doc, "rb")))
            await update.message.reply_media_group(media_group)
            context.user_data["state"] = State.wait_for_youtube_link


async def error(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Возникла неожиданная ошибка. Пожалуйста, повторите запрос ещё раз через некоторое время."
    )
    print(f"При обновлении {update} произошла ошибка: {context.error}")


if __name__ == "__main__":
    dotenv.load_dotenv(".env")
    BOT_TOKEN = os.environ.get("BOT_TOKEN")
    BOT_USERNAME = os.environ.get("BOT_USERNAME")
    app = Application.builder().token(BOT_TOKEN).build()

    # Commands
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))

    # Messages
    app.add_handler(MessageHandler(filters.TEXT, handle_message))

    # Errors
    app.add_error_handler(error)

    print("Загрузка...")
    app.run_polling(poll_interval=3)
